"""Offline validation and isolated restore of an authority recovery pack.

A recovery pack is a directory that carries the signed authority journal, the
owner trust pin, the source rights policy and an evidence index. It is a
*transport format*, not a trust decision.

The verifier deliberately separates two claims:

* **local consistency** - the pack is readable, complete, continuous, identity
  consistent and free of private-key material; and
* **independent currency** - an independently held checkpoint agrees with it.

A pack that passes every local check is still not "trusted" and not "current".
An independently obtained digest can detect disagreement with a known checkpoint,
but cannot prove that it is the custodian's current head. No current adapter
authenticates that external property, so currency remains BLOCKED.
"""

import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from itertools import islice
from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field

from pipeline.authority.ledger import decode_journal, replay
from pipeline.authority.protocol import MAX_RECORD, AuthorityError, Model
from pipeline.authority.registry import TrustPin
from pipeline.filesystem import confined_file, regular_path
from pipeline.generation import bounded_file
from pipeline.strict_json import strict_json

PACK_FORMAT = "techline.editorial.recovery-pack/v1"
MAX_PACK_BYTES = 64_000_000
# Pack member path -> repository-relative source path.
POLICY_SOURCES = {
    "policy/source-rights.json": "config/source-rights.json",
    "policy/sources.yaml": "config/sources.yaml",
}
REQUIRED_POLICY_FILES = tuple(sorted(POLICY_SOURCES))
ALLOWED_MEMBERS = frozenset((*REQUIRED_POLICY_FILES, "authority/journal.json", "authority/trust-pin.json",
                             "evidence/source-candidates.json", "evidence/index.json"))

PASS, FAIL, BLOCKED, INCONCLUSIVE = "PASS", "FAIL", "BLOCKED", "INCONCLUSIVE"

PRIVATE_KEY_MARKERS = (b"PRIVATE KEY-----", b"BEGIN ENCRYPTED PRIVATE KEY", b"-----BEGIN RSA",
                       b"-----BEGIN EC", b"-----BEGIN OPENSSH", b"ssh-ed25519", b"id_ed25519")


class RecoveryVerification(Model):
    """The verifier's answer for one recovery pack."""

    status: Literal["PASS", "FAIL", "BLOCKED", "INCONCLUSIVE"]
    local_consistency: Literal["PASS", "FAIL", "INCONCLUSIVE"]
    independently_trusted: bool = False
    current: bool = False
    checks: list[dict] = Field(default_factory=list)
    pack_sha256: str | None = None
    trust_statement: str = ""
    publication_allowed: bool = False
    ai_submission_allowed: bool = False

    def check(self, name: str) -> dict | None:
        return next((row for row in self.checks if row["check"] == name), None)


def _check(name, result, message, **evidence) -> dict:
    return {"check": name, "result": result, "detail": message, "evidence": evidence}


def _digest(path: Path) -> str:
    return hashlib.sha256(bounded_file(path, 1_000_000)).hexdigest()


def _pack_files(root: Path) -> list[str]:
    files = []

    def scan(directory):
        with os.scandir(directory) as entries:
            children = list(islice(entries, len(ALLOWED_MEMBERS) + 4))
        if len(children) > len(ALLOWED_MEMBERS) + 1:
            raise ValueError("Unexpected recovery pack content")
        for child in children:
            path = Path(child.path)
            relative = path.relative_to(root).as_posix()
            if child.is_dir(follow_symlinks=False):
                regular_path(path / ".path-check")
                if relative not in {"authority", "policy", "evidence"}:
                    raise ValueError("Unexpected recovery pack directory")
                scan(path)
            else:
                regular_path(path)
                files.append(relative)
            if len(files) > len(ALLOWED_MEMBERS) + 1:
                raise ValueError("Unexpected recovery pack content")
    scan(root)
    return sorted(files)


def _validated_pack(pack: Path) -> tuple[dict, dict[str, bytes]]:
    """Bounded, complete preflight. No path or payload is used before validation."""
    manifest_path = confined_file(pack, "manifest.json")
    manifest = strict_json(bounded_file(manifest_path, 1_000_000), max_bytes=1_000_000,
                           max_depth=16, max_tokens=20000)
    if (not isinstance(manifest, dict) or manifest.get("kind") != PACK_FORMAT
            or type(manifest.get("version")) is not int or manifest["version"] != 1):
        raise ValueError("Unsupported recovery pack format")
    listed = manifest.get("files")
    if not isinstance(listed, list) or not 1 <= len(listed) <= len(ALLOWED_MEMBERS):
        raise ValueError("Recovery pack contains no usable files")
    payloads = {}
    total = 0
    for item in listed:
        if not isinstance(item, dict):
            raise ValueError("Invalid recovery pack member")
        relative = item.get("path")
        if not isinstance(relative, str) or relative not in ALLOWED_MEMBERS:
            raise ValueError("Recovery pack contains an unsafe path or unexpected content")
        if relative in payloads or type(item.get("bytes")) is not int or item["bytes"] < 0:
            raise ValueError("Duplicate or invalid recovery pack member")
        total += item["bytes"]
        if total > MAX_PACK_BYTES:
            raise ValueError("Recovery pack exceeds the aggregate size limit")
        payload = bounded_file(confined_file(pack, relative), item["bytes"])
        if len(payload) != item["bytes"] or hashlib.sha256(payload).hexdigest() != item.get("sha256"):
            raise ValueError(f"Recovery pack member failed integrity: {relative}")
        if any(marker in payload for marker in PRIVATE_KEY_MARKERS):
            raise ValueError(f"Refusing private key material: {relative}")
        payloads[relative] = payload
    if set(_pack_files(pack)) != {*payloads, "manifest.json"}:
        raise ValueError("Recovery pack contains unlisted content")
    if (type(manifest.get("journal_present")) is not bool
            or manifest["journal_present"] != ("authority/journal.json" in payloads)):
        raise ValueError("Recovery pack journal inventory disagrees")
    if not {*REQUIRED_POLICY_FILES, "evidence/index.json"} <= payloads.keys():
        raise ValueError("Required recovery policy or evidence index missing")
    return manifest, payloads


def _write_new_directory(destination: Path, payloads: dict[str, bytes]) -> list[str]:
    # A single mkdir claims this destination. Existing/partial directories stay
    # untouched; interrupted operations require inspection and a new destination.
    regular_path(destination / ".path-check")
    if destination.exists():
        raise ValueError("Restore requires a new empty destination")
    destination.mkdir(parents=True, exist_ok=False)
    restored = []
    for relative, payload in payloads.items():
        target = confined_file(destination, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        restored.append(relative)
    return restored


def build_recovery_pack(root, destination, *, now=None, trust_file=None,
                        checkpoint_bytes: bytes | None = None) -> dict:
    """Export a recovery pack. Requires a new, empty destination directory.

    The pack carries public authority material and policy only. Private keys
    are never exported; if one is found in the source tree the export refuses.
    """
    root = Path(root)
    destination = Path(destination)
    regular_path(root / ".path-check")
    regular_path(destination / ".path-check")
    if destination.exists():
        raise ValueError("Use a new recovery pack directory")
    at = now or datetime.now(UTC)
    files: list[dict] = []
    payloads: dict[str, bytes] = {}

    def include(relative: str, source: Path) -> None:
        payload = bounded_file(regular_path(source), MAX_PACK_BYTES)
        if sum(len(value) for value in payloads.values()) + len(payload) > MAX_PACK_BYTES:
            raise ValueError(f"Recovery pack member exceeds the size limit: {relative}")
        for marker in PRIVATE_KEY_MARKERS:
            if marker in payload:
                raise ValueError(f"Refusing to export private key material: {relative}")
        payloads[relative] = payload
        files.append({"path": relative, "bytes": len(payload),
                      "sha256": hashlib.sha256(payload).hexdigest()})

    journal_present = (root / ".cache/authority/journal.json").is_file()
    if journal_present:
        include("authority/journal.json", root / ".cache/authority/journal.json")
    trust_file = trust_file or os.environ.get("TECHLINE_AUTHORITY_TRUST_FILE")
    if trust_file:
        pin_path = regular_path(Path(trust_file))
        include("authority/trust-pin.json", pin_path)
    for relative, source_relative in POLICY_SOURCES.items():
        source = root / source_relative
        if not source.is_file():
            raise ValueError(f"Required recovery policy file is missing: {source_relative}")
        include(relative, source)
    candidates = root / ".cache/phase6/source-candidates.json"
    if candidates.is_file():
        include("evidence/source-candidates.json", candidates)
    evidence_index = {"version": 1, "created_at": at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                       "note": "Digest index only. A digest reference without the retained private "
                               "evidence body is not evidence of a licence.",
                       "sources": []}
    if candidates.is_file():
        try:
            ledger = strict_json(payloads["evidence/source-candidates.json"], max_bytes=MAX_PACK_BYTES)
            evidence_index["sources"] = [
                {"candidate_id": event.get("candidate_id"),
                 "identity": event.get("identity"),
                 "evidence_sha256": (event.get("transition") or {}).get("evidence_sha256")}
                for event in ledger.get("events", [])]
        except (ValueError, OSError):
            evidence_index["sources"] = []
    index_payload = json.dumps(evidence_index, indent=2, sort_keys=True).encode() + b"\n"
    payloads["evidence/index.json"] = index_payload
    files.append({"path": "evidence/index.json", "bytes": len(index_payload),
                  "sha256": hashlib.sha256(index_payload).hexdigest()})

    manifest = {"version": 1, "kind": PACK_FORMAT,
                "created_at": at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "journal_present": journal_present,
                "files": sorted(files, key=lambda row: row["path"]),
                "contains_private_keys": False,
                "note": "Public authority and policy material only. Independent currency requires an "
                        "externally held checkpoint whose digest was obtained separately."}
    payloads["manifest.json"] = json.dumps(manifest, indent=2, sort_keys=True).encode() + b"\n"
    if sum(map(len, payloads.values())) > MAX_PACK_BYTES:
        raise ValueError("Recovery pack exceeds the aggregate size limit")
    _write_new_directory(destination, payloads)
    return manifest


def restore_recovery_pack(pack: Path, destination: Path) -> list[str]:
    """Restore a pack into an isolated directory. Existing content is never overwritten."""
    pack, destination = Path(pack), Path(destination)
    regular_path(destination / ".path-check")
    if destination.exists():
        raise ValueError("Restore requires a new empty destination")
    _manifest, payloads = _validated_pack(pack)
    return _write_new_directory(destination, payloads)


def verify_recovery_pack(pack, *, expected: dict | None = None, checkpoint_bytes: bytes | None = None,
                         expected_checkpoint_sha256: str | None = None,
                         challenge: str | None = None, now=None) -> RecoveryVerification:
    """Validate a recovery pack offline. Never mutates the pack and never trusts it by itself."""
    pack = Path(pack)
    checks: list[dict] = []
    at = now or datetime.now(UTC)

    # --- 1. structurally readable ------------------------------------------------
    manifest_path = pack / "manifest.json"
    try:
        manifest, _payloads = _validated_pack(pack)
    except (ValueError, OSError):
        return RecoveryVerification(status=FAIL, local_consistency=FAIL, checks=[
            _check("pack_readable", FAIL, "Recovery pack failed bounded structural, path or integrity checks")],
            trust_statement="An unreadable pack proves nothing.")
    checks.append(_check("pack_readable", PASS, "All members passed bounded path, size and digest checks"))

    # --- 2. no private key exposure ---------------------------------------------
    checks.append(_check("no_private_key_exposure", PASS,
                         "No recognized private-key markers in allowlisted public-policy members"))

    # --- 3. journal continuity ----------------------------------------------------
    history = None
    journal_path = pack / "authority/journal.json"
    if not journal_path.is_file():
        checks.append(_check("journal_continuity", INCONCLUSIVE,
                             "The pack contains no authority journal; no continuity can be asserted"))
    else:
        try:
            journal = decode_journal(_payloads["authority/journal.json"])
            checks.append(_check("journal_continuity", PASS,
                                 "The journal chain is continuous and its head matches",
                                 event_count=len(journal.events), head_sha256=journal.head_sha256))
        except (ValueError, OSError, AuthorityError) as error:
            checks.append(_check("journal_continuity", FAIL,
                                 "The journal is corrupt, truncated, forked or reordered",
                                 detail=str(error) if isinstance(error, AuthorityError) else
                                 "Journal structure is invalid"))

    # --- 4. expected identity -----------------------------------------------------
    pin = None
    pin_path = pack / "authority/trust-pin.json"
    if pin_path.is_file():
        try:
            pin = TrustPin.model_validate(strict_json(_payloads["authority/trust-pin.json"],
                                                      max_bytes=MAX_RECORD))
        except (ValueError, OSError) as error:
            checks.append(_check("trust_pin_readable", FAIL, "The packed trust pin is not valid",
                                 detail=type(error).__name__))
    expected = expected or {}
    identity_problems = []
    if expected:
        for key, observed in (("ledger_id", pin.ledger_id if pin else None),
                              ("environment", pin.environment if pin else None),
                              ("owner_id", pin.owner_id if pin else None)):
            if key in expected and expected[key] is not None and observed != expected[key]:
                identity_problems.append(f"{key}={observed!r} expected {expected[key]!r}")
        if "head_sha256" in expected and expected["head_sha256"]:
            observed_head = checks and next((row["evidence"].get("head_sha256")
                                             for row in checks if row["check"] == "journal_continuity"), None)
            if observed_head != expected["head_sha256"]:
                identity_problems.append("journal head differs from the expected head")
    if identity_problems:
        checks.append(_check("expected_identity", FAIL, "The pack does not match the expected identity",
                             problems=identity_problems))
    elif expected:
        checks.append(_check("expected_identity", PASS, "The pack matches the expected identity"))
    else:
        checks.append(_check("expected_identity", INCONCLUSIVE,
                             "No expected identity was supplied, so identity cannot be confirmed"))

    # --- 5. consistent authority state --------------------------------------------
    if pin is None:
        checks.append(_check("authority_state_consistent", INCONCLUSIVE,
                             "No packed trust pin is available to replay the journal"))
    elif not journal_path.is_file():
        checks.append(_check("authority_state_consistent", INCONCLUSIVE,
                             "No journal is available to replay against the packed trust pin"))
    else:
        try:
            journal = decode_journal(_payloads["authority/journal.json"])
            history = replay(journal, pin, at, mode="synthetic" if pin.synthetic else "production")
            checks.append(_check("authority_state_consistent", PASS,
                                 "The journal replays cleanly against the packed trust pin",
                                 registry_revision=history.registry.revision,
                                 event_count=len(history.journal.events)))
        except (ValueError, OSError, TypeError) as error:
            checks.append(_check("authority_state_consistent", FAIL,
                                 "The journal does not replay against the packed trust pin",
                                 detail=error.code if isinstance(error, AuthorityError) else
                                 type(error).__name__))

    # --- 6. required policy data ---------------------------------------------------
    missing_policy = [relative for relative in REQUIRED_POLICY_FILES
                      if not (pack / relative).is_file()]
    policy_error = None
    if not missing_policy:
        try:
            strict_json(_payloads["policy/source-rights.json"], max_bytes=MAX_PACK_BYTES)
            yaml.safe_load(_payloads["policy/sources.yaml"])
        except (ValueError, OSError, yaml.YAMLError) as error:
            policy_error = type(error).__name__
    checks.append(_check("required_policy_present",
                         FAIL if (missing_policy or policy_error) else PASS,
                         "Required rights policy data is missing or unreadable"
                         if (missing_policy or policy_error) else
                         "The rights policy and source configuration are present and readable",
                         missing=missing_policy, error=policy_error))

    # --- 7. evidence index ---------------------------------------------------------
    index_path = pack / "evidence/index.json"
    if not index_path.is_file():
        checks.append(_check("evidence_index_present", INCONCLUSIVE,
                             "The pack carries no evidence index"))
    else:
        try:
            index = strict_json(_payloads["evidence/index.json"], max_bytes=MAX_PACK_BYTES)
            ok = isinstance(index, dict) and index.get("version") == 1
            checks.append(_check("evidence_index_present", PASS if ok else FAIL,
                                 "The evidence index is present and well formed" if ok
                                 else "The evidence index is malformed"))
        except (ValueError, OSError):
            checks.append(_check("evidence_index_present", FAIL, "The evidence index is unreadable"))

    # --- 8. restorable into an isolated location ------------------------------------
    restore_detail = None
    try:
        with tempfile.TemporaryDirectory(prefix="techline-recovery-restore-") as temporary:
            restored = _write_new_directory(Path(temporary) / "restored", _payloads)
            restore_detail = len(restored)
        checks.append(_check("restorable", PASS,
                             "The pack restores into an isolated location with matching digests",
                             restored_members=restore_detail))
    except (ValueError, OSError) as error:
        checks.append(_check("restorable", FAIL, "The pack cannot be restored into an isolated location",
                             detail=type(error).__name__))

    # --- 9. comparison with a trusted checkpoint ------------------------------------
    independently_trusted = False
    current = False
    if checkpoint_bytes is None:
        checks.append(_check("trusted_checkpoint_comparison", BLOCKED,
                             "No independently held checkpoint was supplied, so the pack cannot be "
                             "shown to be trusted or current"))
    else:
        from pipeline.authority.checkpoint import (
            IndependentExpectation,
            read_checkpoint_document,
            verify_external_checkpoint,
        )
        try:
            document = read_checkpoint_document(checkpoint_bytes)
        except AuthorityError as error:
            checks.append(_check("trusted_checkpoint_comparison", FAIL,
                                 "The supplied checkpoint document is malformed", detail=str(error)))
            document = None
        if document is not None:
            expectation = IndependentExpectation(document_sha256=expected_checkpoint_sha256,
                                                 challenge=challenge, source="operator-environment")
            if pin is None:
                checks.append(_check("trusted_checkpoint_comparison", BLOCKED,
                                     "No packed trust pin is available to verify the checkpoint"))
            else:
                result = verify_external_checkpoint(document=document, document_bytes=None,
                                                   expectation=expectation, pin=pin, history=history,
                                                   now=at)
                checks.append(_check("trusted_checkpoint_comparison",
                                     PASS if result.status == PASS else result.status,
                                     result.detail, code=result.code,
                                     trust_level=result.trust_level))
                independently_trusted = result.independently_trusted
                current = result.status == PASS and result.trust_level == "CURRENTLY_TRUSTED"

    local_results = {row["result"] for row in checks if row["check"] != "trusted_checkpoint_comparison"}
    local = FAIL if FAIL in local_results else INCONCLUSIVE if INCONCLUSIVE in local_results else PASS
    results = {row["result"] for row in checks}
    if FAIL in results:
        overall = FAIL
    elif BLOCKED in results:
        overall = BLOCKED
    elif INCONCLUSIVE in results:
        overall = INCONCLUSIVE
    else:
        overall = PASS
    statement = ("Local consistency only. This pack is not an externally trusted checkpoint and "
                 "does not establish currency; independent checkpoint evidence is required.")
    if independently_trusted and current:
        statement = ("Local consistency verified and an independently held checkpoint agrees with "
                     "this pack. This does not by itself authorise publication.")
    elif independently_trusted:
        statement = ("Local consistency verified and the checkpoint was independently authenticated, "
                     "but it does not match this pack's history; currency is not established.")
    if local == FAIL:
        statement = "The pack failed a local consistency check and must not be restored or compared."
    return RecoveryVerification(status=overall, local_consistency=local,
                                independently_trusted=independently_trusted, current=current,
                                checks=checks, trust_statement=statement,
                                pack_sha256=_digest(manifest_path))
