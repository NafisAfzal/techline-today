import hashlib
import json
import shutil
import sys

import pytest

import pipeline.runner as runner
from pipeline.backup import export_backup, restore_backup, verify_backup
from pipeline.normalize import classify
from pipeline.ranking import rank
from scripts.production_state import main as workflow_state_main


@pytest.mark.parametrize(("mode", "flag", "enabled"), [("live", None, False), ("live", "false", False), ("live", "true", True), ("fixture", "true", False), ("live", "TRUE", False), ("live", "1", False)])
def test_inference_requires_explicit_live_opt_in(monkeypatch, mode, flag, enabled):
    if flag is None:
        monkeypatch.delenv("PIPELINE_AI_ENABLED", raising=False)
    else:
        monkeypatch.setenv("PIPELINE_AI_ENABLED", flag)
    assert runner.providers_enabled(mode) is enabled


def test_incidental_research_does_not_reclassify_business_news():
    assert classify("NVIDIA invests in a European company", "Its work supports scientific research and cloud computing.", ["ai"]) != "research"
    assert classify("A new research paper on model evaluation", "The API is available.", ["ai"]) == "research"
    assert classify("Critical CVE disclosed in an AI library", "", ["ai"]) == "security"


def test_headline_only_and_community_prose_are_downranked(items, now):
    value = items[0].model_copy(update={"excerpt": "Evidence-backed detailed prose. " * 5, "source_class": "primary"})
    headline_only = value.model_copy(update={"excerpt": ""})
    repeated_title = value.model_copy(update={"excerpt": value.title})
    cfg, categories = runner.config("ranking"), runner.config("categories")["categories"]
    assert rank([value], cfg, categories, now) > rank([headline_only], cfg, categories, now)
    assert rank([repeated_title], cfg, categories, now) == rank([headline_only], cfg, categories, now)


@pytest.fixture
async def live_root(tmp_path, monkeypatch, now):
    root = tmp_path / "data"
    for folder in ("config", "prompts"):
        shutil.copytree(runner.ROOT / folder, root / folder)
    monkeypatch.setattr(runner, "ROOT", root)
    snapshot = await runner.run("fixture", root / "content/generated/snapshot.json", now)
    payload = snapshot.model_dump(mode="json")
    payload["mode"] = "live"
    payload["archive_index"] = []
    for story in payload["stories"]:
        story["is_demo"] = False
        story["translations"] = {}
    for source in payload["sources"].values():
        source["is_demo"] = False
    for offer in payload["offers"]:
        offer["is_demo"] = False
    for release in payload["model_releases"]:
        release["is_demo"] = False
    (root / "content/generated/snapshot.json").write_text(json.dumps(payload), encoding="utf-8")
    (root / ".env").write_text("PRIVATE_VALUE=must-not-be-backed-up\n")
    return root


async def test_backup_roundtrip_omits_credentials_and_caches(live_root, tmp_path):
    pack, restored = tmp_path / "pack", tmp_path / "restored"
    (live_root / "content/archives").mkdir(parents=True, exist_ok=True)
    path = live_root / "content/generated/snapshot.json"
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    entry = {"key": "2025-02", "count": 0, "url": "/archives/2025-02/"}
    snapshot["archive_index"] = [entry]
    path.write_text(json.dumps(snapshot), encoding="utf-8")
    (live_root / "content/archives/2025-02.json").write_text('{"key":"2025-02","stories":[],"sources":{}}')
    (live_root / "content/archives/2025.json").write_text(json.dumps({"year": "2025", "months": [entry], "count": 0}))
    manifest = export_backup(live_root, pack)
    assert all(item["path"] != ".env" for item in manifest["files"])
    restore_backup(pack, restored)
    assert (restored / "content/generated/snapshot.json").read_bytes() == (live_root / "content/generated/snapshot.json").read_bytes()
    assert not (restored / ".env").exists()
    assert (restored / "content/archives/2025.json").read_bytes() == (live_root / "content/archives/2025.json").read_bytes()


async def test_backup_excludes_orphan_fixture_archives_without_deleting_them(live_root, tmp_path):
    orphan = live_root / "content/archives/2025-02.json"
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_text('{"stories":[{"is_demo":true}]}')
    manifest = export_backup(live_root, tmp_path / "pack")
    assert not any(item["path"].startswith("content/archives/") for item in manifest["files"])
    assert orphan.exists()


async def test_backup_rejects_injected_unreferenced_archive_even_with_valid_hash(live_root, tmp_path):
    pack = tmp_path / "pack"
    manifest = export_backup(live_root, pack)
    payload = b'{"stories":[{"is_demo":true}]}'
    name = "content/archives/2025-02.json"
    target = pack / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    manifest["files"].append({"path": name, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})
    (pack / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="unreferenced"):
        verify_backup(pack)


async def test_workflow_cache_roundtrip_validates_pack_before_replacing_fixture(live_root, monkeypatch):
    monkeypatch.chdir(live_root)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setattr(sys, "argv", ["production_state", "save"])
    workflow_state_main()
    snapshot = live_root / "content/generated/snapshot.json"
    original = snapshot.read_bytes()
    snapshot.write_text('{"mode":"fixture"}')
    monkeypatch.setattr(sys, "argv", ["production_state", "restore"])
    workflow_state_main()
    assert snapshot.read_bytes() == original
    assert (live_root / ".env").read_text() == "PRIVATE_VALUE=must-not-be-backed-up\n"


async def test_backup_detects_corruption_before_restore(live_root, tmp_path):
    pack, restored = tmp_path / "pack", tmp_path / "restored"
    export_backup(live_root, pack)
    (pack / "content/generated/snapshot.json").write_text("{}")
    with pytest.raises(ValueError, match="integrity"):
        restore_backup(pack, restored)
    assert not restored.exists()


async def test_backup_rejects_path_injection(live_root, tmp_path):
    pack = tmp_path / "pack"
    manifest = export_backup(live_root, pack)
    manifest["files"][0]["path"] = "../.env"
    (pack / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="allowlisted"):
        verify_backup(pack)


async def test_restore_never_overwrites_existing_directory(live_root, tmp_path):
    pack = tmp_path / "pack"
    export_backup(live_root, pack)
    with pytest.raises(ValueError, match="empty destination"):
        restore_backup(pack, live_root)


async def test_backup_rejects_fixture_mode(live_root, tmp_path):
    path = live_root / "content/generated/snapshot.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["mode"] = "fixture"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="Only live"):
        export_backup(live_root, tmp_path / "pack")


async def test_backup_requires_referenced_archives(live_root, tmp_path):
    path = live_root / "content/generated/snapshot.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["archive_index"] = [{"key": "2025-02", "count": 1, "url": "/archives/2025-02/"}]
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="archive is missing"):
        export_backup(live_root, tmp_path / "pack")


async def test_invalid_summary_consumes_candidate_budget(tmp_path, monkeypatch, now):
    for folder in ("config", "prompts"):
        shutil.copytree(runner.ROOT / folder, tmp_path / folder)
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setenv("PIPELINE_MAX_LLM_STORIES_PER_RUN", "1")
    original = runner.AIRouter.summarize
    attempts = []
    async def summarize(router, group, allow_ai=True):
        attempts.append(allow_ai)
        if len(attempts) == 1:
            raise ValueError("Invalid evidence")
        return await original(router, group, allow_ai=allow_ai)
    monkeypatch.setattr(runner.AIRouter, "summarize", summarize)
    await runner.run("fixture", tmp_path / "content/generated/snapshot.json", now)
    assert attempts[0] and len(attempts) > 1 and not any(attempts[1:])


async def test_backup_rejects_schema_invalid_archive_with_matching_checksums(live_root, tmp_path):
    path = live_root / "content/generated/snapshot.json"
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    snapshot["archive_index"] = [{"key": "2025-02", "count": 1, "url": "/archives/2025-02/"}]
    path.write_text(json.dumps(snapshot), encoding="utf-8")
    archives = live_root / "content/archives"
    archives.mkdir(parents=True, exist_ok=True)
    (archives / "2025-02.json").write_text('{"key":"2025-02","stories":[{}],"sources":{}}')
    (archives / "2025.json").write_text(json.dumps({"year":"2025","months":snapshot["archive_index"],"count":1}))
    with pytest.raises(ValueError):
        export_backup(live_root, tmp_path / "pack")
