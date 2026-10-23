"""Versioned Ed25519 envelopes with a deliberately narrow canonical JSON profile."""

import base64
import binascii
import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Annotated, Literal

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from nacl.bindings import crypto_core_ed25519_is_valid_point
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator, model_validator

from pipeline.strict_json import strict_json

PROTOCOL = "techline.editorial.authority/v1"
POLICY = "phase8-authority-v1"
DOMAIN = b"TECHLINE-TODAY\x00EDITORIAL-AUTHORITY\x00V1\x00"
ZERO = "0" * 64
MAX_RECORD = 64_000
Digest = Annotated[StrictStr, Field(pattern=r"^[a-f0-9]{64}$")]
Identifier = Annotated[StrictStr, Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,127}$")]
ScopeId = Annotated[StrictStr, Field(pattern=r"^(?:[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,127}|\*)$")]
Timestamp = Annotated[StrictStr, Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")]
Role = Literal["source-rights", "fact-checker", "english-editor", "native-bn", "publisher", "suspension"]
Workflow = Literal["editorial", "rights", "translation", "source", "research"]
RESEARCH_POLICY = "research-reference-v1"
RESEARCH_STAGES = (
    "RESEARCH_METADATA_APPROVED", "RESEARCH_EXTRACTIVE_APPROVED", "RESEARCH_FACTUAL_APPROVED",
    "RESEARCH_CLASSIFICATION_APPROVED", "RESEARCH_PUBLICATION_APPROVED",
)

# Only owner administration can create grants. Each reviewer role is independent.
CAPABILITIES = {
    "source-rights": frozenset({"RIGHTS_APPROVED", "RIGHTS_ELIGIBLE", "RIGHTS_REJECTED", "RIGHTS_REVOKED",
                                "RIGHTS_REVIEW_REQUIRED", "RIGHTS_EVIDENCE_RECORDED",
                                "RESEARCH_METADATA_APPROVED"}),
    "fact-checker": frozenset({"FACT_CHECKED", "RESEARCH_FACTUAL_APPROVED"}),
    "english-editor": frozenset({"SOURCE_VALIDATED", "DRAFT_READY", "FACT_CHECK_PENDING",
                                 "EDITORIAL_APPROVAL_PENDING", "APPROVED", "TECHNICALLY_VALIDATED",
                                 "EDITORIAL_REVIEW_REQUIRED", "RESEARCH_EXTRACTIVE_APPROVED",
                                 "RESEARCH_CLASSIFICATION_APPROVED"}),
    "native-bn": frozenset({"DRAFT_TRANSLATION", "LANGUAGE_REVIEW_PENDING", "NATIVE_REVIEW_COMPLETE",
                            "WITHDRAWN", "RESEARCH_BANGLA_APPROVED"}),
    "publisher": frozenset({"PUBLICATION_ELIGIBLE", "PUBLISHED", "APPROVED_TRANSLATION",
                            "PUBLISHED_TRANSLATION", "ELIGIBLE_FOR_ACTIVATION", "RESEARCH_PUBLICATION_APPROVED"}),
    "suspension": frozenset({"REJECTED", "SUSPENDED", "REVOKED", "CORRECTED", "RETRACTED",
                             "ARCHIVED", "WITHDRAWN", "RIGHTS_REVOKED", "TRANSLATION_WITHDRAWN",
                             "RESEARCH_REVOKED"}),
}
DENIALS = frozenset({"RIGHTS_REJECTED", "RIGHTS_REVOKED", "TRANSLATION_REJECTED",
                    "TRANSLATION_WITHDRAWN", "REJECTED", "SUSPENDED", "REVOKED", "CORRECTED",
                    "RETRACTED", "ARCHIVED", "WITHDRAWN", "RESEARCH_REVOKED"})


class AuthorityError(ValueError):
    """Stable diagnostic code; never include a signing key or raw evidence body."""

    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def instant(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
        raise AuthorityError("timestamp", "Use an exact UTC timestamp: YYYY-MM-DDTHH:MM:SSZ")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as error:
        raise AuthorityError("timestamp", "Timestamp contains an invalid calendar date") from error


def clock(value):
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise AuthorityError("clock", "Verification requires an explicit timezone-aware trusted clock")
    return value.astimezone(UTC)


def stamp(value):
    return clock(value).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical(value):
    """ASCII-only keys/values, bounded integers, no floats, sorted keys, no spaces.

    Not a general-purpose JCS implementation. Signed prose is represented by a
    digest instead. Reject unsupported types before encoding; never coerce them.
    """
    pending = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        if depth > 16:
            raise AuthorityError("encoding", "Canonical payload nesting exceeds 16")
        if isinstance(item, str):
            if any(not 32 <= ord(c) <= 126 for c in item):
                raise AuthorityError("encoding", "Signed fields require printable ASCII; bind prose by digest")
        elif type(item) is int:
            if not 0 <= item <= 2**53 - 1:
                raise AuthorityError("encoding", "Integer is outside the canonical profile")
        elif item is None or type(item) is bool:
            pass
        elif isinstance(item, dict):
            if any(type(k) is not str for k in item):
                raise AuthorityError("encoding", "Object keys must be strings")
            pending.extend((k, depth + 1) for k in item)
            pending.extend((v, depth + 1) for v in item.values())
        elif isinstance(item, list):
            pending.extend((v, depth + 1) for v in item)
        else:
            raise AuthorityError("encoding", "Unsupported canonical JSON type")
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode()


def fingerprint(raw_public_key):
    if not isinstance(raw_public_key, bytes) or len(raw_public_key) != 32:
        raise AuthorityError("key", "Ed25519 public keys must contain exactly 32 bytes")
    if not crypto_core_ed25519_is_valid_point(raw_public_key):
        raise AuthorityError("key_point", "Ed25519 public key must be canonical and in the main prime-order subgroup")
    return hashlib.sha256(raw_public_key).hexdigest()


def encode64(value):
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def decode64(value, length):
    try:
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise ValueError("Invalid alphabet")
        raw = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
        if len(raw) != length or encode64(raw) != value:
            raise ValueError("Noncanonical base64url")
        return raw
    except (ValueError, binascii.Error) as error:
        raise AuthorityError("encoding", "Invalid canonical base64url or byte length") from error


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    @field_validator("version", mode="before", check_fields=False)
    @classmethod
    def strict_schema_version(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("Schema version must be integer 1")
        return value


class Key(Model):
    key_id: Digest
    public_key: StrictStr
    active_at: Timestamp
    expires_at: Timestamp

    @model_validator(mode="after")
    def valid(self):
        if fingerprint(decode64(self.public_key, 32)) != self.key_id:
            raise ValueError("Public key fingerprint mismatch")
        if instant(self.active_at) >= instant(self.expires_at):
            raise ValueError("Key activation must precede expiry")
        return self


class Grant(Model):
    grant_id: Identifier
    role: Role
    decisions: list[Identifier] = Field(min_length=1, max_length=20)
    sources: list[Identifier] = Field(min_length=1, max_length=50)
    stories: list[ScopeId] = Field(min_length=1, max_length=100)
    languages: list[Literal["en", "bn"]] = Field(min_length=1, max_length=2)
    workflows: list[Workflow] = Field(min_length=1, max_length=5)
    active_at: Timestamp
    expires_at: Timestamp

    @model_validator(mode="after")
    def valid(self):
        for values in (self.decisions, self.sources, self.stories, self.languages, self.workflows):
            if len(values) != len(set(values)):
                raise ValueError("Duplicate grant scope")
        if not set(self.decisions) <= CAPABILITIES[self.role]:
            raise ValueError("Grant attempts role escalation")
        if self.role == "native-bn" and self.languages != ["bn"]:
            raise ValueError("Native Bangla grants require exactly the bn language")
        if self.role in {"english-editor", "fact-checker"} and self.languages != ["en"]:
            raise ValueError("English review grants require exactly the en language")
        if instant(self.active_at) >= instant(self.expires_at):
            raise ValueError("Grant activation must precede expiry")
        return self


class Common(Model):
    protocol: Literal["techline.editorial.authority/v1"]
    version: Literal[1]
    environment: Literal["synthetic", "production"]
    ledger_id: Identifier
    policy_version: Literal["phase8-authority-v1"]
    record_id: Identifier
    signer_id: Identifier
    key_id: Digest
    issued_at: Timestamp
    expires_at: Timestamp
    sequence: int = Field(ge=1, le=2001)
    previous_sha256: Digest

    @field_validator("version", mode="before")
    @classmethod
    def version_integer(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("Only strict integer version 1 is supported")
        return value

    @model_validator(mode="after")
    def times(self):
        if not 0 < (instant(self.expires_at) - instant(self.issued_at)).total_seconds() <= 366 * 86400:
            raise ValueError("Invalid record lifetime")
        return self


class Admin(Common):
    kind: Literal["admin"]
    role: Literal["owner-admin"]
    operation: Literal["enroll", "grant", "revoke_grant", "rotate_key", "retire_key", "revoke_key",
                       "suspend_reviewer", "reinstate_reviewer", "revoke_reviewer", "revoke_source", "rotate_root"]
    # A reinstatement is a fresh owner act; the new registry revision keeps all
    # signatures from the earlier suspension epoch inactive.
    target_id: Identifier
    key: Key | None
    grant: Grant | None

    @model_validator(mode="after")
    def shape(self):
        needs_key = self.operation in {"enroll", "rotate_key", "rotate_root"}
        needs_grant = self.operation == "grant"
        if (self.key is not None) != needs_key or (self.grant is not None) != needs_grant:
            raise ValueError("Administrative operation has missing or irrelevant fields")
        return self


class Binding(Model):
    source_id: Identifier
    story_id: Identifier
    story_kind: Literal["NEWS", "RESEARCH", "EVERGREEN", "REFERENCE", "SECURITY_ADVISORY", "OFFICIAL_RELEASE"]
    content_sha256: Digest
    source_sha256: Digest
    rights_sha256: Digest
    language: Literal["en", "bn"]
    language_sha256: Digest
    workflow: Workflow


class Decision(Common):
    kind: Literal["decision"]
    role: Role
    grant_id: Identifier
    registry_revision: int = Field(ge=1, le=2000)
    binding: Binding
    decision: Identifier
    from_state: Identifier
    to_state: Identifier
    evidence: list[Digest] = Field(min_length=1, max_length=20)
    supersedes: Identifier | None

    @model_validator(mode="after")
    def valid(self):
        if self.decision != self.to_state or self.decision not in CAPABILITIES[self.role]:
            raise ValueError("Decision is outside the stated role")
        if (instant(self.expires_at) - instant(self.issued_at)).total_seconds() > 30 * 86400:
            raise ValueError("Review decisions expire within 30 days")
        if len(set(self.evidence)) != len(self.evidence):
            raise ValueError("Duplicate evidence digest")
        return self


class Checkpoint(Common):
    kind: Literal["checkpoint"]
    role: Literal["owner-admin"]
    head_sha256: Digest
    event_count: int = Field(ge=1, le=2000)
    registry_revision: int = Field(ge=1, le=2000)
    challenge: Identifier

    @model_validator(mode="after")
    def lifetime(self):
        if (instant(self.expires_at) - instant(self.issued_at)).total_seconds() > 86400:
            raise ValueError("Checkpoint validity cannot exceed 24 hours")
        return self


class ResearchBinding(Binding):
    """Separate research scope without changing historical Binding wire bytes."""

    workflow: Literal["research"]
    research_policy: Literal["research-reference-v1"]
    publication_scope: Literal["metadata-extractive:en", "metadata-extractive:en-bn"]


class ResearchDecision(Decision):
    """Same signature, registry and ledger; explicitly typed research extension."""

    kind: Literal["research-decision"]
    binding: ResearchBinding
    review_checkpoint: Checkpoint
    checkpoint_signature: StrictStr
    checkpoint_sha256: Digest

    @model_validator(mode="after")
    def research_shape(self):
        allowed = {*RESEARCH_STAGES, "RESEARCH_BANGLA_APPROVED", "RESEARCH_REVOKED"}
        if self.decision not in allowed or self.binding.story_kind not in {"RESEARCH", "REFERENCE"}:
            raise ValueError("Research decisions require a research stage and research/reference classification")
        if self.decision != "RESEARCH_REVOKED" and self.binding.language != (
                "bn" if self.decision == "RESEARCH_BANGLA_APPROVED" else "en"):
            raise ValueError("Research stage and language disagree")
        if self.decision == "RESEARCH_REVOKED" and self.supersedes is None:
            raise ValueError("Research revocation must identify the exact decision being revoked")
        if self.binding.language == "bn" and self.binding.publication_scope != "metadata-extractive:en-bn":
            raise ValueError("Bangla review requires a scope including Bangla")
        decode64(self.checkpoint_signature, 64)
        if self.decision != "RESEARCH_REVOKED" and self.binding.rights_sha256 not in self.evidence:
            raise ValueError("Research review must reference its exact bound source-rights evidence digest")
        return self


class Envelope(Model):
    algorithm: Literal["Ed25519"]
    payload: Annotated[Admin | Decision | Checkpoint | ResearchDecision, Field(discriminator="kind")]
    signature: StrictStr
    proof: StrictStr | None

    @model_validator(mode="after")
    def wire(self):
        decode64(self.signature, 64)
        if self.proof is not None:
            decode64(self.proof, 64)
        canonical(self.model_dump(mode="json"))
        if len(canonical(self.model_dump(mode="json"))) > MAX_RECORD:
            raise ValueError("Signed record exceeds size limit")
        return self


def payload_bytes(payload):
    return DOMAIN + canonical(payload.model_dump(mode="json"))


def sign(payload, private_key, *, possession_key=None):
    """Caller supplies a key object; no key lookup, generation or network fallback."""
    if not isinstance(private_key, Ed25519PrivateKey):
        raise AuthorityError("algorithm", "Signing requires an Ed25519 key")
    raw = payload_bytes(payload)
    return Envelope(algorithm="Ed25519", payload=payload, signature=encode64(private_key.sign(raw)),
                    proof=encode64(possession_key.sign(raw)) if possession_key is not None else None)


def verify_signature(envelope, public_key, *, proof=False):
    public = decode64(public_key, 32)
    fingerprint(public)  # Reject neutral/small-order/noncanonical public points.
    try:
        VerifyKey(public).verify(payload_bytes(envelope.payload),
                                 decode64(envelope.proof if proof else envelope.signature, 64))
    except BadSignatureError as error:
        raise AuthorityError("signature", "Ed25519 signature verification failed") from error


def envelope_bytes(envelope):
    return canonical(envelope.model_dump(mode="json"))


def read_envelope(data):
    if not isinstance(data, bytes) or data.startswith(b"\xef\xbb\xbf"):
        raise AuthorityError("encoding", "Signed records require UTF-8 without a BOM")
    raw = data.removesuffix(b"\n")
    value = strict_json(raw, max_bytes=MAX_RECORD, max_depth=16, max_tokens=8000)
    envelope = Envelope.model_validate(value)
    if raw != envelope_bytes(envelope):
        raise AuthorityError("encoding", "Record is not in the exact canonical wire format")
    return envelope
