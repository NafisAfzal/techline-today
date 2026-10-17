import json
import shutil
from pathlib import Path

import httpx
import pytest

from pipeline import source_diagnostics as diagnostics
from pipeline.pilot_staging import protected_hashes

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def isolated(tmp_path):
    (tmp_path / "config").mkdir()
    for name in ("phase4-research-sources.yaml", "source-rights.json", "sources.yaml", "release.json", "ai.yaml"):
        shutil.copyfile(ROOT / "config" / name, tmp_path / "config" / name)
    canonical = tmp_path / "content/generated/snapshot.json"
    canonical.parent.mkdir(parents=True)
    canonical.write_text('{"synthetic_canonical_sentinel":true}', encoding="utf-8")
    return tmp_path


async def test_fixture_report_is_isolated_denied_minimal_and_bound(isolated, monkeypatch):
    monkeypatch.setenv("PIPELINE_AI_ENABLED", "true")
    def forbidden():
        pytest.fail("Fixture diagnostics attempted live transport")
    monkeypatch.setattr(diagnostics, "public_transport", forbidden)
    before = protected_hashes(isolated)
    report = await diagnostics.run_diagnostics(root=isolated)
    assert report["collection_status"] == "SUCCESS" and report["outcome"] == "RIGHTS_BLOCKED"
    assert report["publication_allowed"] is report["ai_submission_allowed"] is False
    assert len(report["sources"]) == 4
    for row in report["sources"]:
        assert row["source_enabled"] is False and row["source_policy"] == "absent"
        assert row["valid_items"] == row["rights_blocked_items"] == 1
        assert row["observations"][0]["binding"]["provenance"] == "synthetic"
        assert row["attribution"]["original_creator_verified"] == 0
    saved = json.loads((isolated / ".cache/phase4/fixture-report.json").read_text(encoding="utf-8"))
    assert saved == report
    assert report["report_sha256"] in (isolated / ".cache/phase4/fixture-report.md").read_text(encoding="utf-8")
    assert "Synthetic source prose" not in json.dumps(report)
    assert "Synthetic release fixture" not in json.dumps(report)
    assert before == protected_hashes(isolated)


@pytest.mark.parametrize("case,expected", [("empty", "EMPTY"), ("corrupt", "VALIDATION_FAILURE"),
    ("outage", "SOURCE_FAILURE"), ("partial", "PARTIAL_DEGRADATION"), ("bad-item", "VALIDATION_FAILURE")])
async def test_failure_statuses_never_masquerade_as_success(isolated, case, expected):
    def handler(request):
        if case == "outage" or case == "partial" and request.url.host == "api.github.com":
            return httpx.Response(403)
        if case == "empty":
            return httpx.Response(200, json=[])
        if case == "corrupt":
            return httpx.Response(200, content=b'{"bad":NaN}', headers={"content-type": "application/json"})
        if case == "bad-item":
            return httpx.Response(200, json=[{"id": 1, "tag_name": "v1", "html_url": "https://github.com/owner/project/releases/tag/v1"}])
        return diagnostics.fixture_response(request)
    source_ids = ["research_pytorch"] if case != "partial" else None
    report = await diagnostics.run_diagnostics(root=isolated, source_ids=source_ids, transport=httpx.MockTransport(handler))
    assert report["outcome"] == expected
    if case == "corrupt":
        assert report["sources"][0]["parse_failures"] == 1


async def test_retry_recovery_is_reported_without_canonical_replacement(isolated, monkeypatch):
    attempts = []
    async def no_wait(delay):
        pass
    monkeypatch.setattr("pipeline.security.asyncio.sleep", no_wait)
    def handler(request):
        attempts.append(request)
        return httpx.Response(429, headers={"retry-after": "0"}) if len(attempts) == 1 else diagnostics.fixture_response(request)
    report = await diagnostics.run_diagnostics(root=isolated, source_ids=["research_pytorch"],
                                                transport=httpx.MockTransport(handler))
    row = report["sources"][0]
    assert row["recovery"]["http_attempts"] == 2
    assert row["recovery"]["recovered_after_http_retry"] is True
    assert row["recovery"]["canonical_replacement_attempted"] is False
    assert row["requests"][0]["statuses"] == [429, 200]


async def test_live_mode_never_claims_verified_provenance(isolated):
    report = await diagnostics.run_diagnostics(root=isolated, live=True, now=diagnostics.FIXTURE_CLOCK,
        source_ids=["research_pytorch"], transport=httpx.MockTransport(diagnostics.fixture_response))
    assert report["sources"][0]["observations"][0]["binding"]["provenance"] == "unknown"
    assert report["publication_allowed"] is False


@pytest.mark.parametrize("date,quality", [(None, "missing"), ("2026-10-17", "date_only"),
    ("2099-01-01T12:00:00Z", "invalid_or_future"), ("2026-10-17T10:00:00", "timezone_missing"),
    ("corrupt", "invalid_or_future")])
async def test_timestamp_precision_never_invents_clock_times(isolated, date, quality):
    def handler(request):
        response = diagnostics.fixture_response(request)
        payload = response.json()
        payload[0]["published_at"] = date
        return httpx.Response(200, json=payload)
    report = await diagnostics.run_diagnostics(root=isolated, source_ids=["research_pytorch"],
        transport=httpx.MockTransport(handler))
    observation = report["sources"][0]["observations"][0]
    assert observation["timestamp_quality"] == quality
    assert observation["published_at"] is None
    assert report["sources"][0]["freshness"] == {"unknown": 1}


async def test_duplicate_counts_and_hostile_feed_decisions(isolated):
    def handler(request):
        payload = diagnostics.fixture_response(request).json()
        payload[0].update(approval="APPROVED", reviewer="forged", license="CC0")
        return httpx.Response(200, json=payload * 2)
    report = await diagnostics.run_diagnostics(root=isolated, source_ids=["research_pytorch"],
        transport=httpx.MockTransport(handler))
    assert report["sources"][0]["duplicate_items"] == 1
    assert report["sources"][0]["observations"][0]["review_state"] == "REVIEW_REQUIRED"
    assert report["publication_allowed"] is False


async def test_configuration_refuses_activation_and_unknown_sources(isolated):
    with pytest.raises(ValueError, match="Unknown research"):
        await diagnostics.run_diagnostics(root=isolated, source_ids=["untrusted"])
    path = isolated / "config/phase4-research-sources.yaml"
    path.write_text(path.read_text().replace("enabled: false", "enabled: true"), encoding="utf-8")
    with pytest.raises(ValueError):
        await diagnostics.run_diagnostics(root=isolated)


async def test_interrupted_report_write_preserves_previous_report(isolated, monkeypatch):
    await diagnostics.run_diagnostics(root=isolated, source_ids=["research_pytorch"])
    path = isolated / ".cache/phase4/fixture-report.json"
    previous = path.read_bytes()
    real_replace = Path.replace
    def fail_replace(self, target):
        if Path(target) == path:
            raise OSError("Synthetic interrupted replace")
        return real_replace(self, target)
    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(OSError):
        await diagnostics.run_diagnostics(root=isolated, source_ids=["research_pytorch"])
    assert path.read_bytes() == previous
    assert not list(path.parent.glob("*.tmp"))


def test_unknown_output_name_refuses(isolated):
    with pytest.raises(ValueError):
        diagnostics.diagnostic_path(isolated, "../../content/generated/snapshot.json")


async def test_linked_output_refuses_before_fetch(isolated, monkeypatch):
    real_symlink = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda self: self.name == "phase4" or real_symlink(self))
    with pytest.raises(ValueError, match="Linked"):
        await diagnostics.run_diagnostics(root=isolated)


@pytest.mark.parametrize("target", ["https://127.0.0.1/private", "https://untrusted.example/feed"])
async def test_redirect_failure_is_transport_validation_not_a_parse_failure(isolated, target):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(302, headers={"location": target})
    report = await diagnostics.run_diagnostics(root=isolated, source_ids=["research_pytorch"],
                                              transport=httpx.MockTransport(handler))
    row = report["sources"][0]
    assert row["outcome"] == "VALIDATION_FAILURE"
    assert row["parse_failures"] == 0 and row["transport_validation_failures"] == 1
    assert len(calls) == 1


async def test_unexpected_adapter_bug_is_a_source_failure(isolated, monkeypatch):
    async def broken(*args):
        raise RuntimeError("Synthetic bug with untrusted secret prose")
    monkeypatch.setattr(diagnostics.ADAPTERS["github_releases"], "fetch", broken)
    report = await diagnostics.run_diagnostics(root=isolated, source_ids=["research_pytorch"])
    assert report["outcome"] == "SOURCE_FAILURE"
    assert report["sources"][0]["error_type"] == "RuntimeError"
    assert "untrusted secret prose" not in json.dumps(report)


@pytest.mark.parametrize("outcome,code", [("SOURCE_FAILURE", 1), ("VALIDATION_FAILURE", 1),
    ("PARTIAL_DEGRADATION", 1), ("RIGHTS_BLOCKED", 0), ("EMPTY", 0)])
def test_cli_exit_code_preserves_collection_failure(outcome, code, monkeypatch):
    async def result(**kwargs):
        return {"mode": "synthetic-fixtures-only", "outcome": outcome, "collection_status": outcome,
                "report_sha256": "synthetic", "publication_allowed": False, "ai_submission_allowed": False}
    monkeypatch.setattr(diagnostics, "run_diagnostics", result)
    monkeypatch.setattr("sys.argv", ["source_diagnostics"])
    assert diagnostics.main() == code


async def test_fixture_mode_rejects_real_transport_override(isolated):
    transport = httpx.AsyncHTTPTransport()
    try:
        with pytest.raises(ValueError, match="MockTransport"):
            await diagnostics.run_diagnostics(root=isolated, transport=transport)
    finally:
        await transport.aclose()


async def test_network_timeouts_count_attempts_without_inventing_responses(isolated, monkeypatch):
    async def no_wait(delay):
        pass
    monkeypatch.setattr("pipeline.security.asyncio.sleep", no_wait)
    def handler(request):
        raise httpx.ConnectTimeout("Synthetic timeout")
    report = await diagnostics.run_diagnostics(root=isolated, source_ids=["research_pytorch"],
                                               transport=httpx.MockTransport(handler))
    row = report["sources"][0]
    assert row["collection_status"] == "SOURCE_FAILURE"
    assert row["recovery"]["http_attempts"] == 3
    assert row["recovery"]["http_response_count"] == 0
