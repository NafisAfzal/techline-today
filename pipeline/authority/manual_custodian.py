"""Manual transport for the existing independently signed current-head protocol.

This adapter performs no network I/O or signing. Independence and UTC accuracy
are ceremony prerequisites, never inferred from a pathname or a typed name.
SQLite is local crash/replay protection, not an independently trusted oracle.
"""

import hashlib
import os
import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Literal

from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from pydantic import Field, StrictStr

from pipeline.authority.ledger import STOP, Anchor, verify_local_anchor
from pipeline.authority.protocol import (
    ZERO,
    AuthorityError,
    Digest,
    Identifier,
    Key,
    Model,
    Timestamp,
    canonical,
    clock,
    decode64,
    envelope_bytes,
    instant,
    read_envelope,
    stamp,
)
from pipeline.filesystem import confined_file, regular_path
from pipeline.generation import bounded_file
from pipeline.operations.custodian import DOMAIN, PROTOCOL, Challenge, Commitment, read_receipt
from pipeline.strict_json import strict_json

ADAPTER = "manual-independent-v1"
MAX_STATE = 4_000_000


def sha(data):
    return hashlib.sha256(data).hexdigest()


class CustodianPin(Model):
    """Independently authenticated ceremony input, outside both repo and state."""

    version: Literal[1]
    adapter: Literal["manual-independent-v1"]
    custodian_id: Identifier
    key: Key
    owner_id: Identifier
    owner_pin_sha256: Digest
    ledger_id: Identifier
    environment: Literal["synthetic", "production"]


class CurrentChallenge(Challenge):
    """Required v1 adapter extension; the unchanged receipt signs its digest."""

    adapter: Literal["manual-independent-v1"]
    owner_id: Identifier
    owner_key_id: Digest
    checkpoint_revision: int = Field(ge=1, le=1_000_000)
    previous_checkpoint_sha256: Digest
    previous_event_count: int = Field(ge=0, le=1_000_000)
    previous_head_sha256: Digest


class _Lease(Model):
    token_sha256: Digest
    checkpoint: Digest
    expires_at: Timestamp


class _State(Model):
    version: Literal[1]
    pin: Digest
    last_time: Timestamp
    frozen: bool
    checkpoint_revision: int = Field(ge=0, le=1_000_000)
    checkpoint_sha256: Digest
    event_count: int = Field(ge=0, le=1_000_000)
    head_sha256: Digest
    registry_revision: int = Field(ge=0, le=1_000_000)
    pending: CurrentChallenge | None
    lease: _Lease | None


class _Archive(Model):
    challenge: CurrentChallenge
    receipt: StrictStr
    checkpoint: StrictStr


def outside(path, root):
    path = regular_path(Path(path))
    if path.is_relative_to(Path(root).absolute()):
        raise AuthorityError("custodian_location", "Custodian inputs and replay state must be outside the checkout")
    return path


def read_pin(path, root):
    data = bounded_file(outside(path, root), 16_000)
    pin = CustodianPin.model_validate(strict_json(data, max_bytes=16_000))
    return pin


def _pin_digest(pin):
    return sha(canonical(pin.model_dump(mode="json")))


def _context(pin, history):
    owner = history.registry.pin
    if (pin.owner_id != owner.owner_id or pin.ledger_id != owner.ledger_id
            or pin.environment != owner.environment
            or pin.owner_pin_sha256 != sha(canonical(owner.model_dump(mode="json")))):
        raise AuthorityError("custodian_context", "Custodian pin disagrees with the independently pinned owner context")


@contextmanager
def _transaction(path, *, create=False):
    path = regular_path(Path(path))
    for suffix in ("-journal", "-wal", "-shm"):
        regular_path(Path(str(path) + suffix))
    if not create and (not path.is_file() or path.stat().st_size > MAX_STATE):
        raise AuthorityError("custodian_state_missing", "Missing or oversized replay state requires independent recovery")
    connection = None
    try:
        connection = sqlite3.connect(path.as_uri() + "?mode=rw", uri=True, timeout=2)
        connection.execute("PRAGMA synchronous=FULL")
        if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise AuthorityError("custodian_state_corrupt", "Replay state integrity check failed")
        connection.execute("BEGIN IMMEDIATE")
        yield connection
        connection.commit()
    except sqlite3.Error as error:
        if connection is not None:
            connection.rollback()
        raise AuthorityError("custodian_state_unavailable", "Replay state is incomplete, busy or inaccessible") from error
    except BaseException:
        if connection is not None:
            connection.rollback()
        raise
    finally:
        if connection is not None:
            connection.close()


def initialize(path, pin, now, *, root):
    """Explicit empty genesis only; never recreate missing state automatically."""
    target = outside(path, root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb"):
        pass
    with _transaction(target, create=True) as db:
        db.execute("CREATE TABLE state (id INTEGER PRIMARY KEY CHECK(id=1), body BLOB NOT NULL)")
        db.execute("CREATE TABLE archive (checkpoint TEXT PRIMARY KEY, body BLOB NOT NULL)")
        state = dict(version=1, pin=_pin_digest(pin), last_time=stamp(now), frozen=False,
                     checkpoint_revision=0, checkpoint_sha256=ZERO, event_count=0, head_sha256=ZERO,
                     registry_revision=0, pending=None, lease=None)
        db.execute("INSERT INTO state VALUES (1, ?)", (canonical(state),))


def _read(db, pin):
    rows = db.execute("SELECT id, body FROM state").fetchall()
    if len(rows) != 1 or rows[0][0] != 1:
        raise AuthorityError("custodian_state_incomplete", "Exactly one replay state record is required")
    try:
        state = _State.model_validate(strict_json(rows[0][1], max_bytes=64_000)).model_dump(mode="json")
    except (ValueError, TypeError) as error:
        raise AuthorityError("custodian_state_incomplete", "Replay state is malformed or incomplete") from error
    if state["pin"] != _pin_digest(pin):
        raise AuthorityError("custodian_state_incomplete", "Replay schema or independently provisioned pin changed")
    instant(state["last_time"])
    return state


def _write(db, state):
    db.execute("UPDATE state SET body=? WHERE id=1", (canonical(state),))


def _floor(state, history, now):
    if state["frozen"]:
        raise AuthorityError("custodian_frozen", "Rejected exchange or interrupted operation requires independent recovery")
    if clock(now) < instant(state["last_time"]):
        raise AuthorityError("clock_regression", "UTC clock regressed below the durable verifier floor")
    count = state["event_count"]
    events = history.journal.events
    if len(events) < count or history.registry.revision < state["registry_revision"]:
        raise AuthorityError("custodian_rollback", "Journal or registry regressed below the accepted independent checkpoint")
    prefix = events[count - 1].event_sha256 if count else ZERO
    if prefix != state["head_sha256"]:
        raise AuthorityError("custodian_fork", "Journal does not extend the independently checkpointed prefix")


def issue(path, pin, history, now, *, emergency_stopped=False):
    _context(pin, history)
    error = None
    with _transaction(path) as db:
        state = _read(db, pin)
        try:
            if emergency_stopped:
                raise AuthorityError("emergency_hold", "Emergency suspension blocks current-head requests")
            _floor(state, history, now)
            if state["lease"] is not None:
                raise AuthorityError("custodian_operation_active", "A previous operation is active or interrupted")
            request = CurrentChallenge(version=1, protocol="techline.custodian.current-head/v1", adapter=ADAPTER,
                                       custodian_id=pin.custodian_id, environment=pin.environment,
                                       ledger_id=pin.ledger_id, owner_id=pin.owner_id,
                                       owner_key_id=history.registry.root_key.key_id, nonce=secrets.token_hex(32),
                                       minimum_event_count=len(history.journal.events),
                                       registry_revision=history.registry.revision,
                                       checkpoint_revision=state["checkpoint_revision"] + 1,
                                       previous_checkpoint_sha256=state["checkpoint_sha256"],
                                       previous_event_count=state["event_count"], previous_head_sha256=state["head_sha256"],
                                       issued_at=stamp(now), expires_at=stamp(clock(now) + timedelta(seconds=120)))
            state.update(pending=request.model_dump(mode="json"), last_time=stamp(now))
        except (ValueError, TypeError) as caught:
            state["frozen"] = True
            error = caught
        _write(db, state)
    if error is not None:
        raise error
    return request


def _verify(pin, request, receipt, checkpoint, history, now):
    """Shared live/historical cryptographic checks; no clock or I/O fallback."""
    _context(pin, history)
    request = CurrentChallenge.model_validate(request)
    p = receipt.payload
    at = clock(now)
    if not instant(request.issued_at) <= at < instant(request.expires_at):
        raise AuthorityError("challenge_expired", "Challenge is expired or future-dated")
    if (instant(request.expires_at) - instant(request.issued_at)).total_seconds() > 120:
        raise AuthorityError("challenge_lifetime", "Challenge exceeds the 120 second manual freshness boundary")
    if not instant(request.issued_at) <= instant(p.issued_at) <= at < instant(p.expires_at):
        raise AuthorityError("receipt_time", "Receipt is stale, future-dated or predates its challenge")
    if instant(p.expires_at) > instant(request.expires_at):
        raise AuthorityError("receipt_time", "Receipt extends its challenge freshness boundary")
    if not instant(pin.key.active_at) <= instant(p.issued_at) <= at < instant(pin.key.expires_at):
        raise AuthorityError("custodian_key_expired", "Pinned custodian key is not active")
    if (p.key_id != pin.key.key_id or p.custodian_id != pin.custodian_id
            or p.environment != pin.environment or p.ledger_id != pin.ledger_id
            or request.custodian_id != pin.custodian_id or request.environment != pin.environment
            or request.ledger_id != pin.ledger_id or request.owner_id != pin.owner_id
            or request.owner_key_id != history.registry.root_key.key_id):
        raise AuthorityError("receipt_context", "Receipt or challenge has a different pinned context")
    try:
        VerifyKey(decode64(pin.key.public_key, 32)).verify(
            DOMAIN + canonical(p.model_dump(mode="json")), decode64(receipt.signature, 64))
    except BadSignatureError as error:
        raise AuthorityError("custodian_signature", "Custodian signature does not verify") from error
    if p.request_sha256 != sha(canonical(request.model_dump(mode="json"))):
        raise AuthorityError("request_replay", "Receipt is not bound to this exact single-use request")
    cp = checkpoint.payload
    anchor = Anchor(envelope_bytes(checkpoint), p.checkpoint_sha256, request.nonce)
    verify_local_anchor(history, anchor, at)
    if instant(cp.issued_at) < instant(request.issued_at):
        raise AuthorityError("checkpoint_time", "Owner checkpoint predates the fresh independent challenge")
    if (p.head_sha256 != cp.head_sha256 or p.event_count != cp.event_count
            or p.registry_revision != cp.registry_revision or p.registry_revision != request.registry_revision
            or p.event_count != request.minimum_event_count):
        raise AuthorityError("commitment_conflict", "Custodian receipt disagrees with the exact owner checkpoint")
    events = history.journal.events
    count = request.previous_event_count
    if count > len(events) or (events[count - 1].event_sha256 if count else ZERO) != request.previous_head_sha256:
        raise AuthorityError("custodian_fork", "Checkpoint does not extend the previous independently retained journal")
    return request


def consume(path, pin, receipt_bytes, checkpoint_bytes, history, now, *, expected_nonce, emergency_stopped=False):
    """Consume against a nonce held by this live operation, never a disk input.

    Client callers must generate the request in this same process and retain
    its expected nonce in memory. Reading the expected nonce from restored
    state, a checkpoint or a response would reintroduce pending-state replay.
    The independent responder instead supplies its authenticated incoming nonce.
    """
    error = None
    token = secrets.token_hex(32)
    with _transaction(path) as db:
        state = _read(db, pin)
        request, state["pending"] = state["pending"], None
        try:
            _floor(state, history, now)
            if emergency_stopped:
                raise AuthorityError("emergency_hold", "Emergency suspension blocks checkpoint acceptance")
            if request is None or state["lease"] is not None:
                raise AuthorityError("custodian_replay", "No pending request or another operation already consumed it")
            if request["nonce"] != expected_nonce:
                raise AuthorityError("custodian_live_nonce", "Persisted request differs from the live process challenge")
            receipt = read_receipt(receipt_bytes)
            checkpoint = read_envelope(checkpoint_bytes)
            request = _verify(pin, request, receipt, checkpoint, history, now)
            if (request.checkpoint_revision != state["checkpoint_revision"] + 1
                    or request.previous_checkpoint_sha256 != state["checkpoint_sha256"]
                    or request.previous_event_count != state["event_count"]
                    or request.previous_head_sha256 != state["head_sha256"]):
                raise AuthorityError("custodian_continuity", "Request conflicts with durable checkpoint continuity")
            record = dict(challenge=request.model_dump(mode="json"), receipt=receipt_bytes.decode("ascii"),
                          checkpoint=envelope_bytes(checkpoint).decode("ascii"))
            digest = receipt.payload.checkpoint_sha256
            db.execute("INSERT INTO archive VALUES (?, ?)", (digest, canonical(record)))
            state.update(checkpoint_revision=request.checkpoint_revision, checkpoint_sha256=digest,
                         head_sha256=receipt.payload.head_sha256, event_count=receipt.payload.event_count,
                         registry_revision=receipt.payload.registry_revision, last_time=stamp(now),
                         lease=dict(token_sha256=sha(token.encode()), checkpoint=digest,
                                    expires_at=receipt.payload.expires_at))
        except (ValueError, TypeError, sqlite3.Error) as caught:
            state["frozen"] = True
            error = caught
        _write(db, state)
    if error is not None:
        raise error
    return token


def prepare_response(path, pin, request_bytes, checkpoint_bytes, history, now, *, emergency_stopped=False):
    """Run on the independent custodian's device with its own retained state.

    The owner cannot select the predecessor: it must match this device's durable
    independent floor. No signature or output is produced here.
    """
    request = CurrentChallenge.model_validate(strict_json(request_bytes, max_bytes=16_000))
    if canonical(request.model_dump(mode="json")) != request_bytes:
        raise AuthorityError("challenge_encoding", "Challenge must be exactly canonical JSON")
    _context(pin, history)
    checkpoint = read_envelope(checkpoint_bytes)
    error = None
    with _transaction(path) as db:
        state = _read(db, pin)
        try:
            _floor(state, history, now)
            if emergency_stopped:
                raise AuthorityError("emergency_hold", "Independent custodian has suspended publication")
            if (state["lease"] is not None or state["pending"] is not None
                    or request.checkpoint_revision != state["checkpoint_revision"] + 1
                    or request.previous_checkpoint_sha256 != state["checkpoint_sha256"]
                    or request.previous_event_count != state["event_count"]
                    or request.previous_head_sha256 != state["head_sha256"]):
                raise AuthorityError("custodian_continuity", "Independent retained state refuses replay, fork or skipped revision")
            if (request.custodian_id != pin.custodian_id or request.environment != pin.environment
                    or request.ledger_id != pin.ledger_id or request.owner_id != pin.owner_id
                    or request.owner_key_id != history.registry.root_key.key_id
                    or request.registry_revision != history.registry.revision
                    or request.minimum_event_count != len(history.journal.events)):
                raise AuthorityError("custodian_context", "Challenge does not identify the independently verified current owner head")
            if not instant(request.issued_at) <= clock(now) < instant(request.expires_at):
                raise AuthorityError("challenge_expired", "Challenge is expired or future-dated")
            if not 0 < (instant(request.expires_at) - instant(request.issued_at)).total_seconds() <= 120:
                raise AuthorityError("challenge_lifetime", "Challenge must expire within 120 seconds")
            verify_local_anchor(history, Anchor(checkpoint_bytes, sha(envelope_bytes(checkpoint)), request.nonce), now)
            state.update(pending=request.model_dump(mode="json"), last_time=stamp(now))
        except (ValueError, TypeError) as caught:
            state["frozen"] = True
            error = caught
        _write(db, state)
    if error is not None:
        raise error
    cp = checkpoint.payload
    return Commitment(version=1, protocol=PROTOCOL, custodian_id=pin.custodian_id, key_id=pin.key.key_id,
                      environment=pin.environment, ledger_id=pin.ledger_id, request_sha256=sha(request_bytes),
                      checkpoint_sha256=sha(envelope_bytes(checkpoint)), head_sha256=cp.head_sha256,
                      event_count=cp.event_count, registry_revision=cp.registry_revision,
                      issued_at=stamp(now), expires_at=request.expires_at)


def close(path, pin, token):
    with _transaction(path) as db:
        state = _read(db, pin)
        if state["lease"] is None or state["lease"]["token_sha256"] != sha(token.encode()):
            raise AuthorityError("custodian_lease", "Operation lease is missing or belongs to another process")
        state["lease"] = None
        _write(db, state)


@dataclass(frozen=True)
class ManualCustodyProof:
    pin_path: Path
    state_path: Path
    token: str
    root: Path

    def _record(self, checkpoint_sha256=None, *, historical=False):
        pin = read_pin(self.pin_path, self.root)
        with _transaction(outside(self.state_path, self.root)) as db:
            state = _read(db, pin)
            if state["frozen"]:
                raise AuthorityError("custodian_frozen", "Custody exchange state is frozen")
            if not historical:
                lease = state["lease"]
                if lease is None or lease["token_sha256"] != sha(self.token.encode()):
                    raise AuthorityError("custodian_lease", "Current operation has no single-use checkpoint lease")
                checkpoint_sha256 = lease["checkpoint"]
            rows = db.execute("SELECT body FROM archive WHERE checkpoint=?", (checkpoint_sha256,)).fetchall()
            if len(rows) != 1:
                raise AuthorityError("custodian_archive_missing", "Historical independent receipt archive is incomplete")
            record = _Archive.model_validate(strict_json(rows[0][0], max_bytes=128_000)).model_dump(mode="json")
        return pin, state, record

    def anchor(self):
        _, _, record = self._record()
        receipt = read_receipt(record["receipt"].encode("ascii"))
        return Anchor(record["checkpoint"].encode("ascii"), receipt.payload.checkpoint_sha256,
                      record["challenge"]["nonce"], self)

    def verify(self, history, anchor, now, *, historical=False):
        if not historical and confined_file(self.root, STOP).exists():
            raise AuthorityError("emergency_hold", "Emergency STOP blocks the active custody operation")
        pin, state, record = self._record(anchor.expected_sha256, historical=historical)
        if not historical:
            _floor(state, history, now)
        receipt = read_receipt(record["receipt"].encode("ascii"))
        checkpoint = read_envelope(record["checkpoint"].encode("ascii"))
        if (anchor.expected_sha256 != receipt.payload.checkpoint_sha256
                or anchor.expected_challenge != record["challenge"]["nonce"]
                or envelope_bytes(read_envelope(anchor.envelope)) != envelope_bytes(checkpoint)):
            raise AuthorityError("custodian_anchor_conflict", "Requested checkpoint differs from the consumed response")
        _verify(pin, record["challenge"], receipt, checkpoint, history, now)
        if not historical:
            # Persist the latest successful UTC observation too, so a clock
            # rollback between repeated checks in one build cannot be hidden.
            with _transaction(outside(self.state_path, self.root)) as db:
                latest = _read(db, pin)
                _floor(latest, history, now)
                if latest["lease"] != state["lease"]:
                    raise AuthorityError("custodian_lease", "Operation lease changed during verification")
                latest["last_time"] = stamp(now)
                _write(db, latest)
        return {"status": "PASS", "code": "independent_current_head_verified" if not historical else
                "independent_historical_receipt_verified", "current": not historical,
                "independently_trusted": pin.environment == "production", "publication_allowed": False,
                "trust_level": ("INDEPENDENTLY_AUTHENTICATED" if historical else "CURRENTLY_TRUSTED")
                if pin.environment == "production" else "LOCAL_SIGNED",
                "synthetic_only": pin.environment == "synthetic", "custodian_id": pin.custodian_id,
                "checkpoint_sha256": receipt.payload.checkpoint_sha256,
                "checkpoint_revision": record["challenge"]["checkpoint_revision"]}


def configured_proof(root, *, historical=False):
    policy = os.environ.get("TECHLINE_CUSTODIAN_PIN_FILE")
    state = os.environ.get("TECHLINE_CUSTODIAN_STATE_FILE")
    token = os.environ.get("TECHLINE_CUSTODIAN_RUN_TOKEN", "")
    if not policy and not state and not token:
        return None
    if not policy or not state or not token and not historical:
        raise AuthorityError("custodian_configuration", "Custodian pin, durable state and scoped run token are required")
    return ManualCustodyProof(outside(policy, root), outside(state, root), token, Path(root))
