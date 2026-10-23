"""Temporary synthetic keys exercise production-shaped wires, never real custody."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest

from pipeline.authority.ledger import append, replay, verify_anchor
from pipeline.authority.manual_custodian import (
    ADAPTER,
    CustodianPin,
    ManualCustodyProof,
    close,
    consume,
    initialize,
    issue,
    prepare_response,
    sha,
)
from pipeline.authority.protocol import AuthorityError, canonical, encode64, envelope_bytes, stamp
from pipeline.authority.service import load_authority
from pipeline.operations.custodian import DOMAIN, Receipt, wire
from pipeline.recovery.fixtures import SYNTHETIC_NOW, SyntheticNewsroom, synthetic_key, synthetic_private


class ProductionShapeRoom(SyntheticNewsroom):
    """Public synthetic fixture credentials in isolated temporary files only."""

    def base(self, *args, **kwargs):
        return dict(super().base(*args, **kwargs), environment="production")

    def history(self):
        return replay(self.journal(), self.pin, SYNTHETIC_NOW, mode="production")

    def store(self, record):
        return append(self.root, record, self.pin, SYNTHETIC_NOW, mode="production")


def sign_receipt(payload, **changes):
    payload = payload.model_copy(update=changes)
    return Receipt(algorithm="Ed25519", payload=payload, signature=encode64(
        synthetic_private("custodian").sign(DOMAIN + canonical(payload.model_dump(mode="json")))))


@pytest.fixture
def exchange(tmp_path):
    from pipeline.recovery.fixtures import synthetic_pin

    owner = synthetic_pin().model_copy(update={"synthetic": False, "environment": "production"})
    room = ProductionShapeRoom(tmp_path / "repo", pin=owner)
    room.appoint("editor", "english-editor")
    history = room.history()
    pin = CustodianPin(version=1, adapter=ADAPTER, custodian_id="independent-fixture",
                       key=synthetic_key("custodian"), owner_id=room.pin.owner_id,
                       owner_pin_sha256=sha(canonical(room.pin.model_dump(mode="json"))),
                       ledger_id=room.pin.ledger_id, environment="production")
    client, independent = tmp_path / "client.db", tmp_path / "independent.db"
    policy = tmp_path / "custodian-pin.json"
    policy.write_bytes(canonical(pin.model_dump(mode="json")))
    for path in (client, independent):
        initialize(path, pin, SYNTHETIC_NOW, root=room.root)
    request = issue(client, pin, history, SYNTHETIC_NOW)
    checkpoint = room.checkpoint(challenge=request.nonce)
    payload = prepare_response(independent, pin, canonical(request.model_dump(mode="json")),
                               envelope_bytes(checkpoint), history, SYNTHETIC_NOW)
    receipt = sign_receipt(payload)
    return room, pin, client, independent, policy, request, checkpoint, receipt


def accepted(exchange):
    room, pin, path, _, policy, _, cp, receipt = exchange
    token = consume(path, pin, wire(receipt), envelope_bytes(cp), room.history(), SYNTHETIC_NOW, expected_nonce=cp.payload.challenge)
    return ManualCustodyProof(policy, path, token, room.root), token


def test_live_production_adapter_reuses_owner_verifier_and_closes_lease(exchange):
    room, pin, path, _, _, _, _, _ = exchange
    proof, token = accepted(exchange)
    anchor = proof.anchor()
    result = proof.verify(room.history(), anchor, SYNTHETIC_NOW)
    assert result["status"] == "PASS" and result["independently_trusted"] and result["current"]
    assert not result["publication_allowed"]
    assert verify_anchor(room.history(), anchor, SYNTHETIC_NOW)
    assert verify_anchor(room.history(), anchor, SYNTHETIC_NOW)  # One operation may reverify.
    close(path, pin, token)
    with pytest.raises(AuthorityError, match="lease"):
        proof.anchor()


def test_production_loader_requires_actual_scoped_receipt(exchange, tmp_path, monkeypatch):
    room, _, path, _, policy, _, _, _ = exchange
    owner_pin = tmp_path / "owner.json"
    owner_pin.write_bytes(canonical(room.pin.model_dump(mode="json")))
    monkeypatch.setenv("TECHLINE_AUTHORITY_TRUST_FILE", str(owner_pin))
    proof, token = accepted(exchange)
    monkeypatch.setenv("TECHLINE_CUSTODIAN_PIN_FILE", str(policy))
    monkeypatch.setenv("TECHLINE_CUSTODIAN_STATE_FILE", str(path))
    monkeypatch.setenv("TECHLINE_CUSTODIAN_RUN_TOKEN", token)
    bundle = load_authority(room.root)
    assert bundle.verify(SYNTHETIC_NOW).journal.head_sha256 == room.history().journal.head_sha256
    monkeypatch.setenv("TECHLINE_CUSTODIAN_RUN_TOKEN", "incorrect")
    with pytest.raises(AuthorityError):
        load_authority(room.root)
    monkeypatch.delenv("TECHLINE_CUSTODIAN_RUN_TOKEN")
    with pytest.raises(AuthorityError):
        load_authority(room.root).verify(SYNTHETIC_NOW)
    assert proof.anchor()


@pytest.mark.parametrize("field,value", [
    ("key_id", "f" * 64), ("custodian_id", "forged"), ("ledger_id", "other"),
    ("environment", "synthetic"), ("request_sha256", "f" * 64),
    ("checkpoint_sha256", "f" * 64), ("head_sha256", "f" * 64),
    ("event_count", 0), ("registry_revision", 0),
    ("issued_at", stamp(SYNTHETIC_NOW + timedelta(seconds=1))),
    ("expires_at", stamp(SYNTHETIC_NOW + timedelta(seconds=121))),
    ("expires_at", stamp(SYNTHETIC_NOW)),
])
def test_signed_contradictory_receipts_are_refused_and_consumed(exchange, field, value):
    room, pin, path, _, _, _, checkpoint, receipt = exchange
    changed = sign_receipt(receipt.payload, **{field: value})
    with pytest.raises((AuthorityError, ValueError)):
        consume(path, pin, wire(changed), envelope_bytes(checkpoint), room.history(), SYNTHETIC_NOW, expected_nonce=checkpoint.payload.challenge)
    with pytest.raises(AuthorityError, match="recovery"):
        issue(path, pin, room.history(), SYNTHETIC_NOW)


def test_forged_signature(exchange):
    room, pin, path, _, _, _, checkpoint, receipt = exchange
    receipt = receipt.model_copy(update={"signature": encode64(b"x" * 64)})
    with pytest.raises(AuthorityError) as error:
        consume(path, pin, wire(receipt), envelope_bytes(checkpoint), room.history(), SYNTHETIC_NOW, expected_nonce=checkpoint.payload.challenge)
    assert error.value.code == "custodian_signature"


@pytest.mark.parametrize("receipt", [None, b"{}", b"x" * 16_001, b'{"a":1,"a":1}'])
def test_unavailable_interrupted_malformed_response_fails_closed(exchange, receipt):
    room, pin, path, _, _, _, checkpoint, _ = exchange
    with pytest.raises((ValueError, TypeError)):
        consume(path, pin, receipt, envelope_bytes(checkpoint), room.history(), SYNTHETIC_NOW, expected_nonce=checkpoint.payload.challenge)
    with pytest.raises(AuthorityError):
        issue(path, pin, room.history(), SYNTHETIC_NOW)


def test_old_receipt_cannot_answer_replacement_nonce(exchange):
    room, pin, path, _, _, _, cp, receipt = exchange
    request = issue(path, pin, room.history(), SYNTHETIC_NOW)
    with pytest.raises(AuthorityError) as error:
        consume(path, pin, wire(receipt), envelope_bytes(cp), room.history(), SYNTHETIC_NOW,
                expected_nonce=request.nonce)
    assert error.value.code == "request_replay"


def test_atomic_duplicate_concurrent_responses(exchange):
    room, pin, path, _, _, _, cp, receipt = exchange

    def attempt():
        try:
            consume(path, pin, wire(receipt), envelope_bytes(cp), room.history(), SYNTHETIC_NOW, expected_nonce=cp.payload.challenge)
            return "PASS"
        except (ValueError, TypeError):
            return "REFUSED"

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(lambda _: attempt(), range(2))) == ["PASS", "REFUSED"]
    # Conflicting verification freezes even the first lease; there is no race
    # where both callers gain authority after the duplicate has been observed.
    with pytest.raises(AuthorityError):
        issue(path, pin, room.history(), SYNTHETIC_NOW)


@pytest.mark.parametrize("seconds", [-1, 120, 3600])
def test_clock_manipulation_refuses_acceptance(exchange, seconds):
    room, pin, path, _, _, _, cp, receipt = exchange
    with pytest.raises(AuthorityError):
        consume(path, pin, wire(receipt), envelope_bytes(cp), room.history(),
                SYNTHETIC_NOW + timedelta(seconds=seconds), expected_nonce=cp.payload.challenge)


def test_emergency_suspension(exchange):
    room, pin, path, _, _, _, cp, receipt = exchange
    with pytest.raises(AuthorityError) as error:
        consume(path, pin, wire(receipt), envelope_bytes(cp), room.history(), SYNTHETIC_NOW,
                emergency_stopped=True, expected_nonce=cp.payload.challenge)
    assert error.value.code == "emergency_hold"


def test_checkpoint_chain_and_historical_receipt_survive_operation_close(exchange):
    room, pin, client, independent, _, _, cp, receipt = exchange
    # Independently retain the first accepted checkpoint on both devices.
    remote_token = consume(independent, pin, wire(receipt), envelope_bytes(cp), room.history(), SYNTHETIC_NOW, expected_nonce=cp.payload.challenge)
    close(independent, pin, remote_token)
    proof, token = accepted(exchange)
    historical_anchor = proof.anchor()
    close(client, pin, token)
    historical = proof.verify(room.history(), historical_anchor, SYNTHETIC_NOW, historical=True)
    assert historical["status"] == "PASS"
    assert historical["trust_level"] == "INDEPENDENTLY_AUTHENTICATED" and not historical["current"]
    request = issue(client, pin, room.history(), SYNTHETIC_NOW + timedelta(seconds=1))
    assert request.checkpoint_revision == 2
    assert request.previous_checkpoint_sha256 == sha(envelope_bytes(cp))
    # A restored empty client cannot move an independent custodian backwards.
    restored = client.parent / "restored.db"
    initialize(restored, pin, SYNTHETIC_NOW, root=room.root)
    old_request = issue(restored, pin, room.history(), SYNTHETIC_NOW)
    old_cp = room.checkpoint(challenge=old_request.nonce)
    with pytest.raises(AuthorityError) as error:
        prepare_response(independent, pin, canonical(old_request.model_dump(mode="json")),
                         envelope_bytes(old_cp), room.history(), SYNTHETIC_NOW)
    assert error.value.code == "custodian_continuity"


def test_journal_rollback_and_conflicting_head_after_accepted_receipt(exchange):
    from dataclasses import replace

    from pipeline.authority.ledger import empty

    room, pin, path, _, _, _, _, _ = exchange
    proof, token = accepted(exchange)
    close(path, pin, token)
    old = replace(room.history(), journal=empty())
    with pytest.raises(AuthorityError):
        issue(path, pin, old, SYNTHETIC_NOW)
    # Existing accepted anchor also detects a journal mismatch before it can
    # assert currency, including when called outside the consolidated console.
    with pytest.raises(AuthorityError):
        proof.verify(old, proof.anchor(), SYNTHETIC_NOW)


def test_custodian_rotation_requires_new_independent_ceremony(exchange):
    room, pin, path, _, policy, _, _, _ = exchange
    changed = pin.model_copy(update={"key": synthetic_key("replacement")})
    policy.write_bytes(canonical(changed.model_dump(mode="json")))
    with pytest.raises(AuthorityError) as error:
        issue(path, changed, room.history(), SYNTHETIC_NOW)
    assert error.value.code == "custodian_state_incomplete"


def test_missing_corrupted_or_truncated_local_state_never_bootstraps(exchange):
    room, pin, path, _, _, _, _, _ = exchange
    path.unlink()
    with pytest.raises(AuthorityError):
        issue(path, pin, room.history(), SYNTHETIC_NOW)
    path.write_bytes(b"incomplete")
    with pytest.raises(AuthorityError):
        issue(path, pin, room.history(), SYNTHETIC_NOW)


def test_initialize_never_overwrites_existing_custody(exchange):
    room, pin, path, _, _, _, _, _ = exchange
    with pytest.raises(FileExistsError):
        initialize(path, pin, SYNTHETIC_NOW, root=room.root)


def test_synthetic_protocol_is_never_production_evidence(exchange):
    room, pin, path, _, _, _, cp, receipt = exchange
    changed = pin.model_copy(update={"environment": "synthetic"})
    with pytest.raises(AuthorityError):
        consume(path, changed, wire(receipt), envelope_bytes(cp), room.history(), SYNTHETIC_NOW, expected_nonce=cp.payload.challenge)


def test_clock_floor_advances_during_one_operation(exchange):
    room, _, _, _, _, _, _, _ = exchange
    proof, _ = accepted(exchange)
    anchor = proof.anchor()
    proof.verify(room.history(), anchor, SYNTHETIC_NOW + timedelta(seconds=10))
    with pytest.raises(AuthorityError) as error:
        proof.verify(room.history(), anchor, SYNTHETIC_NOW + timedelta(seconds=9))
    assert error.value.code == "clock_regression"


def test_canonical_checkpoint_export_with_terminal_newline_is_supported(exchange):
    room, pin, path, _, _, _, cp, receipt = exchange
    token = consume(path, pin, wire(receipt), envelope_bytes(cp) + b"\n", room.history(), SYNTHETIC_NOW, expected_nonce=cp.payload.challenge)
    assert token


def test_new_emergency_stop_is_seen_after_anchor_was_loaded(exchange):
    from pipeline.authority.ledger import emergency_hold

    room, _, _, _, _, _, _, _ = exchange
    proof, _ = accepted(exchange)
    anchor = proof.anchor()
    emergency_hold(room.root, "synthetic emergency after loading", SYNTHETIC_NOW)
    with pytest.raises(AuthorityError) as error:
        verify_anchor(room.history(), anchor, SYNTHETIC_NOW)
    assert error.value.code == "emergency_hold"


def test_existing_owner_root_rotation_is_verified_without_custodian_repinning(exchange):
    room, pin, client, independent, _, _, cp, receipt = exchange
    remote_token = consume(independent, pin, wire(receipt), envelope_bytes(cp), room.history(), SYNTHETIC_NOW, expected_nonce=cp.payload.challenge)
    close(independent, pin, remote_token)
    _, token = accepted(exchange)
    close(client, pin, token)
    room.admin("rotate_root", room.pin.owner_id, replacement="next-owner")
    request = issue(client, pin, room.history(), SYNTHETIC_NOW)
    assert request.owner_key_id == synthetic_key("next-owner").key_id
    cp = room.checkpoint(challenge=request.nonce)
    response = sign_receipt(prepare_response(independent, pin, canonical(request.model_dump(mode="json")),
                                            envelope_bytes(cp), room.history(), SYNTHETIC_NOW))
    assert consume(client, pin, wire(response), envelope_bytes(cp), room.history(), SYNTHETIC_NOW, expected_nonce=cp.payload.challenge)


@pytest.mark.parametrize("arguments", [
    ["--unknown", "ghp_SYNTHETIC_DO_NOT_REPRODUCE"],
    ["--pin", "ignored", "--state", "ignored", "ghp_SYNTHETIC_DO_NOT_REPRODUCE"],
])
def test_cli_argument_refusal_never_echoes_pasted_credentials(arguments, capsys):
    from pipeline.checkpoint_exchange import main

    with pytest.raises(SystemExit) as error:
        main(arguments)
    assert error.value.code == 2
    output = capsys.readouterr()
    assert "ghp_SYNTHETIC_DO_NOT_REPRODUCE" not in output.out + output.err
    assert "argument_error" in output.err


def test_real_shaped_research_append_historical_replay_and_next_live_checkpoint(exchange, monkeypatch):
    """Expired old receipts remain historical evidence; next action needs fresh custody."""
    from pipeline.authority.protocol import RESEARCH_STAGES
    from pipeline.research_approval import bind_research, validate_decision
    from pipeline.research_demo import SyntheticResearchRoom, content

    class ProductionResearchRoom(ProductionShapeRoom, SyntheticResearchRoom):
        pass

    old_room, pin, path, independent, policy, _, _, _ = exchange
    # Fresh isolated fixture with grants for research and no real publication.
    room = ProductionResearchRoom(old_room.root.parent / "research", pin=old_room.pin).team()
    fresh = path.parent / "research-client.db"
    remote = independent.parent / "research-independent.db"
    for target in (fresh, remote):
        initialize(target, pin, SYNTHETIC_NOW, root=room.root)
    monkeypatch.setenv("TECHLINE_CUSTODIAN_PIN_FILE", str(policy))
    monkeypatch.setenv("TECHLINE_CUSTODIAN_STATE_FILE", str(fresh))
    request = issue(fresh, pin, room.history(), SYNTHETIC_NOW)
    cp = room.checkpoint(challenge=request.nonce)
    response = sign_receipt(prepare_response(remote, pin, canonical(request.model_dump(mode="json")),
                                            envelope_bytes(cp), room.history(), SYNTHETIC_NOW))
    token = consume(fresh, pin, wire(response), envelope_bytes(cp), room.history(), SYNTHETIC_NOW, expected_nonce=cp.payload.challenge)
    monkeypatch.setenv("TECHLINE_CUSTODIAN_RUN_TOKEN", token)
    story, sources, rights = content()
    bound = bind_research(story, sources[story.primary_source_id], rights, sources)
    decision = room.prepared(bound, RESEARCH_STAGES[0], "rights", checkpoint=cp)
    assert validate_decision(room.history(), decision, story, sources, rights,
                             SYNTHETIC_NOW)["signature_and_scope_valid"]
    room.store(decision)
    close(fresh, pin, token)
    monkeypatch.delenv("TECHLINE_CUSTODIAN_RUN_TOKEN")
    # Replay checks the archived receipt at the decision's issuance, after the
    # receipt itself is no longer a current authorization.
    later = SYNTHETIC_NOW + timedelta(minutes=10)
    history = replay(room.journal(), room.pin, later)
    assert history.active(bound, RESEARCH_STAGES[0], later)
    next_request = issue(fresh, pin, history, later)
    assert next_request.checkpoint_revision == 2
    assert next_request.previous_event_count == len(room.journal().events) - 1
    # The previous receipt cannot authorize the new post-decision journal.
    with pytest.raises(AuthorityError):
        consume(fresh, pin, wire(response), envelope_bytes(cp), history, later, expected_nonce=cp.payload.challenge)


def test_restored_pending_and_old_valid_receipt_cannot_choose_live_operation_nonce(exchange):
    from pipeline.authority.ledger import JOURNAL, journal_bytes
    from pipeline.filesystem import atomic_bytes, confined_file

    room, pin, client, independent, _, _, cp1, receipt1 = exchange
    old_journal = room.journal()
    pending_backup = client.read_bytes()
    remote_token = consume(independent, pin, wire(receipt1), envelope_bytes(cp1), room.history(),
                           SYNTHETIC_NOW, expected_nonce=cp1.payload.challenge)
    close(independent, pin, remote_token)
    _, token = accepted(exchange)
    close(client, pin, token)
    room.admin("suspend_reviewer", "editor")
    at = SYNTHETIC_NOW + timedelta(seconds=1)
    request2 = issue(client, pin, room.history(), at)
    cp2 = room.checkpoint(challenge=request2.nonce, issued_at=stamp(at))
    receipt2 = sign_receipt(prepare_response(independent, pin, canonical(request2.model_dump(mode="json")),
                                            envelope_bytes(cp2), room.history(), at))
    for state_path in (independent, client):
        token = consume(state_path, pin, wire(receipt2), envelope_bytes(cp2), room.history(), at,
                        expected_nonce=request2.nonce)
        close(state_path, pin, token)
    # Restore the earlier valid client pending nonce and earlier valid journal.
    client.write_bytes(pending_backup)
    atomic_bytes(confined_file(room.root, JOURNAL), journal_bytes(old_journal))
    at += timedelta(seconds=1)
    old_history = replay(old_journal, room.pin, at)
    live_request = issue(client, pin, old_history, at)
    # Even restoring the pending state a second time cannot replace the fresh
    # nonce held in the current run's memory. UTC remains correct throughout.
    client.write_bytes(pending_backup)
    with pytest.raises(AuthorityError) as error:
        consume(client, pin, wire(receipt1), envelope_bytes(cp1), old_history, at,
                expected_nonce=live_request.nonce)
    assert error.value.code == "custodian_live_nonce"


@pytest.mark.parametrize("restore_attack", [False, True])
def test_cli_run_fresh_nonce_refuses_restored_pending_replay(exchange, tmp_path, monkeypatch, capsys, restore_attack):
    from argparse import Namespace
    from types import SimpleNamespace

    import pipeline.checkpoint_exchange as cli
    from pipeline.authority.manual_custodian import CurrentChallenge

    room, pin, client, independent, policy, old_request, cp, receipt = exchange
    pending_backup = client.read_bytes()
    token = consume(independent, pin, wire(receipt), envelope_bytes(cp), room.history(), SYNTHETIC_NOW,
                    expected_nonce=old_request.nonce)
    close(independent, pin, token)
    _, token = accepted(exchange)
    close(client, pin, token)
    owner = tmp_path / "owner.json"
    owner.write_bytes(canonical(room.pin.model_dump(mode="json")))
    monkeypatch.setenv("TECHLINE_AUTHORITY_TRUST_FILE", str(owner))
    monkeypatch.setenv("TECHLINE_CUSTODIAN_PIN_FILE", str(policy))
    monkeypatch.setenv("TECHLINE_CUSTODIAN_STATE_FILE", str(client))
    at = SYNTHETIC_NOW + timedelta(seconds=2)
    challenge_file, checkpoint_file, receipt_file = (tmp_path / name for name in
                                                    ("live-challenge.json", "live-checkpoint.json", "live-receipt.json"))

    class FixedClock:
        @staticmethod
        def now(_timezone):
            return at

    monkeypatch.setattr(cli, "datetime", FixedClock)

    def independent_answer(_seconds):
        request_bytes = challenge_file.read_bytes()
        fresh = CurrentChallenge.model_validate_json(request_bytes)
        assert fresh.nonce != old_request.nonce
        if restore_attack:
            client.write_bytes(pending_backup)
            checkpoint_file.write_bytes(envelope_bytes(cp))
            receipt_file.write_bytes(wire(receipt))
            return
        owner_checkpoint = room.checkpoint(challenge=fresh.nonce, issued_at=stamp(at))
        payload = prepare_response(independent, pin, request_bytes, envelope_bytes(owner_checkpoint),
                                   room.history(), at)
        raw = wire(sign_receipt(payload))
        remote_token = consume(independent, pin, raw, envelope_bytes(owner_checkpoint), room.history(), at,
                               expected_nonce=fresh.nonce)
        close(independent, pin, remote_token)
        checkpoint_file.write_bytes(envelope_bytes(owner_checkpoint))
        receipt_file.write_bytes(raw)

    monkeypatch.setattr(cli.time, "sleep", independent_answer)
    observed_tokens = []

    def local_command(command, *, cwd, env, check):
        assert command == ["synthetic-local-operation"] and cwd == room.root and not check
        observed_tokens.append(env["TECHLINE_CUSTODIAN_RUN_TOKEN"])
        with monkeypatch.context() as child:
            child.setenv("TECHLINE_CUSTODIAN_RUN_TOKEN", observed_tokens[-1])
            assert load_authority(room.root).verify(at)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(cli.subprocess, "run", local_command)
    arguments = Namespace(root=room.root, pin=policy, state=client, action="run",
                          checkpoint=checkpoint_file, receipt=receipt_file, challenge_output=challenge_file,
                          command=["--", "synthetic-local-operation"])
    if restore_attack:
        with pytest.raises(AuthorityError) as error:
            cli.execute(arguments, at)
        assert error.value.code == "custodian_live_nonce" and not observed_tokens
        return
    result = cli.execute(arguments, at)
    assert result["status"] == "PASS"
    assert len(observed_tokens) == 1 and observed_tokens[0] not in capsys.readouterr().out
    with pytest.raises(AuthorityError):
        ManualCustodyProof(policy, client, observed_tokens[0], room.root).anchor()
