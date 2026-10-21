"""Auditable source-candidate onboarding. Never grants rights or activation.

A candidate is a *proposal* to add a publisher. This module records what was
technically observed, which rights evidence exists and what a human must still
decide. It deliberately cannot approve rights, editorial fit or activation:
those transitions raise ``AuthorityUnavailable`` and a ledger that claims them
is rejected on load. Downgrading exposure (suspend/revoke) is always allowed
because it can only reduce risk.

State lives in an append-only, hash-chained ledger under ``.cache/phase6`` so a
future reviewer can onboard a lawful source without editing application code.
"""

import argparse
import hashlib
import json
import re
import unicodedata
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import (
    AfterValidator,
    ConfigDict,
    Field,
    StrictBool,
    StrictStr,
    field_validator,
    model_validator,
)

from pipeline.filesystem import confined_file, regular_path
from pipeline.generation import bounded_file
from pipeline.models import Contract, safe_url
from pipeline.review_governance import bounded_json, digest, writer_lock
from pipeline.storage import atomic_json

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ".cache/phase6/source-candidates.json"
DOSSIER = ".cache/phase6/candidates"
MAX_EVENTS = 500

# Ordered lifecycle. SUSPENDED/REVOKED are reachable from ACTIVATED; REVOKED is
# additionally reachable from any non-terminal state so a rights withdrawal can
# never wait behind an earlier gate.
TRANSITIONS: dict[str, frozenset[str]] = {
    "DISCOVERED": frozenset({"TECHNICALLY_VALIDATED", "SUSPENDED", "REVOKED"}),
    "TECHNICALLY_VALIDATED": frozenset({"RIGHTS_REVIEW_REQUIRED", "SUSPENDED", "REVOKED"}),
    "RIGHTS_REVIEW_REQUIRED": frozenset({"RIGHTS_EVIDENCE_RECORDED", "SUSPENDED", "REVOKED"}),
    "RIGHTS_EVIDENCE_RECORDED": frozenset({"EDITORIAL_REVIEW_REQUIRED", "SUSPENDED", "REVOKED"}),
    "EDITORIAL_REVIEW_REQUIRED": frozenset({"ELIGIBLE_FOR_ACTIVATION", "SUSPENDED", "REVOKED"}),
    "ELIGIBLE_FOR_ACTIVATION": frozenset({"ACTIVATED", "SUSPENDED", "REVOKED"}),
    "ACTIVATED": frozenset({"SUSPENDED", "REVOKED"}),
    "SUSPENDED": frozenset({"RIGHTS_REVIEW_REQUIRED", "REVOKED"}),
    "REVOKED": frozenset(),
}

# No authenticated reviewer authority exists in this project. Promotion into a
# rights- or editorial-approved state is therefore structurally unavailable.
AUTHORITY_GATED = frozenset({"RIGHTS_EVIDENCE_RECORDED", "ELIGIBLE_FOR_ACTIVATION", "ACTIVATED"})

TERMINAL = frozenset({"REVOKED"})

State = Literal[
    "DISCOVERED", "TECHNICALLY_VALIDATED", "RIGHTS_REVIEW_REQUIRED", "RIGHTS_EVIDENCE_RECORDED",
    "EDITORIAL_REVIEW_REQUIRED", "ELIGIBLE_FOR_ACTIVATION", "ACTIVATED", "SUSPENDED", "REVOKED",
]
RightsStatus = Literal["RIGHTS_UNVERIFIED", "RIGHTS_DENIED", "EVIDENCE_RECORDED", "REVOKED"]
FetchOutcome = Literal["NEVER_OBSERVED", "SUCCESS", "EMPTY", "FAILED", "UNKNOWN"]


class AuthorityUnavailable(ValueError):
    """No authenticated reviewer authority exists; approval stays blocked."""


class DuplicateCandidate(ValueError):
    """A candidate with the same publisher identity is already registered."""


def plain(value: str) -> str:
    if not value.strip() or any(unicodedata.category(char) in {"Cc", "Cf", "Cs"} for char in value):
        raise ValueError("Review text must be nonblank and free of control characters")
    return value


Label = Annotated[StrictStr, Field(min_length=1, max_length=200), AfterValidator(plain)]
Note = Annotated[StrictStr, Field(min_length=1, max_length=2000), AfterValidator(plain)]
Digest = Annotated[StrictStr, Field(pattern=r"^[a-f0-9]{64}$")]
CandidateId = Annotated[StrictStr, Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,63}$")]


class OnboardingModel(Contract):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RightsEvidence(OnboardingModel):
    """A reference a human must capture. Recording one is not an approval."""

    url: Annotated[StrictStr, Field(max_length=2048)]
    kind: Literal["terms", "license", "publisher-policy", "contact", "correspondence", "unknown"]
    note: Note
    captured_sha256: Digest | None = None

    _url = field_validator("url")(safe_url)


class SourceCandidate(OnboardingModel):
    candidate_id: CandidateId
    name: Label
    website: Annotated[StrictStr, Field(max_length=2048)]
    endpoint: Annotated[StrictStr, Field(max_length=2048)] | None = None
    fetch_method: Literal["rss", "json_api", "github_releases", "github_document", "html", "manual"]
    category: Annotated[StrictStr, Field(pattern=r"^[a-z0-9-]{2,40}$")]
    language: Literal["en", "bn", "other"]
    scope: Note
    terms_url: Annotated[StrictStr, Field(max_length=2048)]
    discovered_on: date
    verified_on: date | None = None
    rights_evidence_status: RightsStatus = "RIGHTS_UNVERIFIED"
    # None means unknown. True requires recorded evidence plus a reviewer reference.
    attribution_required: StrictBool | None = None
    reproduction_allowed: StrictBool | None = None
    summary_allowed: StrictBool | None = None
    image_allowed: StrictBool | None = None
    archive_retention_allowed: StrictBool | None = None
    ai_submission_allowed: StrictBool | None = None
    reviewer_reference: Label | None = None
    review_decision_at: datetime | None = None
    last_fetch_outcome: FetchOutcome = "NEVER_OBSERVED"
    last_fetch_observed_at: datetime | None = None
    coverage_gaps: list[Note] = Field(default_factory=list, max_length=20)
    evidence: list[RightsEvidence] = Field(default_factory=list, max_length=20)

    _urls = field_validator("website", "terms_url")(safe_url)
    _endpoint = field_validator("endpoint")(lambda value: safe_url(value) if value is not None else value)

    @field_validator("review_decision_at", "last_fetch_observed_at", mode="before")
    @classmethod
    def aware(cls, value):
        if value is None:
            return None
        if isinstance(value, str) and re.fullmatch(
                r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})", value):
            value = datetime.fromisoformat(value)
        if not isinstance(value, datetime):
            raise ValueError("Timestamps require explicit ISO time and timezone")
        if value.tzinfo is None:
            raise ValueError("Timestamps require an explicit timezone")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def rights_consistency(self):
        if self.verified_on and self.verified_on < self.discovered_on:
            raise ValueError("Verification cannot precede discovery")
        if urlsplit(self.endpoint or self.website).hostname != urlsplit(self.website).hostname:
            if self.endpoint and urlsplit(self.endpoint).hostname != "api.github.com":
                raise ValueError("Feed endpoint must be served from the candidate website")
        permissions = {
            "reproduction_allowed": self.reproduction_allowed,
            "summary_allowed": self.summary_allowed,
            "image_allowed": self.image_allowed,
            "archive_retention_allowed": self.archive_retention_allowed,
            "ai_submission_allowed": self.ai_submission_allowed,
        }
        granted = sorted(key for key, value in permissions.items() if value is True)
        if self.rights_evidence_status in {"RIGHTS_UNVERIFIED", "RIGHTS_DENIED", "REVOKED"} and granted:
            raise ValueError(f"Permissions cannot be asserted while rights are {self.rights_evidence_status}")
        if granted and (self.rights_evidence_status != "EVIDENCE_RECORDED" or not self.evidence
                        or not self.reviewer_reference or not self.review_decision_at):
            raise ValueError("Permission claims require recorded rights evidence, "
                             "a reviewer reference and a decision time")
        if self.rights_evidence_status == "RIGHTS_DENIED" and self.ai_submission_allowed:
            raise ValueError("Denied sources cannot permit AI submission")
        return self

    @property
    def identity(self) -> str:
        """Stable publisher identity; duplicate registrations are refused."""
        host = (urlsplit(self.website).hostname or "").lower().removeprefix("www.")
        return hashlib.sha256(f"{host}|{self.fetch_method}|{self.language}".encode()).hexdigest()


def candidate_identity(value: dict) -> str:
    return SourceCandidate.model_validate(value).identity


class TransitionRecord(OnboardingModel):
    from_state: State
    to_state: State
    actor: Label
    at: datetime
    reason: Note
    evidence_sha256: Digest | None = None
    from_candidate_sha256: Digest | None = None
    to_candidate_sha256: Digest

    @field_validator("at", mode="before")
    @classmethod
    def aware(cls, value):
        if isinstance(value, str) and re.fullmatch(
                r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})", value):
            value = datetime.fromisoformat(value)
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise ValueError("Transition timestamps require an explicit timezone")
        return value.astimezone(UTC)


class CandidateEvent(OnboardingModel):
    sequence: int = Field(ge=1, strict=True)
    candidate_id: CandidateId
    identity: Digest
    previous_sha256: Digest
    transition: TransitionRecord | None
    registered: bool = Field(default=False, strict=True)
    candidate_sha256: Digest | None = None
    event_sha256: Digest

    @model_validator(mode="after")
    def shape(self):
        if self.registered == (self.transition is not None):
            raise ValueError("Event must either register a candidate or record a transition")
        if self.registered and self.candidate_sha256 is None:
            raise ValueError("Registration requires the candidate digest")
        return self


class CandidateLedger(OnboardingModel):
    version: Literal[1] = 1
    events: list[CandidateEvent] = Field(default_factory=list, max_length=MAX_EVENTS)
    head_sha256: Digest = "0" * 64

    @field_validator("version", mode="before")
    @classmethod
    def strict_version(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("Unsupported candidate ledger version; strict integer 1 required")
        return value

    @model_validator(mode="after")
    def chain(self):
        previous = "0" * 64
        last_at = None
        seen: dict[str, tuple[str, str]] = {}
        for index, event in enumerate(self.events, 1):
            payload = event.model_dump(mode="json", exclude={"event_sha256"})
            if event.sequence != index or event.previous_sha256 != previous or digest(payload) != event.event_sha256:
                raise ValueError("Corrupted or reordered candidate ledger")
            transition = event.transition
            if event.registered:
                if event.candidate_id in seen or any(identity == event.identity for _, identity in seen.values()):
                    raise ValueError("Duplicate candidate registration in ledger")
                state = "DISCOVERED"
            else:
                if event.candidate_id not in seen:
                    raise ValueError("Candidate transition has no registration")
                state = seen[event.candidate_id][0]
                if event.identity != seen[event.candidate_id][1] or transition.from_state != state:
                    raise ValueError("Candidate identity or prior state changed in ledger")
                if transition.to_state in AUTHORITY_GATED:
                    raise ValueError("Ledger claims an approval this project cannot authorise")
                if transition.to_state not in TRANSITIONS[state]:
                    raise ValueError("Illegal candidate transition in ledger")
            if transition and last_at and transition.at < last_at:
                raise ValueError("Candidate transition timestamps must be monotonic")
            if transition:
                last_at = transition.at
            seen[event.candidate_id] = (transition.to_state if transition else state, event.identity)
            previous = event.event_sha256
        if self.head_sha256 != previous:
            raise ValueError("Candidate ledger head mismatch")
        return self


def ledger_path(root=ROOT) -> Path:
    return confined_file(root, LEDGER)


def dossier_path(root, candidate_id) -> Path:
    """Where the locally retained candidate metadata lives.

    The ledger keeps digests, not bodies. The dossier is the reviewable
    metadata a rights reviewer actually reads; it is local, private and
    git-ignored, and it never carries an approval.
    """
    if not isinstance(candidate_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,63}", candidate_id):
        raise ValueError("Unsafe candidate dossier name")
    path = confined_file(root, f"{DOSSIER}/{candidate_id}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    return confined_file(root, f"{DOSSIER}/{candidate_id}.json")


def write_dossier(root, candidate) -> None:
    """Persist the current candidate metadata for rights review."""
    from pipeline.storage import atomic_json

    candidate = SourceCandidate.model_validate(candidate.model_dump(mode="json"))
    path = dossier_path(root, candidate.candidate_id)
    atomic_json(path, candidate.model_dump(mode="json"))


def load_ledger(root=ROOT) -> CandidateLedger:
    path = ledger_path(root)
    if not path.exists():
        return CandidateLedger()
    payload = bounded_json(path)
    return CandidateLedger.model_validate(payload)


def current_state(ledger: CandidateLedger, candidate_id: str) -> tuple[str, str]:
    """Return (state, identity) for a candidate, defaulting to an unknown lookup."""
    state, identity = None, None
    for event in ledger.events:
        if event.candidate_id == candidate_id:
            identity = event.identity
            state = "DISCOVERED" if event.registered else event.transition.to_state
    return state or "UNKNOWN", identity or ""


def evidence_digest(candidate: SourceCandidate) -> str | None:
    return digest([item.model_dump(mode="json") for item in candidate.evidence]) if candidate.evidence else None


def authenticated_review(candidate, authority, now, *, mode="production"):
    """Report signed onboarding evidence; source activation stays a separate owner act."""
    from pipeline.authority.service import AuthorityBundle, bind_candidate
    if not isinstance(authority, AuthorityBundle):
        raise AuthorityUnavailable("An independently provisioned and anchored authority is required")
    history = authority.verify(now, expected_mode=mode)
    binding = bind_candidate(candidate)
    return {"state": history.state(binding),
            "rights_evidence_recorded": bool(history.active(binding, "RIGHTS_EVIDENCE_RECORDED", now)),
            "eligible_for_activation": bool(history.active(binding, "ELIGIBLE_FOR_ACTIVATION", now)),
            "activation_allowed": False, "ai_submission_allowed": False}


def signed_candidate_allowed(row, local_ledger, history, now):
    """Reconcile preserved local proposal evidence with the authenticated lifecycle.

    Only the full new-edition gate supplies this verified history. Unsigned
    suspension/revocation still denies; a signed review must match the exact most
    recent local candidate digest and identity. No configuration is changed.
    """
    if row["state"] in {"SUSPENDED", "REVOKED"} or any(
            event.candidate_id == row["candidate_id"] and event.transition is not None
            and event.transition.to_state in {"SUSPENDED", "REVOKED"} for event in local_ledger.events):
        return False
    latest = next((event for event in reversed(local_ledger.events)
                   if event.candidate_id == row["candidate_id"]), None)
    if latest is None:
        return False
    expected = latest.candidate_sha256 if latest.registered else latest.transition.to_candidate_sha256
    for envelope in reversed(history.decisions):
        bound = envelope.payload.binding
        if (bound.workflow == "source" and bound.source_id == row["candidate_id"]
                and bound.story_id == "candidate:" + row["candidate_id"]
                and bound.source_sha256 == row["identity"] and bound.content_sha256 == expected):
            return (history.state(bound) == "ELIGIBLE_FOR_ACTIVATION"
                    and bool(history.active(bound, "RIGHTS_EVIDENCE_RECORDED", now))
                    and bool(history.active(bound, "ELIGIBLE_FOR_ACTIVATION", now)))
    return False


def register(candidate, *, actor, now, root=ROOT):
    """Append a candidate registration event. Duplicate identities are refused."""
    candidate = SourceCandidate.model_validate(candidate.model_dump(mode="json"))
    _refuse_permission_claims(candidate)
    plain(actor)
    ledger = load_ledger(root)
    state, identity = current_state(ledger, candidate.candidate_id)
    if state != "UNKNOWN":
        raise ValueError("Candidate identity is already registered")
    if any(event.identity == candidate.identity for event in ledger.events):
        raise DuplicateCandidate("A candidate for this publisher, fetch method and language already exists")
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError("Registration requires an aware clock")
    payload = {"sequence": len(ledger.events) + 1, "candidate_id": candidate.candidate_id,
               "identity": candidate.identity, "previous_sha256": ledger.head_sha256, "registered": True,
               "transition": None, "candidate_sha256": digest(candidate.model_dump(mode="json"))}
    return _append(CandidateEvent(**payload, event_sha256=digest(payload)), now, actor, "Candidate registered",
                   candidate=candidate, root=root)


def transition(candidate, to_state, *, actor, now, reason, evidence=None, root=ROOT):
    """Record a lifecycle transition under the shared writer lock."""
    candidate = SourceCandidate.model_validate(candidate.model_dump(mode="json"))
    if to_state not in {"SUSPENDED", "REVOKED"}:
        _refuse_permission_claims(candidate)
    ledger = load_ledger(root)
    state, identity = current_state(ledger, candidate.candidate_id)
    if state == "UNKNOWN":
        raise ValueError("Unknown candidate; register it before recording a transition")
    if identity != candidate.identity:
        raise ValueError("Candidate identity changed; register a new candidate instead")
    if to_state in AUTHORITY_GATED:
        # Checked before legality so an approval attempt is always refused for
        # the authority reason, never reported as merely an illegal step.
        raise AuthorityUnavailable(
            f"{to_state} requires an authenticated reviewer authority that this project does not have")
    if to_state not in TRANSITIONS.get(state, frozenset()):
        raise ValueError(f"Illegal candidate transition {state} -> {to_state}")
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError("Transition requires an aware clock")
    evidence = list(evidence if evidence is not None else candidate.evidence)
    updated = candidate.model_copy(update={"evidence": evidence,
                                           "verified_on": candidate.verified_on or now.date()})
    if to_state in {"SUSPENDED", "REVOKED"}:
        updated = updated.model_copy(update={key: False for key in (
            "reproduction_allowed", "summary_allowed", "image_allowed", "archive_retention_allowed",
            "ai_submission_allowed")})
        updated = updated.model_copy(update={"rights_evidence_status": "REVOKED" if to_state == "REVOKED"
                                            else "RIGHTS_UNVERIFIED"})
    updated = SourceCandidate.model_validate(updated.model_dump(mode="python"))
    record = TransitionRecord(from_state=state, to_state=to_state, actor=actor, at=now, reason=reason,
                              evidence_sha256=evidence_digest(updated),
                              from_candidate_sha256=digest(candidate.model_dump(mode="json")),
                              to_candidate_sha256=digest(updated.model_dump(mode="json")))
    payload = {"sequence": len(ledger.events) + 1, "candidate_id": candidate.candidate_id,
               "identity": candidate.identity, "previous_sha256": ledger.head_sha256, "registered": False,
               "transition": record.model_dump(mode="json"), "candidate_sha256": None}
    return _append(CandidateEvent(**payload, event_sha256=digest(payload)), now, actor, reason, updated, root=root)


def _refuse_permission_claims(candidate):
    if candidate.rights_evidence_status == "EVIDENCE_RECORDED" or any(
            getattr(candidate, key) is True for key in ("reproduction_allowed", "summary_allowed",
                                                       "image_allowed", "archive_retention_allowed",
                                                       "ai_submission_allowed")):
        raise AuthorityUnavailable("Permission claims require an authenticated reviewer authority")


def _append(event, now, actor, reason, candidate=None, root=ROOT):
    path = ledger_path(root)
    # The dossier is written first. A dossier failure must not leave a ledger
    # entry whose reviewable metadata is missing.
    if candidate is not None:
        # The dossier is review material, never an approval.
        write_dossier(root, candidate)
    with writer_lock(confined_file(root, ".cache/phase6/source-candidates.lock")):
        ledger = load_ledger(root)
        if ledger.head_sha256 != event.previous_sha256 or ledger.events and len(ledger.events) >= MAX_EVENTS:
            raise ValueError("Candidate ledger changed underneath this write; retry with fresh evidence")
        updated = CandidateLedger.model_validate({
            "version": 1,
            "events": [*[e.model_dump(mode="json") for e in ledger.events], event.model_dump(mode="json")],
            "head_sha256": event.event_sha256})
        atomic_json(path, updated)
    return candidate, event


def candidates(root=ROOT):
    """Rebuild every registered candidate from the ledger, in registration order."""
    ledger = load_ledger(root)
    order, rebuilt = [], {}
    for event in ledger.events:
        if event.registered:
            order.append(event.candidate_id)
            rebuilt[event.candidate_id] = {"state": "DISCOVERED", "identity": event.identity,
                                           "last": event.model_dump(mode="json")}
        else:
            entry = rebuilt[event.candidate_id]
            entry["state"] = event.transition.to_state
            entry["last"] = event.model_dump(mode="json")
    return [{"candidate_id": key, "state": rebuilt[key]["state"], "identity": rebuilt[key]["identity"],
             "transitions": sum(1 for e in ledger.events if e.candidate_id == key and not e.registered)}
            for key in order]


def missing_evidence(candidate) -> list[str]:
    """Reviewer-facing gaps. Unknown is never reported as satisfied."""
    gaps = list(candidate.coverage_gaps)
    if candidate.rights_evidence_status == "RIGHTS_UNVERIFIED":
        gaps.append("rights_evidence_missing")
    if not candidate.evidence:
        gaps.append("no_evidence_references_recorded")
    if not candidate.reviewer_reference:
        gaps.append("no_human_reviewer_reference")
    if candidate.reviewer_reference and not candidate.review_decision_at:
        gaps.append("reviewer_reference_without_decision_time")
    if candidate.last_fetch_outcome in {"NEVER_OBSERVED", "UNKNOWN"}:
        gaps.append("no_confirmed_fetch_outcome")
    if not candidate.terms_url:
        gaps.append("no_terms_reference")
    return sorted(set(gaps))


def readiness(candidate):
    """One-line operational readiness. Never reports PASS for an unknown."""
    gaps = missing_evidence(candidate)
    if candidate.rights_evidence_status == "REVOKED":
        return "REVOKED"
    if candidate.rights_evidence_status == "RIGHTS_DENIED":
        return "EXCLUDED"
    if gaps:
        return "RIGHTS_UNVERIFIED" if candidate.rights_evidence_status == "RIGHTS_UNVERIFIED" else "REVIEW_REQUIRED"
    return "EVIDENCE_RECORDED_REVIEW_REQUIRED"


def report(root=ROOT) -> dict:
    from pipeline.source_evidence import evidence_report, load_dossiers

    ledger = load_ledger(root)
    rows = candidates(root)
    blocked = [{"candidate_id": row["candidate_id"], "state": row["state"]} for row in rows
               if row["state"] in AUTHORITY_GATED]
    return {"version": 1, "generated_from": "local candidate ledger only",
            "candidates": rows, "event_count": len(ledger.events),
            "authority_gated_states": sorted(AUTHORITY_GATED),
            "activable_candidates": blocked,
            "evidence": evidence_report(load_dossiers(root)),
            "publication_allowed": False, "ai_submission_allowed": False,
            "note": "No candidate can be activated or rights-approved without an owner-appointed reviewer."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("list", "report", "head", "evidence", "register-research"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--file", type=Path,
                        help="A candidate dossier JSON to check instead of the local dossiers")
    parser.add_argument("--actor", default="phase10-source-research",
                        help="The tool label recorded as the actor. Never a person's identity.")
    args = parser.parse_args()
    try:
        if args.action == "list":
            result = {"candidates": candidates(args.root)}
        elif args.action == "head":
            result = load_ledger(args.root).model_dump(mode="json")
        elif args.action == "register-research":
            from pipeline.source_evidence import (
                configured_source_ids,
                edition_identities,
                research_candidates,
            )

            registered, skipped, configured = [], [], []
            edition = edition_identities(args.root)
            known = configured_source_ids(args.root)
            for candidate in research_candidates(args.root):
                if candidate.candidate_id in known or candidate.identity in edition:
                    configured.append(candidate.candidate_id)
                    continue
                try:
                    register(candidate, actor=args.actor, now=datetime.now(UTC), root=args.root)
                    registered.append(candidate.candidate_id)
                except DuplicateCandidate:
                    skipped.append(candidate.candidate_id)
                except ValueError as error:
                    skipped.append(candidate.candidate_id)
                    print(json.dumps({"status": "refused", "candidate_id": candidate.candidate_id,
                                      "detail": str(error), "publication_allowed": False}))
            result = {"registered": registered, "already_registered": skipped,
                      "already_configured": configured,
                      "actor": args.actor, "publication_allowed": False,
                      "ai_submission_allowed": False,
                      "note": "Registration records a proposal only. Every candidate remains "
                              "RIGHTS_UNVERIFIED until a named human rights reviewer decides."}
        elif args.action == "evidence":
            from pipeline.source_evidence import evidence_report, load_dossiers, read_candidate_document

            if args.file:
                dossiers = [read_candidate_document(bounded_file(regular_path(args.file), 1_000_000))]
            else:
                dossiers = load_dossiers(args.root)
            result = evidence_report(dossiers)
        else:
            result = report(args.root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, TypeError) as error:
        print(json.dumps({"status": "refused", "error_type": type(error).__name__,
                          "publication_allowed": False, "ai_submission_allowed": False}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
