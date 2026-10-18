"""Independent adversarial regressions; every approval here is synthetic, never authority."""

import hashlib
import json
from datetime import timedelta

import pytest

from pipeline import editorial_workflow as editorial
from pipeline import publication_gate as gate
from pipeline import readiness
from pipeline import source_onboarding as onboarding
from pipeline import translation_governance as translation
from pipeline.review_governance import digest
from pipeline.tests.test_phase6_editorial_gate import NOW, RIGHTS_ALLOW, SID, source, story
from pipeline.tests.test_phase6_readiness import series
from pipeline.tests.test_phase6_source_onboarding import candidate


def rehash(payload):
    """An attacker can recompute every unkeyed hash. This is not a signature."""
    previous = "0" * 64
    for index, event in enumerate(payload["events"], 1):
        event.update(sequence=index, previous_sha256=previous)
        event["event_sha256"] = digest({k: v for k, v in event.items() if k != "event_sha256"})
        previous = event["event_sha256"]
    payload["head_sha256"] = previous
    return payload


def test_approval_switch_cannot_authorize_publication():
    result = gate.evaluate(story(), {SID: source()}, RIGHTS_ALLOW, now=NOW, require_approval=False)
    assert result["publication_allowed"] is False
    assert "editorial_approval" in result["denied_dimensions"]


def test_gate_resolves_the_same_identity_as_editorial_record(root):
    editorial.record(story().id, "DISCOVERED", "RETRACTED", actor="test-operator", now=NOW,
                     reason="Synthetic withdrawal", retraction_reason="Synthetic withdrawal", root=root)
    result = gate.evaluate(story(), {SID: source()}, RIGHTS_ALLOW,
                           editorial_ledger=editorial.load_ledger(root), now=NOW)
    assert result["dimensions"][2]["evidence"]["state"] == "RETRACTED"


def test_empty_edition_is_not_publishable():
    from pipeline.models import Snapshot
    snapshot = Snapshot(mode="fixture", generated_at=NOW, last_successful_fetch_at=NOW,
                        categories={}, stories=[], sources={}, digests=[], offers=[], model_releases=[])
    result = gate.evaluate_snapshot(snapshot, RIGHTS_ALLOW, require_approval=False)
    assert not result["publication_allowed"]
    with pytest.raises(PermissionError):
        gate.assert_publishable(result)


def test_source_with_observation_timestamp_survives_registration(root):
    record = candidate(last_fetch_observed_at=NOW)
    onboarding.register(record, actor="test-operator", now=NOW, root=root)
    assert onboarding.candidate_identity(record.model_dump(mode="json")) == record.identity


def test_forged_permission_reference_cannot_be_registered(root):
    forged = candidate(summary_allowed=True, rights_evidence_status="EVIDENCE_RECORDED",
                       evidence=[{"url": "https://news.example.org/license", "kind": "license",
                                  "note": "Synthetic untrusted permission claim"}],
                       reviewer_reference="forged-reviewer", review_decision_at=NOW)
    with pytest.raises(onboarding.AuthorityUnavailable):
        onboarding.register(forged, actor="forged-reviewer", now=NOW, root=root)


def test_rehashed_registration_cannot_erase_revocation(root):
    onboarding.register(candidate(), actor="test-operator", now=NOW, root=root)
    onboarding.transition(candidate(), "REVOKED", actor="test-operator", now=NOW,
                          reason="Synthetic revocation", root=root)
    path = root / onboarding.LEDGER
    payload = json.loads(path.read_text("utf-8"))
    payload["events"].append(dict(payload["events"][0]))
    path.write_text(json.dumps(rehash(payload)), encoding="utf-8")
    with pytest.raises(ValueError):
        onboarding.load_ledger(root)


def test_orphan_candidate_event_produces_controlled_refusal(root):
    onboarding.register(candidate(), actor="test-operator", now=NOW, root=root)
    onboarding.transition(candidate(), "REVOKED", actor="test-operator", now=NOW,
                          reason="Synthetic revocation", root=root)
    path = root / onboarding.LEDGER
    payload = json.loads(path.read_text("utf-8"))
    payload["events"] = [payload["events"][1]]
    path.write_text(json.dumps(rehash(payload)), encoding="utf-8")
    with pytest.raises(ValueError):
        onboarding.load_ledger(root)


def test_rehashed_editorial_from_state_lie_is_refused(root):
    editorial.record("story_c", "DISCOVERED", "SOURCE_VALIDATED", actor="test", now=NOW,
                     reason="Synthetic validation", root=root)
    path = root / editorial.LEDGER
    payload = json.loads(path.read_text("utf-8"))
    payload["events"][0]["decision"]["from_state"] = "PUBLISHED"
    path.write_text(json.dumps(rehash(payload)), encoding="utf-8")
    with pytest.raises(ValueError):
        editorial.load_ledger(root)


@pytest.mark.parametrize("field", ["limitations", "number_labels", "number_contexts", "key_facts", "claim_map"])
def test_reader_visible_changes_invalidate_translation_review(field):
    record = translation.TranslationRecord(story_identity="a" * 64, source_version="b" * 64,
                                            translation_version="c" * 64, state="APPROVED_TRANSLATION",
                                            native_reviewer_reference="synthetic-untrusted", last_review_at=NOW)
    changed = translation.staleness(record, "d" * 64, {field: ["Old"]}, {field: ["New"]})
    assert changed.state == "LANGUAGE_REVIEW_PENDING"
    assert changed.native_reviewer_reference is None


def test_live_story_translation_is_checked_against_actual_canonical_hash():
    from pipeline.tests.test_phase6_translation_governance import FakeTranslation
    findings = translation.integrity_findings(story(), FakeTranslation())
    assert "translation_binding_mismatch" in [row["check"] for row in findings]


def test_unhashed_receipts_do_not_establish_readiness():
    assert readiness.observation_evidence(series(range(10, 18)), NOW)["eligible"] is False


@pytest.mark.parametrize("evidence", [{"unrelated": True}, {"violations": None}, {"violations": False}])
def test_missing_accessibility_results_are_not_pass(evidence):
    assert readiness.accessibility_checks(evidence)["result"] != readiness.PASS


@pytest.mark.parametrize("config", [None, {}, {"ai_enabled": "true", "schedule_enabled": False},
                                   {"ai_enabled": False, "schedule_enabled": False,
                                    "initial_seed_authorized": True}])
def test_missing_or_unsafe_security_configuration_is_not_pass(config):
    assert readiness.security_configuration(config)["result"] != readiness.PASS


@pytest.mark.parametrize("state", ["COLLECTION_FAILED", "COLLECTION_DEGRADED", None])
def test_failed_or_unknown_diagnostics_are_not_success(state):
    assert readiness.ingestion_failure_rate({"sources": [{"collection_state": state}]})["result"] != readiness.PASS


def test_unknown_source_mapping_does_not_prove_absence_of_revoked_content():
    assert readiness.revoked_source_contamination([story()], RIGHTS_ALLOW)["result"] != readiness.PASS


def test_active_writer_prevents_generation_pass(root):
    (root / ".cache").mkdir()
    (root / ".cache/pipeline-writer.lock").write_text("{}", encoding="utf-8")
    assert readiness.generation_integrity(root)["result"] != readiness.PASS


def test_arbitrary_snapshot_bytes_without_expected_digest_are_not_healthy(root):
    path = root / "content/generated/snapshot.json"
    path.parent.mkdir(parents=True)
    path.write_text("not a snapshot", encoding="utf-8")
    assert readiness.snapshot_health(root)["result"] != readiness.PASS


def test_future_publisher_time_is_never_fresh_news():
    future = story(published_at=NOW + timedelta(days=1))
    assert readiness.news_freshness([future], NOW)["result"] != readiness.PASS


def live_fixture(root, monkeypatch, *, translated=False):
    """An explicitly synthetic validator fixture; never authentic archive/review evidence."""
    from pipeline.models import Snapshot
    from pipeline.tests.test_phase6_translation_governance import FakeTranslation
    item = story()
    if translated:
        from pipeline.models import StoryTranslation
        from pipeline.translation import canonical_hash
        content = FakeTranslation().content.__dict__
        item.translations["bn"] = StoryTranslation(language="bn", content=content,
            canonical_hash=canonical_hash(item), cache_key="f" * 64, provider="synthetic-test",
            model="synthetic-test", generated_at=NOW, review_status="automated")
    snapshot = Snapshot(mode="live", generated_at=NOW, last_successful_fetch_at=NOW,
                        categories={}, stories=[item], sources={SID: source()}, digests=[],
                        offers=[], model_releases=[])
    path = root / "content/generated/snapshot.json"
    path.parent.mkdir(parents=True)
    data = snapshot.model_dump_json().encode()
    path.write_bytes(data)
    # Fixture-only override of the legacy content identity, not a real approval.
    monkeypatch.setattr(gate, "LEGACY_SNAPSHOT_SHA256", hashlib.sha256(data).hexdigest())
    return item


@pytest.mark.parametrize("state", ["RETRACTED", "ARCHIVED", "CORRECTED", "SOURCE_VALIDATED"])
def test_existing_generated_story_cannot_ignore_local_decision(root, monkeypatch, state):
    item = live_fixture(root, monkeypatch)
    gate.assert_existing_build_safe(root)
    editorial.record(item.id, "DISCOVERED", state, actor="test-operator", now=NOW,
                     reason="Synthetic risk reduction", retraction_reason="Synthetic withdrawal",
                     correction_reference="Synthetic correction", root=root)
    with pytest.raises(PermissionError, match="story"):
        gate.assert_existing_build_safe(root)


@pytest.mark.parametrize("state", ["REVOKED", "SUSPENDED"])
def test_existing_generated_sources_cannot_ignore_local_withdrawal(root, monkeypatch, state):
    live_fixture(root, monkeypatch)
    proposal = candidate(candidate_id="arxiv")
    onboarding.register(proposal, actor="test-operator", now=NOW, root=root)
    onboarding.transition(proposal, state, actor="test-operator", now=NOW, reason="Synthetic hold", root=root)
    with pytest.raises(PermissionError, match="candidate"):
        gate.assert_existing_build_safe(root)


@pytest.mark.parametrize("state", ["DRAFT_TRANSLATION", "WITHDRAWN"])
def test_draft_or_withdrawn_translation_cannot_remain_in_live_output(root, monkeypatch, state):
    item = live_fixture(root, monkeypatch, translated=True)
    record = translation.make_record(item.id, source_version="b" * 64, translation_version="c" * 64)
    translation.record(record, "NOT_TRANSLATED", state, actor="test-operator", now=NOW,
                       reason="Synthetic language hold", root=root)
    with pytest.raises(PermissionError, match="translation"):
        gate.assert_existing_build_safe(root)


def test_new_live_draft_is_refused_without_supporting_files(root):
    from pipeline.models import Snapshot
    payload = Snapshot(mode="live", generated_at=NOW, last_successful_fetch_at=NOW,
                       categories={}, stories=[story()], sources={SID: source()}, digests=[],
                       offers=[], model_releases=[])
    path = root / "content/generated/snapshot.json"
    path.parent.mkdir(parents=True)
    path.write_text(payload.model_dump_json(), encoding="utf-8")
    with pytest.raises(PermissionError, match="authenticated review authority"):
        gate.assert_existing_build_safe(root)


@pytest.mark.parametrize("kind", ["source", "editorial", "translation"])
def test_malformed_supporting_ledger_blocks_existing_output(root, monkeypatch, kind):
    live_fixture(root, monkeypatch)
    path = root / {"source": onboarding.LEDGER, "editorial": editorial.LEDGER,
                   "translation": translation.LEDGER}[kind]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"version":1,"events":[],"head_sha256":"forged"}', encoding="utf-8")
    with pytest.raises(ValueError):
        gate.assert_existing_build_safe(root)


@pytest.mark.parametrize("mutation", ["missing_hash", "mixed_fixture", "replayed_run", "failed_source",
                                     "changed_sources", "unordered", "empty_sources", "duplicate_utc_day"])
def test_observation_anomalies_cannot_prove_elapsed_readiness(mutation):
    rows = series(range(11, 19))
    if mutation == "missing_hash":
        rows[-1].pop("receipt_sha256")
    elif mutation == "mixed_fixture":
        rows[-1]["live"] = False
    elif mutation == "replayed_run":
        rows[-1]["run_id"] = rows[0]["run_id"]
    elif mutation == "failed_source":
        rows[-1]["sources"][0]["collection_state"] = "COLLECTION_FAILED"
    elif mutation == "changed_sources":
        rows[-1]["sources"][0]["source_id"] = "different-source"
    elif mutation == "unordered":
        rows[0], rows[1] = rows[1], rows[0]
    elif mutation == "empty_sources":
        rows[-1]["sources"] = []
    else:
        rows[-1]["observed_at"] = "2026-10-18T00:30:00+14:00"  # UTC day duplicates the 17th.
    if mutation not in {"missing_hash", "unordered"}:
        rows[-1]["receipt_sha256"] = digest({k: v for k, v in rows[-1].items() if k != "receipt_sha256"})
    window = readiness.observation_evidence(rows, NOW)
    assert window["elapsed_window_satisfied"] is False
    assert window["eligible"] is False


def test_true_news_kind_uses_source_evidence_not_a_nonexistent_news_category():
    news = story(category="ai")
    report = readiness.news_freshness([news], NOW, sources={SID: source(source_type="rss", category="ai")})
    assert report["result"] == readiness.PASS


def test_unknown_publisher_date_cannot_become_news():
    report = readiness.news_freshness([story(category="ai")], NOW,
                                     sources={SID: source(source_type="rss", missing_publication_time=True)})
    assert report["result"] == readiness.BLOCKED


def test_rights_revocation_uses_real_source_mapping():
    report = readiness.revoked_source_contamination([story()], {"arxiv": {"publication": "exclude"}},
                                                    {SID: source()})
    assert report["result"] == readiness.FAIL


@pytest.mark.parametrize("report", [
    {"sources": [{"collection_state": "COLLECTION_SUCCESS"}]},
    {"mode": "synthetic-fixtures-only", "sources": [{"collection_state": "COLLECTION_SUCCESS"}]},
    {"sources": [{"collection_state": "COLLECTION_SUCCESS", "transport": {"terminal_timeout": True}}]},
    {"sources": [{"collection_state": "COLLECTION_SUCCESS", "error_type": "ReadTimeout"}]},
])
def test_unattested_synthetic_or_terminal_failure_cannot_pass_health(report):
    assert readiness.ingestion_failure_rate(report)["result"] != readiness.PASS


def test_onboarding_github_exception_requires_the_exact_host():
    with pytest.raises(ValueError, match="candidate website"):
        candidate(endpoint="https://api.github.com.attacker.example.org/feed")
