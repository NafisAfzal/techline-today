"""Newsroom launch readiness. Every item states its evidence and what is missing."""

import json
from pathlib import Path

from pipeline.newsroom_readiness import (
    BLOCKED,
    FAIL,
    INCONCLUSIVE,
    PASS,
    human_report,
    newsroom_readiness,
    security_advisory_status,
)

REPO = Path(__file__).resolve().parents[2]


def item(report, name):
    return next(row for row in report["items"] if row["item"] == name)


def test_the_readiness_report_covers_every_required_dimension():
    report = newsroom_readiness(REPO)
    names = {row["item"] for row in report["items"]}
    for required in ["authority_provisioning", "trusted_checkpoint", "source_rights_coverage",
                     "rights_evidence_completeness", "source_candidate_backlog",
                     "current_news_coverage", "editorial_backlog", "english_editorial_approval",
                     "native_bangla_review", "translation_staleness",
                     "operational_observation_coverage", "publication_eligibility",
                     "security_advisory", "preview_readiness", "production_launch_readiness"]:
        assert required in names


def test_every_item_uses_the_four_verdicts_and_names_what_is_missing():
    report = newsroom_readiness(REPO)
    for row in report["items"]:
        assert row["result"] in {PASS, FAIL, BLOCKED, INCONCLUSIVE}
        assert row["detail"].strip()
        if row["result"] != PASS:
            assert row["missing"], f"{row['item']} reports no missing evidence"


def test_the_report_never_authorises_anything():
    report = newsroom_readiness(REPO)
    assert report["publication_allowed"] is False
    assert report["ai_submission_allowed"] is False
    assert "Neither is a pass." in report["note"]


def test_production_launch_readiness_is_derived_from_the_other_items():
    report = newsroom_readiness(REPO)
    others = [row for row in report["items"] if row["item"] != "production_launch_readiness"]
    results = {row["result"] for row in others}
    launch = item(report, "production_launch_readiness")
    if FAIL in results:
        assert launch["result"] == FAIL
    elif BLOCKED in results:
        assert launch["result"] == BLOCKED
    elif INCONCLUSIVE in results:
        assert launch["result"] == INCONCLUSIVE
    else:
        assert launch["result"] == PASS


def test_the_unprovisioned_authority_is_reported_as_blocked_not_passed():
    report = newsroom_readiness(REPO)
    assert item(report, "authority_provisioning")["result"] == BLOCKED
    assert item(report, "trusted_checkpoint")["result"] == BLOCKED


def test_the_canonical_snapshot_is_reported_with_its_digest():
    import hashlib

    from pipeline.publication_gate import LEGACY_SNAPSHOT_SHA256

    path = REPO / "content/generated/snapshot.json"
    if not path.is_file():
        return
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == LEGACY_SNAPSHOT_SHA256


def test_the_security_advisory_status_reflects_the_recorded_mitigation():
    row = security_advisory_status(REPO)
    assert row["result"] == PASS
    advisory = row["evidence"]["advisories"][0]
    assert advisory["id"] == "GHSA-ch52-4w7c-c8xp"
    assert advisory["mitigation_present"] is True
    assert advisory["patched_versions"] is None
    assert advisory["reassessment_due"] == "2026-11-03"


def test_a_missing_advisory_record_is_inconclusive(tmp_path):
    row = security_advisory_status(tmp_path)
    assert row["result"] == INCONCLUSIVE
    assert row["missing"]


def test_a_missing_mitigation_artifact_fails_the_advisory_check(tmp_path):
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config/security-advisories.json").write_text(json.dumps({
        "version": 1, "advisories": [{
            "id": "GHSA-test", "package": "example", "locked_version": "1.0.0",
            "mitigation_artifact": "patches/missing.patch", "reassessment_due": "2099-01-01"}]}),
        encoding="utf-8")
    row = security_advisory_status(tmp_path)
    assert row["result"] == FAIL
    assert any("mitigation artifact" in item for item in row["missing"])


def test_the_human_report_lists_the_blockers():
    report = newsroom_readiness(REPO)
    text = human_report(report)
    assert "# Newsroom launch readiness" in text
    assert "This report authorises nothing." in text
    assert "production_launch_readiness" in text
