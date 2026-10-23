"""One signature-checked journal, existing lifecycle projections and sticky denials."""

import hashlib
import os
from dataclasses import dataclass, field
from typing import Literal

from pydantic import Field, model_validator

from pipeline.authority.protocol import (
    DENIALS,
    RESEARCH_STAGES,
    ZERO,
    Admin,
    AuthorityError,
    Checkpoint,
    Decision,
    Digest,
    Envelope,
    Model,
    ResearchDecision,
    canonical,
    clock,
    instant,
    read_envelope,
    stamp,
)
from pipeline.authority.registry import Registry, TrustPin
from pipeline.filesystem import atomic_bytes, confined_file
from pipeline.generation import assert_stable, bounded_file, writer
from pipeline.strict_json import strict_json

JOURNAL = ".cache/authority/journal.json"
STOP = ".cache/authority/STOP_PUBLICATION"
MAX_BYTES = 8_000_000


class Event(Model):
    sequence: int = Field(ge=1, le=2000)
    previous_sha256: Digest
    record: Envelope
    event_sha256: Digest


class Journal(Model):
    version: Literal[1]
    events: list[Event] = Field(max_length=2000)
    head_sha256: Digest

    @model_validator(mode="after")
    def chain(self):
        if type(self.version) is not int:
            raise ValueError("Journal version must be integer 1")
        previous = ZERO
        for index, event in enumerate(self.events, 1):
            raw = event.model_dump(mode="json", exclude={"event_sha256"})
            if (event.sequence != index or event.previous_sha256 != previous
                    or hashlib.sha256(canonical(raw)).hexdigest() != event.event_sha256):
                raise ValueError("Corrupt, truncated, forked or reordered journal")
            if event.record.payload.previous_sha256 != previous or event.record.payload.sequence != index:
                raise ValueError("Signature does not bind this exact journal position")
            previous = event.event_sha256
        if self.head_sha256 != previous:
            raise ValueError("Journal head mismatch")
        return self


def empty():
    return Journal(version=1, events=[], head_sha256=ZERO)


def journal_bytes(journal):
    return canonical(journal.model_dump(mode="json")) + b"\n"


def decode_journal(data):
    raw = data.removesuffix(b"\n")
    value = strict_json(raw, max_bytes=MAX_BYTES, max_depth=16, max_tokens=500_000,
                        max_container_items=20_000)
    journal = Journal.model_validate(value)
    if raw != canonical(journal.model_dump(mode="json")):
        raise AuthorityError("encoding", "Journal is not canonical UTF-8 JSON")
    return journal


def load(root):
    path = confined_file(root, JOURNAL)
    return decode_journal(bounded_file(path, MAX_BYTES)) if path.exists() else empty()


def binding_id(binding):
    return hashlib.sha256(canonical(binding.model_dump(mode="json"))).hexdigest()


def lifecycle(binding):
    """Use the actual project state machines, adding only authenticated edges."""
    if binding.workflow == "research":
        stages = ("RESEARCH_REVIEW_REQUIRED", *(RESEARCH_STAGES if binding.language == "en" else
                                                ("RESEARCH_BANGLA_APPROVED",)))
        transitions = {state: frozenset(stages[1:index + 2]) for index, state in enumerate(stages)}
        return stages[0], transitions
    if binding.workflow == "editorial":
        from pipeline.editorial_workflow import TRANSITIONS
        transitions = dict(TRANSITIONS)
        transitions["EDITORIAL_APPROVAL_PENDING"] |= frozenset({"APPROVED"})
        return "DISCOVERED", transitions
    if binding.workflow == "translation":
        from pipeline.translation_governance import TRANSITIONS
        transitions = dict(TRANSITIONS)
        transitions["LANGUAGE_REVIEW_PENDING"] |= frozenset({"NATIVE_REVIEW_COMPLETE"})
        return "NOT_TRANSLATED", transitions
    if binding.workflow == "source":
        from pipeline.source_onboarding import TRANSITIONS
        return "DISCOVERED", TRANSITIONS
    return "REVIEW_REQUIRED", {
        "REVIEW_REQUIRED": frozenset({"RIGHTS_APPROVED", "RIGHTS_REJECTED", "RIGHTS_REVOKED"}),
        "RIGHTS_APPROVED": frozenset({"RIGHTS_REJECTED", "RIGHTS_REVOKED"}),
        "RIGHTS_REJECTED": frozenset(), "RIGHTS_REVOKED": frozenset(),
    }


@dataclass
class VerifiedHistory:
    registry: Registry
    journal: Journal
    states: dict = field(default_factory=dict)
    decisions: list = field(default_factory=list)
    by_id: dict = field(default_factory=dict)
    withdrawn: set = field(default_factory=set)
    research_challenges: set = field(default_factory=set)

    def state(self, binding):
        initial, _ = lifecycle(binding)
        return self.states.get((self.registry.revision, binding_id(binding)), initial)

    def blocked(self, binding):
        if binding.source_id in self.registry.revoked_sources:
            return "source_authorization_revoked"
        for envelope in self.decisions:
            d = envelope.payload
            if d.decision not in DENIALS:
                continue
            b = d.binding
            same_story = b.story_id == binding.story_id
            if b.workflow == "source" and b.source_id == binding.source_id:
                return "source_suspended_or_revoked"
            if b.workflow == "rights" and same_story and b.source_id == binding.source_id:
                return "rights_rejected_or_revoked"
            if b.workflow == "translation" and same_story and binding.language == b.language:
                return "translation_withdrawn"
            if b.workflow == "editorial" and same_story:
                if d.decision != "CORRECTED" or b.content_sha256 == binding.content_sha256:
                    return "story_withdrawn_or_superseded"
            if b.workflow == "research" and same_story and b.source_id == binding.source_id:
                return "research_authorization_revoked"
        return None

    def active(self, binding, decision, at):
        if self.blocked(binding):
            return None
        for envelope in reversed(self.decisions):
            payload = envelope.payload
            if (payload.binding == binding and payload.decision == decision
                    and payload.record_id not in self.withdrawn):
                try:
                    self.registry.authorize(envelope, clock(at))
                except AuthorityError:
                    return None
                return payload.record_id
        return None

    def apply_decision(self, envelope):
        d = envelope.payload
        self.registry.authorize(envelope, instant(d.issued_at), current=False)
        if (d.binding.workflow == "research") != isinstance(d, ResearchDecision):
            raise AuthorityError("workflow", "Research workflow requires a typed research decision")
        research_names = {*RESEARCH_STAGES, "RESEARCH_BANGLA_APPROVED", "RESEARCH_REVOKED"}
        if not isinstance(d, ResearchDecision) and d.decision in research_names:
            raise AuthorityError("workflow", "Research decisions cannot enter another workflow")
        if isinstance(d, ResearchDecision):
            from pipeline.research_approval import verify_review_checkpoint
            verify_review_checkpoint(self, d, instant(d.issued_at), historical=True)
        if envelope.proof is not None:
            raise AuthorityError("proof", "Reviewer decisions cannot carry administrative possession proofs")
        if d.binding.workflow != "research" and d.binding.language != (
                "bn" if d.binding.workflow == "translation" else "en"):
            raise AuthorityError("language", "Decision language does not match this workflow")
        initial, transitions = lifecycle(d.binding)
        state_key = (d.registry_revision, binding_id(d.binding))
        current = self.states.get(state_key, initial)
        if d.from_state != current:
            raise AuthorityError("previous_state", "Decision does not match the actual prior lifecycle state")
        denial = d.decision in DENIALS
        if not denial and (self.blocked(d.binding) or d.to_state not in transitions.get(current, frozenset())):
            raise AuthorityError("transition", "Illegal, stale or withdrawn approval transition")
        if not denial:
            ordered_states = list(transitions)
            if (ordered_states.index(d.to_state) < ordered_states.index(current)
                    or isinstance(d, ResearchDecision) and d.to_state == current):
                # Returning to a review stage supersedes all later approvals.
                # A fresh native/factual review cannot revive an older publisher
                # decision merely because its signature has not expired.
                cutoff = ordered_states.index(d.to_state)
                self.withdrawn.update(previous.payload.record_id for previous in self.decisions
                    if previous.payload.binding == d.binding
                    and previous.payload.to_state in ordered_states
                    and ordered_states.index(previous.payload.to_state) >= cutoff)
        if denial and d.decision not in {"RIGHTS_REJECTED", "RIGHTS_REVOKED"}:
            # Risk reduction need not wait for a positive lifecycle prerequisite.
            allowed = {"editorial": {"CORRECTED", "RETRACTED", "ARCHIVED", "REJECTED", "SUSPENDED",
                                       "REVOKED", "WITHDRAWN"},
                       "translation": {"WITHDRAWN", "TRANSLATION_WITHDRAWN", "TRANSLATION_REJECTED"},
                       "source": {"SUSPENDED", "REVOKED"}, "rights": set(), "research": {"RESEARCH_REVOKED"}}
            if d.decision not in allowed[d.binding.workflow]:
                raise AuthorityError("workflow", "Denial is outside this workflow")
        if d.decision in {"RIGHTS_REJECTED", "RIGHTS_REVOKED"} and d.binding.workflow != "rights":
            raise AuthorityError("workflow", "Rights denial requires the rights workflow")
        if d.decision == "CORRECTED" and d.supersedes is None:
            raise AuthorityError("supersedes", "Correction requires the decision it supersedes")
        if d.supersedes is not None:
            previous = self.by_id.get(d.supersedes)
            if (previous is None or not isinstance(previous.payload, Decision)
                    or previous.payload.binding != d.binding):
                raise AuthorityError("supersedes", "Superseded record does not belong to this exact evidence binding")
            self.withdrawn.add(d.supersedes)
        self.states[state_key] = d.to_state
        self.decisions.append(envelope)


def replay(journal, pin, at, *, mode="production"):
    at = clock(at)
    pin = TrustPin.model_validate(pin.model_dump(mode="json"))
    if mode not in {"production", "synthetic"}:
        raise AuthorityError("mode", "Unknown verification mode")
    if mode == "production" and (pin.synthetic or pin.environment != "production"):
        raise AuthorityError("synthetic", "Synthetic trust is forbidden in production verification")
    if mode == "synthetic" and not pin.synthetic:
        raise AuthorityError("synthetic", "Demonstration mode cannot use a production trust root")
    # Revalidate caller-mutated Pydantic objects too.
    journal = decode_journal(journal_bytes(journal))
    history = VerifiedHistory(Registry(pin), journal)
    last_at = None
    for event in journal.events:
        record = event.record
        payload = record.payload
        issued = instant(payload.issued_at)
        if issued > at or last_at is not None and issued < last_at:
            raise AuthorityError("ordering", "Journal contains a future or nonmonotonic timestamp")
        if payload.record_id in history.by_id:
            raise AuthorityError("duplicate", "Decision and administrative record IDs must be globally unique")
        if isinstance(payload, Admin):
            history.registry.apply(record)
        elif isinstance(payload, Decision):
            history.apply_decision(record)
        else:
            raise AuthorityError("checkpoint", "Checkpoints are external anchors, not journal events")
        history.by_id[payload.record_id] = record
        last_at = issued
    return history


@dataclass(frozen=True)
class Anchor:
    """Expected digest/challenge must come independently, not from a backup."""

    envelope: bytes
    expected_sha256: str
    expected_challenge: str
    custody: object | None = None


@dataclass(frozen=True)
class CheckpointComparison:
    """Outcome of comparing one trusted checkpoint against the replayed local journal.

    Pure inspection: no clock, no I/O and no signature check. The Phase 8
    anchor verifier and the Phase 10 external-checkpoint verifier share this so
    rollback detection has exactly one implementation.
    """

    matched: bool
    code: str
    detail: str
    evidence: dict


def compare_checkpoint(history, cp) -> CheckpointComparison:
    """Compare a trusted checkpoint against the replayed local journal.

    A checkpoint is *current* only when the local journal head, event count and
    registry revision agree with it exactly. Everything else is a named,
    separately reportable defect rather than one generic rollback verdict.
    """
    journal = history.journal
    events = journal.events
    evidence = {"checkpoint_event_count": cp.event_count, "local_event_count": len(events),
                "checkpoint_head_sha256": cp.head_sha256, "local_head_sha256": journal.head_sha256,
                "checkpoint_registry_revision": cp.registry_revision,
                "local_registry_revision": history.registry.revision}
    if cp.registry_revision != history.registry.revision:
        return CheckpointComparison(False, "registry_mismatch",
                                    "The trust registry revision differs from the checkpointed revision",
                                    evidence)
    if cp.previous_sha256 != cp.head_sha256 or cp.sequence != cp.event_count + 1:
        return CheckpointComparison(False, "checkpoint_malformed",
                                    "The checkpoint does not describe its own journal position", evidence)
    if cp.event_count > len(events):
        return CheckpointComparison(False, "journal_revision_regression",
                                    "The local journal is shorter than the trusted checkpoint; "
                                    "the local state was rolled back", evidence)
    if cp.event_count == len(events):
        if cp.head_sha256 != journal.head_sha256:
            return CheckpointComparison(False, "journal_hash_mismatch",
                                        "The local journal head differs from the trusted checkpoint head",
                                        evidence)
        return CheckpointComparison(True, "matched",
                                    "The local journal head matches the trusted checkpoint", evidence)
    # The local journal is longer. It is continuous with the trusted checkpoint
    # only when the checkpointed prefix chains to the same head digest.
    prefix = ZERO
    for index, event in enumerate(events[:cp.event_count], 1):
        if event.sequence != index or event.previous_sha256 != prefix:
            return CheckpointComparison(False, "incomplete_history",
                                        "The local journal history is not continuous with the trusted "
                                        "checkpoint", evidence)
        prefix = event.event_sha256
    if prefix != cp.head_sha256:
        return CheckpointComparison(False, "incomplete_history",
                                    "The local journal does not extend the trusted checkpoint head", evidence)
    return CheckpointComparison(False, "checkpoint_not_current",
                                "The trusted checkpoint does not cover the current local journal head",
                                evidence)


def verify_local_anchor(history, anchor, at):
    """Signature/position only. Cannot establish independent checkpoint custody."""
    if anchor is None:
        raise AuthorityError("checkpoint_missing", "An independently trusted current checkpoint is required")
    if hashlib.sha256(anchor.envelope.removesuffix(b"\n")).hexdigest() != anchor.expected_sha256:
        raise AuthorityError("checkpoint_digest", "Checkpoint differs from the independently trusted digest")
    envelope = read_envelope(anchor.envelope)
    cp = envelope.payload
    if not isinstance(cp, Checkpoint) or envelope.proof is not None:
        raise AuthorityError("checkpoint", "Expected a signed owner checkpoint")
    history.registry.owner(envelope)
    if not instant(cp.issued_at) <= clock(at) < instant(cp.expires_at):
        raise AuthorityError("checkpoint_expired", "Checkpoint is stale or future-dated")
    if history.journal.events and instant(cp.issued_at) < instant(history.journal.events[-1].record.payload.issued_at):
        raise AuthorityError("checkpoint_time", "Checkpoint predates its claimed history")
    if (cp.head_sha256 != history.journal.head_sha256 or cp.previous_sha256 != cp.head_sha256
            or cp.event_count != len(history.journal.events) or cp.sequence != cp.event_count + 1
            or cp.registry_revision != history.registry.revision):
        comparison = compare_checkpoint(history, cp)
        raise AuthorityError("rollback", "Journal is truncated, ahead of, or forked from the trusted "
                                         f"checkpoint ({comparison.detail})")
    if cp.challenge != anchor.expected_challenge:
        raise AuthorityError("checkpoint_challenge", "Checkpoint is not for this independent publication challenge")
    if not instant(history.registry.root_key.active_at) <= clock(at) < instant(history.registry.root_key.expires_at):
        raise AuthorityError("owner_expired", "Current owner root has expired")
    return envelope


def verify_anchor(history, anchor, at):
    envelope = verify_local_anchor(history, anchor, at)
    if not history.registry.pin.synthetic:
        from pipeline.authority.manual_custodian import ManualCustodyProof, configured_proof

        proof = anchor.custody or configured_proof(os.getcwd())
        if not isinstance(proof, ManualCustodyProof):
            raise AuthorityError("independent_freshness_unverified",
                               "A digest and challenge do not authenticate an independent custodian's current state; "
                               "a separately provisioned custody operation is required")
        proof.verify(history, anchor, at)
    return envelope


def append(root, envelope, pin, at, *, mode="production"):
    envelope = read_envelope(canonical(envelope.model_dump(mode="json")))
    payload = envelope.payload
    # A STOP_PUBLICATION marker is an exposure barrier, not just a report flag.
    # Risk-reducing denials remain possible, but no new positive content decision
    # may enter the journal while the marker is present.
    if (isinstance(payload, Decision) and payload.decision not in DENIALS
            and confined_file(root, STOP).exists()):
        raise AuthorityError("emergency_hold",
                             "An emergency publication stop is present; positive decisions are frozen "
                             "until owner-reviewed recovery")
    with writer(root):
        assert_stable(root)
        journal = load(root)
        updated, event = stage(journal, envelope, pin, at, mode=mode)
        data = journal_bytes(updated)
        if len(data) > MAX_BYTES:
            raise AuthorityError("capacity", "Journal capacity reached; preserve history and plan owner-reviewed archival")
        atomic_bytes(confined_file(root, JOURNAL), data)
    return event


def stage(journal, envelope, pin, at, *, mode="production"):
    """Verify a proposed transaction without writing or activating any approval."""
    payload = envelope.payload
    reducing = (isinstance(payload, Decision) and payload.decision in DENIALS or
                isinstance(payload, Admin) and payload.operation in {
                    "revoke_grant", "retire_key", "revoke_key", "suspend_reviewer", "revoke_reviewer",
                    "revoke_source"})
    if not reducing:
        if not instant(payload.issued_at) <= clock(at) < instant(payload.expires_at):
            raise AuthorityError("expired", "A new positive transaction must still be within its signed validity period")
        before = replay(journal, pin, at, mode=mode)
        if isinstance(payload, Decision):
            before.registry.authorize(envelope, clock(at))
            if isinstance(payload, ResearchDecision):
                from pipeline.research_approval import verify_review_checkpoint
                verify_review_checkpoint(before, payload, clock(at))
        else:
            owner_key = before.registry.root_key
            if not instant(owner_key.active_at) <= clock(at) < instant(owner_key.expires_at):
                raise AuthorityError("owner_expired", "Expired owner root cannot issue fresh authority")
            if payload.key and not instant(payload.key.active_at) <= clock(at) < instant(payload.key.expires_at):
                raise AuthorityError("key_expired", "New reviewer/root key is already expired")
    if payload.previous_sha256 != journal.head_sha256 or payload.sequence != len(journal.events) + 1:
        raise AuthorityError("conflict", "Journal changed; inspect and prepare a new decision against its current head")
    raw = {"sequence": payload.sequence, "previous_sha256": journal.head_sha256,
           "record": envelope.model_dump(mode="json")}
    event = Event(**raw, event_sha256=hashlib.sha256(canonical(raw)).hexdigest())
    updated = Journal(version=1, events=[*journal.events, event], head_sha256=event.event_sha256)
    replay(updated, pin, at, mode=mode)
    return updated, event


def emergency_hold(root, reason, at):
    """Always reduces exposure, including while credentials/history are unavailable.

    This irreversible local stop is deliberately separate from positive evidence.
    It is written before any journal work and never automatically cleared.
    """
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 2000:
        raise AuthorityError("reason", "A bounded nonempty hold reason is required")
    payload = {"status": "STOP_PUBLICATION", "at": stamp(at),
               "reason_sha256": hashlib.sha256(reason.encode("utf-8")).hexdigest()}
    path = confined_file(root, STOP)
    # Preserve the first denial; additional detailed signed denials can be appended.
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Existence is the barrier, including a killed/partial marker write.
        with path.open("xb") as stream:
            stream.write(canonical(payload) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        return {"status": "STOP_PUBLICATION", "already_held": True}
    return payload
