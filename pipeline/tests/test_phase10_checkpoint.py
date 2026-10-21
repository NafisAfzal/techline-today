"""External checkpoint verification: trust levels, defect detection and fail-closed behaviour.

Every identity here is synthetic. No test provisions production authority,
contacts a network or writes outside an isolated temporary directory.
"""

import hashlib
import json
from datetime import timedelta

import pytest

from pipeline.authority.checkpoint import (
    BLOCKED,
    FAIL,
    INCONCLUSIVE,
    IndependentExpectation,
    MissingCheckpointStore,
    OperatorFileCheckpointStore,
    ProtectedHistoryCheckpointStore,
    build_attestation,
    conflicting_checkpoints,
    digest_attestation,
    read_checkpoint_document,
    verify_checkpoint_set,
    verify_external_checkpoint,
)
from pipeline.authority.ledger import emergency_hold
from pipeline.authority.protocol import AuthorityError, canonical
from pipeline.recovery.fixtures import SYNTHETIC_NOW, SyntheticNewsroom, synthetic_pin


def room(tmp_path):
    newsroom = SyntheticNewsroom(tmp_path / "newsroom")
    (tmp_path / "newsroom").mkdir(parents=True, exist_ok=True)
    newsroom.team()
    newsroom.publish()
    return newsroom


def document_for(newsroom, **kwargs):
    envelope = newsroom.checkpoint(**kwargs)
    document = build_attestation(envelope, custody="operator-offline-file",
                                 authentication="operator-attested", captured_at=SYNTHETIC_NOW)
    return document


def verify(newsroom, document, *, digest=None, challenge=None, now=SYNTHETIC_NOW, **kwargs):
    expectation = IndependentExpectation(
        document_sha256=digest if digest is not None else digest_attestation(document),
        challenge=challenge, source="synthetic-test")
    kwargs.setdefault("custody", "operator-offline-file")
    return verify_external_checkpoint(document=document, document_bytes=None, expectation=expectation,
                                     pin=newsroom.pin, history=newsroom.history(), now=now, **kwargs)


def test_signed_local_agreement_does_not_authenticate_independent_current_state(tmp_path):
    newsroom = room(tmp_path)
    document = document_for(newsroom)
    result = verify(newsroom, document)
    assert result.status == BLOCKED
    assert result.code == "independent_freshness_unverified"
    assert result.trust_level == "EXTERNAL_STORED"
    assert not result.independently_trusted and not result.current
    assert result.publication_allowed is False


def test_a_stored_document_without_independent_evidence_is_blocked_not_passed(tmp_path):
    newsroom = room(tmp_path)
    document = document_for(newsroom)
    result = verify_external_checkpoint(
        document=document, document_bytes=None,
        expectation=IndependentExpectation(source="none"), pin=newsroom.pin,
        history=newsroom.history(), now=SYNTHETIC_NOW)
    assert result.status == BLOCKED
    assert result.code == "independent_evidence_missing"
    assert result.trust_level == "LOCAL_SIGNED"
    assert result.current is False


def test_a_local_custody_document_never_reaches_the_currently_trusted_level(tmp_path):
    newsroom = room(tmp_path)
    envelope = newsroom.checkpoint()
    document = build_attestation(envelope, custody="local-state-directory", authentication="none",
                                 captured_at=SYNTHETIC_NOW)
    result = verify(newsroom, document)
    assert result.status in {BLOCKED, FAIL}
    assert result.trust_level == "EXTERNAL_STORED"
    assert result.trust_level != "CURRENTLY_TRUSTED"


def test_a_wrong_independent_digest_is_refused(tmp_path):
    newsroom = room(tmp_path)
    document = document_for(newsroom)
    result = verify(newsroom, document, digest="f" * 64)
    assert result.status == FAIL
    assert result.code == "expected_digest_mismatch"


def test_a_ledger_from_another_newsroom_is_refused(tmp_path):
    newsroom = room(tmp_path)
    other = SyntheticNewsroom(tmp_path / "other", pin=synthetic_pin(ledger_id="another-newsroom"))
    (tmp_path / "other").mkdir(parents=True, exist_ok=True)
    other.admin("revoke_source", "synthetic-source")
    document = build_attestation(other.checkpoint(), custody="operator-offline-file",
                                 authentication="operator-attested", captured_at=SYNTHETIC_NOW)
    result = verify(newsroom, document)
    assert result.status == FAIL
    assert result.code == "unknown_ledger"


def test_a_rolled_back_journal_is_detected_as_a_revision_regression(tmp_path):
    from pipeline.authority.ledger import Journal

    newsroom = room(tmp_path)
    document = document_for(newsroom)
    full = newsroom.history().journal
    kept = full.events[:-1]
    rolled_back = Journal(version=1, events=kept, head_sha256=kept[-1].event_sha256)
    from pipeline.authority.ledger import replay

    history = replay(rolled_back, newsroom.pin, SYNTHETIC_NOW, mode="synthetic")
    result = verify_external_checkpoint(
        document=document, document_bytes=None,
        expectation=IndependentExpectation(document_sha256=digest_attestation(document)),
        pin=newsroom.pin, history=history, now=SYNTHETIC_NOW)
    assert result.status == FAIL
    assert result.code == "journal_revision_regression"


def test_a_registry_revision_mismatch_is_named(tmp_path):
    newsroom = room(tmp_path)
    document = document_for(newsroom)
    newsroom.admin("revoke_source", "news-wire")
    result = verify(newsroom, document)
    assert result.status == FAIL
    assert result.code == "registry_mismatch"


def test_an_expired_checkpoint_is_stale(tmp_path):
    newsroom = room(tmp_path)
    document = document_for(newsroom)
    result = verify(newsroom, document, now=SYNTHETIC_NOW + timedelta(hours=3))
    assert result.status == FAIL
    assert result.code == "checkpoint_stale"


def test_a_checkpoint_older_than_the_operator_freshness_policy_is_stale(tmp_path):
    newsroom = room(tmp_path)
    document = document_for(newsroom)
    result = verify(newsroom, document, now=SYNTHETIC_NOW + timedelta(minutes=30), max_age_seconds=60)
    assert result.status == FAIL
    assert result.code == "checkpoint_stale"


def test_a_checkpoint_for_another_challenge_is_refused(tmp_path):
    newsroom = room(tmp_path)
    document = document_for(newsroom, challenge="synthetic-recovery-challenge")
    result = verify(newsroom, document, challenge="a-different-publication-challenge")
    assert result.status == FAIL
    assert result.code == "challenge_mismatch"


def test_a_checkpoint_signed_by_an_unknown_signer_is_refused(tmp_path):
    newsroom = room(tmp_path)
    stranger = SyntheticNewsroom(tmp_path / "stranger",
                                 pin=synthetic_pin(owner_id="another-owner"))
    (tmp_path / "stranger").mkdir(parents=True, exist_ok=True)
    stranger.admin("revoke_source", "synthetic-source")
    document = build_attestation(stranger.checkpoint(), custody="operator-offline-file",
                                 authentication="operator-attested", captured_at=SYNTHETIC_NOW)
    result = verify(newsroom, document)
    assert result.status == FAIL
    assert result.code in {"unknown_signer", "invalid_signature"}


def test_a_tampered_signature_is_refused(tmp_path):
    newsroom = room(tmp_path)
    document = document_for(newsroom)
    envelope = document.checkpoint_envelope.model_copy(
        update={"signature": "A" * 86})
    broken = document.model_copy(update={"checkpoint_envelope": envelope})
    result = verify(newsroom, broken)
    assert result.status == FAIL
    assert result.code in {"invalid_signature", "checkpoint_malformed"}


def test_a_cross_environment_checkpoint_is_refused(tmp_path):
    newsroom = room(tmp_path)
    document = document_for(newsroom)
    foreign = document.model_copy(update={"environment": "production"})
    result = verify(newsroom, foreign, digest=digest_attestation(foreign))
    assert result.status == FAIL
    assert result.code == "cross_environment_replay"


def test_an_unsupported_protocol_version_is_refused(tmp_path):
    newsroom = room(tmp_path)
    document = document_for(newsroom)
    broken = document.model_dump(mode="json")
    broken["checkpoint_envelope"]["payload"]["protocol"] = "techline.future/v9"
    result = verify_external_checkpoint(
        document=None, document_bytes=canonical(broken), pin=newsroom.pin,
        history=newsroom.history(), now=SYNTHETIC_NOW, expectation=IndependentExpectation())
    assert result.status == FAIL
    assert result.code == "unsupported_protocol_version"


def test_a_malformed_document_is_refused(tmp_path):
    newsroom = room(tmp_path)
    result = verify_external_checkpoint(
        document=None, document_bytes=b"not json at all", expectation=IndependentExpectation(
            document_sha256="0" * 64), pin=newsroom.pin, history=newsroom.history(), now=SYNTHETIC_NOW)
    assert result.status == FAIL
    assert result.code == "checkpoint_malformed"


def test_a_missing_document_is_blocked_not_a_pass(tmp_path):
    newsroom = room(tmp_path)
    result = verify_external_checkpoint(
        document=None, document_bytes=None, expectation=IndependentExpectation(),
        pin=newsroom.pin, history=newsroom.history(), now=SYNTHETIC_NOW)
    assert result.status == BLOCKED
    assert result.code == "checkpoint_missing"


def test_unavailable_local_state_is_inconclusive_rather_than_a_claim(tmp_path):
    newsroom = room(tmp_path)
    document = document_for(newsroom)
    result = verify_external_checkpoint(
        document=document, document_bytes=None,
        expectation=IndependentExpectation(document_sha256=digest_attestation(document)),
        pin=newsroom.pin, history=None, now=SYNTHETIC_NOW)
    assert result.status == INCONCLUSIVE
    assert result.code == "local_state_unavailable"


def test_an_emergency_stop_blocks_even_a_valid_checkpoint(tmp_path):
    newsroom = room(tmp_path)
    document = document_for(newsroom)
    emergency_hold(newsroom.root, "Synthetic test hold", SYNTHETIC_NOW)
    result = verify(newsroom, document, emergency_stopped=True)
    assert result.status == BLOCKED
    assert result.code == "emergency_hold"


def test_conflicting_independent_checkpoints_are_refused(tmp_path):
    newsroom = room(tmp_path)
    first = document_for(newsroom)
    newsroom.admin("revoke_source", "news-wire")
    second = document_for(newsroom)
    conflict = conflicting_checkpoints([first, second])
    assert conflict is not None
    result = verify_checkpoint_set(documents=[first, second],
                                   expectation=IndependentExpectation(
                                       document_sha256=digest_attestation(first)),
                                   pin=newsroom.pin, history=newsroom.history(), now=SYNTHETIC_NOW)
    assert result["status"] == FAIL
    assert result["code"] == "conflicting_checkpoints"


def test_agreeing_checkpoints_do_not_report_a_conflict(tmp_path):
    newsroom = room(tmp_path)
    first = document_for(newsroom)
    second = document_for(newsroom)
    assert conflicting_checkpoints([first, second]) is None


def test_a_bare_phase8_envelope_is_accepted_at_the_lowest_trust_level(tmp_path):
    newsroom = room(tmp_path)
    raw = newsroom.checkpoint_bytes()
    document = read_checkpoint_document(raw)
    assert document.trust.custody == "local-state-directory"
    result = verify(newsroom, document)
    assert result.status in {BLOCKED, FAIL}
    assert result.trust_level != "CURRENTLY_TRUSTED"


def test_a_canonical_document_is_required(tmp_path):
    newsroom = room(tmp_path)
    document = document_for(newsroom)
    payload = json.dumps(document.model_dump(mode="json"), indent=2).encode()
    with pytest.raises(AuthorityError):
        read_checkpoint_document(payload)


def test_the_custodian_digest_is_stable_across_reencodes(tmp_path):
    newsroom = room(tmp_path)
    document = document_for(newsroom)
    raw = canonical(document.model_dump(mode="json")) + b"\n"
    assert digest_attestation(read_checkpoint_document(raw)) == digest_attestation(document)
    assert hashlib.sha256(raw.removesuffix(b"\n")).hexdigest() == digest_attestation(document)
    # The document digest and the signed-envelope digest are different bindings.
    assert digest_attestation(document) != document.checkpoint_sha256


def test_the_operator_file_store_refuses_a_custodian_inside_the_checkout(tmp_path):
    inside = tmp_path / "checkpoint.json"
    inside.write_bytes(b"{}")
    store = OperatorFileCheckpointStore(inside, require_outside=tmp_path)
    with pytest.raises(AuthorityError):
        store.read()


def test_the_protected_history_store_is_offline_only(tmp_path):
    store = ProtectedHistoryCheckpointStore(tmp_path / "materialised")
    assert store.describe()["network_access"] is False
    assert store.describe()["requires_manual_materialization"] is True
    with pytest.raises(AuthorityError):
        store.read()


def test_the_missing_store_reports_a_custodian_action(tmp_path):
    store = MissingCheckpointStore()
    assert store.describe()["present"] is False
    with pytest.raises(AuthorityError):
        store.read()
