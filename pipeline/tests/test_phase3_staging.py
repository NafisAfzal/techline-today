"""Reproducible local failure evaluation; all network responses are synthetic."""

import json
import shutil
from pathlib import Path

import httpx
import pytest
import yaml

from pipeline import pilot_staging as staging
from pipeline.review_governance import digest, local_path
from pipeline.runner import ROOT


@pytest.fixture(scope="module")
async def staging_suite(tmp_path_factory):
    root = tmp_path_factory.mktemp("phase3-staging")
    shutil.copytree(ROOT / "config", root / "config")
    (root / "content/generated").mkdir(parents=True)
    (root / "content/generated/snapshot.json").write_text('{"synthetic_protected_sentinel":true}')
    before = staging.protected_hashes(root)
    def forbidden(*args, **kwargs):
        pytest.fail("Real HTTP transport/AI must never be instantiated")
    from pipeline.ai import AIRouter
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("PIPELINE_AI_ENABLED", "true")
        patch.setattr(httpx, "AsyncHTTPTransport", forbidden)
        patch.setattr(AIRouter, "summarize", forbidden)
        report, path = await staging.run_staging(root)
    assert before == staging.protected_hashes(root)
    return root, report, path


def result(staging_suite, scenario):
    return next(row for row in staging_suite[1]["deterministic"]["results"] if row["scenario"] == scenario)


def test_all_scenarios_are_measured_without_publication(staging_suite):
    _, report, path = staging_suite
    data = report["deterministic"]
    assert len(data["results"]) == len(staging.SCENARIOS) == 25
    assert report["status"] == "passed" and report["outcome"] == "success"
    assert all(row["verdict"] == "passed" for row in data["results"])
    assert data["live_requests"] == 0 and not data["publication_allowed"] and not data["ai_submission_allowed"]
    assert report["measurements"]["total_seconds"] > 0
    assert report["measurements"]["traced_python_peak_bytes"] > 0
    assert path.stat().st_size == report["measurements"]["serialized_report_bytes"]
    for row in data["results"]:
        assert row["publication_items"] == 0 and row["ai_calls"] == 0
        assert not row["source_enablement_changed"] and row["post_selection_dedupe_stable"]
        assert all(not c["rights_review"]["publication_allowed"] for c in row["contracts"])
        assert all(not c["rights_review"]["ai_submission_allowed"] for c in row["contracts"])


def test_rss_json_ids_dedupe_freshness_and_observation_routing(staging_suite):
    normal = result(staging_suite, "normal")
    assert {o["source_id"] for o in normal["outcomes"]} == {"kubernetes", "cisa_kev"}
    assert all(o["status"] == "held" for o in normal["outcomes"])
    assert normal["duplicates_removed"] >= 2
    observations = normal["observations"]
    assert len(observations) == 6  # Distinct review evidence survives shared GUIDs.
    assert {o["freshness"] for o in observations} == {
        "recent-announcement", "recent-advisory-date", "stale", "unknown-publication-time"}
    assert all(o["review_status"] == "REVIEW_REQUIRED" and o["synthetic"] for o in observations)


def test_large_synthetic_feeds_are_bounded_before_retention(staging_suite):
    row = result(staging_suite, "bounded-volume")
    outcomes = {o["source_id"]: o for o in row["outcomes"]}
    assert outcomes["kubernetes"]["raw"] == 20 and outcomes["cisa_kev"]["raw"] == 30
    assert len(row["observations"]) == 50
    assert all(1_000_000 < size <= 3_000_000 for size in row["fixture_response_bytes"].values())
    metrics = next(m for m in staging_suite[1]["measurements"]["sources"] if m["scenario"] == "bounded-volume")
    assert all(m["parser_seconds"] > 0 and m["items_per_second"] > 0 for m in metrics["sources"])


@pytest.mark.parametrize("scenario,failed", [("partial-outage", 1), ("total-outage", 2), ("oversize", 2),
    ("redirect-private", 2), ("redirect-off-domain", 2), ("redirect-loop", 2),
    ("xml-entities", 1), ("xml-utf32", 1), ("malformed-json", 1),
    ("duplicate-json-keys", 1), ("deep-json", 1)])
def test_adversarial_failures_are_isolated(staging_suite, scenario, failed):
    row = result(staging_suite, scenario)
    assert sum(o["status"] == "failed" for o in row["outcomes"]) == failed
    assert all("error_type" in o for o in row["outcomes"] if o["status"] == "failed")


def test_retries_and_conditional_revalidation_are_actual_fixture_requests(staging_suite):
    retry = result(staging_suite, "retry")
    assert retry["attempts"] == {"kubernetes": 2, "cisa_kev": 2}
    assert retry["status_counts"] == {"429": 2, "200": 2}
    conditional = result(staging_suite, "conditional")
    assert conditional["status_counts"] == {"200": 2, "304": 2}
    assert sum(r["conditional"] for r in conditional["requests"]) == 2
    assert all("evil.example" not in r["url"] and "127.0.0.1" not in r["url"]
               for row in staging_suite[1]["deterministic"]["results"] for r in row["requests"])


@pytest.mark.parametrize("scenario,source_id", [("malformed-cve", "cisa_kev"),
                                               ("template-origin", "cisa_kev"),
                                               ("unsafe-item-url", "kubernetes")])
def test_malformed_identity_url_and_template_are_quarantined(staging_suite, scenario, source_id):
    outcome = next(o for o in result(staging_suite, scenario)["outcomes"] if o["source_id"] == source_id)
    assert outcome["normalized"] == 0 and outcome["invalid"] > 0


def test_html_and_forged_feed_fields_never_enter_a_public_contract(staging_suite):
    for scenario in ("html-injection", "forged-feed-approval"):
        row = result(staging_suite, scenario)
        payload = json.dumps(row)
        assert "<script>" not in payload and "syntheticAttack" not in payload
        assert "third-party.example" not in payload
        assert all(not c["independently_verified"] and not c["breaking_news"] for c in row["contracts"])
        assert all(c["original_creator"] is None and c["applicable_license"] is None for c in row["contracts"])


async def test_repeat_run_is_idempotent_and_preserves_snapshot(staging_suite):
    root, report, _ = staging_suite
    before = staging.protected_hashes(root)
    again, _ = await staging.run_staging(root, scenarios=("normal",))
    assert again["deterministic"]["results"][0] == result(staging_suite, "normal")
    assert digest(again["deterministic"]) == again["deterministic_sha256"]
    assert staging.protected_hashes(root) == before
    assert report["deterministic_sha256"] == digest(report["deterministic"])


def test_interrupted_atomic_write_preserves_last_report_and_rerun_recovers(staging_suite, monkeypatch):
    root, _, path = staging_suite
    before = path.read_bytes()
    def interruption(*args, **kwargs):
        raise OSError("Synthetic interrupted atomic replace")
    with monkeypatch.context() as patch:
        patch.setattr(Path, "replace", interruption)
        with pytest.raises(OSError):
            staging.write_report(root, {"incomplete": True})
    assert path.read_bytes() == before
    leftover = local_path(root, ".cache/phase3/staging/interrupted.tmp")
    leftover.write_text("incomplete synthetic write")
    staging.write_report(root, {"complete": True})
    assert json.loads(path.read_text()) == {"complete": True}
    assert leftover.exists()  # Partial files are never read as completed input.


async def test_enabled_pilot_or_changed_rights_refuses_run_without_overwriting_report(staging_suite):
    root, _, path = staging_suite
    config_path = root / "config/sources.yaml"
    original, before = config_path.read_bytes(), path.read_bytes()
    config = yaml.safe_load(original)
    next(s for s in config["sources"] if s["id"] == "kubernetes")["enabled"] = True
    try:
        config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
        with pytest.raises(ValueError, match="disabled"):
            await staging.run_staging(root, scenarios=("normal",))
        assert path.read_bytes() == before
    finally:
        config_path.write_bytes(original)


@pytest.mark.parametrize("payload", [b'{"a":1,"a":2}', b"NaN", b"[" * 34 + b"0" + b"]" * 34])
def test_strict_local_json_preflight_rejects_ambiguity(payload):
    with pytest.raises(ValueError):
        staging.strict_fixture_json(payload)
