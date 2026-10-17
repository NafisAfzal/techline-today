"""Isolated adversarial regressions for the master execution checkpoint."""

import asyncio
import errno
import json
import shutil
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

from pipeline import runner, source_diagnostics
from pipeline.adapters import ADAPTERS
from pipeline.normalize import normalize
from pipeline.security import SafeFetcher
from pipeline.storage import atomic_json
from pipeline.strict_json import strict_json

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("payload", [b'"\\ud800"', b'"\\udfff"', b'{"\\ud800":0}',
    b'"\\ud800x\\udc00"', b'"\\udc00\\ud800"', b'"\xff"'])
def test_invalid_unicode_is_rejected(payload):
    with pytest.raises(ValueError):
        strict_json(payload)


def test_valid_unicode_and_literal_escape_are_preserved():
    assert strict_json(b'"\\ud83d\\ude80"') == "\U0001f680"
    assert strict_json(b'"\\\\ud800"') == r"\ud800"
    assert strict_json('"বাংলা"'.encode()) == "বাংলা"


@pytest.mark.parametrize("payload,limits", [
    (b'[0,0,0,0]', {"max_container_items": 3}),
    (b'{"a":0,"b":0,"c":0,"d":0}', {"max_container_items": 3}),
    (b'[[0],[0],[0]]', {"max_tokens": 5}),
    (b'"' + b'x' * 40 + b'"', {"max_string_chars": 32}),
    (b'1' * 140, {}),
])
def test_allocation_limits_apply_before_json_decoder(payload, limits, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("JSON decoder ran before resource budget refusal")
    monkeypatch.setattr("pipeline.strict_json.json.loads", forbidden)
    with pytest.raises(ValueError, match="limit"):
        strict_json(payload, **limits)


@pytest.mark.parametrize("payload", [b'null', b'false', b'42', b'"text"', b'[]', b'{}'])
def test_parser_keeps_valid_json_types_for_adapter_schema_validation(payload):
    assert strict_json(payload) == json.loads(payload)


async def test_atom_update_is_not_a_publication(source, now):
    xml = b'<feed xmlns="http://www.w3.org/2005/Atom"><title>Updates</title><entry><id>one</id><title>Official project update</title><link href="https://example.com/update"/><updated>2026-10-03T10:00:00Z</updated></entry></feed>'
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(
            200, content=xml, headers={"content-type": "application/atom+xml"}))) as client:
        raw = (await ADAPTERS["rss"].fetch(source, SafeFetcher(client, {}, "SyntheticTest")))[0]
    item = normalize(raw, source, now)
    assert raw["published_at"] is None
    assert raw["updated_at"] == "2026-10-03T10:00:00Z"
    assert item.missing_publication_time is True


async def test_all_invalid_sources_refuse_instead_of_success(source, now):
    registry = [source.model_copy(update={"id": name, "enabled": True, "adapter": "json_api", "item_path": ""})
                for name in ("first", "second")]
    report = {}
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(
            200, json=[{"title": "A title without a URL"}]))) as client:
        with pytest.raises(ValueError, match="previous snapshot preserved"):
            await runner.collect(registry, SafeFetcher(client, {}, "SyntheticTest"), now, [], report, now)
    assert all(row["status"] == "failed" and row["invalid_items"] == 1 for row in report["sources"])


async def test_all_invalid_live_run_preserves_previous_snapshot(tmp_path, monkeypatch, now, source):
    for name in ("config", "prompts"):
        shutil.copytree(ROOT / name, tmp_path / name)
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    output = tmp_path / "content/generated/snapshot.json"
    await runner.run("fixture", output, now)
    before = output.read_bytes()
    source = source.model_copy(update={"enabled": True, "adapter": "json_api", "item_path": "",
                                       "verified_at": "2026-10-03"})
    original_config = runner.config
    monkeypatch.setattr(runner, "config", lambda name: {"sources": [source.model_dump(mode="json")]}
                        if name == "sources" else original_config(name))
    monkeypatch.setattr(runner, "public_transport", lambda: httpx.MockTransport(
        lambda req: httpx.Response(200, json=[{"title": "Missing source URL"}])))
    with pytest.raises(ValueError, match="previous snapshot preserved"):
        await runner.run("live", output, now)
    assert output.read_bytes() == before


async def test_unknown_publication_is_not_upgraded_by_retained_cache(tmp_path, monkeypatch, now, source):
    for name in ("config", "prompts"):
        shutil.copytree(ROOT / name, tmp_path / name)
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    source = source.model_copy(update={"id": "arxiv", "enabled": True, "verified_at": "2026-10-03"})
    raw = {"title": "Synthetic project provides an engineering update", "url": "https://example.com/a",
           "text": "The project provides an engineering update with source evidence."}
    old = normalize({**raw, "published_at": "2026-10-02T10:00:00Z"}, source, now)
    fresh = normalize(raw, source, now)
    assert old.missing_publication_time is False and fresh.missing_publication_time is True
    atomic_json(tmp_path / ".cache/state-live.json", {"fetch": {}, "providers": {},
        "items": [old.model_dump(mode="json")]})
    original_config = runner.config
    monkeypatch.setattr(runner, "config", lambda name: {"sources": [source.model_dump(mode="json")]}
                        if name == "sources" else original_config(name))
    async def collect(*args, **kwargs):
        return [fresh]
    monkeypatch.setattr(runner, "collect", collect)
    candidate = await runner.run("live", tmp_path / "content/generated/snapshot.json", now)
    retained = candidate.sources[fresh.id]
    assert retained.missing_publication_time is True
    assert retained.published_at == old.published_at  # Stable placeholder, never public evidence.


async def test_partial_invalid_collection_is_explicit(source, now):
    source = source.model_copy(update={"enabled": True, "adapter": "json_api", "item_path": ""})
    report = {}
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=[
            {"title": "Invalid item"}, {"title": "Valid project announcement", "url": "https://example.com/a"}]))) as client:
        items = await runner.collect([source], SafeFetcher(client, {}, "SyntheticTest"), now, [], report, now)
    assert len(items) == 1
    assert report["sources"][0]["collection_state"] == "COLLECTION_DEGRADED"


def release(**changes):
    return {"id": 1, "tag_name": "v1", "html_url": "https://github.com/owner/project/releases/tag/v1",
            "url": "https://api.github.com/repos/owner/project/releases/1", "draft": False,
            "prerelease": False, "published_at": "2026-10-03T10:00:00Z", **changes}


async def fetch_releases(source, payload):
    source = source.model_copy(update={"adapter": "github_releases", "endpoint": "https://api.github.com",
                                      "allowed_hosts": ["api.github.com"], "repositories": ["owner/project"]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=payload))) as client:
        return await ADAPTERS["github_releases"].fetch(source, SafeFetcher(client, {}, "SyntheticTest"))


@pytest.mark.parametrize("changes", [
    {"url": "https://api.github.com/repos/other/project/releases/1"},
    {"url": "https://api.github.com/repos/owner/project/releases/2"},
    {"url": "https://api.github.com/repos/owner/project/releases/1?spoof=yes"},
    {"url": "https://attacker.example/repos/owner/project/releases/1"},
    {"repository": {"full_name": "other/project"}},
])
async def test_contradictory_release_identity_refuses(source, changes):
    with pytest.raises(ValueError, match="identity"):
        await fetch_releases(source, [release(**changes)])


async def test_conflicting_duplicate_release_id_refuses(source):
    with pytest.raises(ValueError, match="Conflicting"):
        await fetch_releases(source, [release(), release(tag_name="v2",
            html_url="https://github.com/owner/project/releases/tag/v2")])


async def test_repository_case_is_insensitive_but_tag_is_exact(source):
    assert len(await fetch_releases(source, [release(
        html_url="https://github.com/OWNER/PROJECT/releases/tag/v1",
        url="https://api.github.com/repos/OWNER/PROJECT/releases/1")])) == 1
    with pytest.raises(ValueError):
        await fetch_releases(source, [release(html_url="https://github.com/owner/project/releases/tag/V1")])


@pytest.fixture
def diagnostic_root(tmp_path):
    (tmp_path / "config").mkdir()
    for name in ("phase4-research-sources.yaml", "source-rights.json", "sources.yaml", "release.json", "ai.yaml"):
        shutil.copyfile(ROOT / "config" / name, tmp_path / "config" / name)
    sentinel = tmp_path / "content/generated/snapshot.json"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_text('{"synthetic_sentinel":true}', encoding="utf-8")
    return tmp_path


async def test_concurrent_diagnostics_refuse_before_second_network_call(diagnostic_root):
    entered, finish = asyncio.Event(), asyncio.Event()
    calls = []
    async def response(request):
        calls.append(request)
        entered.set()
        await finish.wait()
        return source_diagnostics.fixture_response(request)
    task = asyncio.create_task(source_diagnostics.run_diagnostics(root=diagnostic_root,
        source_ids=["research_pytorch"], transport=httpx.MockTransport(response)))
    await asyncio.wait_for(entered.wait(), 3)
    try:
        with pytest.raises(FileExistsError):
            await source_diagnostics.run_diagnostics(root=diagnostic_root, source_ids=["research_nodejs"])
    finally:
        finish.set()
        report = await task
    assert len(calls) == 1
    assert report["collection_state"] == "COLLECTION_SUCCESS"
    assert report["rights_status"] == "RIGHTS_REVIEW_REQUIRED"
    assert report["editorial_status"] == "EDITORIAL_PENDING"
    assert report["exit_code"] == 0 and report["run_id"]
    assert not (diagnostic_root / ".cache/phase4/writer.lock").exists()


async def test_disk_full_preserves_diagnostic_last_good(diagnostic_root, monkeypatch):
    await source_diagnostics.run_diagnostics(root=diagnostic_root, source_ids=["research_pytorch"])
    path = diagnostic_root / ".cache/phase4/fixture-report.json"
    before = path.read_bytes()
    def disk_full(*args, **kwargs):
        raise OSError(errno.ENOSPC, "Synthetic full disk")
    monkeypatch.setattr("pipeline.storage.json.dump", disk_full)
    with pytest.raises(OSError):
        await source_diagnostics.run_diagnostics(root=diagnostic_root, source_ids=["research_pytorch"])
    assert path.read_bytes() == before
    assert not list(path.parent.glob("*.tmp"))
    assert not (path.parent / "writer.lock").exists()


def test_atomic_write_cannot_leave_corrupt_target(tmp_path):
    path = tmp_path / "last-good.json"
    atomic_json(path, {"generation": 1})
    with pytest.raises(TypeError):
        atomic_json(path, {"unserializable": object()})
    assert json.loads(path.read_text()) == {"generation": 1}
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize("value,precision", [("2026-10-02", "date"),
    ("2026-10-02T10:00:00", "unknown"), ("2026-10-02T10:00:00Z", "timestamp"),
    (None, "unknown"), ("2026-02-30", "unknown")])
def test_auxiliary_date_precision_is_honest(value, precision, now):
    evidence = source_diagnostics.date_evidence(value, now)
    assert evidence["precision"] == precision
    if precision != "timestamp":
        assert evidence["timestamp"] is None


async def test_release_creation_is_separate_from_publication(diagnostic_root):
    def handler(request):
        payload = source_diagnostics.fixture_response(request).json()
        payload[0].update(created_at="2026-10-15T10:00:00Z", published_at="2026-10-17T10:00:00Z")
        return httpx.Response(200, json=payload)
    report = await source_diagnostics.run_diagnostics(root=diagnostic_root, source_ids=["research_pytorch"],
        transport=httpx.MockTransport(handler))
    dates = report["sources"][0]["observations"][0]["dates"]
    assert dates["release_created"]["timestamp"] == "2026-10-15T10:00:00+00:00"
    assert dates["source_published"]["timestamp"] == "2026-10-17T10:00:00+00:00"
    assert dates["source_updated"]["precision"] == "unknown"


@pytest.mark.parametrize("relative", ["../escape.json", "config/source-rights.json", "pipeline/runner.py",
    ".cache/output.txt", "content/generated/other.json", ".cache/state-live.json",
    ".cache/phase3/reviews/ledger.json", ".cache/phase4/live-report.json"])
async def test_output_path_refuses_before_any_work(tmp_path, monkeypatch, relative):
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    def forbidden(*args, **kwargs):
        pytest.fail("Invalid output path reached configuration loading")
    monkeypatch.setattr(runner, "config", forbidden)
    with pytest.raises(ValueError, match="output"):
        await runner.run("fixture", tmp_path / relative)
    assert not list(tmp_path.iterdir())


def test_linked_snapshot_target_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda self: self.name == "generated" or original(self))
    with pytest.raises(ValueError, match="Linked"):
        runner.snapshot_output(tmp_path / "content/generated/snapshot.json")


def test_review_output_stays_local(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    assert runner.snapshot_output(tmp_path / ".cache/source-review.json") == tmp_path / ".cache/source-review.json"


def test_actual_link_cannot_redirect_snapshot_review_output(tmp_path, monkeypatch):
    root, outside = tmp_path / "repo", tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    sentinel = outside / "source-review.json"
    sentinel.write_bytes(b'{"preserve":true}')
    linked = root / ".cache"
    if sys.platform == "win32":
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(linked), str(outside)],  # noqa: S603,S607
                                check=False, capture_output=True)
        assert result.returncode == 0, "Synthetic junction setup failed"
    else:
        linked.symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(runner, "ROOT", root)
    try:
        with pytest.raises(ValueError, match="Linked"):
            runner.snapshot_output(linked / "source-review.json")
        assert sentinel.read_bytes() == b'{"preserve":true}'
    finally:
        if sys.platform == "win32":
            linked.rmdir()
        else:
            linked.unlink()


@pytest.mark.parametrize("xml", [b'<html><body>Not a feed</body></html>', b'<rss/>', b'<data/>'])
async def test_nonfeed_xml_is_not_an_empty_success(source, xml):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(
            200, content=xml, headers={"content-type": "application/xml"}))) as client:
        with pytest.raises(ValueError, match="feed"):
            await ADAPTERS["rss"].fetch(source, SafeFetcher(client, {}, "SyntheticTest"))


async def test_abrupt_writer_termination_leaves_last_good_and_refuses_stale_lock(diagnostic_root):
    await source_diagnostics.run_diagnostics(root=diagnostic_root, source_ids=["research_pytorch"])
    path = diagnostic_root / ".cache/phase4/fixture-report.json"
    previous = path.read_bytes()
    lock = path.parent / "writer.lock"
    code = ("import os,sys; from pathlib import Path; "
            "from pipeline.review_governance import writer_lock; "
            "guard=writer_lock(Path(sys.argv[1])); guard.__enter__(); os._exit(9)")
    result = subprocess.run([sys.executable, "-c", code, str(lock)], check=False, capture_output=True)  # noqa: S603
    assert result.returncode == 9 and lock.exists()
    with pytest.raises(FileExistsError):
        await source_diagnostics.run_diagnostics(root=diagnostic_root, source_ids=["research_pytorch"])
    assert path.read_bytes() == previous
    # Only this test owns the terminated synthetic writer and its isolated lock.
    lock.unlink()
    report = await source_diagnostics.run_diagnostics(root=diagnostic_root, source_ids=["research_pytorch"])
    assert report["collection_state"] == "COLLECTION_SUCCESS"
