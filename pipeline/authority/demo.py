"""Ephemeral offline demonstration: no credentials or authority survive the run."""

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pipeline.authority.ledger import Anchor, append, load, replay, verify_anchor
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


def demonstrate():
    at = datetime.now(UTC).replace(microsecond=0)
    # Synthetic identities exist only in memory and a TemporaryDirectory.
    owner, reviewer = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    def key(private):
        raw = private.public_key().public_bytes_raw()
        return Key(key_id=fingerprint(raw), public_key=encode64(raw), active_at=stamp(at),
                   expires_at=stamp(at + timedelta(days=30)))
    owner_key, reviewer_key = key(owner), key(reviewer)
    pin = TrustPin(version=1, owner_id="synthetic-owner", ledger_id="synthetic-demo", environment="synthetic",
                   policy_version=POLICY, synthetic=True, root_key=owner_key)
    with TemporaryDirectory(prefix="techline-synthetic-authority-") as directory:
        root = Path(directory)
        def common(record_id, signer, signing_key):
            journal = load(root)
            return dict(protocol=PROTOCOL, version=1, environment="synthetic", ledger_id=pin.ledger_id,
                        policy_version=POLICY, record_id=record_id, signer_id=signer, key_id=signing_key.key_id,
                        issued_at=stamp(at), expires_at=stamp(at + timedelta(hours=1)),
                        sequence=len(journal.events) + 1, previous_sha256=journal.head_sha256)
        def store(record):
            append(root, record, pin, at, mode="synthetic")
        store(sign(Admin(**common("enroll", pin.owner_id, owner_key), kind="admin", role="owner-admin",
                         operation="enroll", target_id="synthetic-editor", key=reviewer_key, grant=None),
                   owner, possession_key=reviewer))
        grant = Grant(grant_id="synthetic-editor-grant", role="english-editor", decisions=["SOURCE_VALIDATED"],
                      sources=["synthetic-wire"], stories=["synthetic-story"], languages=["en"],
                      workflows=["editorial"], active_at=stamp(at), expires_at=stamp(at + timedelta(days=1)))
        store(sign(Admin(**common("appoint", pin.owner_id, owner_key), kind="admin", role="owner-admin",
                         operation="grant", target_id="synthetic-editor", key=None, grant=grant), owner))
        bound = Binding(source_id="synthetic-wire", story_id="synthetic-story", story_kind="NEWS",
                        content_sha256="1" * 64, source_sha256="2" * 64, rights_sha256="3" * 64,
                        language="en", language_sha256=ZERO, workflow="editorial")
        store(sign(Decision(**common("review", "synthetic-editor", reviewer_key), kind="decision",
                            role="english-editor", grant_id=grant.grant_id, registry_revision=2, binding=bound,
                            decision="SOURCE_VALIDATED", from_state="DISCOVERED", to_state="SOURCE_VALIDATED",
                            evidence=["4" * 64], supersedes=None), reviewer))
        history = replay(load(root), pin, at, mode="synthetic")
        def checkpoint(history):
            values = common("checkpoint", pin.owner_id, owner_key)
            cp = sign(Checkpoint(**values, kind="checkpoint", role="owner-admin", head_sha256=history.journal.head_sha256,
                                 event_count=len(history.journal.events), registry_revision=history.registry.revision,
                                 challenge="synthetic-publication-challenge"), owner)
            raw = envelope_bytes(cp)
            return Anchor(raw, hashlib.sha256(raw).hexdigest(), "synthetic-publication-challenge")
        verify_anchor(history, checkpoint(history), at)
        accepted = bool(history.active(bound, "SOURCE_VALIDATED", at))
        mismatch_rejected = not history.active(bound.model_copy(update={"content_sha256": "5" * 64}),
                                                "SOURCE_VALIDATED", at)
        store(sign(Admin(**common("revoke", pin.owner_id, owner_key), kind="admin", role="owner-admin",
                         operation="revoke_grant", target_id=grant.grant_id, key=None, grant=None), owner))
        history = replay(load(root), pin, at, mode="synthetic")
        verify_anchor(history, checkpoint(history), at)
        return {"synthetic_only": True, "scoped_signature_accepted": accepted,
                "version_mismatch_rejected": mismatch_rejected,
                "revoked_grant_rejected": not history.active(bound, "SOURCE_VALIDATED", at),
                "publication_allowed": False, "production_authority_available": False,
                "credentials_persisted": False, "real_reviewers_appointed": False}
