"""Editorial lifecycle and composite publication gate adversarial tests."""

from datetime import UTC, datetime, timedelta

import pytest

from pipeline.editorial_workflow import (
    AUTHORITY_GATED,
    AuthorityUnavailable,
    DateEvidence,
    DecisionRecord,
    classify_kind,
    date_violations,
    load_ledger,
    record,
    review_queue,
    story_identity,
    story_state,
)
from pipeline.models import (
    AIMetadata,
    Change,
    Fact,
    Snapshot,
    SourceItem,
    Story,
)
from pipeline.publication_gate import assert_publishable, evaluate, evaluate_snapshot

NOW = datetime(2026, 10, 19, 9, tzinfo=UTC)
PAST = NOW - timedelta(hours=6)
EARLIER = NOW - timedelta(days=1)
SID = "src_" + "a" * 20
RID = "arxivid_technology"


def ident(story_ref="story_c"):
    """The stable editorial identity used in ledger records."""
    return story_identity(story_id=story_ref, source_ids=[])


def advance(root, *states):
    """Walk the lifecycle legally so later decisions have a real prior state."""
    previous, at = "DISCOVERED", NOW
    for state in states:
        record("story_c", previous, state, actor="pipeline", now=at, reason="Fixture progression.",
               fact_check_reference="checklist-fixture" if state == "FACT_CHECKED" else None,
               retraction_reason="Fixture withdrawal." if state == "RETRACTED" else None, root=root)
        previous, at = state, at + timedelta(minutes=1)


def source(**overrides):
    base = {"id": SID, "source_registry_id": "arxiv", "canonical_url": "https://arxiv.org/abs/2601.00001",
            "original_url": "https://arxiv.org/abs/2601.00001", "domain": "arxiv.org",
            "publisher": "arXiv", "title": "A measured technical result for synthetic testing",
            "author": "A. Author", "published_at": PAST, "fetched_at": PAST, "source_type": "arxiv",
            "source_class": "primary", "source_independence_group": "arxiv-authors",
            "content_hash": "b" * 64, "excerpt": "Synthetic prose used only in tests.", "category": "research"}
    return SourceItem.model_validate({**base, **overrides})


def story(**overrides):
    base = {"id": "story_" + "c" * 16, "slug": "synthetic-story-cccccc", "canonical_topic": "synthetic",
            "source_ids": [SID], "primary_source_id": SID, "evidence_state": "primary-confirmed",
            "published_at": PAST, "first_seen_at": EARLIER, "updated_at": PAST, "last_verified_at": PAST,
            "importance_score_internal": 0.5, "novelty_score_internal": 1.0,
            "change_log": [Change(at=PAST, text="First published from the cited source evidence.",
                                  source_ids=[SID])],
            "ai_metadata": AIMetadata(generation_mode="extractive", evidence_hash="c" * 64),
            **dict(headline="A synthetic measured result for testing purposes",
                                            summary_bullets=["First synthetic observation for the test suite.",
                                                              "Second synthetic observation retained as evidence.",
                                                              "Third synthetic observation for completeness."],
                                            why_it_matters="Establishes reproducible local verification.",
                                            broader_summary="Synthetic prose for offline verification only.",
                                            key_facts=[Fact(text="Synthetic fact for verification tests.",
                                                            source_ids=[SID], attribution="primary")],
                                            claim_map=[
                                                Fact(text="First synthetic observation for the test suite.",
                                                     source_ids=[SID], attribution="primary"),
                                                Fact(text="Second synthetic observation retained as evidence.",
                                                     source_ids=[SID], attribution="primary"),
                                                Fact(text="Third synthetic observation for completeness.",
                                                     source_ids=[SID], attribution="primary")],
                                            category="research")}
    return Story.model_validate({**base, **overrides})


RIGHTS_ALLOW = {"arxiv": {"publication": "allow", "license": "CC0-1.0",
                          "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
                          "scope": "Descriptive metadata only: titles, abstracts, authors and identifiers."}}


# --- lifecycle transitions -----------------------------------------------------

def test_story_state_is_keyed_by_stable_identity(root):
    record("story_c", "DISCOVERED", "SOURCE_VALIDATED", actor="pipeline", now=NOW, reason="V.", root=root)
    assert story_state(load_ledger(root), "story_c") == "DISCOVERED"
    assert story_state(load_ledger(root), ident()) == "SOURCE_VALIDATED"


def test_forward_transitions_are_recorded(root):
    event = record("story_c", "DISCOVERED", "SOURCE_VALIDATED", actor="pipeline", now=NOW,
                   reason="Source parsed and normalised.", root=root)
    assert event.decision.to_state == "SOURCE_VALIDATED"
    assert story_state(load_ledger(root), ident()) == "SOURCE_VALIDATED"


@pytest.mark.parametrize("target", sorted(AUTHORITY_GATED))
def test_approval_transitions_are_blocked(root, target):
    with pytest.raises(AuthorityUnavailable, match="authenticated editor identity"):
        record("story_c", "FACT_CHECKED", target, actor="pipeline", now=NOW,
               reason="Attempted approval.", root=root)


def test_illegal_transition_is_refused(root):
    with pytest.raises(ValueError, match="Illegal editorial transition"):
        record("story_c", "DISCOVERED", "FACT_CHECKED", actor="pipeline", now=NOW,
               reason="Skip ahead.", root=root)


def test_fact_check_requires_evidence(root):
    advance(root, "SOURCE_VALIDATED", "RIGHTS_ELIGIBLE", "DRAFT_READY", "FACT_CHECK_PENDING")
    with pytest.raises(ValueError, match="checklist reference"):
        record("story_c", "FACT_CHECK_PENDING", "FACT_CHECKED", actor="reviewer", now=NOW + timedelta(hours=2),
               reason="Checked.", root=root)
    event = record("story_c", "FACT_CHECK_PENDING", "FACT_CHECKED", actor="reviewer",
                   now=NOW + timedelta(hours=3),
                   reason="Checked against cited evidence.", fact_check_reference="checklist-2026-10-19-a",
                   root=root)
    assert event.decision.fact_check_reference == "checklist-2026-10-19-a"


def test_retraction_requires_a_reason(root):
    advance(root, "SOURCE_VALIDATED", "RIGHTS_ELIGIBLE", "DRAFT_READY")
    with pytest.raises(ValueError, match="recorded reason"):
        record("story_c", "DRAFT_READY", "RETRACTED", actor="pipeline", now=NOW,
               reason="Remove.", root=root)


def test_retraction_is_reachable_from_any_non_terminal_state(root):
    advance(root, "SOURCE_VALIDATED", "RIGHTS_ELIGIBLE", "RETRACTED")
    assert story_state(load_ledger(root), ident()) == "RETRACTED"


def test_approval_attempt_is_refused_even_from_a_valid_prior_state(root):
    advance(root, "SOURCE_VALIDATED", "RIGHTS_ELIGIBLE", "DRAFT_READY", "FACT_CHECK_PENDING", "FACT_CHECKED",
            "EDITORIAL_APPROVAL_PENDING")
    with pytest.raises(AuthorityUnavailable):
        record("story_c", "EDITORIAL_APPROVAL_PENDING", "APPROVED", actor="owner-editor", now=NOW,
               reason="Approved by the owner.", root=root)
    assert story_state(load_ledger(root), ident()) == "EDITORIAL_APPROVAL_PENDING"


def test_tampered_editorial_ledger_is_detected(root):
    record("story_c", "DISCOVERED", "SOURCE_VALIDATED", actor="pipeline", now=NOW,
           reason="Validated.", root=root)
    import json
    path = root / ".cache/phase6/editorial-decisions.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["events"][0]["decision"]["actor"] = "owner"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="Corrupted or reordered"):
        load_ledger(root)


def test_forged_approval_ledger_is_rejected(root):
    import json

    from pipeline.review_governance import digest
    record("story_c", "DISCOVERED", "SOURCE_VALIDATED", actor="pipeline", now=NOW,
           reason="Validated.", root=root)
    path = root / ".cache/phase6/editorial-decisions.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    decision = DecisionRecord(from_state="SOURCE_VALIDATED", to_state="APPROVED", actor="owner-editor",
                              at=NOW + timedelta(hours=1), reason="Approved.", story_id=ident())
    body = {"sequence": 2, "previous_sha256": payload["head_sha256"], "decision": decision.model_dump(mode="json")}
    event = {**body, "event_sha256": digest(body)}
    payload["events"].append(event)
    payload["head_sha256"] = event["event_sha256"]
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="cannot authorise"):
        load_ledger(root)


def test_story_identity_is_stable_and_order_independent():
    a = story_identity(story_id="story_1", source_ids=["b", "a"], canonical_url="https://arxiv.org/abs/1")
    b = story_identity(story_id="story_1", source_ids=["a", "b"], canonical_url="https://arxiv.org/abs/1")
    assert a == b
    assert a != story_identity(story_id="story_1", source_ids=["a"], canonical_url="https://arxiv.org/abs/1")


def test_queue_reports_missing_approval(root):
    record("story_c", "DISCOVERED", "SOURCE_VALIDATED", actor="pipeline", now=NOW,
           reason="Validated.", root=root)
    queue = review_queue(load_ledger(root), root)
    assert queue[0]["publication_allowed"] is False
    assert "awaiting_editorial_decision" in queue[0]["blockers"]


# --- news versus research classification --------------------------------------

def test_research_is_never_current_news_by_recency():
    assert classify_kind(source_type="arxiv", source_class="primary") == "RESEARCH"
    assert classify_kind(source_type="rss", source_class="primary") == "NEWS"
    assert classify_kind(source_type="github_document", source_class="primary") == "EVERGREEN"
    assert classify_kind(source_type="github_releases", source_class="primary") == "OFFICIAL_RELEASE"
    assert classify_kind(source_type="rss", source_class="community") == "REFERENCE"


def test_build_timestamp_must_not_become_the_publication_date():
    dates = DateEvidence(published_at=NOW, first_seen_at=EARLIER, last_verified_at=NOW,
                         build_time=NOW)
    findings = date_violations(dates, "NEWS", NOW + timedelta(minutes=1))
    assert "publication_date_matches_build_time" in findings


def test_unknown_publication_date_is_reported_not_filled():
    dates = DateEvidence(published_at=None, first_seen_at=EARLIER, last_verified_at=EARLIER)
    assert "publication_date_unknown" in date_violations(dates, "NEWS", NOW)


def test_future_publication_date_is_reported():
    dates = DateEvidence(published_at=NOW + timedelta(days=2), first_seen_at=NOW, last_verified_at=NOW)
    assert "publication_date_in_future" in date_violations(dates, "NEWS", NOW)


def test_inconsistent_date_ordering_is_refused():
    with pytest.raises(ValueError, match="Inconsistent dates"):
        DateEvidence(published_at=PAST, first_seen_at=NOW, last_verified_at=PAST)


# --- composite publication gate ------------------------------------------------

def test_story_with_rights_but_no_approval_is_denied():
    result = evaluate(story(), {SID: source()}, RIGHTS_ALLOW, now=NOW, build_time=NOW)
    assert result["allowed"] is False
    assert "editorial_approval" in result["denied_dimensions"]


def test_approval_without_rights_evidence_is_denied():
    result = evaluate(story(), {SID: source()}, {"arxiv": {"publication": "exclude"}}, now=NOW, build_time=NOW)
    assert "rights_evidence" in result["denied_dimensions"]


def test_rights_allow_without_license_scope_is_denied():
    partial = {"arxiv": {"publication": "allow"}}
    result = evaluate(story(), {SID: source()}, partial, now=NOW, build_time=NOW)
    assert "rights_evidence_incomplete:arxiv" in result["dimensions"][0]["reasons"]


def test_missing_source_evidence_is_denied():
    result = evaluate(story(), {}, RIGHTS_ALLOW, now=NOW, build_time=NOW)
    assert "missing_source_evidence" in result["dimensions"][0]["reasons"]


def test_item_held_for_rights_review_is_denied():
    held = source(rights_review={"state": "REVIEW_REQUIRED", "reasons": ["license_missing"],
                                 "evidence_sha256": "d" * 64})
    result = evaluate(story(), {SID: held}, RIGHTS_ALLOW, now=NOW, build_time=NOW)
    assert "rights_evidence" in result["denied_dimensions"]


def test_security_advisory_sources_cannot_publish_as_news():
    advisory = source(source_registry_id="cisa_kev", source_type="json_api",
                      editorial_kind="security-advisory", published_at=None, missing_publication_time=True,
                      advisory={"catalog_added_on": "2026-10-01", "remediation_due_on": "2026-11-01"})
    result = evaluate(story(), {SID: advisory}, RIGHTS_ALLOW, now=NOW, build_time=NOW)
    assert "rights_evidence" in result["denied_dimensions"]


def test_demo_content_is_denied():
    result = evaluate(story(), {SID: source(is_demo=True)}, RIGHTS_ALLOW, now=NOW, build_time=NOW)
    assert "source_validation" in result["denied_dimensions"]


def test_ai_generated_story_is_denied():
    generated = story(ai_metadata=AIMetadata(generation_mode="ai", evidence_hash="c" * 64))
    result = evaluate(generated, {SID: source()}, RIGHTS_ALLOW, now=NOW, build_time=NOW)
    assert "ai_generation_requires_owner_approval" in result["dimensions"][2]["reasons"]


def test_machine_translation_of_news_is_denied():
    news_source = source(source_registry_id="example_news", source_type="rss", category="ai")
    translated = story(translations={"bn": {
        "language": "bn", "canonical_hash": "e" * 64, "cache_key": "f" * 64, "provider": "example",
        "model": "example-v1", "generated_at": NOW, "review_status": "automated",
        "content": {"headline": "কৃত্রিম পরীক্ষা শিরোনাম এখানে রয়েছে এবং যাচাই করা হয়েছে",
                    "summary_bullets": ["প্রথম কৃত্রিম পর্যবেক্ষণ এখানে রয়েছে এবং যাচাই করা হয়েছে।",
                                        "দ্বিতীয় কৃত্রিম পর্যবেক্ষণ এখানে রয়েছে এবং যাচাই করা হয়েছে।",
                                        "তৃতীয় কৃত্রিম পর্যবেক্ষণ এখানে রয়েছে এবং যাচাই করা হয়েছে।"],
                    "why_it_matters": "এটি একটি কৃত্রিম যাচাইকরণ ব্যাখ্যা।",
                    "broader_summary": "কৃত্রিম বিবরণ এখানে রয়েছে এবং যাচাই করা হয়েছে।",
                    "key_fact_texts": ["কৃত্রিম তথ্য এখানে রয়েছে এবং যাচাই করা হয়েছে।"]}}})
    rights = {"example_news": {"publication": "allow", "license": "CC-BY-4.0",
                               "license_url": "https://creativecommons.org/licenses/by/4.0/",
                               "scope": "Attributed excerpts."}}
    result = evaluate(translated, {SID: news_source}, rights, now=NOW, build_time=NOW)
    assert result["dimensions"][0]["result"] == "ALLOWED"
    assert "translation_not_native_reviewed" in result["dimensions"][4]["reasons"]


def test_no_provenance_history_is_denied():
    unprovenanced = story(change_log=[])
    result = evaluate(unprovenanced, {SID: source()}, RIGHTS_ALLOW, now=NOW, build_time=NOW)
    assert "no_provenance_history" in result["dimensions"][2]["reasons"]


def test_every_dimension_must_hold_not_just_one():
    """A story with only rights satisfied still fails on the editorial dimension."""
    result = evaluate(story(), {SID: source()}, RIGHTS_ALLOW, now=NOW, build_time=NOW)
    satisfied = [d["dimension"] for d in result["dimensions"] if d["result"] == "ALLOWED"]
    assert "rights_evidence" in satisfied
    assert result["allowed"] is False


def test_snapshot_gate_blocks_entire_edition_when_any_story_fails():
    snapshot = Snapshot(mode="fixture", generated_at=NOW, last_successful_fetch_at=NOW,
                        categories={"research": {"label": "Research", "slug": "research"}},
                        stories=[story()], sources={SID: source(is_demo=True)}, digests=[],
                        offers=[], model_releases=[])
    result = evaluate_snapshot(snapshot, RIGHTS_ALLOW, now=NOW)
    assert result["publication_allowed"] is False
    assert result["blocked_count"] == 1
    with pytest.raises(PermissionError, match="Publication refused"):
        assert_publishable(result)


def test_empty_rights_map_denies_everything():
    result = evaluate(story(), {SID: source()}, {}, now=NOW, build_time=NOW)
    assert "rights_not_allowed:arxiv" in result["dimensions"][0]["reasons"]
