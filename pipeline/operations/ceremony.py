"""Prepare a human ceremony; never generate, select or install signing keys."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import Field

from pipeline.authority.ledger import JOURNAL, STOP
from pipeline.authority.protocol import POLICY, PROTOCOL, Identifier, Model
from pipeline.authority.service import status
from pipeline.filesystem import confined_file

CONFIRMATIONS = (
    "device_custody", "encrypted_backup", "backup_restore_rehearsal", "fingerprint_second_channel",
    "clock_checked", "revocation_contact", "witness_or_documented_single_owner",
    "independent_checkpoint_custody", "final_owner_approval_required",
)


class CeremonyProposal(Model):
    version: Literal[1]
    protocol: Literal["techline.editorial.authority/v1"]
    policy_version: Literal["phase8-authority-v1"]
    environment_id: Identifier
    ledger_id: Identifier
    custody_model: Literal["offline-encrypted-file", "hardware-token"]
    confirmations: list[Literal[
        "device_custody", "encrypted_backup", "backup_restore_rehearsal", "fingerprint_second_channel",
        "clock_checked", "revocation_contact", "witness_or_documented_single_owner",
        "independent_checkpoint_custody", "final_owner_approval_required",
    ]] = Field(max_length=9)


def template(environment_id="proposed-production", ledger_id="proposed-newsroom"):
    return CeremonyProposal(version=1, protocol=PROTOCOL, policy_version=POLICY,
                            environment_id=environment_id, ledger_id=ledger_id,
                            custody_model="offline-encrypted-file", confirmations=[]).model_dump(mode="json")


def preflight(root: Path, proposal=None, *, expected_environment=None, now=None):
    at = now or datetime.now(UTC)
    blocked, unknown = [], []
    authority = status(root, at)
    if authority["status"] != "UNPROVISIONED":
        blocked.append("Existing or invalid authority needs reviewed recovery, not initialization")
    try:
        for name in [JOURNAL, STOP]:
            if confined_file(root, name).exists():
                blocked.append("Existing authority state or emergency hold must be preserved")
    except (ValueError, OSError):
        blocked.append("Authority state path cannot be safely inspected")
    missing = list(CONFIRMATIONS)
    checked = None
    if proposal is None:
        blocked.append("No ceremony proposal supplied")
    else:
        checked = CeremonyProposal.model_validate(proposal)
        missing = sorted(set(CONFIRMATIONS) - set(checked.confirmations))
        if len(checked.confirmations) != len(set(checked.confirmations)):
            blocked.append("Duplicate confirmations are not independent evidence")
        if not expected_environment or checked.environment_id != expected_environment:
            blocked.append("Proposal must match explicitly supplied intended environment identity")
        if checked.custody_model == "hardware-token":
            unknown.append("Hardware signing integration is not implemented or verified")
    if missing:
        blocked.append("Human confirmations remain outstanding")
    result = "BLOCKED" if blocked else "INCONCLUSIVE" if unknown else "READY_FOR_HUMAN_CEREMONY"
    return {"version": 1, "status": result, "authority": authority, "missing_confirmations": missing,
            "blockers": blocked, "unverified": unknown, "protocol": PROTOCOL, "policy_version": POLICY,
            "environment_id": checked.environment_id if checked else None,
            "ledger_id": checked.ledger_id if checked else None,
            "key_custody": checked.custody_model if checked else None,
            "confirmation_provenance": "Caller declarations; physical custody and identity not authenticated",
            "next_action": "Human verifies device, backup, fingerprints, clock and independent custody; "
                           "only the owner can authorize a separate provisioning ceremony",
            "production_credentials_created": False, "reviewers_appointed": False,
            "publication_allowed": False, "external_checkpoint_written": False,
            "note": "Readiness for a human ceremony is not completed provisioning or verified trust."}


def appointment_packet(role):
    from pipeline.authority.protocol import CAPABILITIES

    if role not in CAPABILITIES:
        raise ValueError("Choose an existing scoped reviewer role; owner administration is separate")
    return {"version": 1, "role": role, "permitted_decisions": sorted(CAPABILITIES[role]),
            "identity": None, "source_scope": [], "story_scope": [],
            "language_scope": ["bn"] if role == "native-bn" else ["en"] if role in {
                "english-editor", "fact-checker"} else [],
            "workflow_scope": [], "public_key_fingerprint": None,
            "active_at": None, "expires_at": None, "revocation_contact": None,
            "conflict_of_interest_disclosure": None,
            "requirements": ["Verify real identity and consent outside this file",
                             "Compare fingerprint over a separate authenticated channel",
                             "Verify key possession using existing signed enrollment proof",
                             "Use exact source/story/language scope and bounded UTC expiry",
                             "Owner signs enrollment and grant in the existing authority journal",
                             "Replay current revocations and require independent current checkpoint"],
            "appointment_valid": False, "publication_allowed": False,
            "note": "A completed text packet is not an authenticated reviewer appointment."}
