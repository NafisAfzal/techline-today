"""Composite publication gate. One satisfied dimension never publishes a story.

Publication requires every independent dimension to hold at once: rights evidence,
source validation, editorial approval, date integrity and a current editorial state.
Any unknown, missing or revoked input denies publication. Nothing here can grant a
permission; it can only refuse.
"""

from datetime import UTC, datetime

from pipeline.editorial_workflow import (
    AUTHORITY_GATED,
    CURRENT_NEWS_KINDS,
    DateEvidence,
    EditorialLedger,
    StoryKind,
    classify_kind,
    date_violations,
    story_identity,
    story_state,
)

DENIED = "DENIED"
ALLOWED = "ALLOWED"
LEGACY_SNAPSHOT_SHA256 = "d146d528ed8b00bc4e3a1e379ceffa300f46ce5a17ee9d34e8291410e9973eb5"


def _dimension(name, allowed, reasons, evidence):
    return {"dimension": name, "result": ALLOWED if allowed else DENIED, "reasons": sorted(set(reasons)),
            "evidence": evidence}


def evaluate(story, sources, source_rights, *, editorial_ledger=None, now=None,
             build_time=None, require_approval=True, authority=None, authority_mode="production",
             source_registry=None):
    """Evaluate one story against every publication dimension.

    ``story`` is a ``pipeline.models.Story``; ``sources`` maps source ids to
    ``SourceItem``; ``source_rights`` is the parsed ``config/source-rights.json``
    source map. The result is diagnostic JSON, never a boolean shortcut.
    """
    now = now or datetime.now(UTC)
    dimensions = []
    authenticated = None
    authority_error = "authenticated_editor_authority_unavailable"
    if authority is not None:
        from pipeline.authority.service import story_evidence
        try:
            authenticated = story_evidence(authority, story, sources, source_rights, now, mode=authority_mode)
        except (ValueError, TypeError, OSError) as error:
            authority_error = "invalid_authenticated_authority:" + getattr(error, "code", type(error).__name__)

    # --- rights evidence ------------------------------------------------------
    rights_reasons, rights_evidence = [], {}
    cited = [sources[sid] for sid in story.source_ids if sid in sources]
    for sid, source in ((sid, sources[sid]) for sid in story.source_ids if sid in sources):
        registry_id = source.source_registry_id
        entry = source_rights.get(registry_id, {})
        decision = entry.get("publication")
        rights_evidence[registry_id] = decision or "ABSENT"
        if decision != "allow":
            rights_reasons.append(f"rights_not_allowed:{registry_id}")
        elif not entry.get("license") or not entry.get("license_url") or not entry.get("scope"):
            rights_reasons.append(f"rights_evidence_incomplete:{registry_id}")
        if source.rights_review is not None:
            rights_reasons.append(f"item_held_for_review:{sid}")
        if source.editorial_kind != "news":
            rights_reasons.append(f"non_news_source:{sid}")
    if len(cited) != len(story.source_ids):
        rights_reasons.append("missing_source_evidence")
    if authenticated is not None and not authenticated["rights_complete"]:
        rights_reasons.append("missing_active_signed_rights_review")
    dimensions.append(_dimension("rights_evidence", not rights_reasons, rights_reasons, rights_evidence))

    # --- source validation ----------------------------------------------------
    source_reasons = []
    if not cited:
        source_reasons.append("no_cited_sources")
    if any(source.is_demo for source in cited):
        source_reasons.append("demo_content")
    if story.is_demo:
        source_reasons.append("demo_story")
    if any(not source.publisher for source in cited):
        source_reasons.append("unattributed_source")
    if authenticated is not None and authority_mode == "production" and source_registry is None:
        source_reasons.append("trusted_source_registry_unavailable")
    if source_registry is not None:
        from pipeline.models import SourceRegistry
        try:
            registry = SourceRegistry.model_validate(source_registry.model_dump(mode="json"))
            configured = {entry.id: entry for entry in registry.sources}
            for source in cited:
                entry = configured.get(source.source_registry_id)
                if entry is None or not entry.enabled:
                    source_reasons.append(f"source_disabled_or_unknown:{source.source_registry_id}")
                elif entry.adapter != source.source_type:
                    source_reasons.append(f"source_adapter_mismatch:{source.source_registry_id}")
        except (ValueError, TypeError, AttributeError):
            source_reasons.append("invalid_source_registry")
    dimensions.append(_dimension("source_validation", not source_reasons, source_reasons,
                                 {"cited": len(story.source_ids), "resolved": len(cited)}))

    # --- editorial authority ---------------------------------------------------
    identity = "DISCOVERED"
    editorial_reasons = [authority_error] if authenticated is None else []
    if authenticated is not None:
        identity = authenticated["state"]
        if not authenticated["editorial_complete"]:
            editorial_reasons.append("missing_active_signed_editorial_reviews")
        if authenticated["blocked"]:
            editorial_reasons.append(authenticated["blocked"])
    # The compatibility flag may request diagnostics, never permission. Hashes and
    # caller-supplied actor names do not establish an authenticated human editor.
    if editorial_ledger is not None:
        try:
            checked = EditorialLedger.model_validate(editorial_ledger.model_dump(mode="python"))
            local_state = story_state(checked, story_identity(story_id=story.id, source_ids=[]))
            if authenticated is None:
                identity = local_state
            if local_state in {"CORRECTED", "RETRACTED", "ARCHIVED"}:
                editorial_reasons.append(f"local_editorial_withdrawal:{local_state}")
        except (ValueError, TypeError, AttributeError):
            editorial_reasons.append("invalid_editorial_ledger")
    if identity in AUTHORITY_GATED and authenticated is None:
        editorial_reasons.append("approval_state_unreachable_without_authenticated_editor")
    elif identity != "PUBLISHED":
        editorial_reasons.append(f"editorial_state_not_published:{identity}")
    if identity in {"RETRACTED", "ARCHIVED"}:
        editorial_reasons.append(f"editorial_state_withdrawn:{identity}")
    if not story.change_log:
        editorial_reasons.append("no_provenance_history")
    if story.ai_metadata.generation_mode == "ai":
        editorial_reasons.append("ai_generation_requires_owner_approval")
    dimensions.append(_dimension("editorial_approval", not editorial_reasons, editorial_reasons,
                                 {"state": identity, "changes": len(story.change_log)}))

    # --- date integrity -------------------------------------------------------
    primary = next((s for s in cited if not s.missing_publication_time), None)
    kind: StoryKind = classify_kind(
        source_type=primary.source_type if primary else "unknown",
        source_class=primary.source_class if primary else "community",
        editorial_kind=primary.editorial_kind if primary else "news")
    dates = DateEvidence(
        published_at=story.published_at if primary is not None else None,
        first_seen_at=story.first_seen_at,
        last_verified_at=story.last_verified_at,
        last_editorial_update=story.updated_at,
        build_time=build_time)
    violations = date_violations(dates, kind, now)
    dimensions.append(_dimension("date_integrity", not violations, violations,
                                 {"kind": kind, "publication_known": dates.published_at is not None}))

    # --- bilingual publication integrity --------------------------------------
    language_reasons = []
    if story.language != "en":
        language_reasons.append("canonical_language_requires_english_source")
    translation = story.translations.get("bn")
    if translation is not None:
        if kind in CURRENT_NEWS_KINDS and (authenticated is None or not authenticated["native_complete"]):
            # Machine-translated news must never present as reviewed Bangla.
            language_reasons.append("translation_not_native_reviewed")
        if translation.review_status == "fixture-reviewed":
            language_reasons.append("fixture_translation_requires_demo_edition")
        from pipeline.translation import canonical_hash
        if translation.canonical_hash != canonical_hash(story):
            language_reasons.append("translation_binding_mismatch")
        from pipeline.translation_governance import integrity_findings
        language_reasons.extend("translation_integrity:" + finding["check"] for finding in
                                integrity_findings(story, translation) if finding["severity"] == "fail")
    dimensions.append(_dimension("language_review", not language_reasons, language_reasons,
                                 {"bn_present": translation is not None,
                                  "review_status": translation.review_status if translation else None}))

    denied = [d for d in dimensions if d["result"] == DENIED]
    return {"story_id": story.id, "allowed": not denied, "dimensions": dimensions,
            "denied_dimensions": [d["dimension"] for d in denied],
            "publication_allowed": not denied, "ai_submission_allowed": False}


def evaluate_snapshot(snapshot, source_rights, *, editorial_ledger=None, now=None,
                      build_time=None, require_approval=True, authority=None, authority_mode="production",
                      source_registry=None) -> dict:
    """Evaluate every story in a snapshot. Any denial fails the whole edition."""
    # Edition metadata is untrusted evidence, never the authority-verification
    # clock. Restoring an old edition must not make expired signatures current.
    now = datetime.now(UTC) if now is None else now
    build_time = build_time or snapshot.generated_at
    results = [evaluate(story, snapshot.sources, source_rights, editorial_ledger=editorial_ledger,
                        now=now, build_time=build_time, require_approval=require_approval,
                        authority=authority, authority_mode=authority_mode, source_registry=source_registry)
               for story in snapshot.stories]
    blocked = [row for row in results if not row["allowed"]]
    return {"version": 1, "story_count": len(results), "blocked_count": len(blocked),
            "blocked": [{"story_id": row["story_id"], "denied_dimensions": row["denied_dimensions"]}
                        for row in blocked],
            "publication_allowed": bool(results) and not blocked, "ai_submission_allowed": False}


def assert_publishable(result) -> None:
    if not result["publication_allowed"]:
        raise PermissionError("Publication refused: " + ", ".join(
            row["story_id"] + ":" + "/".join(row["denied_dimensions"]) for row in result["blocked"][:10]))


def assert_existing_build_safe(root):
    """Keep the legacy build exception; require authenticated gates for new editions.

    Existing rights-reviewed legacy content retains its established checks. Local
    Phase 6 drafts/withdrawals matching that edition cannot be ignored by a rebuild.
    No unsigned draft ledger, hash or mutable actor field grants permission here.
    """
    import hashlib

    from pipeline.editorial_workflow import load_ledger as editorial_ledger
    from pipeline.filesystem import confined_file
    from pipeline.models import Snapshot
    from pipeline.review_governance import bounded_json
    from pipeline.source_onboarding import candidates, signed_candidate_allowed
    from pipeline.source_onboarding import load_ledger as candidate_ledger
    from pipeline.translation_governance import load_ledger as translation_ledger
    from pipeline.translation_governance import translation_state

    path = confined_file(root, "content/generated/snapshot.json")
    snapshot = Snapshot.model_validate(bounded_json(path, limit=50_000_000))
    if snapshot.mode == "fixture":
        return
    from pipeline.authority.service import assert_build_authority
    authority_history = assert_build_authority(root, snapshot, datetime.now(UTC))
    from urllib.parse import urlsplit

    proposed = candidates(root)
    source_ledger = candidate_ledger(root)
    editorial = editorial_ledger(root)
    translations = translation_ledger(root)
    for source in snapshot.sources.values():
        host = (urlsplit(source.canonical_url).hostname or "").lower().removeprefix("www.")
        identity = hashlib.sha256(f"{host}|{source.source_type}|{source.language}".encode()).hexdigest()
        for row in proposed:
            if row["candidate_id"] == source.source_registry_id or row["identity"] == identity:
                if authority_history is None or not signed_candidate_allowed(
                        row, source_ledger, authority_history, datetime.now(UTC)):
                    raise PermissionError("An unapproved, suspended or revoked candidate is still in the generated edition")
    for story in snapshot.stories:
        primary = snapshot.sources.get(story.primary_source_id)
        identities = {
            story_identity(story_id=story.id, source_ids=[]),
            story_identity(story_id=story.id, source_ids=story.source_ids),
            story_identity(story_id=story.id, source_ids=story.source_ids,
                           canonical_url=primary.canonical_url if primary else None),
        }
        matching_editorial = [event for event in editorial.events if event.decision.story_id in identities]
        if matching_editorial and (authority_history is None or
                                  matching_editorial[-1].decision.to_state in {"CORRECTED", "RETRACTED", "ARCHIVED"}):
            raise PermissionError("A locally governed draft or withdrawn story is still in the generated edition")
        withdrawn_translation = any(event.decision.story_identity in identities and
                                    event.decision.to_state == "WITHDRAWN" for event in translations.events)
        legacy_translation = authority_history is None and any(
            translation_state(translations, identity) != "NOT_TRANSLATED" for identity in identities)
        if story.translations.get("bn") and (withdrawn_translation or legacy_translation):
            raise PermissionError("A draft or withdrawn translation is still in the generated edition")


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Refuse stale generated content affected by local governance")
    parser.add_argument("--existing-build", action="store_true", required=True)
    parser.parse_args()
    try:
        assert_existing_build_safe(Path.cwd())
    except (ValueError, OSError, TypeError) as error:
        print(json.dumps({"status": "refused", "error_type": type(error).__name__, "publication_allowed": False}))
        raise SystemExit(1) from None
    print(json.dumps({"status": "passed", "publication_allowed": False}))
