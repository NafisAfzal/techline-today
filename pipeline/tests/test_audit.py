import json
import shutil
from datetime import timedelta
from pathlib import Path

import httpx
import pytest

import pipeline.runner as runner
from pipeline.ai import AIRouter, RemoteProvider, evidence_hash, extractive
from pipeline.dedupe import cluster
from pipeline.models import Snapshot, safe_url
from pipeline.normalize import canonicalize, normalize
from pipeline.security import SafeFetcher
from pipeline.storage import read_json
from pipeline.verification import validate_summary


@pytest.mark.parametrize("url", ["https://example.com\\@127.0.0.1/", "https://example.com/\nattack", "https://example.com./", "https://127.1/", "https://0x7f.1/", "https://evil.localhost/", "https://%31%32%37.0.0.1/"])
def test_ambiguous_urls_are_rejected(url):
    with pytest.raises(ValueError):
        safe_url(url)


def test_repeated_query_parameter_order_is_preserved():
    assert canonicalize("https://example.com/?z=1&step=b&step=a&utm_source=x") == "https://example.com/?step=b&step=a&z=1"


def test_release_markdown_becomes_plain_evidence(source, now):
    source = source.model_copy(update={"adapter": "github_releases"})
    item = normalize({"url": "https://example.com/release", "title": "Project release 0.16.10",
                      "text": "### Preview features\n- Add a migration guide ([#28087](https://github.com/owner/repo/pull/28087)).\n- Support **64 GB** memory. <script>attack()</script>"}, source, now)
    assert "###" not in item.excerpt and "https://" not in item.excerpt and "28087" not in item.excerpt
    assert "64 GB" in item.excerpt and "attack()" not in item.excerpt


@pytest.mark.parametrize("payload", [{"choices": []}, {"choices": None}, {"choices": [{"message": {"content": "{}"}}], "usage": None}, []])
async def test_malformed_provider_wire_responses_fall_back(items, payload):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))) as client:
        provider = RemoteProvider("bad", "test", "placeholder", "https://example.com/ai", client, 1)
        state = {}
        reservations = []
        router = AIRouter([provider], {**runner.config("ai"), "max_retries": 0}, state, Path("prompts/story_summary.md"), lambda: reservations.append(json.loads(json.dumps(state))))
        summary, metadata = await router.summarize(items[:1])
    assert metadata.generation_mode == "extractive" and summary.claim_map
    assert reservations[0]["bad"]["calls"] == 1 and reservations[-1]["bad"]["errors"] == 1


async def test_provider_redirect_does_not_forward_key(items):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(307, headers={"location": "https://attacker.example/collect"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True) as client:
        provider = RemoteProvider("bad", "test", "placeholder", "https://example.com/ai", client, 1)
        router = AIRouter([provider], {**runner.config("ai"), "max_retries": 0}, {}, Path("prompts/story_summary.md"))
        _, metadata = await router.summarize(items[:1])
    assert len(calls) == 1 and metadata.generation_mode == "extractive"


def test_prompt_and_metadata_changes_invalidate_summary_cache(items):
    settings = runner.config("ai")
    original = evidence_hash(items[:1], settings, "Original prompt")
    assert original != evidence_hash(items[:1], settings, "Changed summary policy")
    assert original != evidence_hash([items[0].model_copy(update={"publisher": "Corrected publisher"})], settings, "Original prompt")


def test_currency_substitution_and_false_attribution_fail(items):
    item = items[0].model_copy(update={"title": "Official developer credit offer", "excerpt": "The developer credit is $25 for eligible users."})
    summary = extractive([item])
    summary.key_numbers[0].value = "€25"
    with pytest.raises(ValueError, match="numeric"):
        validate_summary(summary, [item])
    summary = extractive([item.model_copy(update={"source_class": "community"})])
    summary.key_facts[0].attribution = "primary"
    with pytest.raises(ValueError, match="attribution"):
        validate_summary(summary, [item.model_copy(update={"source_class": "community"})])


def test_adjacent_github_versions_do_not_merge(items):
    left = items[0].model_copy(update={"source_type": "github_releases", "title": "astral-sh ruff stable release 0.16.9"})
    right = left.model_copy(update={"id": "another", "title": "astral-sh ruff stable release 0.16.10", "canonical_url": "https://example.com/new"})
    assert len(cluster([left, right])) == 2


async def test_partial_adapter_failure_does_not_abort(source, now, monkeypatch):
    class Broken:
        async def fetch(self, source, fetcher):
            raise AttributeError("Malformed remote payload")
    monkeypatch.setitem(runner.ADAPTERS, "json_api", Broken())
    broken = source.model_copy(update={"id": "broken", "adapter": "json_api", "enabled": True})
    good = source.model_copy(update={"enabled": True})
    xml = '<rss><channel><title>Feed</title><item><title>Official technology release</title><link>https://example.com/release</link></item></channel></rss>'
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, text=xml, headers={"Content-Type": "application/xml"}))) as client:
        report = {}
        results = await runner.collect([broken, good], SafeFetcher(client, {}, "TestBot"), now, [], report, now)
    assert len(results) == 1
    assert report["sources"][0]["error_type"] == "AttributeError"
    assert report["sources"][1]["status"] == "success"


async def test_304_refreshes_only_evidence_present_in_that_response(source, now):
    source = source.model_copy(update={"enabled": True})
    historical = normalize({"url": "https://example.com/old", "title": "Historical technology release"}, source, now - timedelta(days=2))
    xml = '<rss><channel><title>Feed</title><item><title>Current technology release</title><link>https://example.com/current</link></item></channel></rss>'
    state = {}
    def handler(request):
        if request.headers.get("if-none-match"):
            return httpx.Response(304)
        return httpx.Response(200, text=xml, headers={"Content-Type": "application/xml", "ETag": "stable"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        first = await runner.collect([source], SafeFetcher(client, state, "TestBot"), now, [historical], {}, now - timedelta(days=3))
        second = await runner.collect([source], SafeFetcher(client, state, "TestBot"), now + timedelta(hours=6), [historical, *first], {}, now)
    assert [item.id for item in second] == [first[0].id]
    assert second[0].fetched_at == now + timedelta(hours=6)
    assert historical.fetched_at == now - timedelta(days=2)


async def test_unsolicited_304_is_not_accepted(source):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(304))) as client:
        with pytest.raises(ValueError, match="Unsolicited"):
            await SafeFetcher(client, {}, "TestBot").get(source.endpoint, source, accept=("application/xml",))


async def test_final_validation_failure_never_writes_archives(tmp_path, monkeypatch, now):
    for folder in ("config", "prompts"):
        shutil.copytree(runner.ROOT / folder, tmp_path / folder)
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    output = tmp_path / "content/generated/snapshot.json"
    await runner.run("fixture", output, now)
    previous = output.read_bytes()
    archives = {file: file.read_bytes() for file in (tmp_path / ".cache/fixture-archives").glob("*.json")}
    original = runner.fixture_trackers
    def invalid(stories, at):
        offers, models = original(stories, at)
        offers[0].value_text = "$9999999999 unsupported allowance"
        return offers, models
    monkeypatch.setattr(runner, "fixture_trackers", invalid)
    with pytest.raises(ValueError, match="not supported"):
        await runner.run("fixture", output, now)
    assert output.read_bytes() == previous
    assert all(file.read_bytes() == value for file, value in archives.items())
    payload = read_json(output)
    payload["archive_index"][0]["key"] = "../../.env"
    with pytest.raises(ValueError, match="archive index"):
        Snapshot.model_validate(payload)
