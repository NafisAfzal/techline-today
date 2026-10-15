import shutil
from datetime import timedelta

import httpx
import pytest
from jsonschema import ValidationError

import pipeline.runner as runner
from pipeline.models import Snapshot
from pipeline.normalize import normalize
from pipeline.security import SafeFetcher
from pipeline.storage import read_json, validate_snapshot


async def test_full_pipeline_schema_and_reuse(tmp_path,monkeypatch,now):
    original=runner.ROOT
    for folder in ('config','prompts'):
        shutil.copytree(original/folder,tmp_path/folder)
    monkeypatch.setattr(runner,'ROOT',tmp_path)
    output=tmp_path/'content/generated/snapshot.json'
    snapshot=await runner.run('fixture',output,now)
    assert isinstance(snapshot,Snapshot) and len(snapshot.stories)>=9
    assert {story.category for story in snapshot.stories} == set(snapshot.categories)
    again=await runner.run('fixture',output,now)
    assert [story.id for story in again.stories]==[story.id for story in snapshot.stories]
    # Novelty intentionally changes after the initial seed. A further identical
    # run must be byte-stable once that state has settled.
    permuted_items = list(reversed(runner.fixture_data(now)))
    monkeypatch.setattr(runner, 'fixture_data', lambda time: permuted_items)
    steady = await runner.run('fixture',output,now)
    assert steady.model_dump_json() == again.model_dump_json()
    assert read_json(tmp_path/'content/generated/run-report.json')['cached_summaries']==len(snapshot.stories)
    original_items = runner.fixture_data(now)
    monkeypatch.setattr(runner, 'fixture_data', lambda time: [item.model_copy(update={'fetched_at': time}) for item in original_items])
    refreshed = await runner.run('fixture', output, now + timedelta(hours=6))
    previous_by_id = {story.id: story for story in snapshot.stories}
    assert all(story.last_verified_at == now + timedelta(hours=6) for story in refreshed.stories)
    assert all(story.updated_at == previous_by_id[story.id].updated_at for story in refreshed.stories)
    assert any(story.importance_score_internal < previous_by_id[story.id].importance_score_internal for story in refreshed.stories)
    assert read_json(tmp_path/'content/generated/run-report.json')['cached_summaries']==len(snapshot.stories)
    validate_snapshot(snapshot,tmp_path)
    schema=read_json(tmp_path/'schemas/story.schema.json')
    broken=snapshot.stories[0].model_dump(mode='json')
    broken['evidence_state']='truth-score-99'
    from jsonschema import Draft202012Validator
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(broken)


async def test_total_source_failure_retains_previous_output(source,now):
    enabled=source.model_copy(update={'enabled':True})
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request:httpx.Response(500))) as client:
        fetcher=SafeFetcher(client,{},'TestBot')
        with pytest.raises(ValueError,match='previous snapshot preserved'):
            await runner.collect([enabled],fetcher,now,[],{},now)


async def test_rechecked_old_source_updates_evidence_outside_overlap(source, now):
    enabled = source.model_copy(update={'enabled': True})
    previous = normalize({'url': 'https://example.com/model', 'title': 'Official model release',
                          'text': 'Original evidence', 'published_at': (now - timedelta(days=8)).isoformat()}, source, now - timedelta(hours=6))
    xml = b'<rss version="2.0"><channel><title>Test</title><item><title>Official model release</title><link>https://example.com/model</link><description>Corrected evidence</description><pubDate>Fri, 25 Sep 2026 12:00:00 GMT</pubDate></item></channel></rss>'
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=xml, headers={'Content-Type': 'application/rss+xml'}))) as client:
        items = await runner.collect([enabled], SafeFetcher(client, {}, 'TestBot'), now, [previous], {}, now - timedelta(hours=12))
    assert len(items) == 1 and items[0].id == previous.id
    assert items[0].excerpt == 'Corrected evidence' and items[0].fetched_at == now
    assert items[0].content_hash != previous.content_hash
