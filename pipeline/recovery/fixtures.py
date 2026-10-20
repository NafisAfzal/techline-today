"""Synthetic newsroom fixtures for recovery drills.

Every identity here is derived from a fixed, published seed and exists only
inside an isolated temporary directory. No drill may point one of these at a
real checkpoint, a real reviewer, a real publication or a real custodian. The
point of a drill is to prove the *tooling* refuses unsafe states, never to
claim that a production system was recovered.
"""

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pipeline.authority.ledger import append, load, replay
from pipeline.authority.protocol import (
    POLICY,
    PROTOCOL,
    ZERO,
    Admin,
    Binding,
    Checkpoint,
    Decision,
    Grant,
    Key,
    encode64,
    envelope_bytes,
    fingerprint,
    sign,
    stamp,
)
from pipeline.authority.registry import TrustPin

SYNTHETIC_NOW = datetime(2026, 10, 20, 0, 0, tzinfo=UTC)
SYNTHETIC_LEDGER = "synthetic-recovery-ledger"
SYNTHETIC_OWNER = "synthetic-recovery-owner"


def synthetic_private(name: str) -> Ed25519PrivateKey:
    """A deterministic, publicly known key. Safe because it is synthetic."""
    return Ed25519PrivateKey.from_private_bytes(
        hashlib.sha256(("SYNTHETIC-RECOVERY-FIXTURE-ONLY:" + name).encode()).digest())


def synthetic_key(name: str) -> Key:
    public = synthetic_private(name).public_key().public_bytes_raw()
    return Key(key_id=fingerprint(public), public_key=encode64(public), active_at=stamp(SYNTHETIC_NOW),
               expires_at=stamp(SYNTHETIC_NOW + timedelta(days=365)))


def synthetic_pin(ledger_id: str = SYNTHETIC_LEDGER, owner_id: str = SYNTHETIC_OWNER) -> TrustPin:
    return TrustPin(version=1, owner_id=owner_id, ledger_id=ledger_id,
                     environment="synthetic", policy_version=POLICY, synthetic=True,
                     root_key=synthetic_key("owner"))


def synthetic_binding(**changes) -> Binding:
    values = dict(source_id="news-wire", story_id="story-one", story_kind="NEWS",
                  content_sha256="a" * 64, source_sha256="b" * 64, rights_sha256="c" * 64,
                  language="en", language_sha256=ZERO, workflow="editorial")
    values.update(changes)
    return Binding(**values)


class SyntheticNewsroom:
    """A private, offline journal used only by recovery drills and their tests."""

    def __init__(self, root: Path, pin: TrustPin | None = None):
        self.root = Path(root)
        self.pin = pin or synthetic_pin()
        self.owner_name = "owner"

    def journal(self):
        return load(self.root)

    def history(self):
        return replay(self.journal(), self.pin, SYNTHETIC_NOW, mode="synthetic")

    def base(self, record_id, signer=None, key_name=None):
        journal = self.journal()
        return dict(protocol=PROTOCOL, version=1, environment="synthetic",
                    ledger_id=self.pin.ledger_id, policy_version=POLICY, record_id=record_id,
                    signer_id=signer or self.pin.owner_id,
                    key_id=synthetic_key(key_name or self.owner_name).key_id,
                    issued_at=stamp(SYNTHETIC_NOW), expires_at=stamp(SYNTHETIC_NOW + timedelta(days=1)),
                    sequence=len(journal.events) + 1, previous_sha256=journal.head_sha256)

    def store(self, record):
        return append(self.root, record, self.pin, SYNTHETIC_NOW, mode="synthetic")

    def admin(self, operation, target, *, replacement=None, permission=None):
        payload = Admin(**self.base("admin-" + str(len(self.journal().events) + 1)), kind="admin",
                        role="owner-admin", operation=operation, target_id=target,
                        key=synthetic_key(replacement) if replacement else None, grant=permission)
        envelope = sign(payload, synthetic_private(self.owner_name),
                        possession_key=synthetic_private(replacement) if replacement else None)
        self.store(envelope)
        if operation == "rotate_root":
            self.owner_name = replacement
        return envelope

    def appoint(self, name, role, *, decisions=None, workflows=None, languages=None):
        from pipeline.authority.protocol import CAPABILITIES

        self.admin("enroll", name, replacement=name)
        grant = Grant(grant_id="g-" + name, role=role, decisions=decisions or sorted(CAPABILITIES[role]),
                      sources=["news-wire"], stories=["*"], languages=languages or ["en"],
                      workflows=workflows or ["editorial"], active_at=stamp(SYNTHETIC_NOW),
                      expires_at=stamp(SYNTHETIC_NOW + timedelta(days=90)))
        self.admin("grant", name, permission=grant)
        return grant

    def decide(self, bound, to_state, signer, **changes):
        history = self.history()
        values = dict(**self.base("decision-" + str(len(self.journal().events) + 1), signer, signer),
                      kind="decision", role=history.registry.grants["g-" + signer][1].role,
                      grant_id="g-" + signer, registry_revision=history.registry.revision,
                      binding=bound, decision=to_state, from_state=history.state(bound),
                      to_state=to_state, evidence=["d" * 64], supersedes=None)
        values.update(changes)
        envelope = sign(Decision(**values), synthetic_private(signer))
        self.store(envelope)
        return envelope

    def publish(self, bound=None):
        bound = bound or synthetic_binding()
        self.decide(bound.model_copy(update={"workflow": "rights"}), "RIGHTS_APPROVED", "rights")
        for to_state, signer in [
            ("SOURCE_VALIDATED", "editor"), ("RIGHTS_ELIGIBLE", "rights"), ("DRAFT_READY", "editor"),
            ("FACT_CHECK_PENDING", "editor"), ("FACT_CHECKED", "fact"),
            ("EDITORIAL_APPROVAL_PENDING", "editor"), ("APPROVED", "editor"),
            ("PUBLICATION_ELIGIBLE", "publisher"), ("PUBLISHED", "publisher"),
        ]:
            self.decide(bound, to_state, signer)
        return bound

    def team(self):
        self.appoint("editor", "english-editor", workflows=["editorial", "source"])
        self.appoint("rights", "source-rights", workflows=["editorial", "rights", "source"])
        self.appoint("fact", "fact-checker")
        self.appoint("publisher", "publisher", workflows=["editorial", "translation", "source"],
                     languages=["en", "bn"])
        self.appoint("moderator", "suspension",
                     workflows=["editorial", "rights", "translation", "source"], languages=["en", "bn"])
        return self

    def checkpoint(self, *, challenge="synthetic-recovery-challenge", **changes):
        history = self.history()
        values = dict(**self.base("checkpoint"), kind="checkpoint", role="owner-admin",
                      head_sha256=history.journal.head_sha256, event_count=len(history.journal.events),
                      registry_revision=history.registry.revision, challenge=challenge)
        values["expires_at"] = stamp(SYNTHETIC_NOW + timedelta(hours=1))
        values.update(changes)
        return sign(Checkpoint(**values), synthetic_private(self.owner_name))

    def checkpoint_bytes(self, **changes) -> bytes:
        return envelope_bytes(self.checkpoint(**changes))
