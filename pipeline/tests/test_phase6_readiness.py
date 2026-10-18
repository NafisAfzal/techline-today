"""Operational readiness adversarial tests: fabricated evidence must not pass."""

import json
from datetime import UTC, datetime

from pipeline.readiness import (
    BLOCKED,
    FAIL,
    INCONCLUSIVE,
    PASS,
    assess,
    human_report,
    observation_evidence,
)

NOW = datetime(2026, 10, 19, 9, tzinfo=UTC)
RIGHTS = {"arxiv": {"publication": "allow", "license": "CC0-1.0",
                    "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
                    "scope": "Descriptive metadata only."},
          "cisa_kev": {"publication": "exclude"}}
RELEASE_OK = {"approved": True, "github_publication_approved": True, "public_files_reviewed": True,
              "hosted_ci_verified": True, "durable_backup_verified": True,
              "content_rights_reviewed": True, "free_plan_verified": True,
              "zero_spend_verified": True, "preview_approved": True,
              "ai_enabled": False, "schedule_enabled": False}


def receipt(day, *, live=True, digest=None, run_id="run-1", hour=9):
    observed = datetime(2026, 10, day, hour, tzinfo=UTC)
    return {"version": 1, "live": live, "observed_at": observed.isoformat(),
            "run_id": run_id, "report_sha256": digest or f"{day:02d}" * 32,
            "receipt_sha256": "0" * 64, "collection_state": "COLLECTION_SUCCESS",
            "publication_allowed": False, "ai_submission_allowed": False,
            "sources": [{"source_id": "arxiv", "collection_state": "COLLECTION_SUCCESS",
                         "rights_status": "RIGHTS_REVIEW_REQUIRED", "editorial_status": "EDITORIAL_PENDING",
                         "valid_items": 1, "invalid_items": 0, "duplicate_items": 0,
                         "duration_seconds": 0.1, "freshness": {}, "recovery": {},
                         "transport": {"http_status_counts": {}, "terminal_error_type": None,
                                       "terminal_timeout": False, "timeout_scope": "terminal-only"}}]}


def series(days, **kwargs):
    return [receipt(day, **kwargs) for day in days]


# --- seven-day evidence --------------------------------------------------------

def test_no_receipts_is_inconclusive_not_pass():
    window = observation_evidence([], NOW)
    assert window["eligible"] is False
    assert window["live_observations"] == 0


def test_synthetic_receipts_never_contribute_elapsed_time():
    window = observation_evidence(series(range(1, 15), live=False), NOW)
    assert window["live_observations"] == 0
    assert window["elapsed_days"] == 0
    assert window["eligible"] is False


def test_seven_generous_live_days_are_eligible():
    window = observation_evidence(series(range(10, 18)), NOW)
    assert window["eligible"] is True
    assert window["distinct_days"] == 8
    assert window["elapsed_days"] == 7.0


def test_six_distinct_days_are_not_enough():
    """Six observed days span five elapsed days; seven days need eight observations."""
    window = observation_evidence(series(range(10, 16)), NOW)
    assert window["distinct_days"] == 6
    assert window["elapsed_days"] == 5.0
    assert window["eligible"] is False


def test_seven_synthetic_days_claimed_as_elapsed_real_time_is_rejected():
    window = observation_evidence(series(range(10, 18), live=False), NOW)
    assert window["live_observations"] == 0
    assert window["eligible"] is False


def test_missing_days_are_detected_not_concealed():
    rows = series([10, 11, 12, 14, 15, 16, 17, 18])
    window = observation_evidence(rows, NOW)
    assert "2026-10-13" in window["missing_days"]
    assert window["eligible"] is False


def test_future_timestamps_are_rejected():
    rows = series(range(10, 18)) + [receipt(20)]
    window = observation_evidence(rows, NOW)
    kinds = [a["kind"] for a in window["anomalies"]]
    assert "future_timestamp" in kinds
    assert window["eligible"] is False


def test_manipulated_duplicate_day_is_detected():
    rows = series(range(10, 18))
    rows.append(receipt(15, digest="ff" * 32))
    window = observation_evidence(rows, NOW)
    assert "duplicate_observation_days" in [a["kind"] for a in window["anomalies"]]
    assert window["eligible"] is False


def test_copied_run_evidence_is_detected():
    rows = [receipt(day, digest="ab" * 32) for day in range(10, 18)]
    window = observation_evidence(rows, NOW)
    assert "duplicated_run_evidence" in [a["kind"] for a in window["anomalies"]]
    assert window["eligible"] is False


def test_overlapping_runs_are_detected():
    """A second run four hours after the first on the same day is an overlap."""
    rows = series(range(10, 18)) + [receipt(14, digest="ee" * 32, hour=13)]
    window = observation_evidence(rows, NOW)
    kinds = [a["kind"] for a in window["anomalies"]]
    assert "overlapping_runs" in kinds
    assert "duplicate_observation_days" in kinds
    assert window["eligible"] is False


def test_unparsable_and_naive_timestamps_are_rejected():
    rows = series(range(10, 17)) + [{"version": 1, "live": True, "observed_at": "not-a-time"},
                                    {"version": 1, "live": True, "observed_at": "2026-10-17T09:00:00"}]
    window = observation_evidence(rows, NOW)
    kinds = [a["kind"] for a in window["anomalies"]]
    assert "unparsable_timestamp" in kinds
    assert "naive_timestamp" in kinds
    assert window["eligible"] is False


def test_stale_evidence_is_flagged():
    rows = [receipt(day) for day in range(1, 9)]
    window = observation_evidence(rows, datetime(2026, 10, 20, 9, tzinfo=UTC))
    assert window["latest_age_hours"] > 72
    assert window["eligible"] is False


# --- dimensions ----------------------------------------------------------------

def test_unknown_is_never_reported_as_pass(root):
    result = assess(root=root)
    results = {row["dimension"]: row["result"] for row in result["dimensions"]}
    assert results["source_eligibility"] == INCONCLUSIVE
    assert results["editorial_review_status"] == INCONCLUSIVE
    assert results["bangla_review_coverage"] == INCONCLUSIVE
    assert results["ingestion_failure_rate"] == INCONCLUSIVE
    assert results["build_reproducibility"] == INCONCLUSIVE
    assert results["accessibility_checks"] == INCONCLUSIVE


def test_enabled_source_without_rights_fails(root):
    result = assess(root=root, source_rights=RIGHTS, enabled_sources=["cisa_kev"])
    row = next(r for r in result["dimensions"] if r["dimension"] == "source_eligibility")
    assert row["result"] == FAIL


def test_rights_approved_source_passes_eligibility(root):
    result = assess(root=root, source_rights=RIGHTS, enabled_sources=["arxiv"])
    row = next(r for r in result["dimensions"] if r["dimension"] == "source_eligibility")
    assert row["result"] == PASS


def test_incomplete_rights_evidence_fails(root):
    partial = {"arxiv": {"publication": "allow"}}
    result = assess(root=root, source_rights=partial, enabled_sources=["arxiv"])
    row = next(r for r in result["dimensions"] if r["dimension"] == "rights_evidence_completeness")
    assert row["result"] == FAIL


def test_no_current_news_is_blocked_not_passed(root):
    result = assess(root=root, stories=[])
    row = next(r for r in result["dimensions"] if r["dimension"] == "news_freshness")
    assert row["result"] == INCONCLUSIVE


def test_unauthorised_ai_or_schedule_fails_security(root):
    result = assess(root=root, release_config={**RELEASE_OK, "ai_enabled": True})
    row = next(r for r in result["dimensions"] if r["dimension"] == "security_configuration")
    assert row["result"] == FAIL


def test_missing_preview_prerequisites_are_blocked(root):
    result = assess(root=root, release_config={"approved": False})
    row = next(r for r in result["dimensions"] if r["dimension"] == "preview_deployment_prerequisites")
    assert row["result"] == BLOCKED


def test_scheduler_without_authorization_is_blocked(root):
    result = assess(root=root, release_config=RELEASE_OK)
    row = next(r for r in result["dimensions"] if r["dimension"] == "scheduler_authorization")
    assert row["result"] == BLOCKED


def test_outstanding_generation_journal_fails(root):
    (root / ".cache").mkdir(parents=True, exist_ok=True)
    (root / ".cache/pipeline-transaction.json").write_text("{}", encoding="utf-8")
    result = assess(root=root)
    row = next(r for r in result["dimensions"] if r["dimension"] == "generation_integrity")
    assert row["result"] == FAIL


def test_reports_never_authorise_publication(root):
    result = assess(root=root, source_rights=RIGHTS, enabled_sources=["arxiv"], release_config=RELEASE_OK)
    assert result["publication_allowed"] is False
    assert result["ai_submission_allowed"] is False
    assert result["note"].startswith("INCONCLUSIVE")


def test_summary_counts_every_dimension(root):
    result = assess(root=root)
    assert sum(result["summary"].values()) == len(result["dimensions"])
    assert len(result["dimensions"]) == 16


def test_human_report_is_generated_and_explains_unknown(root):
    result = assess(root=root)
    text = human_report(result)
    assert "INCONCLUSIVE" in text
    assert "never as PASS" in text
    assert "authorises nothing" in text


def test_private_report_is_not_written_into_build_assets(root):
    """Readiness output must stay under .cache and never reach content/ or apps/."""
    from pipeline.readiness import REPORT_DIRECTORY
    assert REPORT_DIRECTORY.startswith(".cache/")
    assert "content" not in REPORT_DIRECTORY
    assert "apps" not in REPORT_DIRECTORY


def test_observation_receipt_reader_tolerates_corrupt_files(root):
    from pipeline.readiness import read_observation_receipts
    directory = root / ".cache/phase4/observations"
    directory.mkdir(parents=True)
    (directory / "2026-10-17.json").write_text(json.dumps(receipt(17)), encoding="utf-8")
    (directory / "2026-10-18.json").write_text("{not json", encoding="utf-8")
    rows = read_observation_receipts(root)
    assert len(rows) == 1
    assert rows[0]["observed_at"].startswith("2026-10-17")