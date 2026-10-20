"""Recovery inventory, offline backup validation and the synthetic disaster drills.

Every drill runs in an isolated temporary directory with synthetic identities.
A green drill proves the tooling refuses unsafe states; it does not certify a
production disaster-recovery capability.
"""

import json

import pytest

from pipeline.recovery.drills import DRILLS, drill_report, run_all_drills, run_drill
from pipeline.recovery.inventory import RECOVERY_ASSETS, inventory_report
from pipeline.recovery.verify import (
    PACK_FORMAT,
    build_recovery_pack,
    restore_recovery_pack,
    verify_recovery_pack,
)


def newsroom(tmp_path, name="newsroom"):
    from pipeline.recovery.fixtures import SyntheticNewsroom

    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "config/source-rights.json").write_text(
        json.dumps({"version": 1, "sources": {}}, indent=2) + "\n", encoding="utf-8")
    (root / "config/sources.yaml").write_text("version: 1\nsources: []\n", encoding="utf-8")
    room = SyntheticNewsroom(root)
    room.team()
    room.publish()
    return room


def pin_file(tmp_path, name="trust"):
    from pipeline.authority.protocol import canonical
    from pipeline.recovery.fixtures import SyntheticNewsroom

    directory = tmp_path / name
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "trust-pin.json"
    path.write_bytes(canonical(SyntheticNewsroom(directory).pin.model_dump(mode="json")) + b"\n")
    return path


# --- inventory ------------------------------------------------------------------

def test_the_inventory_separates_recoverable_data_from_irrecoverable_credentials():
    report = inventory_report()
    assert report["asset_count"] == len(RECOVERY_ASSETS)
    assert "owner-private-signing-key" in report["irrecoverable"]
    assert "reviewer-private-signing-keys" in report["irrecoverable"]
    assert "external-trusted-checkpoints" in report["irrecoverable"]
    assert "authority-journal" in report["recoverable"]
    assert report["credential_count"] >= 2
    assert report["publication_allowed"] is False


def test_every_inventory_asset_names_a_required_action():
    for asset in RECOVERY_ASSETS:
        assert asset.required_action.strip()
        assert asset.protection.strip()
        assert asset.notes.strip()


# --- recovery pack ---------------------------------------------------------------

def test_a_pack_is_readable_and_restorable(tmp_path):
    room = newsroom(tmp_path)
    pack = tmp_path / "pack"
    manifest = build_recovery_pack(room.root, pack, trust_file=pin_file(tmp_path))
    assert manifest["kind"] == PACK_FORMAT
    assert manifest["contains_private_keys"] is False
    verification = verify_recovery_pack(pack)
    assert verification.check("pack_readable")["result"] == "PASS"
    assert verification.check("journal_continuity")["result"] == "PASS"
    assert verification.check("restorable")["result"] == "PASS"
    assert verification.check("no_private_key_exposure")["result"] == "PASS"


def test_a_pack_without_a_checkpoint_is_blocked_for_currency(tmp_path):
    room = newsroom(tmp_path)
    pack = tmp_path / "pack"
    build_recovery_pack(room.root, pack, trust_file=pin_file(tmp_path))
    verification = verify_recovery_pack(pack)
    assert verification.check("trusted_checkpoint_comparison")["result"] == "BLOCKED"
    assert verification.current is False
    assert verification.independently_trusted is False
    assert "not an externally trusted checkpoint" in verification.trust_statement


def test_a_damaged_pack_member_is_detected(tmp_path):
    room = newsroom(tmp_path)
    pack = tmp_path / "pack"
    build_recovery_pack(room.root, pack, trust_file=pin_file(tmp_path))
    target = pack / "authority/journal.json"
    payload = bytearray(target.read_bytes())
    payload[20:24] = b"XXXX"
    target.write_bytes(bytes(payload))
    verification = verify_recovery_pack(pack)
    assert verification.status == "FAIL"
    assert verification.check("pack_readable")["result"] == "FAIL"


def test_a_pack_never_exports_private_key_material(tmp_path):
    room = newsroom(tmp_path)
    secret = tmp_path / "secret-pin.json"
    secret.write_bytes(
        b"-----BEGIN ENCRYPTED PRIVATE KEY-----\nSYNTHETIC-NONSECRET-PLACEHOLDER\n")
    pack = tmp_path / "pack"
    with pytest.raises(ValueError, match="private key material"):
        build_recovery_pack(room.root, pack, trust_file=secret)


def test_a_restore_refuses_a_non_empty_destination(tmp_path):
    room = newsroom(tmp_path)
    pack = tmp_path / "pack"
    build_recovery_pack(room.root, pack, trust_file=pin_file(tmp_path))
    destination = tmp_path / "restore"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "existing.txt").write_text("keep me", encoding="utf-8")
    with pytest.raises(ValueError, match="empty destination"):
        restore_recovery_pack(pack, destination)


def test_a_restore_never_follows_an_unsafe_member_path(tmp_path):
    pack = tmp_path / "pack"
    pack.mkdir(parents=True, exist_ok=True)
    (pack / "manifest.json").write_text(json.dumps({
        "version": 1, "kind": PACK_FORMAT,
        "files": [{"path": "../escape.json", "bytes": 0, "sha256": "0" * 64}]}), encoding="utf-8")
    with pytest.raises(ValueError, match="unsafe path"):
        restore_recovery_pack(pack, tmp_path / "restore")


def test_the_expected_identity_mismatch_is_reported(tmp_path):
    room = newsroom(tmp_path)
    pack = tmp_path / "pack"
    build_recovery_pack(room.root, pack, trust_file=pin_file(tmp_path))
    verification = verify_recovery_pack(pack, expected={"ledger_id": "a-different-ledger"})
    assert verification.check("expected_identity")["result"] == "FAIL"


def test_an_absent_expected_identity_is_inconclusive_not_a_pass(tmp_path):
    room = newsroom(tmp_path)
    pack = tmp_path / "pack"
    build_recovery_pack(room.root, pack, trust_file=pin_file(tmp_path))
    verification = verify_recovery_pack(pack)
    assert verification.check("expected_identity")["result"] == "INCONCLUSIVE"


# --- drills ------------------------------------------------------------------------

@pytest.mark.parametrize("drill_id", sorted(DRILLS))
def test_every_drill_behaves_as_required(drill_id, tmp_path):
    result = run_drill(drill_id, tmp_path / drill_id)
    assert result.result in {"PASS", "FAIL", "BLOCKED"}
    assert result.result != "FAIL", f"{drill_id} did not behave as required: {result.actual_behavior}"
    assert result.fixture.strip()
    assert result.injected_failure.strip()
    assert result.expected_behavior.strip()
    assert result.actual_behavior.strip()
    assert result.human_intervention
    assert result.as_dict()["synthetic_only"] is True


def test_the_drill_set_covers_every_named_scenario():
    results = {row.drill_id: row for row in run_all_drills()}
    assert len(results) == 15
    names = " ".join(row.name.lower() for row in results.values())
    for scenario in ["clean recovery", "incomplete backup", "corrupted ledger", "journal truncation",
                     "old trust registry", "revoked reviewer", "old approval replay",
                     "missing trusted checkpoint", "conflicting", "interrupted halfway",
                     "wrong environment", "duplicate decision", "compromised reviewer key",
                     "lost owner signing key", "emergency publication stop"]:
        assert scenario in names


def test_the_drill_report_never_claims_a_production_certification():
    report = drill_report(run_all_drills())
    assert report["synthetic_only"] is True
    assert report["production_recovery_certified"] is False
    assert report["failed"] == 0
    assert report["drill_count"] == 15
    assert "do not certify" in report["note"]


def test_the_lost_owner_key_drill_is_blocked_because_a_key_cannot_be_restored():
    result = run_drill("DR-14")
    assert result.result == "BLOCKED"
    assert any("owner" in action.lower() for action in result.human_intervention)
    assert "owner-private-signing-key" in result.evidence["irrecoverable_assets"]


def test_the_emergency_stop_drill_refuses_currency():
    result = run_drill("DR-15")
    assert result.result == "PASS"
    assert result.evidence["code"] == "emergency_hold"
    assert result.evidence["status"] == "BLOCKED"


def test_drill_directories_are_isolated_from_the_checkout(tmp_path):
    result = run_drill("DR-01", tmp_path / "isolated")
    assert result.result == "PASS"
    assert str(tmp_path) not in json.dumps(result.as_dict(), default=str)
