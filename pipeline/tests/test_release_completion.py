"""Meaningful parser, transport and interrupted-generation regressions."""

import errno
import gzip
import json
import shutil
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import httpx
import pytest

from pipeline import generation, runner
from pipeline.adapters import ADAPTERS
from pipeline.filesystem import atomic_bytes, confined_file
from pipeline.observations import compact_receipt, summary
from pipeline.review_governance import digest
from pipeline.security import SafeFetcher


async def fetch_feed(source, content):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(
            200, content=content, headers={"content-type": "application/xml"}))) as client:
        return await ADAPTERS["rss"].fetch(source, SafeFetcher(client, {}, "SyntheticTest"))


async def test_feed_depth_is_bounded_before_full_tree_allocation(source):
    xml = b"<rss><channel>" + b"<nested>" * 80 + b"x" + b"</nested>" * 80 + b"</channel></rss>"
    with pytest.raises(ValueError, match="XML.*limit"):
        await fetch_feed(source, xml)


async def test_feed_node_count_is_bounded(source):
    with pytest.raises(ValueError, match="XML.*limit"):
        await fetch_feed(source, b'<rss><channel>' + b'<tiny/>' * 100001 + b'</channel></rss>')


async def test_feed_with_only_invalid_entries_cannot_be_successful_empty(source, now):
    from pipeline.runner import collect
    xml = b"<rss><channel><title>Test</title><item><title>Missing URL</title></item></channel></rss>"
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(
            200, content=xml, headers={"content-type": "application/xml"}))) as client:
        with pytest.raises(ValueError, match="All configured sources failed"):
            await collect([source.model_copy(update={"enabled": True})], SafeFetcher(client, {}, "Test"),
                          now, [], {}, now)


async def test_unrequested_compression_is_refused_before_expansion(source):
    compressed = gzip.compress(b"x" * 4_000_000)
    class UnreadCompressedStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            pytest.fail('Compressed stream was read before the encoding check')
            yield compressed
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(
            200, stream=UnreadCompressedStream(), headers={"content-type": "application/xml", "content-encoding": "gzip"}))) as client:
        with pytest.raises(ValueError, match="[Cc]ompress"):
            await SafeFetcher(client, {}, "Test").get(source.endpoint, source, accept=("application/xml",))


def interrupted(tmp_path, monkeypatch):
    snapshot = tmp_path / 'content/generated/snapshot.json'
    state = tmp_path / '.cache/state-fixture.json'
    atomic_bytes(snapshot, b'old snapshot')
    atomic_bytes(state, b'old state')
    original = generation.atomic_bytes
    def fail(path, payload):
        if path == state and payload == b'new state':
            raise OSError(errno.ENOSPC, 'Synthetic disk full during promotion')
        return original(path, payload)
    with monkeypatch.context() as patch:
        patch.setattr(generation, 'atomic_bytes', fail)
        with generation.writer(tmp_path), pytest.raises(OSError):
            generation.promote(tmp_path, [(snapshot, b'new snapshot'), (state, b'new state')])
    assert snapshot.read_bytes() == b'new snapshot'
    assert state.read_bytes() == b'old state'
    assert not (tmp_path / generation.LOCK).exists()
    with pytest.raises(ValueError, match='Interrupted generation'):
        generation.assert_stable(tmp_path)
    return snapshot, state


@pytest.mark.parametrize('action, expected', [('finish', b'new'), ('rollback', b'old')])
def test_partial_promotion_has_barrier_and_recovery(tmp_path, monkeypatch, action, expected):
    snapshot, state = interrupted(tmp_path, monkeypatch)
    with generation.writer(tmp_path):
        generation.recover(tmp_path, action)
    generation.assert_stable(tmp_path)
    assert snapshot.read_bytes() == expected + b' snapshot'
    assert state.read_bytes() == expected + b' state'
    # A normal repeat is coherent and creates a separate recovery generation.
    with generation.writer(tmp_path):
        generation.promote(tmp_path, [(snapshot, b'next snapshot'), (state, b'next state')])
    assert snapshot.read_bytes() == b'next snapshot' and state.read_bytes() == b'next state'


def test_corrupt_recovery_payload_refuses_before_any_target_changes(tmp_path, monkeypatch):
    snapshot, state = interrupted(tmp_path, monkeypatch)
    before = snapshot.read_bytes(), state.read_bytes()
    journal = json.loads((tmp_path / generation.JOURNAL).read_text())
    (tmp_path / generation.GENERATIONS / journal['generation'] / '1.after').write_bytes(b'corrupt')
    with generation.writer(tmp_path), pytest.raises(ValueError, match='integrity|byte limit'):
        generation.recover(tmp_path, 'finish')
    assert (snapshot.read_bytes(), state.read_bytes()) == before
    assert (tmp_path / generation.JOURNAL).exists()


def test_recovery_preserves_unrelated_post_crash_edits(tmp_path, monkeypatch):
    snapshot, state = interrupted(tmp_path, monkeypatch)
    state.write_bytes(b'user edit after crash')
    with generation.writer(tmp_path), pytest.raises(ValueError, match='outside'):
        generation.recover(tmp_path, 'rollback')
    assert state.read_bytes() == b'user edit after crash' and snapshot.read_bytes() == b'new snapshot'


def test_stage_disk_full_preserves_complete_old_generation(tmp_path, monkeypatch):
    snapshot = tmp_path / 'content/generated/snapshot.json'
    atomic_bytes(snapshot, b'old')
    def full(*args):
        raise OSError(errno.ENOSPC, 'Synthetic stage disk full')
    monkeypatch.setattr(generation, 'atomic_bytes', full)
    with generation.writer(tmp_path), pytest.raises(OSError):
        generation.promote(tmp_path, [(snapshot, b'new')])
    generation.assert_stable(tmp_path)
    assert snapshot.read_bytes() == b'old'


def test_exclusive_writer_and_abrupt_process_death(tmp_path):
    with generation.writer(tmp_path), pytest.raises(FileExistsError), generation.writer(tmp_path):
        pytest.fail('A concurrent writer entered')
    script = ('import os,sys;from pathlib import Path;from pipeline.generation import writer;'
              'guard=writer(Path(sys.argv[1]));guard.__enter__();os._exit(17)')
    result = subprocess.run([sys.executable, '-c', script, str(tmp_path)], check=False, capture_output=True)  # noqa: S603
    assert result.returncode == 17
    with pytest.raises(FileExistsError), generation.writer(tmp_path):
        pytest.fail('A dead writer lock was stolen')
    # Only this test owns the killed process and its temporary directory.
    (tmp_path / generation.LOCK).unlink()


@pytest.mark.parametrize('path', ['../escape.json', 'config/source-rights.json',
    '.cache/phase3/reviews/ledger.json', 'content/generated/CON.json',
    '.cache/source-review/name. /out.json', '.cache/source-review/name:stream.json'])
def test_generation_cannot_target_code_ledgers_or_ambiguous_names(tmp_path, path):
    with generation.writer(tmp_path), pytest.raises(ValueError):
        generation.promote(tmp_path, [(tmp_path / path, b'unsafe')])
    assert not (tmp_path / generation.JOURNAL).exists()


def test_directory_and_case_insensitive_collisions_refuse(tmp_path):
    (tmp_path / '.cache/state-fixture.json').mkdir(parents=True)
    with pytest.raises(ValueError, match='collides'):
        confined_file(tmp_path, '.cache/state-fixture.json')
    path = tmp_path / 'content/generated/snapshot.json'
    with generation.writer(tmp_path), pytest.raises(ValueError, match='Duplicate'):
        generation.promote(tmp_path, [(path, b'one'), (path, b'two')])
    assert not path.exists()


async def test_runner_stages_schemas_snapshot_and_state_as_one_generation(tmp_path, monkeypatch, now):
    root = Path(__file__).resolve().parents[2]
    for directory in ('config', 'prompts'):
        shutil.copytree(root / directory, tmp_path / directory)
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    output = tmp_path / 'content/generated/snapshot.json'
    await runner.run('fixture', output, now)
    manifest = json.loads(next((tmp_path / generation.GENERATIONS).glob('*/manifest.json')).read_text())
    names = {entry['path'] for entry in manifest['files']}
    assert {'content/generated/snapshot.json', 'content/generated/run-report.json', 'content/generated/briefing.md',
            '.cache/state-fixture.json', '.cache/translations-fixture.json', 'schemas/snapshot.schema.json'} <= names
    report = json.loads((tmp_path / 'content/generated/run-report.json').read_text())
    assert report['generation_id'] == manifest['generation']
    # A restart cannot proceed through an unresolved interrupted generation.
    atomic_bytes(tmp_path / generation.JOURNAL, b'{}')
    before = output.read_bytes()
    with pytest.raises(ValueError, match='Interrupted'):
        await runner.run('fixture', output, now)
    assert output.read_bytes() == before


async def test_killed_runner_after_snapshot_promotion_can_roll_back(tmp_path, monkeypatch, now):
    root = Path(__file__).resolve().parents[2]
    for directory in ('config', 'prompts'):
        shutil.copytree(root / directory, tmp_path / directory)
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    output = tmp_path / 'content/generated/snapshot.json'
    await runner.run('fixture', output, now)
    paths = [output, tmp_path / '.cache/state-fixture.json', tmp_path / 'content/generated/run-report.json']
    before = [path.read_bytes() for path in paths]
    script = '''
import asyncio, os, sys
from datetime import datetime
from pathlib import Path
from pipeline import runner, generation
runner.ROOT = Path(sys.argv[1])
target = runner.ROOT / 'content/generated/snapshot.json'
original = generation.atomic_bytes
def terminate_after_snapshot(path, payload):
    original(path, payload)
    if path == target:
        os._exit(19)
generation.atomic_bytes = terminate_after_snapshot
asyncio.run(runner.run('fixture', target, datetime.fromisoformat(sys.argv[2])))
'''
    result = subprocess.run(  # noqa: S603 - fixed fixture program and test-owned paths
        [sys.executable, '-c', script, str(tmp_path), (now + timedelta(hours=6)).isoformat()],
        check=False, capture_output=True)
    assert result.returncode == 19
    assert output.read_bytes() != before[0]
    assert (tmp_path / generation.JOURNAL).exists() and (tmp_path / generation.LOCK).exists()
    with pytest.raises(FileExistsError):
        await runner.run('fixture', output, now)
    # This test owns the dead process and may release only its isolated lock.
    (tmp_path / generation.LOCK).unlink()
    with generation.writer(tmp_path):
        generation.recover(tmp_path, 'rollback')
    assert [path.read_bytes() for path in paths] == before
    generation.assert_stable(tmp_path)


def test_simulation_loops_cannot_replace_elapsed_live_observations(now):
    def receipt(day, *, live=True):
        return {'observed_at': (now + timedelta(days=day)).isoformat(), 'live': live,
                'sources': [{'source_id': 'official', 'collection_state': 'COLLECTION_SUCCESS'}]}
    synthetic = [receipt(day, live=False) for day in range(8)]
    assert summary(synthetic, now + timedelta(days=7))['live_observations'] == 0
    repeated = [receipt(0) for _ in range(8)]
    assert summary(repeated, now)['sustained_threshold_met'] is False
    daily = [receipt(day) for day in range(8)]
    assert summary(daily, now + timedelta(days=7))['sustained_threshold_met'] is True
    daily[-1]['sources'][0]['collection_state'] = 'COLLECTION_FAILED'
    assert summary(daily, now + timedelta(days=7))['sustained_threshold_met'] is False
    with pytest.raises(ValueError, match='clock'):
        summary([receipt(1)], now)


async def test_manual_observation_is_minimal_and_synthetic_never_counts(tmp_path, monkeypatch):
    from pipeline import observations
    for directory in ('config',):
        shutil.copytree(Path(__file__).resolve().parents[2] / directory, tmp_path / directory)
    report = await observations.run_diagnostics(root=tmp_path)
    observed_at = observations.datetime.now(observations.UTC)
    receipt = compact_receipt(report, observed_at)
    serialized = json.dumps(receipt)
    assert not any(word in serialized for word in ('Synthetic release fixture', 'canonical_url', 'excerpt'))
    assert receipt['live'] is False
    report['publication_allowed'] = True
    report['report_sha256'] = digest({key: value for key, value in report.items() if key != 'report_sha256'})
    with pytest.raises(ValueError, match='non-isolated'):
        compact_receipt(report, observed_at)
    result, code = await observations.observe(root=tmp_path)
    assert code == 0 and result['live_observations'] == 0 and not result['sustained_threshold_met']


async def test_duplicate_release_id_cannot_hide_behind_draft_flag(source):
    source = source.model_copy(update={'adapter': 'github_releases', 'endpoint': 'https://api.github.com',
        'allowed_hosts': ['api.github.com'], 'repositories': ['owner/project']})
    release = {'id': 1, 'tag_name': 'v1.0', 'html_url': 'https://github.com/owner/project/releases/tag/v1.0',
               'name': 'Release', 'body': 'Synthetic update', 'draft': False, 'prerelease': False}
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(
            200, json=[release, {**release, 'draft': True}]))) as client:
        with pytest.raises(ValueError, match='Conflicting'):
            await ADAPTERS['github_releases'].fetch(source, SafeFetcher(client, {}, 'Test'))


def test_observation_directory_budget_refuses_before_loading_extra_records(tmp_path, monkeypatch, now):
    from pipeline import observations
    parent = tmp_path / observations.DIRECTORY
    parent.mkdir(parents=True)
    receipt = {'version': 1, 'live': True}
    receipt['receipt_sha256'] = digest(receipt)
    calls = []
    def bounded(*args, **kwargs):
        calls.append(args[0])
        return receipt
    monkeypatch.setattr(observations, 'bounded_json', bounded)
    for day in range(40):
        (parent / f'{(now + timedelta(days=day)).date().isoformat()}.json').write_text('{}')
    with pytest.raises(ValueError, match='retention capacity'):
        observations.read_receipts(tmp_path)
    assert len(calls) <= 31
