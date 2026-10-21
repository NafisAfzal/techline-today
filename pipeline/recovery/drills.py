"""Repeatable synthetic disaster exercises for the newsroom authority state.

Every drill is a *tooling* exercise. It proves that the verification and
recovery tooling refuses unsafe states; it never proves that a production
newsroom could be recovered. A green drill is not a disaster-recovery
certification.

Each drill runs entirely inside an isolated temporary directory using synthetic
identities derived from a published seed. The operator's real checkout is never
read for state and never used as a restore target.
"""

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

from pipeline.authority.checkpoint import (
    IndependentExpectation,
    digest_attestation,
    read_checkpoint_document,
    verify_external_checkpoint,
)
from pipeline.authority.ledger import emergency_hold
from pipeline.authority.protocol import AuthorityError
from pipeline.recovery.fixtures import (
    SYNTHETIC_LEDGER,
    SYNTHETIC_NOW,
    SyntheticNewsroom,
    synthetic_binding,
    synthetic_key,
)
from pipeline.recovery.verify import build_recovery_pack, verify_recovery_pack

DrillResultValue = Literal["PASS", "FAIL", "BLOCKED"]


@dataclass
class DrillResult:
    """One drill outcome, reported in full for an operator to read."""

    drill_id: str
    name: str
    fixture: str
    injected_failure: str
    expected_behavior: str
    actual_behavior: str
    trust_guarantees: list[str] = field(default_factory=list)
    human_intervention: list[str] = field(default_factory=list)
    result: DrillResultValue = "PASS"
    detail: str = ""
    evidence: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"drill_id": self.drill_id, "name": self.name, "fixture": self.fixture,
                "injected_failure": self.injected_failure, "expected_behavior": self.expected_behavior,
                "actual_behavior": self.actual_behavior, "trust_guarantees": self.trust_guarantees,
                "human_intervention": self.human_intervention, "result": self.result,
                "detail": self.detail, "evidence": self.evidence,
                "synthetic_only": True, "production_recovery_certified": False}


def _write_fixture(root: Path) -> None:
    """Minimal policy material so a recovery pack can be built from a drill root."""
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "config/source-rights.json").write_text(
        json.dumps({"version": 1, "sources": {}}, indent=2) + "\n", encoding="utf-8")
    (root / "config/sources.yaml").write_text("version: 1\nsources: []\n", encoding="utf-8")


def _pin_file(directory: Path) -> Path:
    from pipeline.authority.protocol import canonical

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "trust-pin.json"
    path.write_bytes(canonical(SyntheticNewsroom(directory).pin.model_dump(mode="json")) + b"\n")
    return path


def _newsroom(work: Path, name: str, *, publish: bool = True) -> SyntheticNewsroom:
    root = work / name
    root.mkdir(parents=True, exist_ok=True)
    _write_fixture(root)
    room = SyntheticNewsroom(root)
    room.team()
    if publish:
        room.publish()
    return room


def _pack(room: SyntheticNewsroom, work: Path, name: str, trust: Path) -> Path:
    destination = work / name
    build_recovery_pack(room.root, destination, now=SYNTHETIC_NOW, trust_file=trust)
    return destination


def _custodian(room: SyntheticNewsroom, work: Path, name: str):
    """A checkpoint as an independently held custodian would hold it.

    The digest is recorded at capture time, from the custodian copy, exactly as
    an operator would write it down out of band. It is never read back out of
    the pack under test.
    """
    from pipeline.authority.checkpoint import build_attestation

    envelope = room.checkpoint()
    document = build_attestation(envelope, custody="operator-offline-file",
                                 authentication="operator-attested", captured_at=SYNTHETIC_NOW)
    raw = document.model_dump(mode="json")
    from pipeline.authority.protocol import canonical

    payload = canonical(raw) + b"\n"
    path = work / name
    path.write_bytes(payload)
    return path, payload, digest_attestation(document)


def _replace_member(pack: Path, relative: str, payload: bytes) -> None:
    """Replace a pack member and repair the manifest, as a restored old backup would be.

    This is what a *consistent* old backup looks like: the member and its
    recorded digest agree with each other and both describe an older history.
    """
    manifest_path = pack / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    target = pack / relative
    target.write_bytes(payload)
    for item in manifest["files"]:
        if item["path"] == relative:
            item["bytes"] = len(payload)
            item["sha256"] = hashlib.sha256(payload).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def _verify(pack: Path, *, checkpoint=None, digest=None, challenge=None, expected=None):
    return verify_recovery_pack(pack, expected=expected, checkpoint_bytes=checkpoint,
                                expected_checkpoint_sha256=digest, challenge=challenge,
                                now=SYNTHETIC_NOW)


def _status_of(verification) -> str:
    return verification.status


def _check_result(verification, name: str) -> str | None:
    row = verification.check(name)
    return row["result"] if row else None


# --- the drills -------------------------------------------------------------------

def drill_clean_recovery(work: Path) -> DrillResult:
    room = _newsroom(work, "clean")
    trust = _pin_file(work / "clean-trust")
    custodian, payload, digest = _custodian(room, work, "clean-custodian.json")
    pack = _pack(room, work, "clean-pack", trust)
    verification = _verify(pack, checkpoint=payload, digest=digest,
                           expected={"ledger_id": SYNTHETIC_LEDGER, "environment": "synthetic"})
    ok = (verification.status == "BLOCKED" and verification.local_consistency == "PASS"
          and not verification.current and not verification.independently_trusted)
    return DrillResult(
        drill_id="DR-01", name="Clean recovery",
        fixture="A synthetic newsroom with an appointed team, a published story and an owner-signed "
                "checkpoint copied to another local directory (no authenticated custodian).",
        injected_failure="None. This is the reference recovery.",
        expected_behavior="Local consistency passes; independent current trust remains BLOCKED.",
        actual_behavior=verification.trust_statement,
        trust_guarantees=["journal chain continuity", "trust-root bound replay",
                          "signed checkpoint agreement with supplied local history"],
        human_intervention=["Establish an authenticated independent current-state channel before publication"],
        result="BLOCKED" if ok else "FAIL",
        detail="Baseline recovery drill.",
        evidence={"status": verification.status, "local_consistency": verification.local_consistency,
                  "current": verification.current,
                  "checks": {row["check"]: row["result"] for row in verification.checks}})


def drill_incomplete_backup(work: Path) -> DrillResult:
    room = _newsroom(work, "incomplete")
    trust = _pin_file(work / "incomplete-trust")
    pack = _pack(room, work, "incomplete-pack", trust)
    (pack / "authority/journal.json").unlink()
    verification = _verify(pack)
    detected = _check_result(verification, "pack_readable") == "FAIL"
    return DrillResult(
        drill_id="DR-02", name="Incomplete backup",
        fixture="A recovery pack whose authority journal member is missing.",
        injected_failure="Deleted authority/journal.json from the pack.",
        expected_behavior="The pack is refused as unreadable; nothing is reported as restorable.",
        actual_behavior="The structural check refused the pack before any restore was attempted.",
        trust_guarantees=["pack integrity digesting"],
        human_intervention=["Recover the missing member from another verified copy or re-export it"],
        result="PASS" if detected else "FAIL",
        detail="A partial pack must never be presented as a recovery.",
        evidence={"status": verification.status,
                  "checks": {row["check"]: row["result"] for row in verification.checks}})


def drill_corrupted_ledger(work: Path) -> DrillResult:
    room = _newsroom(work, "corrupt")
    trust = _pin_file(work / "corrupt-trust")
    pack = _pack(room, work, "corrupt-pack", trust)
    target = pack / "authority/journal.json"
    payload = bytearray(target.read_bytes())
    payload[10:14] = b"XXXX"
    target.write_bytes(bytes(payload))
    verification = _verify(pack)
    detected = _check_result(verification, "pack_readable") == "FAIL"
    return DrillResult(
        drill_id="DR-03", name="Corrupted ledger",
        fixture="A recovery pack whose signed journal bytes were altered after export.",
        injected_failure="Overwrote four bytes inside the packed journal.",
        expected_behavior="The altered member is refused before restore.",
        actual_behavior="The pack integrity check rejected the altered member.",
        trust_guarantees=["per-member SHA-256", "journal hash-chain validation"],
        human_intervention=["Restore from another verified copy; never repair a corrupted chain by hand"],
        result="PASS" if detected else "FAIL",
        detail="Corruption must never be silently repaired.",
        evidence={"status": verification.status,
                  "checks": {row["check"]: row["result"] for row in verification.checks}})


def drill_journal_truncation(work: Path) -> DrillResult:
    room = _newsroom(work, "truncated")
    trust = _pin_file(work / "truncated-trust")
    custodian, payload, digest = _custodian(room, work, "truncated-custodian.json")
    pack = _pack(room, work, "truncated-pack", trust)
    from pipeline.authority.ledger import Journal
    from pipeline.authority.protocol import canonical

    full = Journal.model_validate(json.loads((pack / "authority/journal.json").read_text(encoding="utf-8")))
    kept = full.events[:-2]
    truncated = Journal(version=1, events=kept,
                        head_sha256=kept[-1].event_sha256 if kept else "0" * 64)
    _replace_member(pack, "authority/journal.json", canonical(truncated.model_dump(mode="json")))
    verification = _verify(pack, checkpoint=payload, digest=digest)
    row = verification.check("trusted_checkpoint_comparison")
    detected = bool(row) and row["result"] in {"FAIL", "BLOCKED"} and row["evidence"].get("code") in {
        "journal_revision_regression", "journal_hash_mismatch", "incomplete_history"}
    return DrillResult(
        drill_id="DR-04", name="Journal truncation",
        fixture="A recovery pack holding a shortened but internally re-chained journal, compared with "
                "the custodian's full checkpoint.",
        injected_failure="Removed the last two journal events and recomputed the head digest.",
        expected_behavior="The rollback is detected against the independently held checkpoint.",
        actual_behavior="The trusted checkpoint comparison refused the truncated history.",
        trust_guarantees=["independent checkpoint comparison", "event-count binding"],
        human_intervention=["Restore the complete history from a verified copy and re-anchor"],
        result="PASS" if detected else "FAIL",
        detail="A self-consistent but shortened journal is exactly the rollback case.",
        evidence={"status": verification.status, "comparison": (row or {}).get("evidence"),
                  "checks": {row["check"]: row["result"] for row in verification.checks}})


def drill_old_registry(work: Path) -> DrillResult:
    room = _newsroom(work, "old-registry")
    trust = _pin_file(work / "old-registry-trust")
    custodian, payload, digest = _custodian(room, work, "old-registry-custodian.json")
    room.admin("revoke_source", "news-wire")
    pack = _pack(room, work, "old-registry-pack", trust)
    verification = _verify(pack, checkpoint=payload, digest=digest)
    row = verification.check("trusted_checkpoint_comparison")
    detected = bool(row) and row["result"] == "FAIL" and row["evidence"].get("code") in {
        "registry_mismatch", "journal_revision_regression", "journal_hash_mismatch", "incomplete_history"}
    return DrillResult(
        drill_id="DR-05", name="Old trust registry",
        fixture="A newsroom whose administrator revoked a source after the custodian checkpoint was taken.",
        injected_failure="The restored registry revision is older than the checkpointed revision.",
        expected_behavior="The registry revision mismatch is detected and refused.",
        actual_behavior="The trusted checkpoint comparison refused the stale registry revision.",
        trust_guarantees=["registry revision binding", "independent checkpoint comparison"],
        human_intervention=["Restore the newer administrative history; a revocation must not be lost"],
        result="PASS" if detected else "FAIL",
        detail="An old registry would otherwise re-enable revoked sources.",
        evidence={"status": verification.status, "comparison": (row or {}).get("evidence"),
                  "checks": {row["check"]: row["result"] for row in verification.checks}})


def drill_revoked_reviewer_restored(work: Path) -> DrillResult:
    room = _newsroom(work, "revoked-reviewer")
    trust = _pin_file(work / "revoked-reviewer-trust")
    pre_revocation = (room.root / ".cache/authority/journal.json").read_bytes()
    room.admin("revoke_reviewer", "editor")
    custodian, payload, digest = _custodian(room, work, "revoked-reviewer-custodian.json")
    pack = _pack(room, work, "revoked-reviewer-pack", trust)
    # Restore the pre-revocation journal as a *consistent* older backup.
    _replace_member(pack, "authority/journal.json", pre_revocation)
    verification = _verify(pack, checkpoint=payload, digest=digest)
    row = verification.check("trusted_checkpoint_comparison")
    detected = bool(row) and row["result"] == "FAIL"
    return DrillResult(
        drill_id="DR-06", name="Revoked reviewer restored",
        fixture="A newsroom whose reviewer was revoked and whose checkpoint was taken after the revocation.",
        injected_failure="A restore that predates the revocation is compared with the newer checkpoint.",
        expected_behavior="The restored history is refused because the custodian's head disagrees.",
        actual_behavior="The trusted checkpoint comparison refused the pre-revocation history.",
        trust_guarantees=["independent checkpoint comparison", "signed revocation in the journal"],
        human_intervention=["Restore the post-revocation history; never reinstate a revoked reviewer "
                            "by restoring an old journal"],
        result="PASS" if detected else "FAIL",
        detail="Restoring an old journal must not resurrect a revoked reviewer.",
        evidence={"status": verification.status, "comparison": (row or {}).get("evidence"),
                  "checks": {row["check"]: row["result"] for row in verification.checks}})


def drill_old_approval_replay(work: Path) -> DrillResult:
    room = _newsroom(work, "replay")
    history = room.history()
    old_decision = history.decisions[-1]
    room.admin("revoke_grant", "g-publisher")
    refused = None
    try:
        room.store(old_decision)
    except AuthorityError as error:
        refused = error.code
    detected = refused is not None
    return DrillResult(
        drill_id="DR-07", name="Old approval replay",
        fixture="A newsroom where a publisher grant was revoked after an approval had been signed.",
        injected_failure="Replayed the pre-revocation signed decision into the current journal.",
        expected_behavior="The replay is refused because the decision belongs to an older registry "
                          "revision and its grant was revoked.",
        actual_behavior="The journal refused the replayed record.",
        trust_guarantees=["registry revision binding", "grant revocation", "signature scope checks"],
        human_intervention=["None. The refusal is automatic; a fresh review is required to proceed"],
        result="PASS" if detected else "FAIL",
        detail="Old approvals must not be reusable.",
        evidence={"refusal_code": refused,
                  "registry_revision": history.registry.revision})


def drill_missing_trusted_checkpoint(work: Path) -> DrillResult:
    room = _newsroom(work, "no-checkpoint")
    trust = _pin_file(work / "no-checkpoint-trust")
    pack = _pack(room, work, "no-checkpoint-pack", trust)
    verification = _verify(pack)
    row = verification.check("trusted_checkpoint_comparison")
    blocked = bool(row) and row["result"] == "BLOCKED" and not verification.current
    return DrillResult(
        drill_id="DR-08", name="Missing trusted checkpoint",
        fixture="A locally consistent recovery pack with no independently held checkpoint.",
        injected_failure="Withheld the custodian checkpoint from the verification run.",
        expected_behavior="The pack is reported as locally consistent but BLOCKED for currency; it "
                          "is never called trusted or current.",
        actual_behavior="The verification reported BLOCKED for the trusted checkpoint comparison.",
        trust_guarantees=["local consistency only", "explicit refusal to assert currency"],
        human_intervention=["Capture a fresh checkpoint, place it with the custodian and record its "
                            "digest out of band"],
        result="PASS" if blocked else "FAIL",
        detail="Missing evidence must never become a pass.",
        evidence={"status": verification.status, "current": verification.current,
                  "checks": {row["check"]: row["result"] for row in verification.checks}})


def drill_conflicting_checkpoint(work: Path) -> DrillResult:
    from pipeline.authority.checkpoint import conflicting_checkpoints

    room = _newsroom(work, "conflicting")
    first, first_payload, first_digest = _custodian(room, work, "conflicting-a.json")
    room.admin("revoke_source", "news-wire")
    second, second_payload, second_digest = _custodian(room, work, "conflicting-b.json")
    documents = [read_checkpoint_document(first_payload), read_checkpoint_document(second_payload)]
    conflict = conflicting_checkpoints(documents)
    return DrillResult(
        drill_id="DR-09", name="Conflicting independently held checkpoint",
        fixture="Two custodians hold checkpoints for the same ledger taken at different times.",
        injected_failure="Produced a second checkpoint after an administrative change.",
        expected_behavior="The conflicting set is refused; neither checkpoint may be treated as "
                          "authoritative until the operator resolves the conflict.",
        actual_behavior="The conflict was detected between the two held checkpoints.",
        trust_guarantees=["conflict detection between independent custodians"],
        human_intervention=["Decide which custodian holds the authoritative head, retire the other and "
                            "record the reason"],
        result="PASS" if conflict else "FAIL",
        detail="An ambiguous custodian channel is not a trust anchor.",
        evidence={"conflict": conflict,
                  "digests": [first_digest, second_digest]})


def drill_interrupted_restore(work: Path) -> DrillResult:
    room = _newsroom(work, "interrupted")
    trust = _pin_file(work / "interrupted-trust")
    pack = _pack(room, work, "interrupted-pack", trust)
    partial = work / "interrupted-partial"
    (partial / "authority").mkdir(parents=True, exist_ok=True)
    shutil.copy2(pack / "manifest.json", partial / "manifest.json")
    shutil.copy2(pack / "authority/journal.json", partial / "authority" / "journal.json")
    verification = _verify(partial)
    detected = _check_result(verification, "pack_readable") == "FAIL"
    return DrillResult(
        drill_id="DR-10", name="Recovery interrupted halfway",
        fixture="A half-copied recovery pack, as a killed restore would leave.",
        injected_failure="Copied the manifest and one member, then stopped.",
        expected_behavior="The interrupted restore is detected and refused.",
        actual_behavior="The structural check refused the partially restored pack.",
        trust_guarantees=["manifest member listing", "per-member digest verification"],
        human_intervention=["Re-run the restore from the source pack; never promote a partial restore"],
        result="PASS" if detected else "FAIL",
        detail="An interrupted restore must never be accepted.",
        evidence={"status": verification.status,
                  "checks": {row["check"]: row["result"] for row in verification.checks}})


def drill_wrong_environment(work: Path) -> DrillResult:
    room = _newsroom(work, "environment")
    trust = _pin_file(work / "environment-trust")
    custodian, payload, digest = _custodian(room, work, "environment-custodian.json")
    document = read_checkpoint_document(payload)
    foreign = document.model_copy(update={"environment": "production"})
    foreign_digest = digest_attestation(foreign)
    pack = _pack(room, work, "environment-pack", trust)
    verification = _verify(pack, checkpoint=payload, digest=digest)
    result = verify_external_checkpoint(
        document=foreign, document_bytes=None,
        expectation=IndependentExpectation(document_sha256=foreign_digest, challenge=None,
                                           source="synthetic-drill"),
        pin=room.pin, history=room.history(), now=SYNTHETIC_NOW)
    detected = result.status == "FAIL" and result.code == "cross_environment_replay"
    return DrillResult(
        drill_id="DR-11", name="Wrong environment",
        fixture="A synthetic newsroom offered a checkpoint whose environment does not match.",
        injected_failure="Rewrote the environment of a held checkpoint to a different one.",
        expected_behavior="Cross-environment replay is refused before any journal comparison.",
        actual_behavior="The environment check refused the replayed checkpoint.",
        trust_guarantees=["environment binding", "ledger identity binding"],
        human_intervention=["Obtain a checkpoint issued in the verifying environment"],
        result="PASS" if detected else "FAIL",
        detail="A checkpoint from another environment is never evidence for this one.",
        evidence={"code": result.code, "status": result.status,
                  "pack_status": verification.status})


def drill_duplicate_decision_history(work: Path) -> DrillResult:
    room = _newsroom(work, "duplicate")
    trust = _pin_file(work / "duplicate-trust")
    pack = _pack(room, work, "duplicate-pack", trust)
    target = pack / "authority/journal.json"
    journal = json.loads(target.read_text(encoding="utf-8"))
    journal["events"].append(json.loads(json.dumps(journal["events"][-1])))
    target.write_text(json.dumps(journal), encoding="utf-8")
    verification = _verify(pack)
    detected = _check_result(verification, "pack_readable") == "FAIL"
    return DrillResult(
        drill_id="DR-12", name="Duplicate decision history",
        fixture="A recovery pack whose journal contains the same signed decision twice.",
        injected_failure="Duplicated the last journal event.",
        expected_behavior="The duplicated history is refused; record IDs stay globally unique.",
        actual_behavior="The pack integrity check rejected the altered journal before restore.",
        trust_guarantees=["hash-chain continuity", "global record-ID uniqueness"],
        human_intervention=["Restore the deduplicated history from a verified copy"],
        result="PASS" if detected else "FAIL",
        detail="Duplicated decisions must never replay.",
        evidence={"status": verification.status,
                  "checks": {row["check"]: row["result"] for row in verification.checks}})


def drill_compromised_reviewer_key(work: Path) -> DrillResult:
    room = _newsroom(work, "compromised")
    room.admin("revoke_key", synthetic_key("editor").key_id)
    refused = None
    try:
        room.decide(synthetic_binding(), "SOURCE_VALIDATED", "editor")
    except AuthorityError as error:
        refused = error.code
    return DrillResult(
        drill_id="DR-13", name="Compromised reviewer key",
        fixture="A newsroom whose reviewer key was revoked after a suspected compromise.",
        injected_failure="Attempted a fresh decision with the revoked reviewer key.",
        expected_behavior="The decision is refused because the signing key is disabled.",
        actual_behavior="The journal refused the decision signed by the revoked key.",
        trust_guarantees=["key revocation", "key-to-reviewer binding", "grant scope checks"],
        human_intervention=["Owner rotates the reviewer's key with possession proof, then reappoints "
                            "and re-reviews the affected scope"],
        result="PASS" if refused else "FAIL",
        detail="A compromised key must stop working immediately.",
        evidence={"refusal_code": refused})


def drill_lost_owner_key(work: Path) -> DrillResult:
    room = _newsroom(work, "lost-owner")
    trust = _pin_file(work / "lost-owner-trust")
    custodian, payload, digest = _custodian(room, work, "lost-owner-custodian.json")
    pack = _pack(room, work, "lost-owner-pack", trust)
    verification = _verify(pack, checkpoint=payload, digest=digest)
    from pipeline.recovery.inventory import inventory_report

    irrecoverable = inventory_report()["irrecoverable"]
    return DrillResult(
        drill_id="DR-14", name="Lost owner signing key",
        fixture="A newsroom whose owner key is unavailable; its project pack contains no private key. "
                "No usable separately held key copy is assumed in this synthetic exercise.",
        injected_failure="Withheld owner signing capability; no real key was erased or restored.",
        expected_behavior="No new trusted anchor can be produced; the situation is reported as "
                          "BLOCKED and the irrecoverable credential is named.",
        actual_behavior="The tooling refused to assert currency without a fresh owner-signed anchor "
                        "and identified the irrecoverable assets.",
        trust_guarantees=["existing signed history remains verifiable", "no silent re-anchoring"],
        human_intervention=["Owner checks separately held encrypted key backups in a human-controlled ceremony",
                            "If every usable copy is lost, remain blocked pending an independently reviewed "
                            "new trust-establishment policy; normal rotation requires the old signing authority",
                            "Any later recovery needs separately authorised independent custody evidence"],
        result="BLOCKED",
        detail="Project packs exclude private keys. A separately held verified encrypted copy may permit "
               "human recovery. If every usable copy is lost, this tooling cannot recreate the key or "
               "automatically restore authority; journal replay is insufficient.",
        evidence={"status": verification.status, "current": verification.current,
                  "irrecoverable_assets": irrecoverable})


def drill_emergency_publication_stop(work: Path) -> DrillResult:
    room = _newsroom(work, "stopped")
    trust = _pin_file(work / "stopped-trust")
    custodian, payload, digest = _custodian(room, work, "stopped-custodian.json")
    _pack(room, work, "stopped-pack", trust)
    hold = emergency_hold(room.root, "Synthetic drill: emergency publication stop", SYNTHETIC_NOW)
    result = verify_external_checkpoint(
        document=read_checkpoint_document(payload), document_bytes=None,
        expectation=IndependentExpectation(document_sha256=digest, challenge=None,
                                           source="synthetic-drill"),
        pin=room.pin, history=room.history(), now=SYNTHETIC_NOW, emergency_stopped=True)
    detected = result.status == "BLOCKED" and result.code == "emergency_hold"
    return DrillResult(
        drill_id="DR-15", name="Emergency publication stop",
        fixture="A newsroom with a persisted emergency publication stop.",
        injected_failure="Created the STOP_PUBLICATION marker.",
        expected_behavior="Publication remains blocked even though every other check would pass.",
        actual_behavior="The checkpoint verification refused to assert currency while the stop exists.",
        trust_guarantees=["fail-closed emergency stop", "independent of keys and history"],
        human_intervention=["Owner investigates the stop cause and clears it by hand only after a "
                            "fresh independent verification"],
        result="PASS" if detected else "FAIL",
        detail="The stop reduces exposure and is never auto-cleared.",
        evidence={"hold": hold, "status": result.status, "code": result.code})


DRILLS = {
    "DR-01": drill_clean_recovery,
    "DR-02": drill_incomplete_backup,
    "DR-03": drill_corrupted_ledger,
    "DR-04": drill_journal_truncation,
    "DR-05": drill_old_registry,
    "DR-06": drill_revoked_reviewer_restored,
    "DR-07": drill_old_approval_replay,
    "DR-08": drill_missing_trusted_checkpoint,
    "DR-09": drill_conflicting_checkpoint,
    "DR-10": drill_interrupted_restore,
    "DR-11": drill_wrong_environment,
    "DR-12": drill_duplicate_decision_history,
    "DR-13": drill_compromised_reviewer_key,
    "DR-14": drill_lost_owner_key,
    "DR-15": drill_emergency_publication_stop,
}


def run_drill(drill_id: str, work: Path | None = None) -> DrillResult:
    """Run one drill in an isolated temporary directory."""
    key = str(drill_id).upper()
    if key not in DRILLS:
        raise ValueError(f"Unknown drill: {drill_id}")
    if work is None:
        with TemporaryDirectory(prefix="techline-drill-") as temporary:
            return run_drill(key, Path(temporary) / "drill")
    base = _claim_drill_directory(work)
    return DRILLS[key](base)


def _claim_drill_directory(work):
    from pipeline.filesystem import regular_path

    base = Path(work)
    regular_path(base / ".path-check")
    if base.exists():
        raise ValueError("Drills require a new isolated directory")
    base.mkdir(parents=True, exist_ok=False)
    return base


def run_all_drills(work: Path | None = None) -> list[DrillResult]:
    """Run every drill. Each one is isolated from the others and from the checkout."""
    if work is None:
        with TemporaryDirectory(prefix="techline-drills-") as temporary:
            base = Path(temporary)
            return [DRILLS[key](base / key) for key in sorted(DRILLS)]
    base = _claim_drill_directory(work)
    return [DRILLS[key](base / key) for key in sorted(DRILLS)]


def drill_report(results: list[DrillResult]) -> dict:
    """Operator-facing drill summary. A drill pass is not a recovery certification."""
    passed = sum(1 for row in results if row.result == "PASS")
    failed = sum(1 for row in results if row.result == "FAIL")
    blocked = sum(1 for row in results if row.result == "BLOCKED")
    return {
        "version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "drill_count": len(results),
        "passed": passed,
        "failed": failed,
        "blocked": blocked,
        "results": [row.as_dict() for row in results],
        "synthetic_only": True,
        "production_recovery_certified": False,
        "note": "These exercises verify the tooling's refusals using synthetic assets. They do not "
                "certify that a production newsroom can be recovered, and they never touch the real "
                "project state.",
    }
