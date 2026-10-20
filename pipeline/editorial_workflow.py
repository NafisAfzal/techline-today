"""Editorial lifecycle with explicit preconditions and a fail-closed authority boundary.

The lifecycle makes every editorial step explicit and auditable without becoming a
second content store. It records decisions and evidence references; it never
asserts that a human approved something.

No authenticated editor identity exists in this project, so ``APPROVED``,
``PUBLICATION_ELIGIBLE`` and ``PUBLISHED`` raise :class:`AuthorityUnavailable` and a
ledger that claims them is rejected on load. ``FACT_CHECKED`` requires a recorded
checklist reference so a check cannot be declared without evidence. Correction,
retraction and archival stay reachable: they reduce reader-facing claims.

Timestamps are kept distinct on purpose. Publication, first observation, last
verification, last editorial update and build time are separate facts, and a
recent build never promotes research or evergreen material into current news.
"""

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, ConfigDict, Field, StrictStr, field_validator, model_validator

from pipeline.filesystem import confined_file
from pipeline.models import Contract
from pipeline.review_governance import bounded_json, digest, writer_lock
from pipeline.storage import atomic_json

ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent
LEDGER = ".cache/phase6/editorial-decisions.json"
MAX_EVENTS = 500

LIFECYCLE = (
    "DISCOVERED", "SOURCE_VALIDATED", "RIGHTS_ELIGIBLE", "DRAFT_READY", "FACT_CHECK_PENDING",
    "FACT_CHECKED", "EDITORIAL_APPROVAL_PENDING", "APPROVED", "PUBLICATION_ELIGIBLE",
    "PUBLISHED", "CORRECTED", "RETRACTED", "ARCHIVED",
)

TRANSITIONS: dict[str, frozenset[str]] = {
    "DISCOVERED": frozenset({"SOURCE_VALIDATED", "RETRACTED"}),
    "SOURCE_VALIDATED": frozenset({"RIGHTS_ELIGIBLE", "RETRACTED"}),
    "RIGHTS_ELIGIBLE": frozenset({"DRAFT_READY", "RETRACTED"}),
    "DRAFT_READY": frozenset({"FACT_CHECK_PENDING", "RETRACTED"}),
    "FACT_CHECK_PENDING": frozenset({"FACT_CHECKED", "DRAFT_READY", "RETRACTED"}),
    "FACT_CHECKED": frozenset({"EDITORIAL_APPROVAL_PENDING", "DRAFT_READY", "RETRACTED"}),
    "EDITORIAL_APPROVAL_PENDING": frozenset({"DRAFT_READY", "RETRACTED", "ARCHIVED"}),
    "APPROVED": frozenset({"PUBLICATION_ELIGIBLE", "DRAFT_READY", "RETRACTED"}),
    "PUBLICATION_ELIGIBLE": frozenset({"PUBLISHED", "DRAFT_READY", "RETRACTED", "ARCHIVED"}),
    "PUBLISHED": frozenset({"CORRECTED", "RETRACTED", "ARCHIVED"}),
    "CORRECTED": frozenset({"RETRACTED", "ARCHIVED"}),
    "RETRACTED": frozenset({"ARCHIVED"}),
    "ARCHIVED": frozenset(),
}

AUTHORITY_GATED = frozenset({"APPROVED", "PUBLICATION_ELIGIBLE", "PUBLISHED"})

# Operators can reduce exposure without waiting for an unavailable approval.
for _state in tuple(TRANSITIONS):
    if _state != "ARCHIVED":
        TRANSITIONS[_state] |= frozenset({"ARCHIVED"})
    if _state not in {"CORRECTED", "RETRACTED", "ARCHIVED"}:
        TRANSITIONS[_state] |= frozenset({"CORRECTED"})

# Kinds are derived from source evidence, never from how recently a build ran.
StoryKind = Literal["NEWS", "RESEARCH", "EVERGREEN", "REFERENCE", "SECURITY_ADVISORY", "OFFICIAL_RELEASE"]
CURRENT_NEWS_KINDS = frozenset({"NEWS"})

State = Literal[
    "DISCOVERED", "SOURCE_VALIDATED", "RIGHTS_ELIGIBLE", "DRAFT_READY", "FACT_CHECK_PENDING",
    "FACT_CHECKED", "EDITORIAL_APPROVAL_PENDING", "APPROVED", "PUBLICATION_ELIGIBLE",
    "PUBLISHED", "CORRECTED", "RETRACTED", "ARCHIVED",
]

Digest = Annotated[StrictStr, Field(pattern=r"^[a-f0-9]{64}$")]


class AuthorityUnavailable(ValueError):
    """No authenticated editor identity exists; approval stays blocked."""


def plain(value: str) -> str:
    import unicodedata

    if not value.strip() or any(unicodedata.category(char) in {"Cc", "Cf", "Cs"} for char in value):
        raise ValueError("Review text must be nonblank and free of control characters")
    return value


Label = Annotated[StrictStr, Field(min_length=1, max_length=200), AfterValidator(plain)]
Note = Annotated[StrictStr, Field(min_length=1, max_length=2000), AfterValidator(plain)]


class EditorialModel(Contract):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DateEvidence(EditorialModel):
    """Distinct clocks for one story. Conflating them is the defect this prevents."""

    published_at: datetime | None = None
    first_seen_at: datetime | None = None
    last_verified_at: datetime | None = None
    last_editorial_update: datetime | None = None
    build_time: datetime | None = None

    @field_validator("*", mode="before")
    @classmethod
    def aware(cls, value):
        if value is None:
            return None
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise ValueError("Editorial timestamps require an explicit timezone")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def ordering(self):
        # First observation may precede the publisher timestamp when feeds backfill,
        # but verification and editorial update can never precede first observation.
        if self.first_seen_at and self.last_verified_at and self.last_verified_at < self.first_seen_at:
            raise ValueError("Inconsistent dates: verified_before_observation")
        if self.first_seen_at and self.last_editorial_update and self.last_editorial_update < self.first_seen_at:
            raise ValueError("Inconsistent dates: edited_before_observation")
        return self


def date_violations(evidence: DateEvidence, kind: StoryKind, now: datetime) -> list[str]:
    """Machine-checkable date integrity. Unknown dates are reported, never filled."""
    findings = []
    if evidence.published_at is None:
        findings.append("publication_date_unknown")
    else:
        if evidence.published_at > now:
            findings.append("publication_date_in_future")
        if evidence.build_time and abs((evidence.build_time - evidence.published_at).total_seconds()) <= 1:
            findings.append("publication_date_matches_build_time")
        if kind not in CURRENT_NEWS_KINDS and evidence.build_time:
            if abs((evidence.build_time - evidence.published_at).total_seconds()) <= 1:
                findings.append("non_news_treated_as_current")
    if evidence.first_seen_at is None:
        findings.append("first_observed_unknown")
    return findings


def classify_kind(*, source_type: str, source_class: str, editorial_kind: str = "news") -> StoryKind:
    """Deterministic kind from source metadata. Age and build time are irrelevant."""
    if editorial_kind == "security-advisory":
        return "SECURITY_ADVISORY"
    if source_type == "arxiv":
        return "RESEARCH"
    if source_type == "github_document":
        return "EVERGREEN"
    if source_type == "github_releases":
        return "OFFICIAL_RELEASE"
    return "NEWS" if source_class in {"primary", "independent"} else "REFERENCE"


class DecisionRecord(EditorialModel):
    from_state: State
    to_state: State
    actor: Label
    at: datetime
    reason: Note
    story_id: Digest
    fact_check_reference: Label | None = None
    correction_reference: Note | None = None
    retraction_reason: Note | None = None
    from_record_sha256: Digest | None = None
    to_record_sha256: Digest | None = None

    @field_validator("at", mode="before")
    @classmethod
    def aware(cls, value):
        if isinstance(value, str) and re.fullmatch(
                r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})", value):
            value = datetime.fromisoformat(value)
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise ValueError("Decision timestamps require an explicit timezone")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def preconditions(self):
        if self.to_state == "FACT_CHECKED" and not self.fact_check_reference:
            raise ValueError("A completed fact check requires a recorded checklist reference")
        if self.to_state == "CORRECTED" and not self.correction_reference:
            raise ValueError("A correction requires a recorded correction reference")
        if self.to_state == "RETRACTED" and not self.retraction_reason:
            raise ValueError("A retraction requires a recorded reason")
        return self


class EditorialEvent(EditorialModel):
    sequence: int = Field(ge=1, strict=True)
    previous_sha256: Digest
    decision: DecisionRecord
    event_sha256: Digest


class EditorialLedger(EditorialModel):
    version: Literal[1] = 1
    events: list[EditorialEvent] = Field(default_factory=list, max_length=MAX_EVENTS)
    head_sha256: Digest = "0" * 64

    @field_validator("version", mode="before")
    @classmethod
    def strict_version(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("Unsupported editorial ledger version; strict integer 1 required")
        return value

    @model_validator(mode="after")
    def chain(self):
        previous = "0" * 64
        states: dict[str, str] = {}
        last_at = None
        for index, event in enumerate(self.events, 1):
            payload = event.model_dump(mode="json", exclude={"event_sha256"})
            if event.sequence != index or event.previous_sha256 != previous or digest(payload) != event.event_sha256:
                raise ValueError("Corrupted or reordered editorial ledger")
            decision = event.decision
            story = decision.story_id
            state = states.get(story, "DISCOVERED")
            if decision.to_state in AUTHORITY_GATED:
                raise ValueError("Ledger claims an editorial approval this project cannot authorise")
            if decision.from_state != state or decision.to_state not in TRANSITIONS[state]:
                raise ValueError("Illegal editorial transition in ledger")
            if last_at and decision.at < last_at:
                raise ValueError("Editorial decision timestamps must be monotonic")
            states[story] = decision.to_state
            last_at = decision.at
            previous = event.event_sha256
        if self.head_sha256 != previous:
            raise ValueError("Editorial ledger head mismatch")
        return self


def ledger_path(root=ROOT):
    return confined_file(root, LEDGER)


def load_ledger(root=ROOT) -> EditorialLedger:
    path = ledger_path(root)
    if not path.exists():
        return EditorialLedger()
    return EditorialLedger.model_validate(bounded_json(path))


def story_state(ledger: EditorialLedger, story_id: str) -> str:
    state = "DISCOVERED"
    for event in ledger.events:
        if event.decision.story_id == story_id:
            state = event.decision.to_state
    return state


def record_authenticated(envelope, *, trust_pin, now, root=ROOT, mode="production"):
    """Authenticated extension of this lifecycle; an actor/status field never suffices.

    Stored signatures remain inactive until an independent current checkpoint is
    supplied to the publication verifier. The legacy draft ledger is preserved.
    """
    from pipeline.authority.ledger import append
    from pipeline.authority.protocol import Decision
    if not isinstance(envelope.payload, Decision) or envelope.payload.binding.workflow != "editorial":
        raise ValueError("Expected a signed editorial lifecycle decision")
    return append(root, envelope, trust_pin, now, mode=mode)


def record(story_id, from_state, to_state, *, actor, now, reason, fact_check_reference=None,
           correction_reference=None, retraction_reason=None, root=ROOT):
    """Append one editorial decision. Approval states are refused, not configurable."""
    story_id = story_identity(story_id=story_id, source_ids=[])
    if to_state not in TRANSITIONS:
        raise ValueError("Unknown editorial state")
    if to_state in AUTHORITY_GATED:
        raise AuthorityUnavailable(
            f"{to_state} requires an authenticated editor identity that this project does not have")
    if from_state not in TRANSITIONS:
        raise ValueError("Unknown editorial state")
    if to_state not in TRANSITIONS[from_state]:
        raise ValueError(f"Illegal editorial transition {from_state} -> {to_state}")
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError("Decision requires an aware clock")
    decision = DecisionRecord(from_state=from_state, to_state=to_state, actor=actor, at=now, reason=reason,
                              story_id=story_id, fact_check_reference=fact_check_reference,
                              correction_reference=correction_reference, retraction_reason=retraction_reason)
    ledger = load_ledger(root)
    payload = {"sequence": len(ledger.events) + 1, "previous_sha256": ledger.head_sha256,
               "decision": decision.model_dump(mode="json")}
    event = EditorialEvent(**payload, event_sha256=digest(payload))
    with writer_lock(confined_file(root, ".cache/phase6/editorial-decisions.lock")):
        current = load_ledger(root)
        if current.head_sha256 != event.previous_sha256:
            raise ValueError("Editorial ledger changed underneath this write; retry with fresh evidence")
        atomic_json(ledger_path(root), EditorialLedger.model_validate({
            "version": 1,
            "events": [*[e.model_dump(mode="json") for e in current.events], event.model_dump(mode="json")],
            "head_sha256": event.event_sha256}))
    return event


def story_identity(*, story_id: str, source_ids: list[str], canonical_url: str | None = None) -> str:
    return hashlib.sha256(json.dumps(
        {"story": story_id, "sources": sorted(source_ids), "url": canonical_url},
        sort_keys=True).encode()).hexdigest()


PRE_APPROVAL = frozenset({"DISCOVERED", "SOURCE_VALIDATED", "RIGHTS_ELIGIBLE", "DRAFT_READY",
                         "FACT_CHECK_PENDING", "FACT_CHECKED"})


def review_queue(ledger: EditorialLedger | None = None, root=ROOT) -> list[dict]:
    """Reviewer-facing queue. Every row states what is still missing."""
    ledger = ledger if ledger is not None else load_ledger(root)
    rows = {}
    for event in ledger.events:
        decision = event.decision
        entry = rows.setdefault(decision.story_id, {"story_id": decision.story_id, "state": "DISCOVERED",
                                                    "transitions": 0, "last_actor": None, "last_at": None})
        entry["state"] = decision.to_state
        entry["transitions"] += 1
        entry["last_actor"] = decision.actor
        entry["last_at"] = decision.at.isoformat()
    queue = []
    for entry in rows.values():
        blockers = []
        if entry["state"] in AUTHORITY_GATED:
            blockers.append("approval_requires_authenticated_editor")
        elif entry["state"] in PRE_APPROVAL:
            blockers.append("awaiting_editorial_decision")
        elif entry["state"] == "EDITORIAL_APPROVAL_PENDING":
            blockers.append("awaiting_named_editor_approval")
        elif entry["state"] in {"RETRACTED", "ARCHIVED"}:
            blockers.append("withdrawn_from_publication")
        queue.append({**entry, "blockers": sorted(set(blockers)), "publication_allowed": False})
    return sorted(queue, key=lambda row: row["story_id"])


def report(root=ROOT) -> dict:
    ledger = load_ledger(root)
    by_state: dict[str, int] = {}
    for event in ledger.events:
        by_state[event.decision.to_state] = by_state.get(event.decision.to_state, 0) + 1
    return {"version": 1, "event_count": len(ledger.events), "decisions_by_state": dict(sorted(by_state.items())),
            "queue": review_queue(ledger, root), "authority_gated_states": sorted(AUTHORITY_GATED),
            "publication_allowed": False,
            "note": "Approval requires an owner-appointed editor; no automated process can reach APPROVED."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("report", "queue", "head"))
    args = parser.parse_args()
    try:
        if args.action == "report":
            result = report()
        elif args.action == "queue":
            result = {"queue": review_queue()}
        else:
            result = load_ledger().model_dump(mode="json")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, TypeError) as error:
        print(json.dumps({"status": "refused", "error_type": type(error).__name__,
                          "publication_allowed": False}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
