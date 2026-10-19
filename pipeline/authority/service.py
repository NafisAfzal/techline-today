"""Trust loading, exact content bindings and publication-time re-verification."""

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from pipeline.authority.ledger import (
    JOURNAL,
    STOP,
    Anchor,
    decode_journal,
    journal_bytes,
    load,
    replay,
    verify_anchor,
)
from pipeline.authority.protocol import MAX_RECORD, ZERO, AuthorityError, Binding, clock
from pipeline.authority.registry import TrustPin
from pipeline.filesystem import confined_file, regular_path
from pipeline.generation import LOCK, assert_stable, bounded_file
from pipeline.review_governance import digest
from pipeline.strict_json import strict_json


@dataclass(frozen=True)
class AuthorityBundle:
    pin_bytes: bytes
    journal_bytes: bytes
    anchor: Anchor | None
    mode: str = "production"
    stopped: bool = False

    def verify(self, now, *, expected_mode="production", anchored=True):
        if self.stopped:
            raise AuthorityError("emergency_hold", "An emergency publication stop requires owner-reviewed recovery")
        if self.mode != expected_mode:
            raise AuthorityError("mode", "Authority evidence belongs to another verification environment")
        pin = TrustPin.model_validate(strict_json(self.pin_bytes, max_bytes=MAX_RECORD))
        history = replay(decode_journal(self.journal_bytes), pin, now, mode=expected_mode)
        if anchored:
            verify_anchor(history, self.anchor, now)
        return history


def assert_readable(root):
    assert_stable(root)
    lock = confined_file(root, LOCK)
    if lock.exists():
        value = strict_json(bounded_file(lock, 8000), max_bytes=8000)
        if (not isinstance(value, dict) or value.get("kind") != "build"
                or not os.environ.get("TECHLINE_BUILD_TOKEN")
                or value.get("token") != os.environ["TECHLINE_BUILD_TOKEN"]):
            raise AuthorityError("writer_pending", "Writer is active or interrupted; inspect the existing lock")


def load_authority(root, *, allow_stopped=False):
    """Production only. Environment inputs are operator trust, not source content.

    No root/key generation, test fixture lookup or repository-local bootstrap.
    Pin files must live outside this checkout; their authenticity/custody remains
    an explicit operator responsibility described in the runbook.
    """
    assert_readable(root)
    stopped = confined_file(root, STOP).exists()
    if stopped and not allow_stopped:
        raise AuthorityError("emergency_hold", "Emergency publication stop is present")
    path = os.environ.get("TECHLINE_AUTHORITY_TRUST_FILE")
    if not path:
        return None
    trust_path = regular_path(Path(path))
    if trust_path.is_relative_to(Path(root).absolute()):
        raise AuthorityError("trust_location", "Owner trust pin must be supplied outside the repository")
    pin_bytes = bounded_file(trust_path, MAX_RECORD)
    # Parse even if no checkpoint is configured, so a fake/unknown registry never
    # becomes a successful status report.
    pin = TrustPin.model_validate(strict_json(pin_bytes, max_bytes=MAX_RECORD))
    if pin.synthetic or pin.environment != "production":
        raise AuthorityError("synthetic", "Production loader refuses synthetic trust roots")
    checkpoint = os.environ.get("TECHLINE_AUTHORITY_CHECKPOINT_FILE")
    expected = os.environ.get("TECHLINE_AUTHORITY_CHECKPOINT_SHA256")
    challenge = os.environ.get("TECHLINE_AUTHORITY_CHALLENGE")
    anchor = None
    if checkpoint and expected and challenge:
        anchor = Anchor(bounded_file(regular_path(Path(checkpoint)), MAX_RECORD), expected, challenge)
    result = AuthorityBundle(pin_bytes, journal_bytes(load(root)), anchor, stopped=stopped)
    assert_readable(root)
    return result


def bind_story(story, source, source_rights, *, language="en", workflow="editorial"):
    from pipeline.editorial_workflow import classify_kind
    story = type(story).model_validate(story.model_dump(mode="json"))
    source = type(source).model_validate(source.model_dump(mode="json"))
    if workflow == "editorial" and story.language != "en":
        raise AuthorityError("language", "English editorial authority requires an English canonical story")
    if source.id not in story.source_ids:
        raise AuthorityError("binding", "Source is not cited by this story")
    kind = classify_kind(source_type=source.source_type, source_class=source.source_class,
                         editorial_kind=source.editorial_kind)
    translation = story.translations.get(language) if language != "en" else None
    if language != "en" and translation is None:
        raise AuthorityError("translation_missing", "No translation exists for this binding")
    return Binding(source_id=source.source_registry_id, story_id=story.id, story_kind=kind,
                   content_sha256=digest(story.model_dump(mode="json", exclude={"translations"})),
                   source_sha256=digest(source.model_dump(mode="json")),
                   rights_sha256=digest(source_rights.get(source.source_registry_id, {})), language=language,
                   language_sha256=digest(translation.model_dump(mode="json")) if translation else ZERO,
                   workflow=workflow)


def bind_candidate(candidate):
    """Technical/rights proposal binding; this never flips source configuration."""
    from pipeline.source_onboarding import SourceCandidate
    candidate = SourceCandidate.model_validate(candidate.model_dump(mode="json"))
    data = candidate.model_dump(mode="json")
    return Binding(source_id=candidate.candidate_id, story_id="candidate:" + candidate.candidate_id,
                   story_kind="REFERENCE", content_sha256=digest(data), source_sha256=candidate.identity,
                   rights_sha256=digest(data["evidence"]), language="en", language_sha256=ZERO, workflow="source")


def source_registry(root):
    from pipeline.models import SourceRegistry
    data = bounded_file(confined_file(root, "config/sources.yaml"), 1_000_000)
    return SourceRegistry.model_validate(yaml.safe_load(data))


def story_evidence(bundle, story, sources, rights, now, *, mode="production"):
    if not isinstance(bundle, AuthorityBundle):
        raise AuthorityError("unprovisioned", "Authenticated owner/reviewer authority is unprovisioned")
    history = bundle.verify(clock(now), expected_mode=mode)
    primary = sources.get(story.primary_source_id)
    if primary is None:
        raise AuthorityError("binding", "Primary source evidence is missing")
    bound = bind_story(story, primary, rights)
    needed = ["FACT_CHECKED", "APPROVED", "PUBLICATION_ELIGIBLE", "PUBLISHED"]
    english = {state: history.active(bound, state, now) for state in needed}
    per_source = {}
    for sid in story.source_ids:
        if sid not in sources:
            raise AuthorityError("binding", "Cited source evidence is missing")
        rb = bind_story(story, sources[sid], rights, workflow="rights")
        per_source[sid] = history.active(rb, "RIGHTS_APPROVED", now)
    native = {}
    native_state = None
    if story.translations.get("bn") is not None:
        translated = bind_story(story, primary, rights, language="bn", workflow="translation")
        native_state = history.state(translated)
        native = {state: history.active(translated, state, now) for state in
                  ["NATIVE_REVIEW_COMPLETE", "APPROVED_TRANSLATION", "PUBLISHED_TRANSLATION"]}
    return {"authenticated": True, "state": history.state(bound), "editorial": english, "rights": per_source,
            "native_bn": native, "editorial_complete": all(english.values()),
            "rights_complete": bool(per_source) and all(per_source.values()),
            "native_complete": all(native.values()) and (not native or native_state == "PUBLISHED_TRANSLATION"),
            "blocked": history.blocked(bound),
            "registry_revision": history.registry.revision, "head_sha256": history.journal.head_sha256,
            "synthetic": history.registry.pin.synthetic}


def status(root, now):
    try:
        bundle = load_authority(root)
        if bundle is None:
            return {"status": "UNPROVISIONED", "production_authority_available": False,
                    "publication_allowed": False, "reason": "No independently pinned owner trust root"}
        history = bundle.verify(now)
        return {"status": "VERIFIED", "production_authority_available": True,
                "registry_revision": history.registry.revision, "event_count": len(history.journal.events),
                "head_sha256": history.journal.head_sha256, "publication_allowed": False,
                "note": "Identity/history verification is not a rights or publication decision"}
    except (ValueError, OSError, TypeError) as error:
        return {"status": "BLOCKED", "production_authority_available": False, "publication_allowed": False,
                "reason": error.code if isinstance(error, AuthorityError) else type(error).__name__}


def assert_build_authority(root, snapshot, now):
    """Negative guard for the unchanged legacy edition; full gate for new content."""
    from pipeline.publication_gate import LEGACY_SNAPSHOT_SHA256, assert_publishable, evaluate_snapshot
    bundle = load_authority(root)
    journal_path = confined_file(root, JOURNAL)
    legacy = hashlib.sha256(confined_file(root, "content/generated/snapshot.json").read_bytes()).hexdigest()
    if legacy == LEGACY_SNAPSHOT_SHA256:
        if journal_path.exists():
            if bundle is None:
                raise AuthorityError("unprovisioned", "Unverifiable authority history cannot be ignored by a legacy build")
            history = bundle.verify(now)
            # A new signed review of a canonical story must not be bypassed by
            # the old edition exception. Only unrelated journal records can pass.
            story_ids = {s.id for s in snapshot.stories}
            registry_ids = {s.source_registry_id for s in snapshot.sources.values()}
            if any(d.payload.binding.story_id in story_ids or
                   d.payload.binding.workflow == "source" and d.payload.binding.source_id in registry_ids
                   for d in history.decisions) or history.registry.revoked_sources & registry_ids:
                raise AuthorityError("legacy_governed", "A governed or withdrawn legacy story requires a fresh reviewed edition")
        return
    if bundle is None:
        raise PermissionError("New live editorial content requires unavailable authenticated review authority")
    rights_path = confined_file(root, "config/source-rights.json")
    source_rights = strict_json(bounded_file(rights_path, MAX_RECORD), max_bytes=MAX_RECORD)["sources"]
    assert_publishable(evaluate_snapshot(snapshot, source_rights, authority=bundle, now=now,
                                         source_registry=source_registry(root)))
    return bundle.verify(now)
