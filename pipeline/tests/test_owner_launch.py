import asyncio
import json
import shutil
from types import SimpleNamespace

import httpx
import pytest

import pipeline.runner as runner
import pipeline.security as security
from pipeline.models import SourceItem


async def test_retry_respects_source_interval_on_every_attempt(source, monkeypatch):
    clock = [10.0]
    starts = []
    async def sleep(seconds):
        clock[0] += seconds
    async def respond(request):
        starts.append(clock[0])
        return httpx.Response(503 if len(starts) == 1 else 200, content=b"evidence", headers={"Content-Type": "text/plain"})
    monkeypatch.setattr(security, "time", SimpleNamespace(monotonic=lambda: clock[0]))
    monkeypatch.setattr(security.asyncio, "sleep", sleep)
    setting = source.model_copy(update={"fetch_policy": source.fetch_policy.model_copy(update={"min_interval_seconds": 3})})
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        await security.SafeFetcher(client, {}, "TestBot").get(setting.endpoint, setting, accept=("text/plain",))
    assert len(starts) == 2 and starts[1] - starts[0] >= 3


async def test_same_host_connections_are_serialized(source):
    active, maximum = 0, 0
    async def respond(request):
        nonlocal active, maximum
        active += 1
        maximum = max(maximum, active)
        await asyncio.sleep(0.01)
        active -= 1
        return httpx.Response(200, content=b"evidence", headers={"Content-Type": "text/plain"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        fetcher = security.SafeFetcher(client, {}, "TestBot")
        await asyncio.gather(*(fetcher.get(source.endpoint + str(i), source, accept=("text/plain",)) for i in range(2)))
    assert maximum == 1


@pytest.mark.parametrize("deny_by", ["disabled", "rights"])
async def test_disabled_feed_cannot_survive_through_retained_summary_or_history(tmp_path, monkeypatch, now, deny_by):
    for folder in ("config", "prompts"):
        shutil.copytree(runner.ROOT / folder, tmp_path / folder)
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    output = tmp_path / "content/generated/snapshot.json"
    fixture = await runner.run("fixture", output, now)
    payload = fixture.model_dump(mode="json")
    payload["mode"], payload["archive_index"] = "live", []
    for source in payload["sources"].values():
        source["source_registry_id"], source["is_demo"] = "nvidia", False
    keep = payload["sources"][payload["stories"][0]["source_ids"][0]]
    keep["source_registry_id"] = "arxiv"
    excluded = next(key for key in payload["sources"] if key != keep["id"])
    for story in payload["stories"]:
        story["is_demo"], story["translations"] = False, {}
    payload["stories"][0]["change_log"].append({"at":now.isoformat(), "text":"Restricted legacy wording", "source_ids":[excluded], "previous_facts":[]})
    for item in [*payload["offers"], *payload["model_releases"]]:
        item["is_demo"] = False
    output.write_text(json.dumps(payload), encoding="utf-8")
    if deny_by == "rights":
        # Source enablement cannot override the authoritative reuse policy.
        import yaml
        registry_path = tmp_path / "config/sources.yaml"
        registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
        next(source for source in registry["sources"] if source["id"] == "nvidia")["enabled"] = True
        registry_path.write_text(yaml.safe_dump(registry), encoding="utf-8")
    async def collect(*args):
        return [SourceItem.model_validate(keep)]
    monkeypatch.setattr(runner, "collect", collect)
    monkeypatch.setenv("PIPELINE_AI_ENABLED", "true")
    calls = []
    async def forbidden_call(request):
        calls.append(request)
        raise AssertionError("Source submission was not permitted")
    monkeypatch.setattr(runner, "configured_providers", lambda *args: [SimpleNamespace(
        id="gemini", model="mock", daily_call_limit=10, generate_structured=forbidden_call)])
    candidate = await runner.run("live", output, now)
    assert calls == []
    assert candidate.stories and all(not story.translations for story in candidate.stories)
    assert {source.source_registry_id for source in candidate.sources.values()} == {"arxiv"}
    assert "Restricted legacy wording" not in candidate.model_dump_json()
    state = json.loads((tmp_path / ".cache/state-live.json").read_text(encoding="utf-8"))
    assert all(item["source_registry_id"] == "arxiv" for item in state["items"])
