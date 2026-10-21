"""Proposed current-head wire protocol and bounded offline mock verifier.

This does not connect to the production checkpoint loader. Process-local replay
state, a caller clock and a synthetic custodian cannot establish independence.
"""

import hashlib
import secrets
from datetime import timedelta
from typing import Literal

from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from pydantic import Field, StrictStr

from pipeline.authority.checkpoint import digest_checkpoint_envelope
from pipeline.authority.ledger import Anchor, compare_checkpoint, verify_anchor
from pipeline.authority.protocol import (
    AuthorityError,
    Checkpoint,
    Digest,
    Identifier,
    Model,
    Timestamp,
    canonical,
    clock,
    decode64,
    encode64,
    envelope_bytes,
    fingerprint,
    instant,
    read_envelope,
    stamp,
)
from pipeline.strict_json import strict_json

PROTOCOL = "techline.custodian.current-head/v1"
DOMAIN = b"TECHLINE-TODAY\x00CUSTODIAN-CURRENT-HEAD\x00V1\x00"


class Challenge(Model):
    version: Literal[1]
    protocol: Literal["techline.custodian.current-head/v1"]
    custodian_id: Identifier
    environment: Literal["synthetic", "production"]
    ledger_id: Identifier
    nonce: Digest
    minimum_event_count: int = Field(ge=0, le=1_000_000)
    registry_revision: int = Field(ge=0, le=1_000_000)
    issued_at: Timestamp
    expires_at: Timestamp


class Commitment(Model):
    version: Literal[1]
    protocol: Literal["techline.custodian.current-head/v1"]
    custodian_id: Identifier
    key_id: Digest
    environment: Literal["synthetic", "production"]
    ledger_id: Identifier
    request_sha256: Digest
    checkpoint_sha256: Digest
    head_sha256: Digest
    event_count: int = Field(ge=0, le=1_000_000)
    registry_revision: int = Field(ge=0, le=1_000_000)
    issued_at: Timestamp
    expires_at: Timestamp


class Receipt(Model):
    algorithm: Literal["Ed25519"]
    payload: Commitment
    signature: StrictStr


def wire(receipt):
    return canonical(receipt.model_dump(mode="json"))


def read_receipt(data):
    value = strict_json(data, max_bytes=16_000, max_depth=8, max_tokens=1000)
    receipt = Receipt.model_validate(value)
    decode64(receipt.signature, 64)
    if wire(receipt) != data:
        raise AuthorityError("receipt_encoding", "Receipt must use exact canonical encoding")
    return receipt


class MockCustodian:
    """A published synthetic key and in-memory head; never independent custody."""

    def __init__(self, checkpoint, *, name="custodian"):
        from pipeline.recovery.fixtures import synthetic_key, synthetic_private

        self.checkpoint = read_envelope(envelope_bytes(checkpoint))
        if not isinstance(self.checkpoint.payload, Checkpoint) or self.checkpoint.payload.environment != "synthetic":
            raise AuthorityError("synthetic_required", "Mock custodian refuses production checkpoints")
        self.key = synthetic_key(name)
        self._private = synthetic_private(name)

    def answer(self, challenge, now):
        challenge = Challenge.model_validate(challenge.model_dump(mode="json"))
        cp = self.checkpoint.payload
        if (challenge.environment != "synthetic" or challenge.ledger_id != cp.ledger_id
                or challenge.registry_revision != cp.registry_revision
                or cp.event_count < challenge.minimum_event_count):
            raise AuthorityError("custodian_context", "Custodian head does not satisfy the challenge context")
        at = clock(now)
        if not instant(challenge.issued_at) <= at < instant(challenge.expires_at):
            raise AuthorityError("challenge_expired", "Challenge is stale or future-dated")
        payload = Commitment(version=1, protocol=PROTOCOL, custodian_id=challenge.custodian_id,
                             key_id=self.key.key_id, environment=cp.environment, ledger_id=cp.ledger_id,
                             request_sha256=hashlib.sha256(canonical(challenge.model_dump(mode="json"))).hexdigest(),
                             checkpoint_sha256=digest_checkpoint_envelope(self.checkpoint),
                             head_sha256=cp.head_sha256, event_count=cp.event_count,
                             registry_revision=cp.registry_revision, issued_at=stamp(at),
                             expires_at=challenge.expires_at)
        return Receipt(algorithm="Ed25519", payload=payload,
                       signature=encode64(self._private.sign(DOMAIN + canonical(payload.model_dump(mode="json")))))


class MockVerificationSession:
    """Single pending request, bounded lifetime, sticky failure; no durable trust.

    Replacement requests invalidate lost responses. Any attempted verification
    consumes the request, including failures. A failure freezes this rehearsal
    session; recovery requires explicit inspection and a new synthetic session.
    """

    def __init__(self, key, *, custodian_id="synthetic-custodian"):
        from pipeline.authority.protocol import Key

        self.key = Key.model_validate(key.model_dump(mode="json"))
        self.custodian_id = custodian_id
        self._pending = None
        self._last_clock = None
        self._floor = (0, 0)
        self._failed = False

    def issue(self, history, now):
        at = clock(now)
        if not history.registry.pin.synthetic:
            raise AuthorityError("synthetic_required", "Production requires a reviewed independent channel")
        if self._failed:
            raise AuthorityError("session_frozen", "Inspect the rejected evidence before starting a new session")
        if self._last_clock is not None and at < self._last_clock:
            self._failed = True
            raise AuthorityError("clock_regression", "Verifier clock regressed")
        current = (len(history.journal.events), history.registry.revision)
        if any(a < b for a, b in zip(current, self._floor, strict=True)):
            self._failed = True
            raise AuthorityError("revision_regression", "Journal or registry regressed below the observed floor")
        self._last_clock = at
        self._pending = Challenge(version=1, protocol=PROTOCOL, custodian_id=self.custodian_id,
                                  environment="synthetic", ledger_id=history.registry.pin.ledger_id,
                                  nonce=secrets.token_hex(32), minimum_event_count=current[0],
                                  registry_revision=current[1], issued_at=stamp(at),
                                  expires_at=stamp(at + timedelta(seconds=120)))
        return self._pending

    def verify(self, data, checkpoint, history, now, *, emergency_stopped=False):
        request, self._pending = self._pending, None
        result = {"status": "BLOCKED", "code": "missing_response", "synthetic_only": True,
                  "independently_trusted": False, "current": False, "publication_allowed": False}
        try:
            if self._failed or request is None:
                raise AuthorityError("session_or_replay", "Session is frozen or challenge was already consumed")
            at = clock(now)
            if emergency_stopped:
                raise AuthorityError("emergency_hold", "Publication freeze is present")
            if data is None:
                raise AuthorityError("missing_response", "Custodian response was lost or unavailable")
            response = read_receipt(data)
            p = response.payload
            if not instant(request.issued_at) <= at < instant(request.expires_at):
                raise AuthorityError("challenge_expired", "Expired or regressed verifier clock")
            if not instant(request.issued_at) <= instant(p.issued_at) <= at < instant(p.expires_at):
                raise AuthorityError("receipt_time", "Receipt is future-dated, stale or predates the challenge")
            if instant(p.expires_at) > instant(request.expires_at):
                raise AuthorityError("receipt_time", "Receipt extends the verifier freshness boundary")
            if (p.custodian_id != request.custodian_id or p.environment != request.environment
                    or p.ledger_id != request.ledger_id or p.key_id != self.key.key_id):
                raise AuthorityError("receipt_context", "Wrong custodian, key, environment or ledger")
            if not instant(self.key.active_at) <= at < instant(self.key.expires_at):
                raise AuthorityError("custodian_key_expired", "Custodian key is not active")
            public = decode64(self.key.public_key, 32)
            fingerprint(public)
            try:
                VerifyKey(public).verify(DOMAIN + canonical(p.model_dump(mode="json")),
                                         decode64(response.signature, 64))
            except BadSignatureError as error:
                raise AuthorityError("custodian_signature", "Custodian signature does not verify") from error
            if p.request_sha256 != hashlib.sha256(canonical(request.model_dump(mode="json"))).hexdigest():
                raise AuthorityError("request_replay", "Receipt is not bound to this single-use challenge")
            envelope = read_envelope(envelope_bytes(checkpoint))
            if not isinstance(envelope.payload, Checkpoint) or not history.registry.pin.synthetic:
                raise AuthorityError("synthetic_required", "Mock verification refuses production authority")
            cp = envelope.payload
            comparison = compare_checkpoint(history, cp)
            if not comparison.matched:
                raise AuthorityError(comparison.code, comparison.detail)
            # Reuse owner signature/context/time/rotation checks. This anchor is
            # explicitly mock-local and never establishes independent custody.
            verify_anchor(history, Anchor(envelope_bytes(envelope), digest_checkpoint_envelope(envelope),
                                           cp.challenge), at)
            if (p.checkpoint_sha256 != digest_checkpoint_envelope(envelope) or p.head_sha256 != cp.head_sha256
                    or p.event_count != cp.event_count or p.registry_revision != cp.registry_revision
                    or p.registry_revision != request.registry_revision
                    or p.event_count < request.minimum_event_count):
                raise AuthorityError("commitment_conflict", "Signed receipt conflicts with owner checkpoint or floor")
            self._floor = (p.event_count, p.registry_revision)
            self._last_clock = at
            result.update(status="PASS", code="synthetic_protocol_verified")
        except (ValueError, TypeError) as error:
            self._failed = True
            result.update(status="BLOCKED" if isinstance(error, AuthorityError) else "FAIL",
                          code=error.code if isinstance(error, AuthorityError) else "malformed_receipt")
        return result
