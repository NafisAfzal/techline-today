"""External checkpoint custody, trust levels and rollback verification.

Phase 8 already signs a journal head as a ``Checkpoint`` envelope. That envelope
proves *which key* signed a head; it does not prove that the head is *current*.
A locally self-consistent journal can be rolled back to an old, internally valid
state, and a signed checkpoint sitting in the same directory is rolled back with
it. This module adds the missing half:

* a **custody envelope** that travels to an independently held custodian, and
* a **verifier** that states plainly which trust level it can actually reach.

Five trust levels are distinguished and never collapsed:

1. ``LOCAL_SNAPSHOT`` - generated locally, never signed.
2. ``LOCAL_SIGNED`` - signed locally; still only local evidence.
3. ``EXTERNAL_STORED`` - written outside the authority state directory.
4. ``INDEPENDENTLY_AUTHENTICATED`` - the verifier holds an independently
   obtained digest/challenge for that exact document.
5. ``CURRENTLY_TRUSTED`` - level 4 *and* signature, ledger identity,
   environment, registry revision and journal head all agree with the local
   state at verification time.

Only level 5 may be reported as a current trusted checkpoint. Level 3 is not
authenticity: a file copied into another folder is still a file on the same
disk. Hash chaining cannot supply what it never had - continuity with the
trusted past. The verifier therefore reports ``BLOCKED`` or ``INCONCLUSIVE``
when independent evidence is absent, and never converts missing evidence into
``PASS``.

Nothing here contacts a network, provisions a key, appoints a reviewer or
grants a permission. Storage adapters are read-only.
"""

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, Protocol

from pydantic import Field, field_validator, model_validator

from pipeline.authority.ledger import VerifiedHistory, compare_checkpoint
from pipeline.authority.protocol import (
    POLICY,
    PROTOCOL,
    AuthorityError,
    Checkpoint,
    Digest,
    Envelope,
    Identifier,
    Model,
    Timestamp,
    canonical,
    clock,
    envelope_bytes,
    instant,
    read_envelope,
    verify_signature,
)
from pipeline.authority.registry import TrustPin
from pipeline.filesystem import regular_path

FORMAT = "techline.editorial.external-checkpoint/v1"
MAX_DOCUMENT_BYTES = 256_000

PASS, FAIL, BLOCKED, INCONCLUSIVE = "PASS", "FAIL", "BLOCKED", "INCONCLUSIVE"

TrustLevel = Literal[
    "LOCAL_SNAPSHOT",
    "LOCAL_SIGNED",
    "EXTERNAL_STORED",
    "INDEPENDENTLY_AUTHENTICATED",
    "CURRENTLY_TRUSTED",
]
Custody = Literal[
    "local-state-directory",
    "operator-offline-file",
    "protected-git-history",
    "read-only-mirror",
    "unknown",
]
Authentication = Literal["none", "operator-attested", "independently-signed"]

# Detection codes. Every one of them refuses to assert currency.
CHECKPOINT_MISSING = "checkpoint_missing"
CHECKPOINT_MALFORMED = "checkpoint_malformed"
UNKNOWN_LEDGER = "unknown_ledger"
REGISTRY_MISMATCH = "registry_mismatch"
JOURNAL_REVISION_REGRESSION = "journal_revision_regression"
JOURNAL_HASH_MISMATCH = "journal_hash_mismatch"
INCOMPLETE_HISTORY = "incomplete_history"
CONFLICTING_CHECKPOINTS = "conflicting_checkpoints"
CHECKPOINT_STALE = "checkpoint_stale"
UNKNOWN_SIGNER = "unknown_signer"
INVALID_SIGNATURE = "invalid_signature"
CROSS_ENVIRONMENT_REPLAY = "cross_environment_replay"
UNSUPPORTED_PROTOCOL_VERSION = "unsupported_protocol_version"
INDEPENDENT_EVIDENCE_MISSING = "independent_evidence_missing"
EXPECTED_DIGEST_MISMATCH = "expected_digest_mismatch"
CHALLENGE_MISMATCH = "challenge_mismatch"
EMERGENCY_HOLD = "emergency_hold"
OWNER_EXPIRED = "owner_expired"
LOCAL_STATE_UNAVAILABLE = "local_state_unavailable"
CHECKPOINT_NOT_CURRENT = "checkpoint_not_current"
CHECKPOINT_CUSTODY_INSUFFICIENT = "checkpoint_custody_insufficient"


class TrustClaim(Model):
    """The custodian's custody/authentication claim for one document.

    This is an *assertion made by the custodian*, not proof. The verifier
    recomputes its own ``independently_trusted`` result from the independently
    supplied expectation and never reads the claim as authority.
    """

    custody: Custody = "unknown"
    authentication: Authentication = "none"
    operator_claims_independence: bool = False
    verified_by: str | None = Field(default=None, max_length=200)
    verified_at: Timestamp | None = None

    @field_validator("verified_by")
    @classmethod
    def plain(cls, value):
        if value is not None and (not value.strip() or len(value) > 200):
            raise ValueError("Custody verification label must be a bounded nonblank string")
        return value


class ExternalCheckpoint(Model):
    """A signed Phase 8 checkpoint plus the custody statement that travels with it.

    The canonical representation is ``canonical(document.model_dump(mode="json"))``.
    Its digest is what an independent channel must carry; a document without an
    independently obtained digest is stored evidence, not trusted evidence.
    """

    format: Literal["techline.editorial.external-checkpoint/v1"]
    format_version: Literal[1]
    ledger_id: Identifier
    environment: Literal["synthetic", "production"]
    policy_version: Literal["phase8-authority-v1"]
    captured_at: Timestamp
    checkpoint_envelope: Envelope
    checkpoint_sha256: Digest
    trust: TrustClaim = TrustClaim()
    challenge: Identifier | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("format_version", mode="before")
    @classmethod
    def strict_format_version(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("External checkpoint format version must be integer 1")
        return value

    @model_validator(mode="after")
    def shape(self):
        payload = self.checkpoint_envelope.payload
        if not isinstance(payload, Checkpoint):
            raise ValueError("External checkpoint must wrap a signed checkpoint payload")
        if payload.ledger_id != self.ledger_id or payload.environment != self.environment:
            raise ValueError("External checkpoint identity disagrees with its signed envelope")
        if payload.policy_version != self.policy_version:
            raise ValueError("External checkpoint policy version disagrees with its signed envelope")
        if digest_checkpoint_envelope(self.checkpoint_envelope) != self.checkpoint_sha256:
            raise ValueError("External checkpoint digest disagrees with its signed envelope")
        if self.challenge is not None and payload.challenge != self.challenge:
            raise ValueError("External checkpoint challenge disagrees with its signed envelope")
        return self


class CheckpointVerification(Model):
    """The verifier's answer. ``status`` is the only thing a caller may act on."""

    status: Literal["PASS", "FAIL", "BLOCKED", "INCONCLUSIVE"]
    code: str
    trust_level: TrustLevel
    detail: str
    independently_trusted: bool = False
    current: bool = False
    evidence: dict = Field(default_factory=dict)
    publication_allowed: bool = False

    @property
    def trusted(self) -> bool:
        return self.status == PASS and self.trust_level == "CURRENTLY_TRUSTED"


def digest_checkpoint_envelope(envelope) -> str:
    """SHA-256 over canonical envelope bytes, excluding the optional terminal LF."""
    return hashlib.sha256(envelope_bytes(envelope)).hexdigest()


def attestation_bytes(document) -> bytes:
    return canonical(document.model_dump(mode="json"))


def digest_attestation(document) -> str:
    return hashlib.sha256(attestation_bytes(document)).hexdigest()


def build_attestation(envelope, *, custody: Custody, authentication: Authentication,
                      captured_at, challenge: str | None = None, verified_by: str | None = None,
                      verified_at=None, notes: str | None = None) -> ExternalCheckpoint:
    """Wrap an already-signed checkpoint envelope in a custody statement.

    This performs no signing and no verification. The caller supplies a signed
    envelope produced by the existing Phase 8 signer.
    """
    envelope = Envelope.model_validate(envelope.model_dump(mode="json"))
    payload = envelope.payload
    if not isinstance(payload, Checkpoint):
        raise AuthorityError("checkpoint", "Expected a signed checkpoint envelope")
    captured = clock(captured_at)
    claim = TrustClaim(custody=custody, authentication=authentication,
                       operator_claims_independence=custody != "local-state-directory",
                       verified_by=verified_by,
                       verified_at=verified_at.strftime("%Y-%m-%dT%H:%M:%SZ")
                       if verified_at is not None else None)
    return ExternalCheckpoint(
        format=FORMAT, format_version=1, ledger_id=payload.ledger_id,
        environment=payload.environment, policy_version=payload.policy_version,
        captured_at=captured.strftime("%Y-%m-%dT%H:%M:%SZ"),
        checkpoint_envelope=envelope, checkpoint_sha256=digest_checkpoint_envelope(envelope),
        trust=claim, challenge=challenge, notes=notes)


def _peek_protocol(value):
    """Reject an unsupported protocol/version before strict validation hides it."""
    if not isinstance(value, dict):
        return
    if value.get("format") is not None and value.get("format") != FORMAT:
        raise AuthorityError(UNSUPPORTED_PROTOCOL_VERSION,
                             f"Unsupported external checkpoint format {value.get('format')!r}")
    if value.get("format_version") is not None and value.get("format_version") != 1:
        raise AuthorityError(UNSUPPORTED_PROTOCOL_VERSION,
                             "Unsupported external checkpoint format version")
    envelope = value.get("checkpoint_envelope")
    if isinstance(envelope, dict):
        payload = envelope.get("payload")
        if isinstance(payload, dict):
            if payload.get("protocol") is not None and payload.get("protocol") != PROTOCOL:
                raise AuthorityError(UNSUPPORTED_PROTOCOL_VERSION,
                                     f"Unsupported authority protocol {payload.get('protocol')!r}")
            if payload.get("version") is not None and payload.get("version") != 1:
                raise AuthorityError(UNSUPPORTED_PROTOCOL_VERSION,
                                     "Unsupported authority record version")
    elif isinstance(value.get("payload"), dict):
        payload = value["payload"]
        if payload.get("protocol") is not None and payload.get("protocol") != PROTOCOL:
            raise AuthorityError(UNSUPPORTED_PROTOCOL_VERSION,
                                 f"Unsupported authority protocol {payload.get('protocol')!r}")


def _parse_document(data: bytes):
    """Parse a checkpoint document body into its raw bytes and decoded value."""
    if not isinstance(data, bytes) or not data:
        raise AuthorityError(CHECKPOINT_MALFORMED, "External checkpoint document is empty")
    if len(data) > MAX_DOCUMENT_BYTES:
        raise AuthorityError(CHECKPOINT_MALFORMED, "External checkpoint document exceeds the size limit")
    from pipeline.strict_json import strict_json

    raw = data.removesuffix(b"\n")
    try:
        value = strict_json(raw, max_bytes=MAX_DOCUMENT_BYTES, max_depth=16, max_tokens=20000)
    except (ValueError, TypeError, RecursionError, UnicodeError) as error:
        raise AuthorityError(CHECKPOINT_MALFORMED, "External checkpoint document is not readable JSON") from error
    _peek_protocol(value)
    return raw, value


def read_attestation(data: bytes) -> ExternalCheckpoint:
    """Parse a canonical custody document. Malformed input never becomes evidence."""
    raw, value = _parse_document(data)
    try:
        document = ExternalCheckpoint.model_validate(value)
    except (ValueError, TypeError) as error:
        raise AuthorityError(CHECKPOINT_MALFORMED, "External checkpoint document is malformed") from error
    if raw != attestation_bytes(document):
        raise AuthorityError(CHECKPOINT_MALFORMED, "External checkpoint document is not canonical")
    return document


def read_checkpoint_document(data: bytes) -> ExternalCheckpoint:
    """Accept either a Phase 10 custody document or a bare Phase 8 signed envelope.

    A bare envelope is accepted so the existing Phase 8 anchors keep working,
    but it carries no custody statement: it can only ever reach
    ``LOCAL_SIGNED`` unless an independently obtained digest is supplied.
    """
    raw, value = _parse_document(data)
    if isinstance(value, dict) and value.get("format") == FORMAT:
        return read_attestation(raw)
    if isinstance(value, dict) and "algorithm" in value and "payload" in value:
        envelope = read_envelope(raw)
        if not isinstance(envelope.payload, Checkpoint):
            raise AuthorityError(CHECKPOINT_MALFORMED, "Expected a signed checkpoint envelope")
        payload = envelope.payload
        return ExternalCheckpoint(
            format=FORMAT, format_version=1, ledger_id=payload.ledger_id,
            environment=payload.environment, policy_version=payload.policy_version,
            captured_at=payload.issued_at, checkpoint_envelope=envelope,
            checkpoint_sha256=digest_checkpoint_envelope(envelope),
            trust=TrustClaim(custody="local-state-directory", authentication="none",
                             operator_claims_independence=False),
            challenge=payload.challenge)
    raise AuthorityError(CHECKPOINT_MALFORMED, "Unreadable external checkpoint document")


def read_envelope_document(data: bytes) -> ExternalCheckpoint:
    """Wrap a bare Phase 8 signed checkpoint envelope as a lowest-trust document."""
    envelope = read_envelope(data)
    if not isinstance(envelope.payload, Checkpoint):
        raise AuthorityError(CHECKPOINT_MALFORMED, "Expected a signed checkpoint envelope")
    payload = envelope.payload
    return ExternalCheckpoint(
        format=FORMAT, format_version=1, ledger_id=payload.ledger_id,
        environment=payload.environment, policy_version=payload.policy_version,
        captured_at=payload.issued_at, checkpoint_envelope=envelope,
        checkpoint_sha256=digest_checkpoint_envelope(envelope),
        trust=TrustClaim(custody="local-state-directory", authentication="none",
                         operator_claims_independence=False),
        challenge=payload.challenge)


@dataclass(frozen=True)
class IndependentExpectation:
    """What the operator obtained through a channel the local state cannot control.

    Nothing here may be derived from the document being checked. A digest read
    out of the same backup that also holds the journal proves nothing.
    """

    document_sha256: str | None = None
    checkpoint_sha256: str | None = None
    challenge: str | None = None
    source: str = "unspecified"


# --- storage adapters ------------------------------------------------------------

class CheckpointStore(Protocol):
    """Read-only source of checkpoint documents. No adapter may write or transmit."""

    def describe(self) -> dict:
        ...

    def read(self) -> bytes:
        ...


@dataclass(frozen=True)
class MissingCheckpointStore:
    """The honest default: the operator has not configured a custodian."""

    reason: str = "No checkpoint custodian is configured"

    def describe(self) -> dict:
        return {"kind": "missing", "present": False, "reason": self.reason, "network_access": False}

    def read(self) -> bytes:
        raise AuthorityError(CHECKPOINT_MISSING, self.reason)


@dataclass(frozen=True)
class OperatorFileCheckpointStore:
    """A checkpoint file held by the operator outside the repository.

    Being outside the checkout is a *custody* property only. It does not make
    the document authentic; that requires an independently obtained digest.
    """

    path: Path
    require_outside: Path | None = None

    def describe(self) -> dict:
        return {"kind": "operator-file", "present": self.path.exists(), "path": str(self.path),
                "outside_repository": self.require_outside is not None, "network_access": False,
                "note": "External storage is custody, not authenticity"}

    @property
    def custody(self) -> Custody:
        """What this store can actually vouch for, independent of any claim."""
        return "operator-offline-file" if self.require_outside is not None else "local-state-directory"

    def read(self) -> bytes:
        target = regular_path(Path(self.path))
        if self.require_outside is not None:
            root = Path(self.require_outside).absolute()
            if target.is_relative_to(root):
                raise AuthorityError("trust_location",
                                     "A checkpoint custodian file must live outside the checkout")
        if not target.is_file():
            raise AuthorityError(CHECKPOINT_MISSING,
                                 "The configured checkpoint custodian file does not exist")
        return target.read_bytes()


@dataclass(frozen=True)
class ProtectedHistoryCheckpointStore:
    """Offline reader for a checkpoint materialised from a protected history.

    This adapter never contacts GitHub. The operator materialises the protected
    branch themselves (clone/fetch/export) into ``materialized_dir``; this
    project reads the resulting regular file and nothing else. The guarantee a
    protected branch provides - retained, access-controlled, independently
    reviewable history - depends on repository settings this project cannot
    configure or verify for itself.
    """

    materialized_dir: Path
    filename: str = "checkpoint.json"

    def describe(self) -> dict:
        return {"kind": "protected-history",
                "present": (Path(self.materialized_dir) / self.filename).is_file(),
                "materialized_dir": str(self.materialized_dir), "network_access": False,
                "requires_manual_materialization": True,
                "note": "No GitHub API is contacted; the operator materializes and protects the history"}

    @property
    def custody(self) -> Custody:
        return "protected-git-history"

    def read(self) -> bytes:
        target = regular_path(Path(self.materialized_dir) / self.filename)
        if not target.is_file():
            raise AuthorityError(CHECKPOINT_MISSING,
                                 "No checkpoint file is present in the materialised protected history")
        return target.read_bytes()


# --- verification ----------------------------------------------------------------

def _result(status, code, detail, trust_level="LOCAL_SNAPSHOT", **evidence) -> CheckpointVerification:
    return CheckpointVerification(status=status, code=code, trust_level=trust_level, detail=detail,
                                  evidence=evidence)


def _base_trust_level(custody: str) -> TrustLevel:
    if custody in {"operator-offline-file", "protected-git-history", "read-only-mirror"}:
        return "EXTERNAL_STORED"
    return "LOCAL_SIGNED"


def verify_external_checkpoint(*, document: ExternalCheckpoint | None,
                               document_bytes: bytes | None,
                               expectation: IndependentExpectation,
                               pin: TrustPin,
                               history: VerifiedHistory | None,
                               now: datetime,
                               max_age_seconds: int = 86400,
                               require_current_journal: bool = True,
                               emergency_stopped: bool = False,
                               custody: Custody | None = None) -> CheckpointVerification:
    """Verify one externally held checkpoint against the local authority state.

    The result is deliberately split into two questions:

    * is this document *independently authenticated*? (a digest/challenge the
      local state does not control), and
    * is it *current*? (signature, ledger, environment, registry revision and
      journal head all agree with the local state right now).

    ``custody`` is what the *store* can actually vouch for. A document's own
    custody claim is recorded as evidence but never upgrades the trust level:
    a document kept inside the authority state directory cannot serve as an
    external anchor, whatever it says about itself.

    Missing evidence yields BLOCKED or INCONCLUSIVE. Contradicted evidence
    yields FAIL. Only fully agreeing, freshly held evidence yields PASS.
    """
    at = clock(now)
    if emergency_stopped:
        return _result(BLOCKED, EMERGENCY_HOLD,
                       "An emergency publication stop is present; recovery requires owner review")

    if document is None:
        if document_bytes is None:
            return _result(BLOCKED, CHECKPOINT_MISSING,
                           "No external checkpoint document was supplied; a custodian action is required")
        try:
            document = read_checkpoint_document(document_bytes)
        except AuthorityError as error:
            return _result(FAIL, error.code, str(error))

    effective_custody = custody or document.trust.custody
    trust_level = _base_trust_level(effective_custody)

    # --- independent authentication ------------------------------------------------
    computed_document = digest_attestation(document)
    computed_checkpoint = digest_checkpoint_envelope(document.checkpoint_envelope)
    if expectation.document_sha256 is None and expectation.checkpoint_sha256 is None:
        return _result(BLOCKED, INDEPENDENT_EVIDENCE_MISSING,
                       "No independently obtained checkpoint digest was supplied; a stored document "
                       "alone cannot establish authenticity", trust_level,
                       document_sha256=computed_document)
    if expectation.document_sha256 is not None:
        if expectation.document_sha256 != computed_document:
            return _result(FAIL, EXPECTED_DIGEST_MISMATCH,
                           "The supplied document digest differs from the independently trusted digest",
                           trust_level, expected=expectation.document_sha256, observed=computed_document)
    elif expectation.checkpoint_sha256 != computed_checkpoint:
        return _result(FAIL, EXPECTED_DIGEST_MISMATCH,
                       "The supplied checkpoint digest differs from the independently trusted digest",
                       trust_level, expected=expectation.checkpoint_sha256, observed=computed_checkpoint)
    trust_level = "INDEPENDENTLY_AUTHENTICATED"

    # --- the signed checkpoint itself ----------------------------------------------
    envelope = document.checkpoint_envelope
    payload = envelope.payload
    if not isinstance(payload, Checkpoint):
        return _result(FAIL, CHECKPOINT_MALFORMED, "The document does not wrap a checkpoint payload",
                       trust_level)
    if effective_custody == "local-state-directory":
        # A document that lives beside the journal cannot be an external anchor.
        # Moving it elsewhere does not help; only a genuinely independent
        # custodian plus an out-of-band digest does.
        return _result(BLOCKED, CHECKPOINT_CUSTODY_INSUFFICIENT,
                       "The checkpoint is stored inside the authority state directory, so it cannot "
                       "act as an independent anchor. Place it with the custodian and supply its "
                       "digest out of band.", "LOCAL_SIGNED",
                       document_sha256=computed_document, claimed_custody=document.trust.custody)
    if payload.protocol != PROTOCOL or payload.version != 1:
        return _result(FAIL, UNSUPPORTED_PROTOCOL_VERSION,
                       f"Unsupported authority protocol {payload.protocol!r} version {payload.version!r}",
                       trust_level)
    if document.ledger_id != pin.ledger_id or payload.ledger_id != pin.ledger_id:
        return _result(FAIL, UNKNOWN_LEDGER, "The checkpoint belongs to a different authority ledger",
                       trust_level, expected=pin.ledger_id, observed=payload.ledger_id)
    if payload.environment != pin.environment or document.environment != pin.environment:
        return _result(FAIL, CROSS_ENVIRONMENT_REPLAY,
                       "The checkpoint environment does not match the verifying environment", trust_level,
                       expected=pin.environment, observed=payload.environment)
    if payload.policy_version != POLICY or document.policy_version != POLICY:
        return _result(FAIL, UNSUPPORTED_PROTOCOL_VERSION, "The checkpoint policy version is not supported",
                       trust_level, observed=payload.policy_version)
    if payload.signer_id != pin.owner_id or payload.key_id != pin.root_key.key_id:
        return _result(FAIL, UNKNOWN_SIGNER, "The checkpoint was not signed by the pinned current owner root",
                       trust_level, expected_signer=pin.owner_id, observed_signer=payload.signer_id)
    try:
        verify_signature(envelope, pin.root_key.public_key)
    except AuthorityError as error:
        return _result(FAIL, INVALID_SIGNATURE, str(error), trust_level)

    # --- challenge ------------------------------------------------------------------
    if expectation.challenge is not None and payload.challenge != expectation.challenge:
        return _result(FAIL, CHALLENGE_MISMATCH,
                       "The checkpoint is not for this independently obtained publication challenge",
                       trust_level)
    if document.challenge is not None and payload.challenge != document.challenge:
        return _result(FAIL, CHALLENGE_MISMATCH, "The custody statement challenge disagrees with the signature",
                       trust_level)

    # --- freshness ------------------------------------------------------------------
    if not instant(payload.issued_at) <= at < instant(payload.expires_at):
        return _result(FAIL, CHECKPOINT_STALE, "The checkpoint is expired or future-dated", trust_level,
                       issued_at=payload.issued_at, expires_at=payload.expires_at)
    age = (at - instant(payload.issued_at)).total_seconds()
    if age > max_age_seconds:
        return _result(FAIL, CHECKPOINT_STALE,
                       f"The checkpoint is older than the operator freshness policy ({max_age_seconds}s)",
                       trust_level, age_seconds=int(age), policy_seconds=max_age_seconds)
    if instant(document.captured_at) > at:
        return _result(FAIL, CHECKPOINT_STALE, "The custody capture timestamp is in the future", trust_level,
                       captured_at=document.captured_at)

    # --- local state comparison ------------------------------------------------------
    if history is None:
        return _result(INCONCLUSIVE, LOCAL_STATE_UNAVAILABLE,
                       "The local authority history is unavailable, so currency cannot be compared",
                       trust_level, checkpoint_sha256=computed_checkpoint)
    comparison = compare_checkpoint(history, payload)
    if not comparison.matched:
        code = CHECKPOINT_NOT_CURRENT if comparison.code == "checkpoint_not_current" else comparison.code
        if code == CHECKPOINT_NOT_CURRENT and not require_current_journal:
            code = CHECKPOINT_NOT_CURRENT
        return _result(FAIL, code, comparison.detail, trust_level, **comparison.evidence)

    if not instant(pin.root_key.active_at) <= at < instant(pin.root_key.expires_at):
        return _result(FAIL, OWNER_EXPIRED, "The pinned owner root is not currently valid", trust_level)

    return CheckpointVerification(
        status=PASS, code="checkpoint_current", trust_level="CURRENTLY_TRUSTED",
        detail="An independently authenticated, unexpired checkpoint agrees with the local journal head",
        independently_trusted=True, current=True,
        evidence={"document_sha256": computed_document, "checkpoint_sha256": computed_checkpoint,
                  "ledger_id": payload.ledger_id, "environment": payload.environment,
                  "event_count": payload.event_count, "registry_revision": payload.registry_revision,
                  "head_sha256": payload.head_sha256, "issued_at": payload.issued_at,
                  "expires_at": payload.expires_at, "custody": document.trust.custody,
                  "authentication": document.trust.authentication,
                  "expectation_source": expectation.source},
        publication_allowed=False)


def conflicting_checkpoints(documents) -> dict | None:
    """Detect two independently held checkpoints that disagree about the same ledger.

    Conflicting checkpoints mean the custodian channel itself is ambiguous. No
    single one of them may be treated as authoritative until the operator
    resolves the conflict.
    """
    seen: dict[str, dict] = {}
    for index, document in enumerate(documents or []):
        if document is None:
            continue
        payload = document.checkpoint_envelope.payload
        claim = {"event_count": payload.event_count, "head_sha256": payload.head_sha256,
                 "registry_revision": payload.registry_revision, "issued_at": payload.issued_at,
                 "document_sha256": digest_attestation(document)}
        previous = seen.get(document.ledger_id)
        if previous is None:
            seen[document.ledger_id] = {**claim, "index": index}
            continue
        if any(previous[field] != claim[field] for field in
               ("event_count", "head_sha256", "registry_revision", "issued_at")):
            return {"ledger_id": document.ledger_id, "first": previous, "second": claim}
    return None


def verify_checkpoint_set(*, documents, expectation: IndependentExpectation, pin: TrustPin,
                          history: VerifiedHistory | None, now: datetime,
                          max_age_seconds: int = 86400) -> dict:
    """Verify several independently held checkpoints and refuse an ambiguous set."""
    conflict = conflicting_checkpoints(documents)
    results = []
    for document in documents or []:
        if document is None:
            results.append(CheckpointVerification(
                status=BLOCKED, code=CHECKPOINT_MISSING, trust_level="LOCAL_SNAPSHOT",
                detail="A configured custodian supplied no document", evidence={}))
            continue
        results.append(verify_external_checkpoint(
            document=document, document_bytes=None, expectation=expectation, pin=pin,
            history=history, now=now, max_age_seconds=max_age_seconds))
    if conflict is not None:
        return {"status": FAIL, "code": CONFLICTING_CHECKPOINTS,
                "detail": "Independently held checkpoints disagree about the same ledger",
                "conflict": conflict, "results": [r.model_dump(mode="json") for r in results],
                "publication_allowed": False}
    trusted = [r for r in results if r.trusted]
    if not trusted:
        best = results[0] if results else None
        return {"status": best.status if best else BLOCKED,
                "code": best.code if best else CHECKPOINT_MISSING,
                "detail": best.detail if best else "No checkpoint custodian is configured",
                "results": [r.model_dump(mode="json") for r in results],
                "publication_allowed": False}
    return {"status": PASS, "code": "checkpoint_current",
            "detail": "At least one independently held checkpoint is current",
            "results": [r.model_dump(mode="json") for r in results],
            "publication_allowed": False}
