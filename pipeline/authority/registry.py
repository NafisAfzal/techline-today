"""Owner-pinned administrative provenance and least-privilege reviewer grants."""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import StrictBool, model_validator

from pipeline.authority.protocol import (
    POLICY,
    Admin,
    AuthorityError,
    Decision,
    Identifier,
    Key,
    Model,
    ResearchDecision,
    instant,
    verify_signature,
)


class TrustPin(Model):
    """Public bootstrap supplied by the trusted operator, never by a review ledger.

    A synthetic pin is usable only in explicitly synthetic API/CLI verification.
    The default production loader has no pin and cannot enroll an owner.
    """

    version: Literal[1]
    owner_id: Identifier
    ledger_id: Identifier
    environment: Literal["synthetic", "production"]
    policy_version: Literal["phase8-authority-v1"]
    synthetic: StrictBool
    root_key: Key

    @model_validator(mode="after")
    def provenance(self):
        if self.synthetic != (self.environment == "synthetic"):
            raise ValueError("Trust pin environment and synthetic marker disagree")
        return self


@dataclass
class Registry:
    pin: TrustPin
    root_key: Key = field(init=False)
    revision: int = 0
    reviewers: dict = field(default_factory=dict)
    keys: dict = field(default_factory=dict)
    grants: dict = field(default_factory=dict)
    revoked_grants: set = field(default_factory=set)
    revoked_sources: set = field(default_factory=set)
    root_history: set = field(default_factory=set)

    def __post_init__(self):
        self.root_key = self.pin.root_key
        self.root_history.add(self.root_key.key_id)

    def common(self, payload):
        if (payload.environment != self.pin.environment or payload.ledger_id != self.pin.ledger_id
                or payload.policy_version != POLICY):
            raise AuthorityError("context", "Environment, journal or policy does not match the trusted pin")

    def owner(self, envelope):
        payload = envelope.payload
        self.common(payload)
        if payload.signer_id != self.pin.owner_id or payload.key_id != self.root_key.key_id:
            raise AuthorityError("owner", "Only the independently pinned current owner root can administer")
        if not instant(self.root_key.active_at) <= instant(payload.issued_at) < instant(self.root_key.expires_at):
            raise AuthorityError("owner_expired", "Owner root was not active at this event")
        verify_signature(envelope, self.root_key.public_key)

    def apply(self, envelope):
        payload = envelope.payload
        if not isinstance(payload, Admin):
            raise AuthorityError("admin", "Expected an administrative record")
        self.owner(envelope)
        op, target = payload.operation, payload.target_id
        key = payload.key
        if key is not None:
            if key.key_id in self.keys or key.key_id in self.root_history:
                raise AuthorityError("key_reuse", "Key IDs cannot be rebound or reused")
            if not instant(key.active_at) <= instant(payload.issued_at) < instant(key.expires_at):
                raise AuthorityError("key_time", "Replacement key must be active at appointment")
            if envelope.proof is None:
                raise AuthorityError("possession", "Enrollment and rotation require replacement-key possession proof")
            verify_signature(envelope, key.public_key, proof=True)
        elif envelope.proof is not None:
            raise AuthorityError("proof", "Unexpected possession proof on this operation")
        if op == "enroll":
            if target == self.pin.owner_id or target in self.reviewers:
                raise AuthorityError("reviewer", "Reviewer ID already exists or collides with the owner")
            self.reviewers[target] = {"key_id": key.key_id, "suspended": False, "revoked": False}
            self.keys[key.key_id] = {"reviewer_id": target, "key": key, "disabled": False}
        elif op == "grant":
            self.member(target)
            grant = payload.grant
            if grant.grant_id in self.grants or grant.grant_id in self.revoked_grants:
                raise AuthorityError("grant_reuse", "Grant IDs are immutable and cannot be reused")
            if instant(grant.active_at) < instant(payload.issued_at):
                raise AuthorityError("grant_time", "A grant cannot retroactively authorize earlier decisions")
            self.grants[grant.grant_id] = (target, grant)
        elif op == "revoke_grant":
            if target not in self.grants:
                raise AuthorityError("grant", "Cannot revoke an unknown grant")
            self.revoked_grants.add(target)
        elif op in {"retire_key", "revoke_key"}:
            if target not in self.keys:
                raise AuthorityError("key", "Cannot retire an unknown reviewer key")
            self.keys[target]["disabled"] = True
        elif op in {"suspend_reviewer", "revoke_reviewer"}:
            member = self.member(target, allow_suspended=True)
            member["suspended" if op == "suspend_reviewer" else "revoked"] = True
        elif op == "reinstate_reviewer":
            member = self.member(target, allow_suspended=True)
            if not member["suspended"]:
                raise AuthorityError("reviewer", "Only an explicitly suspended reviewer can be reinstated")
            member["suspended"] = False
        elif op == "rotate_key":
            member = self.member(target, allow_suspended=True)
            self.keys[member["key_id"]]["disabled"] = True
            member["key_id"] = key.key_id
            self.keys[key.key_id] = {"reviewer_id": target, "key": key, "disabled": False}
        elif op == "revoke_source":
            self.revoked_sources.add(target)
        elif op == "rotate_root":
            if target != self.pin.owner_id:
                raise AuthorityError("owner", "Root rotation cannot change owner identity")
            self.root_key = key
            self.root_history.add(key.key_id)
        self.revision += 1

    def member(self, reviewer_id, *, allow_suspended=False):
        member = self.reviewers.get(reviewer_id)
        if member is None or member["revoked"] or member["suspended"] and not allow_suspended:
            raise AuthorityError("reviewer", "Reviewer is unknown, suspended or revoked")
        return member

    def authorize(self, envelope, at, *, current=True):
        payload = envelope.payload
        if not isinstance(payload, Decision):
            raise AuthorityError("decision", "Expected a signed reviewer decision")
        self.common(payload)
        member = self.member(payload.signer_id)
        key_entry = self.keys.get(payload.key_id)
        if (key_entry is None or key_entry["reviewer_id"] != payload.signer_id
                or member["key_id"] != payload.key_id or key_entry["disabled"]):
            raise AuthorityError("key", "Signing key is unknown, retired, revoked or belongs to another reviewer")
        key = key_entry["key"]
        if not instant(key.active_at) <= at < instant(key.expires_at):
            raise AuthorityError("key_expired", "Signing key is not currently active")
        record = self.grants.get(payload.grant_id)
        if record is None or payload.grant_id in self.revoked_grants or record[0] != payload.signer_id:
            raise AuthorityError("grant", "Missing, revoked or wrong-parent reviewer grant")
        grant = record[1]
        if not instant(grant.active_at) <= at < instant(grant.expires_at):
            raise AuthorityError("grant_expired", "Reviewer authorization is not active")
        binding = payload.binding
        if (payload.role != grant.role or payload.decision not in grant.decisions
                or binding.source_id not in grant.sources
                or binding.story_id not in grant.stories and "*" not in grant.stories
                or binding.language not in grant.languages or binding.workflow not in grant.workflows):
            raise AuthorityError("scope", "Decision exceeds the appointed role, source, story, language or workflow")
        if (isinstance(payload, ResearchDecision) and binding.publication_scope == "metadata-extractive:en-bn"
                and payload.role in {"source-rights", "publisher"} and not {"en", "bn"} <= set(grant.languages)):
            raise AuthorityError("scope", "Bilingual rights/publication approval requires an English and Bangla grant")
        if payload.registry_revision != self.revision:
            raise AuthorityError("registry_revision", "Review belongs to an older administrative registry revision")
        if current and not instant(payload.issued_at) <= at < instant(payload.expires_at):
            raise AuthorityError("decision_expired", "Decision is future-dated or expired")
        verify_signature(envelope, key.public_key)
