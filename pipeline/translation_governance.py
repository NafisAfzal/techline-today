"""Bilingual translation lifecycle and language-integrity checks.

English remains authoritative. A Bangla translation is a *draft* until a named
native reviewer approves it, and no automated process can reach that state here:
``NATIVE_REVIEW_COMPLETE``, ``APPROVED_TRANSLATION`` and ``PUBLISHED_TRANSLATION``
raise :class:`AuthorityUnavailable` and a ledger claiming them is rejected on load.

Machine output never becomes reviewed Bangla silently. When the English source
changes materially after a review, the translation is returned to
``LANGUAGE_REVIEW_PENDING`` rather than continuing to publish as current.

The integrity checks below are preparation for human review. They are not, and do
not claim to be, proof of native-language quality.
"""

import argparse
import json
import re
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AfterValidator, ConfigDict, Field, StrictStr, field_validator, model_validator

from pipeline.editorial_workflow import story_identity
from pipeline.filesystem import confined_file
from pipeline.models import Contract, Story
from pipeline.review_governance import bounded_json, digest, writer_lock
from pipeline.storage import atomic_json
from pipeline.translation import canonical_hash

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ".cache/phase6/translation-decisions.json"
MAX_EVENTS = 500

BANGLA = re.compile(r"[ঀ-৿]")

TRANSITIONS: dict[str, frozenset[str]] = {
    "NOT_TRANSLATED": frozenset({"DRAFT_TRANSLATION", "WITHDRAWN"}),
    "DRAFT_TRANSLATION": frozenset({"LANGUAGE_REVIEW_PENDING", "WITHDRAWN"}),
    "LANGUAGE_REVIEW_PENDING": frozenset({"DRAFT_TRANSLATION", "WITHDRAWN"}),
    "NATIVE_REVIEW_COMPLETE": frozenset({"APPROVED_TRANSLATION", "LANGUAGE_REVIEW_PENDING", "WITHDRAWN"}),
    "APPROVED_TRANSLATION": frozenset({"PUBLISHED_TRANSLATION", "LANGUAGE_REVIEW_PENDING", "WITHDRAWN"}),
    "PUBLISHED_TRANSLATION": frozenset({"LANGUAGE_REVIEW_PENDING", "WITHDRAWN"}),
    "WITHDRAWN": frozenset({"DRAFT_TRANSLATION"}),
}

AUTHORITY_GATED = frozenset({"NATIVE_REVIEW_COMPLETE", "APPROVED_TRANSLATION", "PUBLISHED_TRANSLATION"})

State = Literal["NOT_TRANSLATED", "DRAFT_TRANSLATION", "LANGUAGE_REVIEW_PENDING", "NATIVE_REVIEW_COMPLETE",
                "APPROVED_TRANSLATION", "PUBLISHED_TRANSLATION", "WITHDRAWN"]
Language = Literal["en", "bn"]

Digest = Annotated[StrictStr, Field(pattern=r"^[a-f0-9]{64}$")]


class AuthorityUnavailable(ValueError):
    """No native reviewer has been appointed; reviewed Bangla stays blocked."""


def plain(value: str) -> str:
    if not value.strip() or any(unicodedata.category(char) in {"Cc", "Cf", "Cs"} for char in value):
        raise ValueError("Review text must be nonblank and free of control characters")
    return value


Label = Annotated[StrictStr, Field(min_length=1, max_length=200), AfterValidator(plain)]
Note = Annotated[StrictStr, Field(min_length=1, max_length=2000), AfterValidator(plain)]


class TranslationModel(Contract):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TerminologyDecision(TranslationModel):
    source_term: Label
    target_term: Label
    rationale: Note | None = None


class TranslationRecord(TranslationModel):
    """Stable translation identity bound to an exact English source version."""

    story_identity: Digest
    target_language: Language = "bn"
    source_version: Digest
    translation_version: Digest
    state: State = "NOT_TRANSLATED"
    provider: Label | None = None
    model: Label | None = None
    terminology: list[TerminologyDecision] = Field(default_factory=list, max_length=50)
    native_reviewer_reference: Label | None = None
    last_review_at: datetime | None = None
    corrected_at: datetime | None = None
    stale: bool = False
    stale_reason: Label | None = None

    @field_validator("last_review_at", "corrected_at", mode="before")
    @classmethod
    def aware(cls, value):
        if value is None:
            return None
        if isinstance(value, str) and re.fullmatch(
                r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})", value):
            value = datetime.fromisoformat(value)
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise ValueError("Translation timestamps require an explicit timezone")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def evidence(self):
        if self.state in AUTHORITY_GATED and not self.native_reviewer_reference:
            raise ValueError("Reviewed Bangla requires a named native reviewer reference")
        if self.stale and not self.stale_reason:
            raise ValueError("A stale translation must record why it needs re-review")
        if self.stale and self.state in {"APPROVED_TRANSLATION", "PUBLISHED_TRANSLATION"}:
            raise ValueError("A stale translation cannot hold an approved or published state")
        if self.state in AUTHORITY_GATED and not self.last_review_at:
            raise ValueError("Reviewed Bangla requires a recorded review time")
        return self


def make_record(story_id, *, source_version, translation_version, provider=None, model=None,
                source_ids=None) -> TranslationRecord:
    return TranslationRecord(story_identity=story_identity(story_id=story_id, source_ids=list(source_ids or [])),
                             source_version=source_version, translation_version=translation_version,
                             provider=provider, model=model)


def meaningful_change(previous: dict, current: dict) -> bool:
    """Reader-visible fields only. Metadata-only churn must not force re-review."""
    # Only explicitly operational metadata can be rebound without human re-review.
    # Unknown/evidence fields, numbers, limitations and correction facts are material.
    metadata = {"last_verified_at", "updated_at", "fetched_at", "build_time"}
    return any(previous.get(key) != current.get(key) for key in previous.keys() | current.keys()
               if key not in metadata)


def staleness(record: TranslationRecord, current_source_version: str, previous_content: dict | None = None,
              current_content: dict | None = None) -> TranslationRecord:
    """Return a re-review-pending record when the English source moved."""
    if record.source_version == current_source_version:
        return record
    # Canonical versions exclude operational metadata already. Caller-supplied
    # content projections cannot prove that a different evidence hash is cosmetic.
    # Never rebind an approval to a new hash on that unauthenticated assertion.
    return record.model_copy(update={"state": "LANGUAGE_REVIEW_PENDING", "stale": True,
                                     "stale_reason": "english_source_changed_after_review",
                                     "native_reviewer_reference": None, "last_review_at": None})


class TranslationDecision(TranslationModel):
    from_state: State
    to_state: State
    actor: Label
    at: datetime
    reason: Note
    story_identity: Digest
    reviewer_reference: Label | None = None
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
        if self.to_state in AUTHORITY_GATED and not self.reviewer_reference:
            raise ValueError("Reviewed Bangla requires a named native reviewer reference")
        return self


class TranslationEvent(TranslationModel):
    sequence: int = Field(ge=1, strict=True)
    previous_sha256: Digest
    decision: TranslationDecision
    event_sha256: Digest


class TranslationLedger(TranslationModel):
    version: Literal[1] = 1
    events: list[TranslationEvent] = Field(default_factory=list, max_length=MAX_EVENTS)
    head_sha256: Digest = "0" * 64

    @field_validator("version", mode="before")
    @classmethod
    def strict_version(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("Unsupported translation ledger version; strict integer 1 required")
        return value

    @model_validator(mode="after")
    def chain(self):
        previous = "0" * 64
        states: dict[str, str] = {}
        last_at = None
        for index, event in enumerate(self.events, 1):
            payload = event.model_dump(mode="json", exclude={"event_sha256"})
            if event.sequence != index or event.previous_sha256 != previous or digest(payload) != event.event_sha256:
                raise ValueError("Corrupted or reordered translation ledger")
            decision = event.decision
            state = states.get(decision.story_identity, "NOT_TRANSLATED")
            if decision.to_state in AUTHORITY_GATED:
                raise ValueError("Ledger claims native review this project cannot authorise")
            if decision.from_state != state or decision.to_state not in TRANSITIONS[state]:
                raise ValueError("Illegal translation transition in ledger")
            if last_at and decision.at < last_at:
                raise ValueError("Translation decision timestamps must be monotonic")
            states[decision.story_identity] = decision.to_state
            last_at = decision.at
            previous = event.event_sha256
        if self.head_sha256 != previous:
            raise ValueError("Translation ledger head mismatch")
        return self


def ledger_path(root=ROOT):
    return confined_file(root, LEDGER)


def load_ledger(root=ROOT) -> TranslationLedger:
    path = ledger_path(root)
    if not path.exists():
        return TranslationLedger()
    return TranslationLedger.model_validate(bounded_json(path))


def record(record_obj, from_state, to_state, *, actor, now, reason, reviewer_reference=None, root=ROOT):
    """Append one translation decision. Reviewed states are refused, not configurable."""
    record_obj = TranslationRecord.model_validate(record_obj.model_dump(mode="json"))
    if to_state not in TRANSITIONS:
        raise ValueError("Unknown translation state")
    if to_state in AUTHORITY_GATED:
        raise AuthorityUnavailable(
            f"{to_state} requires an appointed native Bangla reviewer that this project does not have")
    if to_state not in TRANSITIONS.get(from_state, frozenset()):
        raise ValueError(f"Illegal translation transition {from_state} -> {to_state}")
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError("Decision requires an aware clock")
    decision = TranslationDecision(from_state=from_state, to_state=to_state, actor=actor, at=now, reason=reason,
                                   story_identity=record_obj.story_identity,
                                   reviewer_reference=reviewer_reference,
                                   to_record_sha256=digest(record_obj.model_dump(mode="json")))
    ledger = load_ledger(root)
    payload = {"sequence": len(ledger.events) + 1, "previous_sha256": ledger.head_sha256,
               "decision": decision.model_dump(mode="json")}
    event = TranslationEvent(**payload, event_sha256=digest(payload))
    with writer_lock(confined_file(root, ".cache/phase6/translation-decisions.lock")):
        current = load_ledger(root)
        if current.head_sha256 != event.previous_sha256:
            raise ValueError("Translation ledger changed underneath this write; retry with fresh evidence")
        atomic_json(ledger_path(root), TranslationLedger.model_validate({
            "version": 1,
            "events": [*[e.model_dump(mode="json") for e in current.events], event.model_dump(mode="json")],
            "head_sha256": event.event_sha256}))
    return event


def translation_state(ledger: TranslationLedger, story_ident: str) -> str:
    state = "NOT_TRANSLATED"
    for event in ledger.events:
        if event.decision.story_identity == story_ident:
            state = event.decision.to_state
    return state


def record_authenticated(envelope, *, trust_pin, now, root=ROOT, mode="production"):
    """Signed extension of the same translation lifecycle; no content is generated."""
    from pipeline.authority.ledger import append
    from pipeline.authority.protocol import Decision
    if not isinstance(envelope.payload, Decision) or envelope.payload.binding.workflow != "translation":
        raise ValueError("Expected a signed translation lifecycle decision")
    return append(root, envelope, trust_pin, now, mode=mode)


# --- language integrity checks -------------------------------------------------

def integrity_findings(story, translation=None, *, locale="bn") -> list[dict]:
    """Structural checks over a story's Bangla material.

    Automated preparation for human review, not proof of native-language quality.
    """
    findings = []

    def add(check, severity, detail):
        findings.append({"check": check, "severity": severity, "detail": detail})

    if story.language not in {"en", "bn"}:
        add("story_language_tag", "fail", f"unexpected story language tag {story.language!r}")

    if translation is None:
        if locale == "bn":
            add("translation_absent", "notice", "no Bangla translation; English fallback must be labelled")
        return findings

    if translation.language != "bn" or locale != "bn":
        add("translation_language_tag", "fail", "translation language tag does not match locale")

    content = translation.content
    texts = [content.headline, *content.summary_bullets, content.why_it_matters, content.broader_summary,
             *content.key_fact_texts, *content.limitations]

    if any(not text.strip() for text in texts):
        add("empty_translation_field", "fail", "a translated field is empty")
    if not BANGLA.search(content.headline):
        add("english_fallback_mislabelled", "fail", "Bangla content contains no Bangla script")
    if any(BANGLA.search(text) for text in [story.headline, *story.summary_bullets]):
        add("source_language_mismatch", "fail", "English source field contains Bangla script")
    if any(re.search(r"[�\ud800-\udfff]", text) or "Ã" in text or "à¦" in text for text in texts):
        add("broken_unicode", "fail", "replacement characters or mojibake detected")
    if any(unicodedata.category(char) == "Cc" for text in texts for char in text):
        add("control_characters", "fail", "control characters in translated content")
    expected_hash = canonical_hash(story) if isinstance(story, Story) else getattr(story, "_canonical_hash", None)
    if expected_hash is None:
        add("translation_binding_unknown", "notice", "no canonical source version is available")
    elif translation.canonical_hash != expected_hash:
        add("translation_binding_mismatch", "fail", "translation does not match the current English evidence")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", story.slug):
        add("invalid_slug", "fail", "story slug is not URL safe")
    return findings


def edition_language_report(stories, *, locale="bn", authority=None, sources=None,
                            source_rights=None, now=None, authority_mode="production") -> dict:
    """Machine-readable bilingual coverage across an edition."""
    rows = []
    for story in stories:
        translation = story.translations.get("bn")
        findings = integrity_findings(story, translation, locale=locale)
        native_verified = False
        if authority is not None and translation is not None:
            from pipeline.authority.service import story_evidence
            try:
                evidence = story_evidence(authority, story, sources or {}, source_rights or {},
                                          now or datetime.now(UTC), mode=authority_mode)
                native_verified = bool(evidence["native_bn"]) and evidence["native_complete"]
            except (ValueError, TypeError, OSError):
                native_verified = False
        native_verified = native_verified and not any(f["severity"] == "fail" for f in findings)
        rows.append({"story_id": story.id, "translated": translation is not None,
                     "review_status": translation.review_status if translation else None,
                     "authenticated_native_review": native_verified,
                     "findings": findings,
                     "blocking": [f["check"] for f in findings if f["severity"] == "fail"]})
    return {"version": 1, "locale": locale, "story_count": len(rows),
            "translated_count": sum(row["translated"] for row in rows),
            "blocking_story_count": sum(1 for row in rows if row["blocking"]),
            "native_reviewed_count": sum(row["authenticated_native_review"] for row in rows),
            "rows": rows,
            "publication_allowed": False,
            "note": "Structural checks only; native-language review remains a human prerequisite."}


def backlog(ledger: TranslationLedger | None = None, root=ROOT) -> list[dict]:
    ledger = ledger if ledger is not None else load_ledger(root)
    rows = {}
    for event in ledger.events:
        decision = event.decision
        entry = rows.setdefault(decision.story_identity, {"story_identity": decision.story_identity,
                                                          "state": "NOT_TRANSLATED", "transitions": 0})
        entry["state"] = decision.to_state
        entry["transitions"] += 1
    return sorted(
        [{**row, "blockers": sorted(
            {"awaiting_native_reviewer"} if row["state"] in {"DRAFT_TRANSLATION", "LANGUAGE_REVIEW_PENDING"}
             else {"approval_requires_native_reviewer"} if row["state"] in AUTHORITY_GATED else set())}
         for row in rows.values()],
        key=lambda row: row["story_identity"])


def report(root=ROOT) -> dict:
    ledger = load_ledger(root)
    return {"version": 1, "event_count": len(ledger.events), "backlog": backlog(ledger, root),
            "authority_gated_states": sorted(AUTHORITY_GATED), "publication_allowed": False,
            "note": "No native Bangla reviewer has been appointed; reviewed translations stay blocked."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("report", "backlog", "head"))
    args = parser.parse_args()
    try:
        if args.action == "report":
            result = report()
        elif args.action == "backlog":
            result = {"backlog": backlog()}
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
