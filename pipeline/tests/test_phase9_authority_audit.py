"""Independent synthetic attack exercises; never provisions production authority."""

import getpass
import io
import multiprocessing
from datetime import timedelta

import pytest

from pipeline.authority.cli import protected_key
from pipeline.authority.ledger import STOP, emergency_hold, empty, stage
from pipeline.authority.protocol import (
    AuthorityError,
    decode64,
    encode64,
    payload_bytes,
    sign,
    verify_signature,
)
from pipeline.authority.service import bind_story, status
from pipeline.models import Snapshot
from pipeline.publication_gate import evaluate_snapshot
from pipeline.tests.authority_support import NOW, Newsroom, enrollment, key, private
from pipeline.tests.test_phase6_editorial_gate import SID
from pipeline.tests.test_phase8_integration import RIGHTS, bundle, content


class MemoryNewsroom(Newsroom):
    """Exercise real journal staging/replay without disk for encoding attacks."""

    def __init__(self, root):
        super().__init__(root)
        self.current = empty()

    def journal(self):
        return self.current

    def store(self, record):
        self.current, event = stage(self.current, record, self.pin, NOW, mode="synthetic")
        return event


def test_snapshot_timestamp_cannot_choose_the_authority_verification_clock(tmp_path, monkeypatch):
    import pipeline.publication_gate as gate

    room = MemoryNewsroom(tmp_path).team()
    item, sources = content()
    room.publish(bind_story(item, sources[SID], RIGHTS))
    edition = Snapshot(mode="live", generated_at=NOW, last_successful_fetch_at=NOW,
                       categories={"research": {}}, stories=[item], sources=sources,
                       digests=[], offers=[], model_releases=[])
    evidence = bundle(room)
    assert evaluate_snapshot(edition, RIGHTS, authority=evidence, authority_mode="synthetic",
                             now=NOW)["publication_allowed"]

    class TrustedClock:
        @staticmethod
        def now(tz):
            return NOW + timedelta(days=2)

    monkeypatch.setattr(gate, "datetime", TrustedClock)
    assert not evaluate_snapshot(edition, RIGHTS, authority=evidence,
                                 authority_mode="synthetic")["publication_allowed"]


def test_signer_refuses_getpass_echo_fallback_even_when_tty_checks_pass(tmp_path, monkeypatch):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    key_file = tmp_path / "nonsecret-placeholder.pem"
    key_file.write_bytes(b"SYNTHETIC NONSECRET ENCRYPTED PRIVATE KEY PLACEHOLDER")
    key_file.chmod(0o600)
    attempts = []

    def unsafe_read(*args, **kwargs):
        attempts.append(True)
        return "synthetic-nonsecret-placeholder"

    def fallback(prompt):
        return getpass.fallback_getpass(prompt, stream=io.StringIO())

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stderr.isatty", lambda: True)
    monkeypatch.setattr(getpass, "getpass", fallback)
    monkeypatch.setattr(getpass, "_raw_input", unsafe_read)
    with pytest.raises(ValueError):
        protected_key(key_file, checkout)
    assert not attempts, "A failed private prompt must never attempt echoed input"


@pytest.mark.parametrize("bangla", [False, True])
def test_secondary_source_evidence_change_requires_full_factual_editorial_and_native_review(tmp_path, bangla):
    from pipeline.models import StoryTranslation
    from pipeline.publication_gate import evaluate
    from pipeline.tests.test_phase6_translation_governance import FakeTranslation
    from pipeline.translation import canonical_hash

    room = MemoryNewsroom(tmp_path).team()
    item, sources = content()
    other = "src_" + "b" * 20
    item = item.model_copy(deep=True)
    item.source_ids.append(other)
    item.key_facts[0].source_ids = [other]
    item.claim_map[0].source_ids = [other]
    sources[other] = sources[SID].model_copy(update={"id": other, "content_hash": "7" * 64,
                                                     "excerpt": "Distinct synthetic secondary evidence."})
    if bangla:
        item.translations["bn"] = StoryTranslation(language="bn", content=FakeTranslation().content.__dict__,
            canonical_hash=canonical_hash(item), cache_key="f" * 64, provider="synthetic-test",
            model="synthetic-test", generated_at=NOW, review_status="automated")

    def bound(source_id, **kwargs):
        return bind_story(item, sources[source_id], RIGHTS, sources=sources, **kwargs)

    room.publish(bound(SID))
    room.decide(bound(other, workflow="rights"), "RIGHTS_APPROVED", "rights")
    if bangla:
        translated = bound(SID, workflow="translation", language="bn")
        for state, actor in [("DRAFT_TRANSLATION", "native"), ("LANGUAGE_REVIEW_PENDING", "native"),
                             ("NATIVE_REVIEW_COMPLETE", "native"), ("APPROVED_TRANSLATION", "publisher"),
                             ("PUBLISHED_TRANSLATION", "publisher")]:
            room.decide(translated, state, actor)
    assert evaluate(item, sources, RIGHTS, authority=bundle(room), authority_mode="synthetic",
                    now=NOW)["publication_allowed"]
    sources[other] = sources[other].model_copy(update={"content_hash": "8" * 64,
        "excerpt": "Changed secondary evidence after the factual and editorial reviews."})
    room.decide(bound(other, workflow="rights"), "RIGHTS_APPROVED", "rights")
    result = evaluate(item, sources, RIGHTS, authority=bundle(room), authority_mode="synthetic", now=NOW)
    assert not result["publication_allowed"]
    assert "editorial_approval" in result["denied_dimensions"]
    if bangla:
        assert "language_review" in result["denied_dimensions"]
    room.publish(bound(SID))
    if bangla:
        translated = bound(SID, workflow="translation", language="bn")
        for state, actor in [("DRAFT_TRANSLATION", "native"), ("LANGUAGE_REVIEW_PENDING", "native"),
                             ("NATIVE_REVIEW_COMPLETE", "native"), ("APPROVED_TRANSLATION", "publisher"),
                             ("PUBLISHED_TRANSLATION", "publisher")]:
            room.decide(translated, state, actor)
    assert evaluate(item, sources, RIGHTS, authority=bundle(room), authority_mode="synthetic",
                    now=NOW)["publication_allowed"]


def test_protocol_signatures_interoperate_with_an_independent_signing_library():
    from nacl.signing import SigningKey

    payload = enrollment()
    envelope = sign(payload, private("owner"), possession_key=private("editor"))
    independent = SigningKey(private("owner").private_bytes_raw()).sign(payload_bytes(payload)).signature
    assert decode64(envelope.signature, 64) == independent
    verify_signature(envelope, key("owner").public_key)
    altered = SigningKey(private("owner").private_bytes_raw()).sign(b"OTHER-DOMAIN" + payload_bytes(payload))
    with pytest.raises(AuthorityError, match="verification failed"):
        verify_signature(envelope.model_copy(update={"signature": encode64(altered.signature)}),
                         key("owner").public_key)


def test_noncanonical_ed25519_scalar_is_rejected_by_actual_verifier():
    envelope = sign(enrollment(), private("owner"), possession_key=private("editor"))
    raw = decode64(envelope.signature, 64)
    order = 2**252 + 27742317777372353535851937790883648493
    altered = raw[:32] + (int.from_bytes(raw[32:], "little") + order).to_bytes(32, "little")
    with pytest.raises(AuthorityError, match="verification failed"):
        verify_signature(envelope.model_copy(update={"signature": encode64(altered)}), key("owner").public_key)


@pytest.mark.parametrize("mutation", ["missing-set", "missing-item", "wrong-map-id", "selected-version-disagrees"])
def test_multisource_binding_rejects_partial_or_contradictory_evidence(mutation):
    item, sources = content()
    other = "src_" + "b" * 20
    item = item.model_copy(update={"source_ids": [SID, other]})
    sources[other] = sources[SID].model_copy(update={"id": other})
    selected = sources[SID]
    if mutation == "missing-set":
        sources = None
    elif mutation == "missing-item":
        sources.pop(other)
    elif mutation == "wrong-map-id":
        sources[other] = selected
    else:
        selected = selected.model_copy(update={"content_hash": "9" * 64})
    with pytest.raises(AuthorityError, match="source"):
        bind_story(item, selected, RIGHTS, sources=sources)


def _hold_synthetic_writer(root, ready, finish):
    from pipeline.generation import writer

    with writer(root):
        ready.set()
        finish.wait(timeout=30)


def test_killed_writer_leaves_a_blocking_lock_and_emergency_stop_still_works(tmp_path):
    context = multiprocessing.get_context("spawn")
    ready, finish = context.Event(), context.Event()
    process = context.Process(target=_hold_synthetic_writer, args=(tmp_path, ready, finish), daemon=True)
    process.start()
    try:
        assert ready.wait(timeout=10), "Synthetic writer did not reach the crash boundary"
        process.kill()
        process.join(timeout=10)
        assert not process.is_alive()
        lock = tmp_path / ".cache/pipeline-writer.lock"
        assert lock.exists()
        assert status(tmp_path, NOW)["status"] == "BLOCKED"
        emergency_hold(tmp_path, "Synthetic process crash", NOW)
        first = (tmp_path / STOP).read_bytes()
        assert emergency_hold(tmp_path, "Preserve the first denial", NOW)["already_held"]
        assert (tmp_path / STOP).read_bytes() == first and lock.exists()
    finally:
        if process.is_alive():
            process.kill()
            process.join(timeout=10)
        process.close()
