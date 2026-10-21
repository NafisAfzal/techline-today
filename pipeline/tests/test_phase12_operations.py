import json
from datetime import timedelta

import pytest

from pipeline.authority.protocol import AuthorityError, canonical, encode64, stamp
from pipeline.operations.ceremony import (
    CONFIRMATIONS,
    CeremonyProposal,
    appointment_packet,
    preflight,
    template,
)
from pipeline.operations.custodian import (
    DOMAIN,
    MockCustodian,
    MockVerificationSession,
    read_receipt,
    wire,
)
from pipeline.operations.rehearsal import rehearse
from pipeline.recovery.fixtures import SYNTHETIC_NOW, SyntheticNewsroom, synthetic_private


@pytest.fixture
def channel(tmp_path):
    room = SyntheticNewsroom(tmp_path / "synthetic")
    room.appoint("editor", "english-editor")
    cp = room.checkpoint()
    mock = MockCustodian(cp)
    session = MockVerificationSession(mock.key)
    request = session.issue(room.history(), SYNTHETIC_NOW)
    receipt = mock.answer(request, SYNTHETIC_NOW)
    return room, cp, mock, session, receipt


def signed_change(receipt, **changes):
    payload = receipt.payload.model_copy(update=changes)
    return receipt.model_copy(update={"payload": payload, "signature": encode64(
        synthetic_private("custodian").sign(DOMAIN + canonical(payload.model_dump(mode="json"))))})


def test_mock_round_trip_never_promotes_production(channel):
    room, cp, _, session, receipt = channel
    result = session.verify(wire(receipt), cp, room.history(), SYNTHETIC_NOW)
    assert result["status"] == "PASS"
    assert result["synthetic_only"]
    assert not result["publication_allowed"] and not result["independently_trusted"] and not result["current"]
    assert session.verify(wire(receipt), cp, room.history(), SYNTHETIC_NOW)["status"] == "BLOCKED"


@pytest.mark.parametrize("field,value", [
    ("custodian_id", "other"), ("ledger_id", "other"), ("environment", "production"),
    ("key_id", "f" * 64), ("request_sha256", "f" * 64), ("checkpoint_sha256", "f" * 64),
    ("head_sha256", "f" * 64), ("event_count", 1), ("registry_revision", 1),
    ("issued_at", stamp(SYNTHETIC_NOW + timedelta(seconds=1))),
    ("expires_at", stamp(SYNTHETIC_NOW + timedelta(seconds=121))),
    ("expires_at", stamp(SYNTHETIC_NOW)),
])
def test_even_valid_custodian_signature_cannot_override_binding(channel, field, value):
    room, cp, _, session, receipt = channel
    changed = signed_change(receipt, **{field: value})
    result = session.verify(wire(changed), cp, room.history(), SYNTHETIC_NOW)
    assert result["status"] != "PASS"
    with pytest.raises(AuthorityError) as stopped:
        session.issue(room.history(), SYNTHETIC_NOW)
    assert stopped.value.code == "session_frozen"


@pytest.mark.parametrize("payload", [b"{}", b"[]", b"x" * 16_001, b'{"version":1,"version":1}', b"\xef\xbb\xbf{}"])
def test_bounded_malformed_receipts_fail_closed(channel, payload):
    room, cp, _, session, _ = channel
    assert session.verify(payload, cp, room.history(), SYNTHETIC_NOW)["status"] != "PASS"


def test_noncanonical_and_wrong_signature_rejected(channel):
    room, cp, _, session, receipt = channel
    with pytest.raises(ValueError):
        read_receipt(json.dumps(receipt.model_dump(mode="json"), indent=2).encode())
    forged = receipt.model_copy(update={"signature": encode64(b"x" * 64)})
    assert session.verify(wire(forged), cp, room.history(), SYNTHETIC_NOW)["code"] == "custodian_signature"


def test_single_use_replacement_and_lost_response(channel):
    room, cp, _, session, receipt = channel
    session.issue(room.history(), SYNTHETIC_NOW)
    assert session.verify(wire(receipt), cp, room.history(), SYNTHETIC_NOW)["code"] == "request_replay"
    fresh = MockVerificationSession(channel[2].key)
    fresh.issue(room.history(), SYNTHETIC_NOW)
    assert fresh.verify(None, cp, room.history(), SYNTHETIC_NOW)["code"] == "missing_response"


@pytest.mark.parametrize("seconds", [-1, 120, 3600])
def test_clock_skew_expiry_and_emergency_freeze(channel, seconds):
    room, cp, _, session, receipt = channel
    assert session.verify(wire(receipt), cp, room.history(),
                          SYNTHETIC_NOW + timedelta(seconds=seconds))["status"] != "PASS"


def test_freeze_and_key_rotation_are_not_automatic_trust(channel):
    room, cp, _, session, receipt = channel
    assert session.verify(wire(receipt), cp, room.history(), SYNTHETIC_NOW,
                          emergency_stopped=True)["code"] == "emergency_hold"
    changed = MockCustodian(cp, name="rotated-custodian")
    session = MockVerificationSession(channel[2].key)
    request = session.issue(room.history(), SYNTHETIC_NOW)
    assert session.verify(wire(changed.answer(request, SYNTHETIC_NOW)), cp,
                          room.history(), SYNTHETIC_NOW)["code"] == "receipt_context"


def test_monotonic_clock_and_registry_floor(channel):
    room, _, _, session, _ = channel
    old_history = room.history()
    room.admin("revoke_reviewer", "editor")
    cp = room.checkpoint()
    custodian = MockCustodian(cp)
    request = session.issue(room.history(), SYNTHETIC_NOW)
    assert session.verify(wire(custodian.answer(request, SYNTHETIC_NOW)), cp,
                          room.history(), SYNTHETIC_NOW)["status"] == "PASS"
    with pytest.raises(AuthorityError, match="regressed"):
        session.issue(old_history, SYNTHETIC_NOW)
    fresh = MockVerificationSession(custodian.key)
    fresh.issue(room.history(), SYNTHETIC_NOW)
    with pytest.raises(AuthorityError, match="clock regressed"):
        fresh.issue(room.history(), SYNTHETIC_NOW - timedelta(seconds=1))


def test_ceremony_is_read_only_and_requires_human_declarations(tmp_path):
    assert preflight(tmp_path, now=SYNTHETIC_NOW)["status"] == "BLOCKED"
    proposal = template()
    proposal["confirmations"] = list(CONFIRMATIONS)
    result = preflight(tmp_path, proposal, expected_environment="proposed-production", now=SYNTHETIC_NOW)
    assert result["status"] == "READY_FOR_HUMAN_CEREMONY"
    assert not result["production_credentials_created"] and not result["publication_allowed"]
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("confirmation", CONFIRMATIONS)
def test_each_ceremony_condition_required(tmp_path, confirmation):
    proposal = template()
    proposal["confirmations"] = [c for c in CONFIRMATIONS if c != confirmation]
    assert preflight(tmp_path, proposal, expected_environment="proposed-production")["status"] == "BLOCKED"


def test_unsupported_hardware_fake_key_or_existing_state(tmp_path):
    proposal = template()
    proposal["confirmations"] = list(CONFIRMATIONS)
    proposal["custody_model"] = "hardware-token"
    assert preflight(tmp_path, proposal, expected_environment="proposed-production")["status"] == "INCONCLUSIVE"
    with pytest.raises(ValueError):
        CeremonyProposal.model_validate({**proposal, "private_key": "forbidden"})
    state = tmp_path / ".cache/authority/journal.json"
    state.parent.mkdir(parents=True)
    state.write_bytes(b"not a journal")
    assert preflight(tmp_path, proposal, expected_environment="proposed-production")["status"] == "BLOCKED"
    assert state.read_bytes() == b"not a journal"


def test_appointment_packet_is_not_authority():
    native = appointment_packet("native-bn")
    assert native["language_scope"] == ["bn"] and not native["appointment_valid"]
    assert native["identity"] is None and native["public_key_fingerprint"] is None
    assert "RIGHTS_APPROVED" not in native["permitted_decisions"]
    assert "NATIVE_REVIEW_COMPLETE" not in appointment_packet("source-rights")["permitted_decisions"]
    with pytest.raises(ValueError):
        appointment_packet("owner-admin")


def test_integrated_synthetic_role_and_language_rehearsal(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = rehearse()
    assert result["status"] == "PASS", result["checks"]
    assert len(result["checks"]) >= 20
    assert not result["publication_allowed"] and not result["real_reviewers_appointed"]
    assert not list(tmp_path.iterdir())
