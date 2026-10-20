"""Independent adversarial regressions; every write uses an isolated fixture."""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest

from pipeline.authority.checkpoint import (
    IndependentExpectation,
    build_attestation,
    digest_attestation,
    verify_external_checkpoint,
)
from pipeline.recovery.fixtures import SYNTHETIC_NOW, SyntheticNewsroom
from pipeline.recovery.verify import PACK_FORMAT, restore_recovery_pack, verify_recovery_pack


def checkpoint(tmp_path):
    room = SyntheticNewsroom(tmp_path / "room")
    room.admin("revoke_source", "preexisting-denial")
    document = build_attestation(room.checkpoint(), custody="protected-git-history",
                                 authentication="independently-signed", captured_at=SYNTHETIC_NOW,
                                 verified_by="forged-independent-custodian")
    return room, document


@pytest.mark.parametrize("custody", [None, "unknown", "operator-offline-file", "protected-git-history",
                                    "read-only-mirror", "local-state-directory"])
@pytest.mark.parametrize("challenge", [None, "synthetic-recovery-challenge"])
def test_local_claims_and_copied_digest_cannot_establish_current_trust(tmp_path, custody, challenge):
    room, document = checkpoint(tmp_path)
    result = verify_external_checkpoint(
        document=document, document_bytes=None, pin=room.pin, history=room.history(), now=SYNTHETIC_NOW,
        custody=custody, expectation=IndependentExpectation(
            document_sha256=digest_attestation(document), challenge=challenge, source="forged-custodian"))
    assert result.status == "BLOCKED"
    assert not result.current and not result.independently_trusted and not result.trusted
    assert result.trust_level not in {"CURRENTLY_TRUSTED", "INDEPENDENTLY_AUTHENTICATED"}


def test_self_consistent_old_state_with_rolled_back_clock_is_not_current(tmp_path):
    room, document = checkpoint(tmp_path)
    old_history = room.history()
    room.admin("revoke_source", "new-denial")
    result = verify_external_checkpoint(
        document=document, document_bytes=None, pin=room.pin, history=old_history, now=SYNTHETIC_NOW,
        custody="protected-git-history", expectation=IndependentExpectation(
            document_sha256=digest_attestation(document), challenge=document.checkpoint_envelope.payload.challenge))
    assert result.status == "BLOCKED" and not result.current


def pack_with(tmp_path, paths):
    pack = tmp_path / "pack"
    pack.mkdir()
    rows = []
    for name in paths:
        data = b"{}"
        rows.append({"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        if name in {"policy/source-rights.json", "policy/sources.yaml", "evidence/index.json"}:
            file = pack / name
            file.parent.mkdir(exist_ok=True)
            file.write_bytes(data)
    (pack / "manifest.json").write_text(json.dumps({"version": 1, "kind": PACK_FORMAT,
                                                  "journal_present": False, "files": rows}))
    return pack


@pytest.mark.parametrize("unsafe", ["../escape", "C:/escape", "C:escape", "\\escape", "//server/share",
                                   "policy/NUL.json", "policy/sources.yaml.", "policy/sources.yaml ",
                                   "policy/sources.yaml:stream", "run.exe"])
def test_restore_preflights_all_members_before_any_write(tmp_path, unsafe):
    pack = pack_with(tmp_path, ["policy/source-rights.json", unsafe])
    destination = tmp_path / "restore"
    with pytest.raises(ValueError):
        restore_recovery_pack(pack, destination)
    assert not destination.exists()
    result = verify_recovery_pack(pack)
    assert result.status == "FAIL"


def test_restore_duplicate_members_are_refused_without_writes(tmp_path):
    pack = pack_with(tmp_path, ["policy/source-rights.json"] * 2)
    destination = tmp_path / "restore"
    with pytest.raises(ValueError):
        restore_recovery_pack(pack, destination)
    assert not destination.exists()


def test_concurrent_restores_have_only_one_writer(tmp_path):
    pack = pack_with(tmp_path, ["policy/source-rights.json", "policy/sources.yaml", "evidence/index.json"])
    destination = tmp_path / "restore"

    def restore(_):
        try:
            restore_recovery_pack(pack, destination)
            return "restored"
        except (ValueError, FileExistsError):
            return "refused"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(restore, range(2))) == ["refused", "restored"]
    with pytest.raises(ValueError):
        restore_recovery_pack(pack, destination)


@pytest.mark.parametrize("value", [[], None, {"version": True, "kind": PACK_FORMAT, "files": [None]}])
def test_malformed_manifests_fail_closed(tmp_path, value):
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "manifest.json").write_text(json.dumps(value))
    assert verify_recovery_pack(pack).status == "FAIL"


def test_rotated_root_checkpoint_uses_replayed_current_key(tmp_path):
    room, _ = checkpoint(tmp_path)
    room.admin("rotate_root", room.pin.owner_id, replacement="rotated-owner")
    document = build_attestation(room.checkpoint(), custody="operator-offline-file",
                                 authentication="none", captured_at=SYNTHETIC_NOW)
    result = verify_external_checkpoint(
        document=document, document_bytes=None, pin=room.pin, history=room.history(), now=SYNTHETIC_NOW,
        custody="operator-offline-file", expectation=IndependentExpectation(
            document_sha256=digest_attestation(document)))
    assert result.status == "BLOCKED" and result.code == "independent_freshness_unverified"


@pytest.mark.parametrize("delta", [-1, 7200])
def test_clock_changes_cannot_restore_current_trust(tmp_path, delta):
    room, document = checkpoint(tmp_path)
    result = verify_external_checkpoint(
        document=document, document_bytes=None, pin=room.pin, history=room.history(),
        now=SYNTHETIC_NOW + timedelta(seconds=delta), custody="operator-offline-file",
        expectation=IndependentExpectation(document_sha256=digest_attestation(document)))
    assert result.status == "FAIL" and result.code == "checkpoint_stale"


def test_production_bundle_cannot_bypass_external_freshness_via_phase8_anchor(tmp_path):
    from pipeline.authority.ledger import Anchor, append, journal_bytes, load
    from pipeline.authority.protocol import AuthorityError, canonical, envelope_bytes, sign
    from pipeline.authority.service import AuthorityBundle
    from pipeline.recovery.fixtures import synthetic_private

    room, _ = checkpoint(tmp_path)
    pin = room.pin.model_copy(update={"environment": "production", "synthetic": False})
    record = room.journal().events[0].record.payload.model_copy(update={"environment": "production"})
    production_fixture = tmp_path / "production-mode-fixture"
    append(production_fixture, sign(record, synthetic_private("owner")), pin, SYNTHETIC_NOW)
    journal = load(production_fixture)
    signed = envelope_bytes(room.checkpoint(environment="production", head_sha256=journal.head_sha256,
                                          previous_sha256=journal.head_sha256))
    anchor = Anchor(signed, hashlib.sha256(signed).hexdigest(), "synthetic-recovery-challenge")
    bundle = AuthorityBundle(canonical(pin.model_dump(mode="json")), journal_bytes(journal), anchor)
    with pytest.raises(AuthorityError, match="independent custodian"):
        bundle.verify(SYNTHETIC_NOW)


def test_drill_refuses_existing_work_without_touching_it(tmp_path):
    from pipeline.recovery.drills import run_drill

    protected = tmp_path / "existing"
    protected.mkdir()
    sentinel = protected / "keep.txt"
    sentinel.write_bytes(b"protected")
    with pytest.raises(ValueError, match="isolated"):
        run_drill("DR-01", protected)
    assert list(protected.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b"protected"


@pytest.mark.parametrize("kind", ["member", "destination", "export-source", "dossier-write"])
def test_windows_junction_paths_are_refused_before_writes(tmp_path, kind):
    import os
    import subprocess
    from pathlib import Path

    from pipeline.recovery.verify import build_recovery_pack

    if os.name != "nt":
        pytest.skip("Windows junction probe")
    pack = pack_with(tmp_path, ["policy/source-rights.json", "policy/sources.yaml", "evidence/index.json"])
    outside = tmp_path / "protected"
    outside.mkdir()
    destination = tmp_path / "restore"
    link = tmp_path / "junction"
    command = str(Path(os.environ["SystemRoot"]) / "System32/cmd.exe")
    # The executable and arguments are fixed; both targets are pytest temporary paths.
    subprocess.run([command, "/c", "mklink", "/J", str(link), str(outside)], check=True,  # noqa: S603
                   capture_output=True)
    if kind == "destination":
        destination = link / "restore"
    elif kind == "member":
        (pack / "policy/source-rights.json").unlink()
        (pack / "policy/sources.yaml").unlink()
        (pack / "policy").rmdir()
        subprocess.run([command, "/c", "mklink", "/J", str(pack / "policy"), str(outside)],  # noqa: S603
                       check=True, capture_output=True)
    with pytest.raises(ValueError, match="Linked|Reparse"):
        if kind == "export-source":
            build_recovery_pack(link, destination)
        elif kind == "dossier-write":
            from pipeline.source_onboarding import dossier_path

            dossier_path(link, "synthetic_candidate")
        else:
            restore_recovery_pack(pack, destination)
    assert not destination.exists() and not list(outside.iterdir())


@pytest.mark.parametrize("policy", [0, -1, True, 86401, float("inf")])
def test_unbounded_or_ambiguous_freshness_policies_are_refused(tmp_path, policy):
    room, document = checkpoint(tmp_path)
    result = verify_external_checkpoint(
        document=document, document_bytes=None, pin=room.pin, history=room.history(), now=SYNTHETIC_NOW,
        max_age_seconds=policy, custody="operator-offline-file", expectation=IndependentExpectation(
            document_sha256=digest_attestation(document)))
    assert result.status == "FAIL" and not result.current


@pytest.mark.parametrize("body", [b'{"format":1,"format":2}', b'[]', b'{', b'null', b'{}',
                                  b'{' + b' ' * 256001 + b'}'],
                         ids=["duplicate-keys", "array", "truncated", "null", "missing-fields", "oversize"])
def test_ambiguous_malformed_and_oversize_checkpoint_documents_fail(tmp_path, body):
    room = SyntheticNewsroom(tmp_path / "empty")
    result = verify_external_checkpoint(
        document=None, document_bytes=body, pin=room.pin, history=room.history(), now=SYNTHETIC_NOW,
        expectation=IndependentExpectation(document_sha256="0" * 64))
    assert result.status == "FAIL" and result.code == "checkpoint_malformed"


def test_observation_labels_cannot_fabricate_genuine_elapsed_days(monkeypatch):
    from pathlib import Path

    from pipeline.newsroom_readiness import newsroom_readiness

    monkeypatch.setattr("pipeline.readiness.read_observation_receipts", lambda root: [])
    monkeypatch.setattr("pipeline.newsroom_readiness.observation_evidence", lambda receipts, at: {
        "elapsed_window_satisfied": True, "live_observations": 8, "distinct_days": 8,
        "elapsed_days": 7, "missing_days": [], "anomalies": []})
    report = newsroom_readiness(Path(__file__).resolve().parents[2])
    row = next(row for row in report["items"] if row["item"] == "operational_observation_coverage")
    assert row["result"] == "INCONCLUSIVE"


@pytest.mark.parametrize("entries", [[None], [{}], [{"id": "forged", "package": "absent",
                            "mitigation_artifact": "present.txt", "reassessment_due": "not-a-date"}]])
def test_malformed_advisory_records_cannot_turn_green(tmp_path, entries):
    from pipeline.newsroom_readiness import security_advisory_status

    (tmp_path / "config").mkdir()
    (tmp_path / "present.txt").write_text("placeholder")
    (tmp_path / "config/security-advisories.json").write_text(json.dumps({"advisories": entries}))
    assert security_advisory_status(tmp_path, SYNTHETIC_NOW)["result"] in {"FAIL", "INCONCLUSIVE"}


def test_corrupt_candidate_history_is_not_reported_as_empty_backlog(monkeypatch):
    from pathlib import Path

    from pipeline.newsroom_readiness import newsroom_readiness

    def invalid(_):
        raise ValueError("synthetic corrupt candidate ledger")

    monkeypatch.setattr("pipeline.source_onboarding.candidates", invalid)
    report = newsroom_readiness(Path(__file__).resolve().parents[2])
    row = next(row for row in report["items"] if row["item"] == "source_candidate_backlog")
    assert row["result"] == "FAIL"


def test_interrupted_restore_is_not_reused_or_promoted(tmp_path, monkeypatch):
    from pathlib import Path

    pack = pack_with(tmp_path, ["policy/source-rights.json", "policy/sources.yaml", "evidence/index.json"])
    destination = tmp_path / "restore"
    original_open = Path.open

    def interrupted(path, mode="r", *args, **kwargs):
        if path == destination / "evidence/index.json" and mode == "xb":
            raise OSError("synthetic interrupted write")
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", interrupted)
    with pytest.raises(OSError, match="interrupted"):
        restore_recovery_pack(pack, destination)
    before = {path.relative_to(destination): path.read_bytes() for path in destination.rglob("*") if path.is_file()}
    with pytest.raises(ValueError, match="new empty"):
        restore_recovery_pack(pack, destination)
    assert before == {path.relative_to(destination): path.read_bytes() for path in destination.rglob("*") if path.is_file()}
    assert not (destination / "manifest.json").exists()


def test_secret_in_late_export_member_leaves_no_destination(tmp_path):
    from pipeline.recovery.verify import build_recovery_pack

    root = tmp_path / "source"
    (root / "config").mkdir(parents=True)
    (root / "config/source-rights.json").write_bytes(b"{}")
    (root / "config/sources.yaml").write_bytes(b"-----BEGIN ENCRYPTED PRIVATE KEY-----\nSYNTHETIC ONLY")
    destination = tmp_path / "backup"
    with pytest.raises(ValueError, match="private key material"):
        build_recovery_pack(root, destination)
    assert not destination.exists()


def test_manifest_identity_cannot_override_the_packed_trust_pin(tmp_path):
    from pipeline.authority.protocol import canonical

    room, _ = checkpoint(tmp_path)
    pack = pack_with(tmp_path, ["policy/source-rights.json", "policy/sources.yaml", "evidence/index.json"])
    pin_data = canonical(room.pin.model_dump(mode="json"))
    target = pack / "authority/trust-pin.json"
    target.parent.mkdir()
    target.write_bytes(pin_data)
    manifest_path = pack / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest.update(environment="production", ledger_id="forged", owner_id="forged-owner")
    manifest["files"].append({"path": "authority/trust-pin.json", "bytes": len(pin_data),
                              "sha256": hashlib.sha256(pin_data).hexdigest()})
    manifest_path.write_text(json.dumps(manifest))
    result = verify_recovery_pack(pack, expected={"environment": "production", "ledger_id": "forged"})
    assert result.check("expected_identity")["result"] == "FAIL"


@pytest.mark.parametrize("shape", ["duplicate-json", "unlisted-file", "deep-directory", "oversize"])
def test_pack_inventory_is_complete_unambiguous_and_bounded(tmp_path, shape):
    pack = pack_with(tmp_path, ["policy/source-rights.json", "policy/sources.yaml", "evidence/index.json"])
    manifest_path = pack / "manifest.json"
    if shape == "duplicate-json":
        manifest_path.write_bytes(b'{"version":1,"version":1}')
    elif shape == "unlisted-file":
        (pack / "surprise.exe").write_bytes(b"synthetic nonexecutable marker")
    elif shape == "deep-directory":
        (pack / "unlisted/subdir").mkdir(parents=True)
    else:
        manifest = json.loads(manifest_path.read_bytes())
        manifest["files"][0]["bytes"] = 64_000_001
        manifest_path.write_text(json.dumps(manifest))
    destination = tmp_path / "restore"
    assert verify_recovery_pack(pack).status == "FAIL"
    with pytest.raises(ValueError):
        restore_recovery_pack(pack, destination)
    assert not destination.exists()


@pytest.mark.parametrize("shape", ["malformed", "oversize", "inventory-overflow"])
def test_dossier_evidence_cannot_be_silently_omitted(tmp_path, shape):
    from pipeline.source_evidence import load_dossiers

    directory = tmp_path / ".cache/phase6/candidates"
    directory.mkdir(parents=True)
    if shape == "inventory-overflow":
        for index in range(201):
            (directory / f"candidate-{index}.json").write_bytes(b"{}")
    else:
        (directory / "candidate.json").write_bytes(b"{" if shape == "malformed" else b" " * 1_000_001)
    with pytest.raises(ValueError):
        load_dossiers(tmp_path)


@pytest.mark.parametrize("ages", [[45, 0], [-1], [31]])
def test_new_translation_cannot_conceal_stale_or_future_translation(monkeypatch, ages):
    from datetime import UTC, datetime
    from pathlib import Path

    from pipeline.newsroom_readiness import newsroom_readiness

    at = datetime.now(UTC)
    monkeypatch.setattr("pipeline.newsroom_readiness._translation_rows", lambda snapshot: [
        {"story_id": str(index), "generated_at": at - timedelta(days=age), "review_status": "unreviewed"}
        for index, age in enumerate(ages)])
    report = newsroom_readiness(Path(__file__).resolve().parents[2], at)
    row = next(row for row in report["items"] if row["item"] == "translation_staleness")
    assert row["result"] == "FAIL"


@pytest.mark.parametrize("reason", ["stale", "future", "fixture", "uncleared", "missing-date"])
def test_news_classification_alone_cannot_make_coverage_green(monkeypatch, reason):
    from datetime import UTC, datetime
    from pathlib import Path

    from pipeline.newsroom_readiness import _snapshot, newsroom_readiness

    root = Path(__file__).resolve().parents[2]
    at = datetime.now(UTC)
    snapshot = _snapshot(root)
    story = snapshot.stories[0].model_copy(update={"category": "ai", "published_at":
        at - timedelta(days=40) if reason == "stale" else at + timedelta(days=1) if reason == "future" else at})
    snapshot = snapshot.model_copy(update={"stories": [story], "mode": "fixture" if reason == "fixture" else "live"})
    if reason == "missing-date":
        snapshot.sources[story.primary_source_id] = snapshot.sources[story.primary_source_id].model_copy(
            update={"missing_publication_time": True})
    denied = [{"story_id": story.id, "denied_dimensions": ["rights"]}] if reason == "uncleared" else []
    monkeypatch.setattr("pipeline.newsroom_readiness._snapshot", lambda root: snapshot)
    monkeypatch.setattr("pipeline.newsroom_readiness._news_stories", lambda snapshot: [story])
    monkeypatch.setattr("pipeline.publication_gate.evaluate_snapshot", lambda *args, **kwargs: {
        "blocked": denied, "blocked_count": len(denied), "publication_allowed": not denied, "story_count": 1})
    report = newsroom_readiness(root, at)
    row = next(row for row in report["items"] if row["item"] == "current_news_coverage")
    assert row["result"] == "BLOCKED" and row["evidence"]["news_count"] == 0


def test_retired_owner_root_cannot_sign_a_new_checkpoint_after_rotation(tmp_path):
    from pipeline.authority.protocol import sign
    from pipeline.recovery.fixtures import synthetic_key, synthetic_private

    room, _ = checkpoint(tmp_path)
    room.admin("rotate_root", room.pin.owner_id, replacement="rotated-owner")
    payload = room.checkpoint().payload.model_copy(update={"key_id": synthetic_key("owner").key_id})
    document = build_attestation(sign(payload, synthetic_private("owner")), custody="operator-offline-file",
                                 authentication="none", captured_at=SYNTHETIC_NOW)
    result = verify_external_checkpoint(
        document=document, document_bytes=None, pin=room.pin, history=room.history(), now=SYNTHETIC_NOW,
        custody="operator-offline-file", expectation=IndependentExpectation(
            document_sha256=digest_attestation(document)))
    assert result.status == "FAIL" and result.code == "unknown_signer"


@pytest.mark.parametrize("command", ["recovery", "source-evidence"])
def test_operator_file_arguments_are_bounded_before_reading(tmp_path, monkeypatch, command):
    from pathlib import Path

    from pipeline.recovery.__main__ import main as recovery_main
    from pipeline.source_onboarding import main as source_main

    evidence = tmp_path / "oversize.json"
    evidence.write_bytes(b" " * 1_000_001)
    original_read = Path.read_bytes

    def no_unbounded_read(path):
        if path == evidence:
            raise AssertionError("Operator evidence must use a bounded stream")
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", no_unbounded_read)
    if command == "recovery":
        assert recovery_main(["verify", str(tmp_path / "unused-pack"), "--checkpoint", str(evidence)]) == 1
    else:
        monkeypatch.setattr("sys.argv", ["source-onboarding", "evidence", "--file", str(evidence),
                                        "--root", str(tmp_path)])
        assert source_main() == 1
