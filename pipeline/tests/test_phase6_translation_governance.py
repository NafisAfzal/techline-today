"""Bilingual governance adversarial tests: fallback, staleness and native review."""

import json
from datetime import UTC, datetime, timedelta

import pytest

from pipeline.editorial_workflow import story_identity
from pipeline.translation_governance import (
    AUTHORITY_GATED,
    AuthorityUnavailable,
    TranslationRecord,
    backlog,
    edition_language_report,
    integrity_findings,
    load_ledger,
    make_record,
    meaningful_change,
    record,
    staleness,
    translation_state,
)

NOW = datetime(2026, 10, 19, 9, tzinfo=UTC)
SID = "src_" + "a" * 20


class FakeContent:
    def __init__(self, **overrides):
        base = {"headline": "কৃত্রিম শিরোনাম এখানে রয়েছে এবং যাচাই করা হয়েছে",
                "summary_bullets": ["প্রথম পর্যবেক্ষণ এখানে রয়েছে।", "দ্বিতীয় পর্যবেক্ষণ এখানে রয়েছে।",
                                    "তৃতীয় পর্যবেক্ষণ এখানে রয়েছে।"],
                "why_it_matters": "এটি একটি কৃত্রিম ব্যাখ্যা।",
                "broader_summary": "কৃত্রিম বিবরণ এখানে রয়েছে।",
                "key_fact_texts": ["কৃত্রিম তথ্য এখানে রয়েছে।"],
                "number_labels": [], "number_contexts": [], "limitations": []}
        self.__dict__.update({**base, **overrides})


class FakeTranslation:
    def __init__(self, **content_overrides):
        self.language = "bn"
        self.canonical_hash = "a" * 64
        self.review_status = "automated"
        self.content = FakeContent(**content_overrides)


class FakeStory:
    def __init__(self, language="en", headline="An English headline for the synthetic test story"):
        self.id = "story_1"
        self.slug = "an-english-headline"
        self.language = language
        self.headline = headline
        self.summary_bullets = ["First synthetic observation for verification purposes.",
                                "Second synthetic observation retained as evidence.",
                                "Third synthetic observation retained as evidence."]
        self.translations = {}


def ident(story_ref="story_1"):
    return story_identity(story_id=story_ref, source_ids=[])


# --- lifecycle -----------------------------------------------------------------

def test_draft_translation_can_be_recorded(root):
    rec = make_record("story_1", source_version="b" * 64, translation_version="c" * 64,
                      provider="example", model="example-v1", source_ids=[SID])
    event = record(rec, "NOT_TRANSLATED", "DRAFT_TRANSLATION", actor="pipeline", now=NOW,
                   reason="Machine draft produced.", root=root)
    assert event.decision.to_state == "DRAFT_TRANSLATION"
    assert translation_state(load_ledger(root), rec.story_identity) == "DRAFT_TRANSLATION"


def test_draft_can_enter_the_review_queue(root):
    rec = make_record("story_1", source_version="b" * 64, translation_version="c" * 64, source_ids=[SID])
    record(rec, "NOT_TRANSLATED", "DRAFT_TRANSLATION", actor="pipeline", now=NOW, reason="Draft.", root=root)
    record(rec, "DRAFT_TRANSLATION", "LANGUAGE_REVIEW_PENDING", actor="pipeline", now=NOW + timedelta(minutes=1),
           reason="Queued for a native reviewer.", root=root)
    assert translation_state(load_ledger(root), rec.story_identity) == "LANGUAGE_REVIEW_PENDING"
    assert backlog(load_ledger(root), root)[0]["blockers"] == ["awaiting_native_reviewer"]


@pytest.mark.parametrize("target", sorted(AUTHORITY_GATED))
def test_native_review_states_are_blocked(root, target):
    rec = make_record("story_1", source_version="b" * 64, translation_version="c" * 64, source_ids=[SID])
    record(rec, "NOT_TRANSLATED", "DRAFT_TRANSLATION", actor="pipeline", now=NOW, reason="Draft.", root=root)
    record(rec, "DRAFT_TRANSLATION", "LANGUAGE_REVIEW_PENDING", actor="pipeline", now=NOW + timedelta(minutes=1),
           reason="Queued.", root=root)
    with pytest.raises(AuthorityUnavailable, match="native Bangla reviewer"):
        record(rec, "LANGUAGE_REVIEW_PENDING", target, actor="pipeline", now=NOW + timedelta(minutes=2),
               reason="Approve.", root=root)


def test_machine_translation_cannot_be_marked_native_reviewed():
    with pytest.raises(ValueError, match="native reviewer reference"):
        TranslationRecord(story_identity=ident(), source_version="b" * 64, translation_version="c" * 64,
                          state="NATIVE_REVIEW_COMPLETE")


def test_illegal_transition_is_refused(root):
    rec = make_record("story_1", source_version="b" * 64, translation_version="c" * 64, source_ids=[SID])
    with pytest.raises(ValueError, match="Illegal translation transition"):
        record(rec, "NOT_TRANSLATED", "LANGUAGE_REVIEW_PENDING", actor="pipeline", now=NOW,
               reason="Skip.", root=root)


def test_withdrawal_is_reachable(root):
    rec = make_record("story_1", source_version="b" * 64, translation_version="c" * 64, source_ids=[SID])
    record(rec, "NOT_TRANSLATED", "DRAFT_TRANSLATION", actor="pipeline", now=NOW, reason="Draft.", root=root)
    record(rec, "DRAFT_TRANSLATION", "WITHDRAWN", actor="pipeline", now=NOW + timedelta(minutes=1),
           reason="Reviewer declined the draft.", root=root)
    assert translation_state(load_ledger(root), rec.story_identity) == "WITHDRAWN"


def test_forged_native_review_ledger_is_rejected(root):
    from pipeline.review_governance import digest
    from pipeline.translation_governance import TranslationDecision
    rec = make_record("story_1", source_version="b" * 64, translation_version="c" * 64, source_ids=[SID])
    record(rec, "NOT_TRANSLATED", "DRAFT_TRANSLATION", actor="pipeline", now=NOW, reason="Draft.", root=root)
    path = root / ".cache/phase6/translation-decisions.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    decision = TranslationDecision(from_state="DRAFT_TRANSLATION", to_state="NATIVE_REVIEW_COMPLETE",
                                   actor="named-native-reviewer", at=NOW + timedelta(hours=1),
                                   reason="Reviewed by a native speaker.", story_identity=rec.story_identity,
                                   reviewer_reference="named-native-reviewer")
    body = {"sequence": 2, "previous_sha256": payload["head_sha256"],
            "decision": decision.model_dump(mode="json")}
    event = {**body, "event_sha256": digest(body)}
    payload["events"].append(event)
    payload["head_sha256"] = event["event_sha256"]
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="cannot authorise"):
        load_ledger(root)


def test_tampered_translation_ledger_is_detected(root):
    rec = make_record("story_1", source_version="b" * 64, translation_version="c" * 64, source_ids=[SID])
    record(rec, "NOT_TRANSLATED", "DRAFT_TRANSLATION", actor="pipeline", now=NOW, reason="Draft.", root=root)
    path = root / ".cache/phase6/translation-decisions.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["events"][0]["decision"]["actor"] = "owner"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="Corrupted or reordered"):
        load_ledger(root)


# --- staleness -----------------------------------------------------------------

def test_unchanged_source_leaves_review_state_alone():
    rec = TranslationRecord(story_identity=ident(), source_version="b" * 64, translation_version="c" * 64,
                            state="DRAFT_TRANSLATION")
    assert staleness(rec, "b" * 64) is rec


def test_meaningful_source_change_returns_translation_to_review():
    rec = TranslationRecord(story_identity=ident(), source_version="b" * 64, translation_version="c" * 64,
                            state="APPROVED_TRANSLATION", native_reviewer_reference="reviewer",
                            last_review_at=NOW)
    result = staleness(rec, "d" * 64, {"headline": "Old"}, {"headline": "New"})
    assert result.state == "LANGUAGE_REVIEW_PENDING"
    assert result.stale is True
    assert result.native_reviewer_reference is None
    assert result.last_review_at is None


def test_metadata_only_change_does_not_force_re_review():
    rec = TranslationRecord(story_identity=ident(), source_version="b" * 64, translation_version="c" * 64,
                            state="APPROVED_TRANSLATION", native_reviewer_reference="reviewer",
                            last_review_at=NOW)
    result = staleness(rec, "b" * 64, {"headline": "Same", "last_verified_at": "old"},
                       {"headline": "Same", "last_verified_at": "new"})
    assert result.state == "APPROVED_TRANSLATION"
    assert result.source_version == "b" * 64


def test_meaningful_change_only_considers_reader_visible_fields():
    assert meaningful_change({"headline": "A"}, {"headline": "B"}) is True
    assert meaningful_change({"headline": "A"}, {"headline": "A"}) is False


def test_stale_translation_cannot_hold_an_approved_state():
    with pytest.raises(ValueError, match="stale translation cannot hold"):
        TranslationRecord(story_identity=ident(), source_version="b" * 64, translation_version="c" * 64,
                          state="APPROVED_TRANSLATION", native_reviewer_reference="reviewer",
                          stale=True, stale_reason="english_source_changed_after_review")


def test_correction_is_not_silently_dropped():
    rec = TranslationRecord(story_identity=ident(), source_version="b" * 64, translation_version="c" * 64,
                            state="APPROVED_TRANSLATION", native_reviewer_reference="reviewer",
                            last_review_at=NOW, corrected_at=NOW)
    assert rec.corrected_at == NOW


# --- language integrity --------------------------------------------------------

def test_missing_translation_is_reported_as_fallback_not_failure():
    findings = integrity_findings(FakeStory(), None)
    assert [f["check"] for f in findings] == ["translation_absent"]
    assert findings[0]["severity"] == "notice"


def test_english_fallback_mislabelled_as_bangla_is_detected():
    translation = FakeTranslation(headline="An English headline presented as Bangla content")
    findings = integrity_findings(FakeStory(), translation)
    assert "english_fallback_mislabelled" in [f["check"] for f in findings]


def test_empty_translation_field_is_detected():
    translation = FakeTranslation(broader_summary="   ")
    findings = integrity_findings(FakeStory(), translation)
    assert "empty_translation_field" in [f["check"] for f in findings]


def test_broken_unicode_is_detected():
    translation = FakeTranslation(broader_summary="কৃত্রিম � বিবরণ")
    findings = integrity_findings(FakeStory(), translation)
    assert "broken_unicode" in [f["check"] for f in findings]


def test_mojibake_is_detected():
    translation = FakeTranslation(broader_summary="à¦•à¦§à¦¤à¦§à¦£à¦—à¦¶à¦° à¦¬à¦•à¦§à¦£à¦§à¦")
    findings = integrity_findings(FakeStory(), translation)
    assert "broken_unicode" in [f["check"] for f in findings]


def test_bangla_in_the_english_source_is_detected():
    translation = FakeTranslation()
    findings = integrity_findings(FakeStory(headline="একটি বাংলা শিরোনাম"), translation)
    assert "source_language_mismatch" in [f["check"] for f in findings]


def test_wrong_language_tag_is_detected():
    story = FakeStory(language="fr")
    findings = integrity_findings(story, FakeTranslation())
    assert "story_language_tag" in [f["check"] for f in findings]


def test_valid_bangla_translation_has_no_blocking_findings():
    findings = integrity_findings(FakeStory(), FakeTranslation())
    assert [f for f in findings if f["severity"] == "fail"] == []


def test_edition_report_counts_bilingual_coverage():
    first, second = FakeStory(), FakeStory()
    second.translations = {"bn": FakeTranslation()}
    result = edition_language_report([first, second])
    assert result["story_count"] == 2
    assert result["translated_count"] == 1
    assert result["native_reviewed_count"] == 0
    assert result["publication_allowed"] is False
