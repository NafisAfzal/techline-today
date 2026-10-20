"""Local newsroom tools. No automatic identity provisioning, network or activation."""

import argparse
import getpass
import json
import os
import stat
import sys
import warnings
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from pipeline.authority.ledger import (
    append,
    emergency_hold,
    load,
    replay,
    stage,
)
from pipeline.authority.protocol import (
    MAX_RECORD,
    POLICY,
    PROTOCOL,
    Admin,
    AuthorityError,
    Checkpoint,
    Decision,
    canonical,
    fingerprint,
    read_envelope,
    sign,
    stamp,
)
from pipeline.authority.registry import TrustPin
from pipeline.authority.service import (
    bind_story,
    load_authority,
    source_registry,
    status,
)
from pipeline.filesystem import atomic_bytes, confined_file, regular_path
from pipeline.generation import bounded_file, writer
from pipeline.models import Snapshot
from pipeline.strict_json import strict_json

ROOT = Path(__file__).resolve().parents[2]


def read_json(path):
    return strict_json(bounded_file(regular_path(path), MAX_RECORD), max_bytes=MAX_RECORD)


def snapshot(root):
    return Snapshot.model_validate(strict_json(bounded_file(confined_file(root, "content/generated/snapshot.json"),
                                                          50_000_000), max_bytes=50_000_000))


def policy(root):
    return read_json(confined_file(root, "config/source-rights.json"))["sources"]


def trusted_history(root, now):
    bundle = load_authority(root, allow_stopped=True)
    if bundle is None:
        raise AuthorityError("unprovisioned", "Owner trust root is unprovisioned; use inspect/report/demo safely")
    pin = TrustPin.model_validate(strict_json(bundle.pin_bytes, max_bytes=MAX_RECORD))
    return pin, replay(load(root), pin, now)


def output(root, relative, value):
    name = Path(relative)
    if name.parts[:3] != (".cache", "authority", "outbox") or name.suffix != ".json":
        raise AuthorityError("output", "Write review documents only under .cache/authority/outbox/*.json")
    path = confined_file(root, relative)
    with writer(root):
        if path.exists():
            raise AuthorityError("output_exists", "Preserve the existing document; choose a fresh output name")
        atomic_bytes(path, canonical(value) + b"\n")
    return str(name.as_posix())


def common(history, reviewer_id, key_id, now):
    return dict(protocol=PROTOCOL, version=1, environment=history.registry.pin.environment,
                ledger_id=history.registry.pin.ledger_id, policy_version=POLICY, record_id=uuid4().hex,
                signer_id=reviewer_id, key_id=key_id, issued_at=stamp(now),
                expires_at=stamp(now + timedelta(hours=24)), sequence=len(history.journal.events) + 1,
                previous_sha256=history.journal.head_sha256)


def protected_key(path, root):
    confined_file(root, ".cache/authority/key-boundary-check")
    path = regular_path(Path(path))
    if path.is_relative_to(Path(root).absolute()):
        raise AuthorityError("key_location", "Private signing keys must be kept outside the repository")
    if os.name != "nt" and path.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise AuthorityError("key_permissions", "Private key file must not be accessible to group/other users")
    data = bounded_file(path, 32_000)
    if b"ENCRYPTED PRIVATE KEY" not in data:
        raise AuthorityError("key_encryption", "Use a user-managed encrypted PKCS8 key file")
    if not sys.stdin.isatty() or not sys.stderr.isatty():
        raise AuthorityError("interactive_required", "Signing requires a private interactive terminal; no echoed-input fallback")
    # Password never enters argv, environment, a report, or a public artifact.
    try:
        # isatty() alone does not guarantee echo can be disabled. getpass warns
        # before its echoed fallback; turn that warning into a refusal first.
        with warnings.catch_warnings(action="error", category=getpass.GetPassWarning):
            password = getpass.getpass("Encrypted signing key passphrase: ").encode("utf-8")
    except getpass.GetPassWarning:
        raise AuthorityError("interactive_required", "Terminal cannot guarantee private passphrase input") from None
    private = load_pem_private_key(data, password=password)
    if not isinstance(private, Ed25519PrivateKey):
        raise AuthorityError("algorithm", "Only Ed25519 signing keys are supported")
    return private


def require_confirmation(args, record_id):
    if args.confirm != record_id:
        raise AuthorityError("confirmation", "Inspect the exact payload, then repeat with --confirm RECORD_ID")


def inspect_story(root, story_id):
    edition = snapshot(root)
    found = next((s for s in edition.stories if s.id == story_id), None)
    if found is None:
        raise AuthorityError("story", "Story is not present in the local edition")
    rights = policy(root)
    rows = []
    for sid in found.source_ids:
        source = edition.sources[sid]
        bound = bind_story(found, source, rights, sources=edition.sources)
        rows.append({"source_item_id": sid, "registry_id": source.source_registry_id,
                     "publisher": source.publisher, "canonical_url": source.canonical_url,
                     "kind_from_source": bound.story_kind, "binding": bound.model_dump(mode="json"),
                     "policy": rights.get(source.source_registry_id, {}).get("publication", "ABSENT"),
                     "item_held": source.rights_review is not None})
    return {"story_id": found.id, "headline": found.headline, "edition_mode": edition.mode,
            "sources": rows, "bn_present": "bn" in found.translations,
            "bn_status": found.translations["bn"].review_status if "bn" in found.translations else "ABSENT",
            "authority": status(root, datetime.now(UTC)), "publication_allowed": False}


def execute(args, now):
    root = args.root
    if args.action == "demo":
        from pipeline.authority.demo import demonstrate
        return demonstrate()
    if args.action == "status":
        return status(root, now)
    if args.action == "schema":
        from pipeline.authority.ledger import Journal
        from pipeline.authority.protocol import Envelope, Grant
        model = {"envelope": Envelope, "trust-pin": TrustPin, "journal": Journal, "grant": Grant}[args.type]
        return {"$schema": "https://json-schema.org/draft/2020-12/schema", **model.model_json_schema()}
    if args.action == "hold":
        if args.confirm != "STOP_PUBLICATION":
            raise AuthorityError("confirmation", "Use --confirm STOP_PUBLICATION to create the persistent stop")
        return emergency_hold(root, args.reason, now)
    if args.action == "checkpoint-status":
        from pipeline.authority.service import checkpoint_status
        return checkpoint_status(root, now, max_age_seconds=args.max_age_seconds)
    if args.action == "checkpoint-verify":
        from pipeline.authority.checkpoint import read_checkpoint_document
        from pipeline.authority.service import verify_checkpoint_document
        raw = bounded_file(regular_path(args.input), MAX_RECORD)
        document = read_checkpoint_document(raw)
        return verify_checkpoint_document(root, now, document=document,
                                          expected_sha256=args.expected_sha256, challenge=args.challenge,
                                          max_age_seconds=args.max_age_seconds)
    if args.action == "checkpoint-attest":
        from pipeline.authority.checkpoint import build_attestation, digest_attestation
        envelope = read_envelope(bounded_file(regular_path(args.input), MAX_RECORD))
        document = build_attestation(envelope, custody=args.custody, authentication=args.authentication,
                                     captured_at=now, challenge=args.challenge, notes=args.notes)
        target = output(root, args.output, document.model_dump(mode="json"))
        return {"attestation_document_sha256": digest_attestation(document),
                "checkpoint_sha256": document.checkpoint_sha256,
                "custody": document.trust.custody, "authentication": document.trust.authentication,
                "output": target, "publication_allowed": False,
                "note": "The document is custody evidence only; it becomes trusted only when an "
                        "independently obtained digest accompanies it"}
    if args.action == "inspect":
        return inspect_story(root, args.story)
    if args.action == "queue":
        edition = snapshot(root)
        from pipeline.publication_gate import evaluate
        authority_status = status(root, now)
        bundle = load_authority(root) if authority_status["status"] == "VERIFIED" else None
        rights = policy(root)
        rows = []
        for story in edition.stories:
            review = evaluate(story, edition.sources, rights, authority=bundle, now=now,
                               source_registry=source_registry(root))
            if not review["publication_allowed"]:
                rows.append({"story_id": story.id, "primary_source_id": story.primary_source_id,
                             "native_bn": "pending" if "bn" in story.translations else "English fallback",
                             "denied_dimensions": review["denied_dimensions"]})
        return {"edition_mode": edition.mode, "authority": authority_status, "publication_allowed": False,
                "pending": rows}
    if args.action in {"history", "reviewers"}:
        pin, history = trusted_history(root, now)
        if args.action == "reviewers":
            return {"registry_revision": history.registry.revision, "activation_checked": False,
                    "reviewers": [{"reviewer_id": name, **member,
                                   "grants": [{**grant.model_dump(mode="json"),
                                               "revoked": gid in history.registry.revoked_grants}
                                              for gid, (reviewer_id, grant) in history.registry.grants.items()
                                              if reviewer_id == name]}
                                  for name, member in sorted(history.registry.reviewers.items())],
                    "publication_allowed": False}
        return {"signature_history_verified": True, "activation_checked": False,
                "registry_revision": history.registry.revision, "head_sha256": history.journal.head_sha256,
                "events": [{"sequence": e.sequence, "record_id": e.record.payload.record_id,
                            "signer_id": e.record.payload.signer_id, "kind": e.record.payload.kind,
                            "decision": getattr(e.record.payload, "decision", None),
                            "operation": getattr(e.record.payload, "operation", None)} for e in history.journal.events],
                "publication_allowed": False}
    if args.action in {"report", "validate"}:
        bundle = load_authority(root)
        if args.action == "validate":
            if bundle is None:
                raise AuthorityError("unprovisioned", "Production authority is unprovisioned")
            history = bundle.verify(now)
            return {"status": "VERIFIED", "event_count": len(history.journal.events), "publication_allowed": False}
        from pipeline.publication_gate import evaluate_snapshot
        edition = snapshot(root)
        result = evaluate_snapshot(edition, policy(root), authority=bundle, now=now,
                                   source_registry=source_registry(root))
        return {"authority": status(root, now), "edition_mode": edition.mode, "publication": result,
                "publication_allowed": False,
                "note": "Readiness report only; deployment and owner release approval remain separate"}
    if args.action == "sign":
        value = read_json(args.input)
        types = {"decision": Decision, "admin": Admin, "checkpoint": Checkpoint}
        if not isinstance(value, dict) or value.get("kind") not in types:
            raise AuthorityError("payload", "Expected a prepared typed authority payload")
        payload = types[value["kind"]].model_validate(value)
        if payload.environment != "production":
            raise AuthorityError("synthetic", "Use demo for synthetic identities; this signer has no test fallback")
        require_confirmation(args, payload.record_id)
        private = protected_key(args.key_file, root)
        if fingerprint(private.public_key().public_bytes_raw()) != payload.key_id:
            raise AuthorityError("key", "Signing key does not match the reviewed payload key ID")
        proof = protected_key(args.possession_key_file, root) if args.possession_key_file else None
        envelope = sign(payload, private, possession_key=proof)
        target = output(root, args.output, envelope.model_dump(mode="json"))
        return {"signed_record_id": payload.record_id, "output": target, "publication_allowed": False}
    pin, history = trusted_history(root, now)
    if args.action in {"record", "verify"}:
        envelope = read_envelope(bounded_file(regular_path(args.input), MAX_RECORD))
        stage(history.journal, envelope, pin, now)
        if args.action == "record":
            require_confirmation(args, envelope.payload.record_id)
            append(root, envelope, pin, now)
        return {"record_id": envelope.payload.record_id, "signature_and_scope_valid": True,
                "stored": args.action == "record", "publication_allowed": False,
                "note": "A separately trusted current checkpoint is required for activation"}
    if args.action == "prepare":
        edition = snapshot(root)
        story = next((s for s in edition.stories if s.id == args.story), None)
        if story is None:
            raise AuthorityError("story", "Unknown local story ID")
        source = edition.sources.get(args.source or story.primary_source_id)
        if source is None:
            raise AuthorityError("source", "Unknown cited source ID")
        bound = bind_story(story, source, policy(root), language=args.language, workflow=args.workflow,
                           sources=edition.sources)
        member = history.registry.member(args.reviewer)
        grant_record = history.registry.grants.get(args.grant)
        if grant_record is None or grant_record[0] != args.reviewer:
            raise AuthorityError("grant", "Grant does not belong to this reviewer")
        payload = Decision(**common(history, args.reviewer, member["key_id"], now), kind="decision",
                           role=grant_record[1].role, grant_id=args.grant,
                           registry_revision=history.registry.revision, binding=bound, decision=args.decision,
                           from_state=history.state(bound), to_state=args.decision, evidence=args.evidence,
                           supersedes=args.supersedes)
    elif args.action == "prepare-admin":
        request = read_json(args.input)
        payload = Admin(**common(history, pin.owner_id, history.registry.root_key.key_id, now),
                        kind="admin", role="owner-admin", **request)
    elif args.action == "prepare-checkpoint":
        payload = Checkpoint(**common(history, pin.owner_id, history.registry.root_key.key_id, now),
                             kind="checkpoint", role="owner-admin", head_sha256=history.journal.head_sha256,
                             event_count=len(history.journal.events), registry_revision=history.registry.revision,
                             challenge=args.challenge)
    else:
        raise AuthorityError("action", "Unsupported action")
    target = output(root, args.output, payload.model_dump(mode="json"))
    return {"prepared_record_id": payload.record_id, "signer": payload.signer_id,
            "key_id": payload.key_id, "role": payload.role, "output": target,
            "publication_allowed": False, "note": "Unsigned preparation is not an approval"}


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--root", type=Path, default=ROOT)
    sub = result.add_subparsers(dest="action", required=True)
    for name in ["status", "queue", "history", "reviewers", "report", "validate", "demo"]:
        sub.add_parser(name)
    schema = sub.add_parser("schema")
    schema.add_argument("--type", choices=["envelope", "trust-pin", "journal", "grant"], default="envelope")
    inspect = sub.add_parser("inspect")
    inspect.add_argument("--story", required=True)
    hold = sub.add_parser("hold")
    hold.add_argument("--reason", required=True)
    hold.add_argument("--confirm", required=True)
    prepare = sub.add_parser("prepare")
    for name in ["story", "reviewer", "grant", "decision"]:
        prepare.add_argument("--" + name, required=True)
    prepare.add_argument("--source")
    prepare.add_argument("--workflow", choices=["editorial", "rights", "translation"], default="editorial")
    prepare.add_argument("--language", choices=["en", "bn"], default="en")
    prepare.add_argument("--evidence", action="append", required=True, help="SHA-256 reference; never a private body")
    prepare.add_argument("--supersedes")
    prepare.add_argument("--output", required=True)
    for name in ["prepare-admin", "sign", "record", "verify"]:
        item = sub.add_parser(name)
        item.add_argument("--input", type=Path, required=True)
        if name in {"sign", "record"}:
            item.add_argument("--confirm", required=True)
        if name in {"prepare-admin", "sign"}:
            item.add_argument("--output", required=True)
        if name == "sign":
            item.add_argument("--key-file", type=Path, required=True)
            item.add_argument("--possession-key-file", type=Path)
    cp = sub.add_parser("prepare-checkpoint")
    cp.add_argument("--challenge", required=True)
    cp.add_argument("--output", required=True)
    attest = sub.add_parser("checkpoint-attest")
    attest.add_argument("--input", type=Path, required=True, help="A signed checkpoint envelope JSON")
    attest.add_argument("--output", required=True)
    attest.add_argument("--custody", choices=["local-state-directory", "operator-offline-file",
                                              "protected-git-history", "read-only-mirror", "unknown"],
                        default="operator-offline-file")
    attest.add_argument("--authentication", choices=["none", "operator-attested", "independently-signed"],
                        default="operator-attested")
    attest.add_argument("--challenge")
    attest.add_argument("--notes")
    for name in ("checkpoint-verify", "checkpoint-status"):
        item = sub.add_parser(name)
        if name == "checkpoint-verify":
            item.add_argument("--input", type=Path, required=True)
            item.add_argument("--expected-sha256", dest="expected_sha256",
                              help="Independently obtained digest of the custody document")
            item.add_argument("--challenge")
        item.add_argument("--max-age-seconds", type=int, default=86400,
                          help="Operator freshness policy for the checkpoint")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        data = execute(args, datetime.now(UTC).replace(microsecond=0))
        # ASCII JSON also works through Windows legacy-codepage pipes. Unicode
        # content remains exact JSON escapes rather than failing during output.
        print(json.dumps(data, ensure_ascii=True, indent=2))
        return 0
    except (ValueError, OSError, TypeError, EOFError) as error:
        print(json.dumps({"status": "REFUSED", "code": getattr(error, "code", type(error).__name__),
                          "detail": str(error) if isinstance(error, AuthorityError) else
                          "Malformed input or inaccessible file; inspect schemas, paths and permissions.",
                          "publication_allowed": False}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
