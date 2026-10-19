"""Daily observations retain useful transport facts without publisher content."""

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from pipeline import observations
from pipeline.review_governance import digest
from pipeline.source_diagnostics import fixture_response, run_diagnostics


@pytest.fixture
def observation_root(tmp_path, monkeypatch):
    shutil.copytree(Path(__file__).resolve().parents[2] / "config", tmp_path / "config")

    async def no_wait(delay):
        pass

    monkeypatch.setattr("pipeline.security.asyncio.sleep", no_wait)
    return tmp_path


@pytest.mark.parametrize("scenario, statuses, error, timeout", [
    ("success", {"200": 1}, None, False),
    ("recovered_429", {"200": 1, "429": 1}, None, False),
    ("exhausted_429", {"429": 3}, "HTTPStatusError", False),
    ("timeout", {}, "ConnectTimeout", True),
    ("base_timeout", {}, "TimeoutException", True),
])
async def test_receipts_preserve_rate_limits_terminal_timeouts_and_recovery(
        observation_root, scenario, statuses, error, timeout):
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        if scenario in {"timeout", "base_timeout"}:
            error_class = httpx.ConnectTimeout if scenario == "timeout" else httpx.TimeoutException
            raise error_class("PrivatePublisherBodyMarker must never be retained")
        if scenario == "exhausted_429" or (scenario == "recovered_429" and calls == 1):
            return httpx.Response(429, headers={"retry-after": "0"}, text="PrivatePublisherBodyMarker")
        return fixture_response(request)

    report = await run_diagnostics(root=observation_root, source_ids=["research_pytorch"],
                                   transport=httpx.MockTransport(handler))
    receipt = observations.compact_receipt(report, datetime.now(UTC))
    row = receipt["sources"][0]
    assert row["transport"] == {"http_status_counts": statuses, "terminal_error_type": error,
                                "terminal_timeout": timeout, "timeout_scope": "terminal-only"}
    assert row["recovery"]["recovered_after_http_retry"] is (scenario == "recovered_429")
    assert row["recovery"]["http_attempts"] == calls
    assert receipt["publication_allowed"] is False and receipt["ai_submission_allowed"] is False
    serialized = json.dumps(receipt)
    assert not any(value in serialized for value in (
        "PrivatePublisherBodyMarker", "Synthetic release fixture", "canonical_url", "excerpt", "html_url"))


@pytest.mark.parametrize("field, value", [("statuses", [999]), ("error_type", "Raw publisher prose here")])
async def test_receipt_refuses_unbounded_or_invalid_transport_categories(observation_root, field, value):
    report = await run_diagnostics(root=observation_root, source_ids=["research_pytorch"])
    if field == "statuses":
        report["sources"][0]["requests"][0][field] = value
    else:
        report["sources"][0][field] = value
    report["report_sha256"] = digest({key: value for key, value in report.items() if key != "report_sha256"})
    with pytest.raises(ValueError, match="Invalid HTTP|Invalid diagnostic"):
        observations.compact_receipt(report, datetime.now(UTC))


async def test_observation_records_measured_duration_without_creating_live_evidence(observation_root):
    summary, code = await observations.observe(root=observation_root)
    receipt = json.loads((observation_root / observations.DIRECTORY / "synthetic-latest.json").read_text())
    assert code == 0 and summary["live_observations"] == 0
    assert summary["sustained_threshold_met"] is False
    assert isinstance(receipt["run_duration_seconds"], float) and receipt["run_duration_seconds"] >= 0
    assert all(row["transport"]["http_status_counts"] == {"200": 1} for row in receipt["sources"])


async def test_existing_daily_receipts_without_new_transport_fields_still_validate(observation_root):
    report = await run_diagnostics(root=observation_root, source_ids=["research_pytorch"])
    receipt = observations.compact_receipt(report, datetime.now(UTC))
    for row in receipt["sources"]:
        row.pop("transport")
    receipt["receipt_sha256"] = digest(receipt)
    directory = observation_root / observations.DIRECTORY
    directory.mkdir(parents=True)
    (directory / "2026-10-17.json").write_text(json.dumps(receipt), encoding="utf-8")
    assert observations.read_receipts(observation_root) == [receipt]
