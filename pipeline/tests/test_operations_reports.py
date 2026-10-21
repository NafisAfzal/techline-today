import json
import shutil
from pathlib import Path

import pytest

from pipeline.operations.__main__ import main
from pipeline.operations.reports import console, observation_plan, preview_report, rights_packets
from pipeline.recovery.fixtures import SYNTHETIC_NOW

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def isolated(tmp_path):
    (tmp_path / "config").mkdir()
    for name in ["source-research.json", "source-rights.json", "sources.yaml", "release.json",
                 "security-advisories.json"]:
        shutil.copyfile(ROOT / "config" / name, tmp_path / "config" / name)
    return tmp_path


async def test_source_fault_matrix_uses_only_mock_transport_and_isolated_outputs(tmp_path, monkeypatch):
    from pipeline import source_diagnostics
    from pipeline.operations.reliability import source_rehearsal

    def forbidden():
        pytest.fail("Offline rehearsal attempted a real network transport")
    monkeypatch.setattr(source_diagnostics, "public_transport", forbidden)
    before = set(tmp_path.iterdir())
    result = await source_rehearsal(ROOT)
    assert result["status"] == "PASS", result["cases"]
    assert len(result["cases"]) == 16 and not result["publication_allowed"]
    assert set(tmp_path.iterdir()) == before


def test_packets_reuse_existing_candidates_without_grants_or_registration(isolated):
    result = rights_packets(isolated, now=SYNTHETIC_NOW)
    assert len(result["packets"]) == 3 and result["status"] == "BLOCKED"
    for p in result["packets"]:
        assert p["candidate"]["rights_evidence_status"] == "RIGHTS_UNVERIFIED"
        assert p["reviewer_identity"] is None
        assert p["candidate"]["ai_submission_allowed"] is None
        assert not p["publication_allowed"] and not p["activation_allowed"]
    assert not (isolated / ".cache").exists()


@pytest.mark.parametrize("requested", [[], ["unknown"], ["cisa_kev", "cisa_kev"], ["unknown"] * 6])
def test_packets_refuse_unknown_duplicate_and_unbounded_scope(isolated, requested):
    with pytest.raises(ValueError):
        rights_packets(isolated, requested)


def test_console_reads_clean_checkout_without_generated_snapshot(isolated):
    before = {str(p.relative_to(isolated)): p.read_bytes() for p in isolated.rglob("*") if p.is_file()}
    result = console(isolated, now=SYNTHETIC_NOW)
    assert result["status"] == "BLOCKED" and not result["unreadable_sections"]
    assert result["sections"]["ceremony"]["authority"]["status"] == "UNPROVISIONED"
    assert not result["publication_allowed"]
    after = {str(p.relative_to(isolated)): p.read_bytes() for p in isolated.rglob("*") if p.is_file()}
    assert before == after


def test_corrupt_editorial_queue_is_failure_not_empty_health(isolated):
    p = isolated / ".cache/phase6/editorial-decisions.json"
    p.parent.mkdir(parents=True)
    p.write_bytes(b'{"events": [')
    result = console(isolated, now=SYNTHETIC_NOW)
    assert result["status"] == "FAIL" and "editorial_queue" in result["unreadable_sections"]
    assert p.read_bytes() == b'{"events": ['


def test_fake_observation_template_never_creates_days(isolated):
    result = observation_plan(isolated, now=SYNTHETIC_NOW)
    assert len(result["planned_utc_dates"]) == 8
    assert result["genuinely_authenticated_days"] == 0
    assert result["existing_window"]["eligible"] is False
    assert result["daily_template"]["kind"] == "TEMPLATE_NOT_RECEIPT"
    assert not (isolated / ".cache").exists()


def test_preview_never_promotes_local_flags_to_account_verification(isolated):
    p = isolated / "config/release.json"
    data = json.loads(p.read_text())
    data.update(preview_approved=True, free_plan_verified=True, zero_spend_verified=True)
    p.write_text(json.dumps(data))
    result = preview_report(isolated, now=SYNTHETIC_NOW)
    assert result["status"] == "BLOCKED" and result["account_settings"] == "INCONCLUSIVE"
    assert not result["deployment_performed"] and not result["publication_allowed"]


@pytest.mark.parametrize("args,code", [
    (["ceremony", "--template"], 0), (["ceremony"], 2), (["schema", "receipt"], 0),
    (["appointment-packet", "native-bn"], 0), (["observation-plan"], 2),
    (["preview"], 2), (["console"], 2), (["rights-packets"], 2),
])
def test_cli_outputs_honest_status_and_exit_code(isolated, capsys, args, code):
    assert main(["--root", str(isolated), *args]) == code
    result = json.loads(capsys.readouterr().out)
    assert result.get("publication_allowed") is not True
    assert not (isolated / ".cache").exists()
