"""Offline owner/reviewer preparation. No keys, signatures, enrollment or writes."""

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from pydantic import Field, StrictStr, model_validator

from pipeline.authority.custody import protected_file
from pipeline.authority.protocol import (
    POLICY,
    PROTOCOL,
    Digest,
    Grant,
    Identifier,
    Key,
    Model,
    Timestamp,
    decode64,
    fingerprint,
    instant,
)
from pipeline.filesystem import regular_path
from pipeline.generation import bounded_file
from pipeline.operations import ceremony
from pipeline.operations.redaction import refusal, scan_payload
from pipeline.strict_json import strict_json

PrivateText = Annotated[StrictStr, Field(min_length=1, max_length=500)]
_GUIDANCE = {
    "device_custody": "This device and signing storage are controlled by the intended owner",
    "encrypted_backup": "A separately held encrypted backup and recovery procedure actually exist",
    "backup_restore_rehearsal": "A separately authorized offline restore/decryption rehearsal succeeded",
    "fingerprint_second_channel": "The public fingerprint was compared over another authenticated channel",
    "clock_checked": "Current UTC time was compared against an independently trusted clock",
    "revocation_contact": "A working suspension/revocation contact and incident procedure are documented",
    "witness_or_documented_single_owner": "A witness checked the ceremony or sole-owner limitations are documented",
    "independent_checkpoint_custody": "The checkpoint custodian has genuinely separate control and authentication",
    "final_owner_approval_required": "I understand provisioning, appointment and publication require separate owner approval",
}


class ReviewerProposal(Model):
    version: Literal[1]
    protocol: Literal["techline.editorial.authority/v1"]
    policy_version: Literal["phase8-authority-v1"]
    environment: Literal["production"]
    ledger_id: Identifier
    reviewer_id: Identifier
    intended_identity: PrivateText
    key: Key
    grant: Grant
    issued_at: Timestamp
    expires_at: Timestamp
    revocation_contact: PrivateText
    conflict_of_interest_disclosure: PrivateText
    acceptance_evidence_sha256: Digest | None

    @model_validator(mode="after")
    def bounded(self):
        issued, expiry = instant(self.issued_at), instant(self.expires_at)
        if not 0 < (expiry - issued).total_seconds() <= 90 * 86400:
            raise ValueError("Preparation expires within 90 days")
        if ("*" in self.grant.stories or instant(self.grant.active_at) < issued
                or instant(self.grant.expires_at) > expiry
                or instant(self.key.active_at) > instant(self.grant.active_at)
                or instant(self.key.expires_at) < instant(self.grant.expires_at)):
            raise ValueError("Use exact items and a grant bounded by packet and key validity")
        return self


def reviewer_template(role):
    packet = ceremony.appointment_packet(role)
    return {"status": "TEMPLATE", "proposal": {
        "version": 1, "protocol": PROTOCOL, "policy_version": POLICY, "environment": "production",
        "ledger_id": None, "reviewer_id": None, "intended_identity": None, "key": None,
        "grant": None, "issued_at": None, "expires_at": None, "revocation_contact": None,
        "conflict_of_interest_disclosure": None, "acceptance_evidence_sha256": None},
        "existing_role_guidance": packet,
        "completion_schema": "python -m pipeline.operations.onboarding schema reviewer",
        "appointment_valid": False, "publication_allowed": False}


def reviewer_packet(value, *, environment_id, ledger_id, now=None):
    packet = ReviewerProposal.model_validate(value)
    at = now or datetime.now(UTC)
    blockers = []
    if packet.environment != environment_id or packet.ledger_id != ledger_id:
        blockers.append("Packet must match the explicitly verified environment and ledger")
    if not instant(packet.issued_at) <= at < instant(packet.expires_at):
        blockers.append("Packet has not started or has expired")
    if packet.acceptance_evidence_sha256 is None:
        blockers.append("Obtain and retain the reviewer's acceptance and custody evidence privately")
    return {"version": 1, "status": "BLOCKED" if blockers else "PASS", "blockers": blockers,
            "unsigned_proposal": packet.model_dump(mode="json"),
            "public_key_fingerprint": packet.key.key_id,
            "owner_requests": [
                {"operation": "enroll", "target_id": packet.reviewer_id,
                 "key": packet.key.model_dump(mode="json"), "grant": None},
                {"operation": "grant", "target_id": packet.reviewer_id, "key": None,
                 "grant": packet.grant.model_dump(mode="json")}],
            "human_checks": ["Independently verify intended identity, expertise, consent and conflicts",
                             "Compare displayed public fingerprint through an authenticated second channel",
                             "Reviewer retains encrypted key and proves possession using the existing protocol",
                             "Owner personally approves each exact unsigned enrollment and grant request",
                             "Refresh the independent checkpoint after all signed administrative changes"],
            "revocation": {"lost_reviewer_key": "Suspend reviewer; owner revokes or rotates the affected key",
                           "compromise": "Emergency STOP, preserve evidence, owner-reviewed recovery",
                           "lost_owner_key": "No automatic reset; recover separately held encrypted backup or "
                                             "use a newly reviewed external trust-establishment ceremony"},
            "appointment_valid": False, "production_credentials_created": False,
            "publication_allowed": False,
            "note": "PASS means an unsigned preparation packet is complete. Typed identity and acceptance "
                    "digest are declarations, not authenticated identity, consent or appointment."}


def public_fingerprint(path):
    raw = bounded_file(regular_path(path), 16_000)
    if raw.startswith(b"-----BEGIN PUBLIC KEY-----"):
        public = load_pem_public_key(raw)
        if not isinstance(public, Ed25519PublicKey):
            raise ValueError("Only Ed25519 public keys are supported")
        return fingerprint(public.public_bytes_raw())
    return fingerprint(decode64(raw.decode("ascii").strip(), 32))


def inspect_encrypted_file(path, root):
    checked = protected_file(path, root)
    raw = bounded_file(checked, 32_000)
    if (not raw.startswith(b"-----BEGIN ENCRYPTED PRIVATE KEY-----\n")
            and not raw.startswith(b"-----BEGIN ENCRYPTED PRIVATE KEY-----\r\n")):
        raise ValueError("Use encrypted PKCS8 PEM; plaintext signing files are refused")
    if not raw.rstrip().endswith(b"-----END ENCRYPTED PRIVATE KEY-----"):
        raise ValueError("Encrypted PEM is incomplete")
    # Never decrypt, echo, serialize or persist encrypted key bytes here.
    return hashlib.sha256(raw).hexdigest()


def owner_preflight(root, proposal, *, environment_id, ledger_id, public_file=None,
                    expected_fingerprint=None, custody_file=None, backup_file=None, now=None):
    result = ceremony.preflight(root, proposal, expected_environment=environment_id, now=now)
    blockers = result["blockers"]
    if environment_id != "production" or result["ledger_id"] != ledger_id:
        blockers.append("Existing authority protocol requires production and the explicitly intended ledger")
    checks = {}
    if public_file is None or expected_fingerprint is None:
        blockers.append("Supply public key and independently obtained expected fingerprint")
    else:
        displayed = public_fingerprint(public_file)
        result["public_key_fingerprint"] = displayed
        checks["public_fingerprint"] = "PASS" if displayed == expected_fingerprint else "FAIL"
        if checks["public_fingerprint"] != "PASS":
            blockers.append("Public fingerprint differs from the independently obtained value")
    if custody_file is None or backup_file is None:
        blockers.append("Supply separately held encrypted custody and backup files for local integrity checks")
    else:
        first, second = regular_path(custody_file), regular_path(backup_file)
        if first == second or first.samefile(second):
            blockers.append("Backup must be a separate file; physical independence still needs human verification")
        else:
            matching = inspect_encrypted_file(first, root) == inspect_encrypted_file(second, root)
            checks["encrypted_backup_integrity"] = "PASS" if matching else "FAIL"
            if not matching:
                blockers.append("Encrypted backup bytes differ; privately reconcile before ceremony")
    result.update(status="BLOCKED" if blockers else result["status"], checks=checks,
                  actual_signing_algorithm_verified=False,
                  encrypted_file_public_key_match_verified=False,
                  identity_authenticated=False,
                  note="Read-only preparation. Encrypted PEM framing and byte equality do not prove decryptability "
                       "or key/public-key correspondence. The owner must rehearse decryption, backup restoration "
                       "and signing in a separately authorized private ceremony. No key is generated or installed.")
    return result


def _read(path):
    return strict_json(bounded_file(regular_path(path), 32_000), max_bytes=32_000)


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "Invalid onboarding arguments; use --help.\n")


def main(argv=None):
    parser = _Parser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    sub = parser.add_subparsers(dest="action", required=True)
    owner = sub.add_parser("owner")
    owner.add_argument("--proposal", type=Path)
    owner.add_argument("--environment-id", required=True)
    owner.add_argument("--ledger-id", required=True)
    owner.add_argument("--public-file", type=Path)
    owner.add_argument("--expected-fingerprint")
    owner.add_argument("--custody-file", type=Path)
    owner.add_argument("--backup-file", type=Path)
    owner.add_argument("--interactive", action="store_true")
    reviewer = sub.add_parser("reviewer")
    reviewer.add_argument("--template", metavar="ROLE")
    reviewer.add_argument("--proposal", type=Path)
    reviewer.add_argument("--environment-id", default="production")
    reviewer.add_argument("--ledger-id")
    schema = sub.add_parser("schema")
    schema.add_argument("kind", choices=["reviewer"])
    args = parser.parse_args(argv)
    try:
        if args.action == "schema":
            result = ReviewerProposal.model_json_schema()
        elif args.action == "reviewer":
            result = reviewer_template(args.template) if args.template else reviewer_packet(
                _read(args.proposal), environment_id=args.environment_id, ledger_id=args.ledger_id)
        else:
            proposal = _read(args.proposal) if args.proposal else ceremony.template(
                args.environment_id, args.ledger_id)
            if args.interactive:
                if not sys.stdin.isatty():
                    raise ValueError("Interactive guide requires a terminal")
                confirmations = []
                print("Preparation only. Confirm actual evidence; names and answers prove no identity.", file=sys.stderr)
                for condition in ceremony.CONFIRMATIONS:
                    answer = input(f"{_GUIDANCE[condition]}. Type YES only if personally verified: ")
                    if answer == "YES":
                        confirmations.append(condition)
                proposal = {**proposal, "confirmations": confirmations}
            result = owner_preflight(args.root, proposal, environment_id=args.environment_id,
                                     ledger_id=args.ledger_id, public_file=args.public_file,
                                     expected_fingerprint=args.expected_fingerprint,
                                     custody_file=args.custody_file, backup_file=args.backup_file)
        detections = scan_payload(result)
        if detections:
            result = refusal(detections)
        serialized = json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False)
    except Exception:
        result = {"status": "FAIL", "publication_allowed": False,
                  "note": "Input or custody check failed. Inspect it privately; nothing was granted or written."}
        serialized = json.dumps(result)
    print(serialized)
    return 1 if result.get("status") in {"FAIL", "REFUSED"} else 2 if result.get("status") in {
        "BLOCKED", "INCONCLUSIVE"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
