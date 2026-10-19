"""Synthetic in-memory identities only. Never imported by production code."""

import hashlib
from datetime import UTC, datetime, timedelta

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pipeline.authority.protocol import (
    POLICY,
    PROTOCOL,
    ZERO,
    Admin,
    Binding,
    Grant,
    Key,
    encode64,
    fingerprint,
    stamp,
)
from pipeline.authority.registry import TrustPin

NOW = datetime(2026, 10, 20, 0, 0, tzinfo=UTC)


def private(name):
    return Ed25519PrivateKey.from_private_bytes(hashlib.sha256(("SYNTHETIC-PHASE8-TEST-ONLY:" + name).encode()).digest())


def key(name):
    public = private(name).public_key().public_bytes_raw()
    return Key(key_id=fingerprint(public), public_key=encode64(public), active_at=stamp(NOW),
               expires_at=stamp(NOW + timedelta(days=365)))


def pin():
    return TrustPin(version=1, owner_id="test-owner", ledger_id="synthetic-newsroom", environment="synthetic",
                    policy_version=POLICY, synthetic=True, root_key=key("owner"))


def common(record_id, signer="test-owner", key_name="owner", *, sequence=1, previous=ZERO, at=NOW):
    return dict(protocol=PROTOCOL, version=1, environment="synthetic", ledger_id="synthetic-newsroom",
                policy_version=POLICY, record_id=record_id, signer_id=signer, key_id=key(key_name).key_id,
                issued_at=stamp(at), expires_at=stamp(at + timedelta(days=1)), sequence=sequence,
                previous_sha256=previous)


def enrollment(name="editor", **kwargs):
    return Admin(**common("enroll-" + name, **kwargs), kind="admin", role="owner-admin", operation="enroll",
                 target_id=name, key=key(name), grant=None)


def grant(name="g-editor", role="english-editor", decisions=None, languages=None, workflows=None):
    return Grant(grant_id=name, role=role, decisions=decisions or ["APPROVED"], sources=["news-wire"],
                 stories=["*"], languages=languages or ["en"], workflows=workflows or ["editorial"],
                 active_at=stamp(NOW), expires_at=stamp(NOW + timedelta(days=90)))


def binding(**changes):
    return Binding(source_id="news-wire", story_id="story-one", story_kind="NEWS", content_sha256="a" * 64,
                   source_sha256="b" * 64, rights_sha256="c" * 64, language="en", language_sha256=ZERO,
                   workflow="editorial").model_copy(update=changes)


class Newsroom:
    """A private tmp_path journal; all roots, keys and checkpoints are synthetic."""

    def __init__(self, root):
        self.root, self.pin, self.owner_name = root, pin(), "owner"

    def journal(self):
        from pipeline.authority.ledger import load
        return load(self.root)

    def history(self):
        from pipeline.authority.ledger import replay
        return replay(self.journal(), self.pin, NOW, mode="synthetic")

    def base(self, record_id, signer="test-owner", key_name=None):
        journal = self.journal()
        return common(record_id, signer, key_name or self.owner_name, sequence=len(journal.events) + 1,
                      previous=journal.head_sha256)

    def store(self, record):
        from pipeline.authority.ledger import append
        return append(self.root, record, self.pin, NOW, mode="synthetic")

    def admin(self, operation, target, *, replacement=None, permission=None):
        from pipeline.authority.protocol import sign
        payload = Admin(**self.base("admin-" + str(len(self.journal().events) + 1)), kind="admin",
                        role="owner-admin", operation=operation, target_id=target,
                        key=key(replacement) if replacement else None, grant=permission)
        envelope = sign(payload, private(self.owner_name),
                        possession_key=private(replacement) if replacement else None)
        self.store(envelope)
        if operation == "rotate_root":
            self.owner_name = replacement
        return envelope

    def appoint(self, name, role, *, decisions=None, workflows=None, languages=None):
        from pipeline.authority.protocol import CAPABILITIES
        self.admin("enroll", name, replacement=name)
        self.admin("grant", name, permission=grant("g-" + name, role,
                   decisions or sorted(CAPABILITIES[role]), languages, workflows or ["editorial"]))

    def prepared(self, bound, to_state, signer, *, supersedes=None, **changes):
        from pipeline.authority.protocol import Decision, sign
        history = self.history()
        values = dict(**self.base("decision-" + str(len(self.journal().events) + 1), signer, signer),
                      kind="decision", role=history.registry.grants["g-" + signer][1].role,
                      grant_id="g-" + signer, registry_revision=history.registry.revision,
                      binding=bound, decision=to_state, from_state=history.state(bound), to_state=to_state,
                      evidence=["d" * 64], supersedes=supersedes)
        values.update(changes)
        return sign(Decision(**values), private(signer))

    def decide(self, bound, to_state, signer, **changes):
        record = self.prepared(bound, to_state, signer, **changes)
        self.store(record)
        return record

    def team(self):
        self.appoint("editor", "english-editor", workflows=["editorial", "source"])
        self.appoint("rights", "source-rights", workflows=["editorial", "rights", "source"])
        self.appoint("fact", "fact-checker")
        self.appoint("publisher", "publisher", workflows=["editorial", "translation", "source"],
                     languages=["en", "bn"])
        self.appoint("native", "native-bn", workflows=["translation"], languages=["bn"])
        self.appoint("moderator", "suspension", workflows=["editorial", "rights", "translation", "source"],
                     languages=["en", "bn"])
        return self

    def publish(self, bound):
        self.decide(bound.model_copy(update={"workflow": "rights"}), "RIGHTS_APPROVED", "rights")
        for to_state, signer in [
            ("SOURCE_VALIDATED", "editor"), ("RIGHTS_ELIGIBLE", "rights"), ("DRAFT_READY", "editor"),
            ("FACT_CHECK_PENDING", "editor"), ("FACT_CHECKED", "fact"),
            ("EDITORIAL_APPROVAL_PENDING", "editor"), ("APPROVED", "editor"),
            ("PUBLICATION_ELIGIBLE", "publisher"), ("PUBLISHED", "publisher"),
        ]:
            self.decide(bound, to_state, signer)

    def anchor(self, *, challenge="publication-1", **changes):
        from pipeline.authority.ledger import Anchor
        from pipeline.authority.protocol import Checkpoint, envelope_bytes, sign
        history = self.history()
        values = dict(**self.base("checkpoint"), kind="checkpoint", role="owner-admin",
                      head_sha256=history.journal.head_sha256, event_count=len(history.journal.events),
                      registry_revision=history.registry.revision, challenge=challenge)
        values["expires_at"] = stamp(NOW + timedelta(hours=1))
        values.update(changes)
        record = sign(Checkpoint(**values), private(self.owner_name))
        wire = envelope_bytes(record)
        return Anchor(wire, hashlib.sha256(wire).hexdigest(), challenge)
