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
    StoryKind,
    classify_kind,
    date_violations,
    story_state,
)

DENIED = "DENIED"
ALLOWED = "ELLOWED"


def _dimension(name, allowed, reasons, evidence):
    return {"dimension": name, "result": ALLOWED if allowed else DENIED, "reasons": sorted(set(reasons)),
            "evidence": evidence}


def evaluate(story, sources, source_rights, *, editorial_ledger=None, now=None,
             build_time=None, require_approval=True):
    """Evaluate one story against every publication dimension.

    ``story`` is a ``pipeline.models.Story``; ``sources`` maps source ids to
    ``SourceItem``; ``source_rights`` is the parsed ``config/source-rights.json``
    source map. The result is diagnostic JSON, never a boolean shortcut.
    """
    now = now or datetime.now(UTC)
    dimensions = []

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
        elif not entry.get("license") or not entry.get("scope"):
            rights_reasons.append(f"rights_evidence_incomplete:{registry_id}")
        if source.rights_review is not None:
            rights_reasons.append(f"item_held_for_review:{sid}")
        if source.editorial_kind != "news":
            rights_reasons.append(f"non_news_source:{sid}")
    if len(cited) != len(story.source_ids):
        rights_reasons.append("missing_source_evidence")
    dimensions.append(_dimension("rights_evidence", not rights_reasons, rights_reasons, rights_evidence))

    # --- source validation ----------------------------------------------------
    source_reasons = []
    if not cited:
        source_reasons.append("no_cited_sources")
    if any(source.is_demo for source in cited):
        source_reasons.append("demo_content")
    if any(not source.publisher for source in cited):
        source_reasons.append("unattributed_source")
    dimensions.append(_dimension("source_validation", not source_reasons, source_reasons,
                                 {"cited": len(story.source_ids), "resolved": len(cited)}))

    # --- editorial authority ---------------------------------------------------
    identity = story_state(editorial_ledger, story.id) if editorial_ledger is not None else "DISCOVERED"
    editorial_reasons = []
    if require_approval:
        if identity in AUTHORITY_GATED:
            editorial_reasons.append("approval_state_unreachable_without_authenticated_editor")
        elif identity not in {"PUBLISHED"}:
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
    translation = story.translations.get("bn")
    if translation is not None:
        if translation.review_status not in {"fixture-reviewed"} and kind in CURRENT_NEWS_KINDS:
            # Machine-translated news must never present as reviewed Bangla.
            language_reasons.append("translation_not_native_reviewed")
        if story.is_demo and translation.review_status == "fixture-reviewed":
            language_reasons.append("fixture_translation_requires_demo_edition")
    dimensions.append(_dimension("language_review", not language_reasons, language_reasons,
                                 {"bn_present": translation is not None,
                                  "review_status": translation.review_status if translation else None}))

    denied = [d for d in dimensions if d["result"] == DENIED]
    return {"story_id": story.id, "allowed": not denied, "dimensions": dimensions,
            "denied_dimensions": [d["dimension"] for d in denied],
            "publication_allowed": not denied, "ai_submission_allowed": False}


def evaluate_snapshot(snapshot, source_rights, *, editorial_ledger=None, now=None,
                      build_time=None, require_approval=True) -> dict:
    """Evaluate every story in a snapshot. Any denial fails the whole edition."""
    now = now or snapshot.generated_at
    build_time = build_time or snapshot.generated_at
    results = [evaluate(story, snapshot.sources, source_rights, editorial_ledger=editorial_ledger,
                        now=now, build_time=build_time, require_approval=require_approval)
               for story in snapshot.stories]
    blocked = [row for row in results if not row["allowed"]]
    return {"version": 1, "story_count": len(results), "blocked_count": len(blocked),
            "blocked": [{"story_id": row["story_id"], "denied_dimensions": row["denied_dimensions"]}
                        for row in blocked],
            "publication_allowed": not blocked, "ai_submission_allowed": False}


def assert_publishable(result) -> None:
    if not result["publication_allowed"]:
        raise PermissionError("Publication refused: " + ", ".join(
            row["story_id"] + ":" + "/".join(row["denied_dimensions"]) for row in result["blocked"][:10]))