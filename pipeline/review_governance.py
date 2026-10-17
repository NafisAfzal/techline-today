"""Inactive local operator review contract. Never grants publication or AI rights.

Production deliberately does not import this module. Hashes detect corruption,
not operator authenticity; even a recomputed forged chain cannot approve reuse.
"""

import argparse
import hashlib
import json
import os
import re
import unicodedata
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AfterValidator, ConfigDict, Field, StrictStr, field_validator, model_validator

from pipeline.models import Contract, safe_url
from pipeline.storage import atomic_json
from pipeline.strict_json import strict_json
from pipeline.strict_json import unique_keys as unique_keys

POLICY_VERSION = "phase3-rights-review-v1"
MAX_LEDGER_BYTES = 2_000_000
MAX_EVENTS = 500
ZERO_HASH = "0" * 64
Digest = Annotated[StrictStr, Field(pattern=r"^[a-f0-9]{64}$")]

def review_text(value):
    if not value.strip() or any(unicodedata.category(char) in {"Cc", "Cf", "Cs"} for char in value):
        raise ValueError("Review text must be nonblank and contain no controls or formatting overrides")
    return value


Label = Annotated[StrictStr, Field(min_length=1, max_length=200), AfterValidator(review_text)]
Note = Annotated[StrictStr, Field(min_length=1, max_length=2000), AfterValidator(review_text)]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def bounded_json(path, limit=MAX_LEDGER_BYTES):
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Local JSON size limit exceeded")
    try:
        return strict_json(data, max_bytes=limit)
    except (RecursionError, UnicodeError) as error:
        raise ValueError("Invalid bounded JSON") from error


def local_path(root, relative):
    """Constrain every local write, including ancestors, to .cache/phase3."""
    root = Path(root).resolve()
    relative = Path(relative)
    if relative.is_absolute() or ".." in relative.parts or relative.parts[:2] != (".cache", "phase3"):
        raise ValueError("Phase 3 state must remain under .cache/phase3")
    target = root / relative
    for candidate in [target, *target.parents]:
        if candidate == root:
            break
        if candidate.is_symlink() or candidate.is_junction():
            raise ValueError("Linked local-state paths are forbidden")
    if not target.resolve().is_relative_to(root / ".cache" / "phase3"):
        raise ValueError("Local-state path escaped isolation")
    return target


class ReviewModel(Contract):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ItemBinding(ReviewModel):
    item_id: Annotated[StrictStr, Field(pattern=r"^src_[a-f0-9]{20}$")]
    source_id: Annotated[StrictStr, Field(pattern=r"^[a-z0-9_-]{1,80}$")]
    canonical_url: Annotated[StrictStr, Field(max_length=2048)]
    content_sha256: Digest
    evidence_sha256: Digest
    # No trusted live attestation exists in this inactive workflow. Absence is
    # unknown, never evidence that an observation came from a real publisher.
    provenance: Literal["synthetic", "unknown"] = "unknown"

    _url = field_validator("canonical_url")(safe_url)

    @model_validator(mode="after")
    def identity(self):
        expected = "src_" + hashlib.sha256((self.source_id + self.canonical_url).encode()).hexdigest()[:20]
        if self.item_id != expected:
            raise ValueError("Review item/source/canonical identity mismatch")
        return self


def bind_item(item, raw):
    # Never copy feed approval, reviewer or decision fields. All raw fields are
    # evidence fingerprint inputs, never trusted policy or approval inputs.
    return ItemBinding(item_id=item.id, source_id=item.source_registry_id,
                       canonical_url=item.canonical_url, content_sha256=item.content_hash,
                       evidence_sha256=digest(raw), provenance="synthetic" if item.is_demo else "unknown")


class ReviewEvidence(ReviewModel):
    url: Annotated[StrictStr, Field(max_length=2048)]
    scope: Literal["specific-item", "license-grant", "creator", "publisher", "original-publication",
                   "exception", "source-policy"]
    note: Note
    captured_sha256: Digest | None = None

    _url = field_validator("url")(safe_url)


class ReviewDecision(ReviewModel):
    binding: ItemBinding
    original_publication_url: Annotated[StrictStr, Field(max_length=2048)] | None = None
    publisher: Label
    original_creator: Label | None = None
    applicable_license: Label | None = None
    evidence: list[ReviewEvidence] = Field(default_factory=list, max_length=20)
    permitted_fields: list[Literal["title", "metadata", "excerpt"]] = Field(default_factory=list, max_length=3)
    permitted_transformations: list[Literal["verbatim", "extractive-summary", "translation"]] = Field(
        default_factory=list, max_length=3)
    attribution_obligations: list[Note] = Field(default_factory=list, max_length=20)
    license_exceptions: list[Note] = Field(default_factory=list, max_length=20)
    review_status: Literal["REVIEW_REQUIRED", "REJECTED", "REVOKED"]
    reviewer_identity: Label
    reviewed_at: datetime
    review_reason: Note
    expires_at: datetime
    rereview_triggers: list[Label] = Field(min_length=1, max_length=20)
    policy_version: Label = POLICY_VERSION
    synthetic: bool = Field(default=False, strict=True)

    @field_validator("reviewed_at", "expires_at", mode="before")
    @classmethod
    def aware(cls, value):
        if isinstance(value, str) and re.fullmatch(
                r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})", value):
            value = datetime.fromisoformat(value)
        if not isinstance(value, datetime):
            raise ValueError("Review timestamps require explicit ISO time and timezone")
        if value.tzinfo is None:
            raise ValueError("Review timestamps require an explicit timezone")
        return value.astimezone(UTC)

    @field_validator("original_publication_url")
    @classmethod
    def optional_url(cls, value):
        return safe_url(value) if value is not None else None

    @model_validator(mode="after")
    def bounds_and_evidence(self):
        if self.synthetic != (self.binding.provenance == "synthetic"):
            raise ValueError("Decision and binding provenance disagree")
        if not self.reviewed_at < self.expires_at <= self.reviewed_at + timedelta(days=90):
            raise ValueError("Re-review must be after review and within 90 days")
        if self.original_publication_url and not any(
                e.scope == "original-publication" and e.url == self.original_publication_url for e in self.evidence):
            raise ValueError("Original publication needs explicit scoped evidence")
        if self.original_creator and not any(e.scope == "creator" for e in self.evidence):
            raise ValueError("Creator needs explicit scoped evidence")
        if self.applicable_license and not any(e.scope == "license-grant" for e in self.evidence):
            raise ValueError("License needs explicit scoped evidence")
        return self


class AuditEvent(ReviewModel):
    sequence: int = Field(ge=1, strict=True)
    previous_sha256: Digest
    decision: ReviewDecision
    event_sha256: Digest


class ReviewLedger(ReviewModel):
    version: Literal[1] = 1
    events: list[AuditEvent] = Field(default_factory=list, max_length=MAX_EVENTS)
    head_sha256: Digest = ZERO_HASH

    @field_validator("version", mode="before")
    @classmethod
    def strict_version(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("Unsupported review ledger version; strict integer 1 required")
        return value

    @model_validator(mode="after")
    def chain(self):
        previous = ZERO_HASH
        last_review = None
        for index, event in enumerate(self.events, 1):
            payload = event.model_dump(mode="json", exclude={"event_sha256"})
            if event.sequence != index or event.previous_sha256 != previous or digest(payload) != event.event_sha256:
                raise ValueError("Corrupted or reordered review audit trail")
            if last_review and event.decision.reviewed_at < last_review:
                raise ValueError("Review audit timestamps must be monotonic")
            previous, last_review = event.event_sha256, event.decision.reviewed_at
        if self.head_sha256 != previous:
            raise ValueError("Review audit head mismatch")
        return self


def load_ledger(path):
    if not path.exists():
        return ReviewLedger()
    data = bounded_json(path)
    if not isinstance(data, dict) or "version" not in data:
        raise ValueError("Stored review ledger requires an explicit version")
    return ReviewLedger.model_validate(data)


@contextmanager
def writer_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, str(os.getpid()).encode())
        yield
    finally:
        os.close(descriptor)
        path.unlink()


def append_decision(root, decision):
    # Revalidate even caller-created or mutated model instances.
    decision = ReviewDecision.model_validate(decision.model_dump(mode="json"))
    path = local_path(root, ".cache/phase3/reviews/ledger.json")
    lock = local_path(root, ".cache/phase3/reviews/writer.lock")
    with writer_lock(lock):
        ledger = load_ledger(path)
        payload = {"sequence": len(ledger.events) + 1, "previous_sha256": ledger.head_sha256,
                   "decision": decision.model_dump(mode="json")}
        event = AuditEvent(**payload, event_sha256=digest(payload))
        updated = ReviewLedger.model_validate({"version": 1, "events": [
            *[e.model_dump(mode="json") for e in ledger.events], event.model_dump(mode="json")],
            "head_sha256": event.event_sha256})
        if len(json.dumps(updated.model_dump(mode="json")).encode()) > MAX_LEDGER_BYTES:
            raise ValueError("Review ledger capacity reached; preserve and archive for operator review")
        atomic_json(path, updated)
    return event


def latest_event(binding, ledger):
    """Latest item/source event; retain changed evidence so invalidation is visible."""
    return next((event for event in reversed(ledger.events)
                 if event.decision.binding.item_id == binding.item_id
                 and event.decision.binding.source_id == binding.source_id), None)


def decision_reason(binding, record, now):
    if record.binding != binding:
        return "evidence_or_identity_changed"
    if record.policy_version != POLICY_VERSION:
        return "policy_changed"
    if record.reviewed_at > now:
        return "future_review"
    if record.expires_at <= now:
        return "expired_review"
    return record.review_status.lower()


def evaluate(binding, ledger, now):
    binding = ItemBinding.model_validate(binding.model_dump(mode="json"))
    ledger = ReviewLedger.model_validate(ledger.model_dump(mode="json"))
    if now.tzinfo is None:
        raise ValueError("Evaluation requires an aware clock")
    event = latest_event(binding, ledger)
    reason = "missing_record"
    if event:
        reason = decision_reason(binding, event.decision, now)
    return {"publication_allowed": False, "ai_submission_allowed": False,
            "approval_path_active": False, "reason": reason, "policy_version": POLICY_VERSION}


def draft(binding, publisher, reviewer, now, *, synthetic=None):
    binding = ItemBinding.model_validate(binding.model_dump(mode="json"))
    derived = binding.provenance == "synthetic"
    if synthetic is not None and synthetic != derived:
        raise ValueError("CLI/argument provenance cannot override the observation binding")
    return ReviewDecision(binding=binding, publisher=publisher, review_status="REVIEW_REQUIRED",
                          reviewer_identity=reviewer, reviewed_at=now, expires_at=now + timedelta(days=30),
                          review_reason="Evidence and reuse scope require independent human review.",
                          rereview_triggers=["content-or-origin-change", "license-change", "policy-change"],
                          synthetic=derived)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("draft", "record", "inspect", "evaluate"))
    parser.add_argument("--file", type=Path, help="Bounded local binding or decision JSON, never a URL")
    parser.add_argument("--publisher")
    parser.add_argument("--reviewer")
    parser.add_argument("--synthetic", action="store_true", help="Explicitly label a fixture-only pending review")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    now = datetime.now(UTC)
    try:
        ledger_path = local_path(root, ".cache/phase3/reviews/ledger.json")
        if args.action == "inspect":
            result = load_ledger(ledger_path).model_dump(mode="json")
        elif args.action == "record":
            if not args.file:
                parser.error("record requires --file")
            result = append_decision(root, ReviewDecision.model_validate(bounded_json(args.file))).model_dump(mode="json")
        else:
            if not args.file:
                parser.error("draft/evaluate requires --file with an ItemBinding")
            binding = ItemBinding.model_validate(bounded_json(args.file))
            if args.action == "draft":
                if not args.publisher or not args.reviewer:
                    parser.error("draft requires --publisher and --reviewer")
                result = draft(binding, args.publisher, args.reviewer, now,
                               synthetic=True if args.synthetic else None).model_dump(mode="json")
                atomic_json(local_path(root, ".cache/phase3/reviews/draft.json"), result)
            else:
                result = evaluate(binding, load_ledger(ledger_path), now)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, TypeError) as error:
        print(json.dumps({"status": "refused", "error_type": type(error).__name__,
                          "publication_allowed": False, "ai_submission_allowed": False}))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
