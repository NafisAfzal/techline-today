import hashlib
from dataclasses import replace
from datetime import timedelta

import pytest

from pipeline.authority.ledger import (
    JOURNAL,
    STOP,
    decode_journal,
    emergency_hold,
    journal_bytes,
    replay,
    verify_anchor,
)
from pipeline.authority.protocol import AuthorityError, canonical, sign
from pipeline.tests.authority_support import NOW, Newsroom, binding, key, private


@pytest.fixture
def room(tmp_path):
    return Newsroom(tmp_path).team()


def test_complete_scoped_editorial_path_and_independent_checkpoint(room):
    bound = binding()
    room.publish(bound)
    history = room.history()
    assert history.state(bound) == "PUBLISHED"
    for state in ["FACT_CHECKED", "APPROVED", "PUBLISHED"]:
        assert history.active(bound, state, NOW)
    verify_anchor(history, room.anchor(), NOW)
    assert history.active(bound.model_copy(update={"workflow": "rights"}), "RIGHTS_APPROVED", NOW)


@pytest.mark.parametrize("field,value", [
    ("source_id", "other-source"), ("story_id", "other-story"), ("language", "bn"),
    ("content_sha256", "1" * 64), ("source_sha256", "2" * 64), ("language_sha256", "3" * 64),
    ("rights_sha256", "4" * 64), ("workflow", "translation"), ("story_kind", "RESEARCH"),
])
def test_approval_is_not_reusable_across_any_binding_dimension(room, field, value):
    bound = binding()
    room.publish(bound)
    assert room.history().active(bound.model_copy(update={field: value}), "PUBLISHED", NOW) is None


@pytest.mark.parametrize("field,value", [
    ("grant_id", "unknown-parent"), ("registry_revision", 1), ("role", "source-rights"),
    ("from_state", "APPROVED"), ("key_id", key("fact").key_id),
    ("binding", binding(source_id="other-source")),
    ("binding", binding(language="bn")),
    ("environment", "production"), ("ledger_id", "other-workflow"),
])
def test_invalid_authorization_or_prior_state_is_rejected(room, field, value):
    with pytest.raises(ValueError):
        record = room.prepared(binding(), "SOURCE_VALIDATED", "editor", **{field: value})
        room.store(record)


def test_conflicting_concurrent_decisions_are_not_lost_updates(room):
    first = room.prepared(binding(), "SOURCE_VALIDATED", "editor")
    second = room.prepared(binding(story_id="story-two"), "SOURCE_VALIDATED", "editor")
    room.store(first)
    with pytest.raises(AuthorityError, match="Journal changed"):
        room.store(second)
    assert len(room.history().decisions) == 1


@pytest.mark.parametrize("operation,target", [
    ("revoke_reviewer", "editor"), ("suspend_reviewer", "editor"),
    ("retire_key", key("editor").key_id), ("revoke_key", key("editor").key_id),
    ("revoke_grant", "g-editor"), ("revoke_source", "news-wire"),
])
def test_administrative_revocation_invalidates_earlier_approval(room, operation, target):
    room.publish(binding())
    old_anchor = room.anchor()
    room.admin(operation, target)
    history = room.history()
    assert history.active(binding(), "APPROVED", NOW) is None
    assert history.active(binding(), "PUBLISHED", NOW) is None
    with pytest.raises(AuthorityError, match="truncated, ahead"):
        verify_anchor(history, old_anchor, NOW)
    verify_anchor(history, room.anchor(), NOW)


def test_rights_revocation_cannot_be_undone_by_replayed_or_fresh_approval(room):
    rights = binding(workflow="rights")
    old = room.prepared(rights, "RIGHTS_APPROVED", "rights")
    room.store(old)
    room.decide(rights, "RIGHTS_REVOKED", "rights", supersedes=old.payload.record_id)
    assert room.history().blocked(binding()) == "rights_rejected_or_revoked"
    with pytest.raises(AuthorityError):
        room.store(old)
    with pytest.raises(AuthorityError):
        room.decide(rights, "RIGHTS_APPROVED", "rights")


def test_retraction_and_correction_survive_registry_changes(room):
    bound = binding()
    room.publish(bound)
    published = room.history().active(bound, "PUBLISHED", NOW)
    room.decide(bound, "CORRECTED", "moderator", supersedes=published)
    assert room.history().active(bound, "PUBLISHED", NOW) is None
    room.admin("revoke_grant", "g-fact")
    assert room.history().blocked(bound)
    assert room.history().blocked(binding(content_sha256="f" * 64)) is None
    room.decide(binding(content_sha256="f" * 64), "RETRACTED", "moderator")
    assert room.history().blocked(binding(content_sha256="e" * 64))


def test_correction_cannot_supersede_some_other_story(room):
    room.decide(binding(story_id="other"), "SOURCE_VALIDATED", "editor")
    with pytest.raises(AuthorityError, match="exact evidence binding"):
        room.decide(binding(), "CORRECTED", "moderator", supersedes=room.history().decisions[-1].payload.record_id)


def test_key_loss_rotation_requires_owner_and_new_key_possession(room):
    room.publish(binding())
    room.admin("rotate_key", "editor", replacement="editor-new")
    assert room.history().registry.reviewers["editor"]["key_id"] == key("editor-new").key_id
    assert room.history().active(binding(), "APPROVED", NOW) is None
    with pytest.raises(AuthorityError, match="retired"):
        room.decide(binding(), "SOURCE_VALIDATED", "editor")


def test_owner_root_rotation_preserves_chain_and_retires_old_root(room):
    room.admin("rotate_root", "test-owner", replacement="owner-new")
    verify_anchor(room.history(), room.anchor(), NOW)
    record = room.admin("revoke_source", "source-x")
    forged = sign(record.payload.model_copy(update={"key_id": key("owner").key_id}), private("owner"))
    with pytest.raises(AuthorityError, match="current owner"):
        room.history().registry.apply(forged)


def test_expiration_is_checked_at_publication_time(room):
    room.publish(binding())
    assert room.history().active(binding(), "PUBLISHED", NOW + timedelta(days=2)) is None
    with pytest.raises(AuthorityError, match="stale"):
        verify_anchor(room.history(), room.anchor(), NOW + timedelta(hours=2))


def test_self_consistent_older_backup_is_rejected_by_independent_anchor(room):
    room.publish(binding())
    old = room.journal()
    room.admin("revoke_source", "news-wire")
    old_history = replay(old, room.pin, NOW, mode="synthetic")
    with pytest.raises(AuthorityError, match="truncated, ahead"):
        verify_anchor(old_history, room.anchor(), NOW)


@pytest.mark.parametrize("mutation", [
    lambda a: replace(a, expected_sha256="f" * 64),
    lambda a: replace(a, expected_challenge="other-publication"),
    lambda a: None,
])
def test_anchor_must_be_independent_exact_and_for_this_publication(room, mutation):
    with pytest.raises(AuthorityError):
        verify_anchor(room.history(), mutation(room.anchor()), NOW)


def test_recomputed_hash_chain_does_not_forge_signatures(room):
    data = room.journal().model_dump(mode="json")
    data["events"][-1]["record"]["payload"]["target_id"] = "attacker"
    previous = data["events"][-1]
    previous["event_sha256"] = hashlib.sha256(canonical({k: v for k, v in previous.items()
                                                       if k != "event_sha256"})).hexdigest()
    data["head_sha256"] = previous["event_sha256"]
    with pytest.raises(AuthorityError, match="verification failed"):
        replay(decode_journal(canonical(data)), room.pin, NOW, mode="synthetic")


def test_interrupted_atomic_replace_keeps_old_complete_history(room, monkeypatch):
    import pipeline.filesystem
    before = (room.root / JOURNAL).read_bytes()
    record = room.prepared(binding(), "SOURCE_VALIDATED", "editor")
    def interrupted_replace(*args, **kwargs):
        raise PermissionError("Synthetic Windows sharing violation before replacement")
    monkeypatch.setattr(pipeline.filesystem.Path, "replace", interrupted_replace)
    with pytest.raises(PermissionError):
        room.store(record)
    assert (room.root / JOURNAL).read_bytes() == before
    assert not (room.root / ".cache/pipeline-writer.lock").exists()
    assert not list((room.root / ".cache/authority").glob("*.tmp"))


def test_missing_history_and_corrupt_journal_refused(room):
    data = room.journal().model_dump(mode="json")
    data["events"].pop(0)
    with pytest.raises(ValueError):
        decode_journal(canonical(data))
    with pytest.raises(ValueError):
        decode_journal(b'{"version":1,"events":')


def test_generation_recovery_barrier_and_lock_are_respected(room):
    (room.root / ".cache/pipeline-transaction.json").write_text("{}")
    with pytest.raises(ValueError, match="Interrupted generation"):
        room.store(room.prepared(binding(), "SOURCE_VALIDATED", "editor"))
    (room.root / ".cache/pipeline-transaction.json").unlink()
    lock = room.root / ".cache/pipeline-writer.lock"
    lock.write_text("interrupted owner process; inspect manually")
    with pytest.raises(FileExistsError):
        room.store(room.prepared(binding(), "SOURCE_VALIDATED", "editor"))
    assert lock.exists()


def test_emergency_hold_needs_neither_keys_nor_a_valid_journal(tmp_path):
    path = tmp_path / JOURNAL
    path.parent.mkdir(parents=True)
    path.write_text("corrupt")
    emergency_hold(tmp_path, "Withdraw exposure while owner is unavailable", NOW)
    before = (tmp_path / STOP).read_bytes()
    assert emergency_hold(tmp_path, "Second reason cannot erase the first denial", NOW)["already_held"]
    assert (tmp_path / STOP).read_bytes() == before


def test_no_synthetic_fallback_in_production(room):
    with pytest.raises(AuthorityError, match="forbidden in production"):
        replay(room.journal(), room.pin, NOW)


def test_translation_uses_existing_lifecycle_and_is_version_bound(room):
    bound = binding(workflow="translation", language="bn", language_sha256="e" * 64)
    for state, actor in [("DRAFT_TRANSLATION", "native"), ("LANGUAGE_REVIEW_PENDING", "native"),
                         ("NATIVE_REVIEW_COMPLETE", "native"), ("APPROVED_TRANSLATION", "publisher"),
                         ("PUBLISHED_TRANSLATION", "publisher")]:
        room.decide(bound, state, actor)
    assert room.history().active(bound, "NATIVE_REVIEW_COMPLETE", NOW)
    assert not room.history().active(bound.model_copy(update={"content_sha256": "f" * 64}),
                                     "NATIVE_REVIEW_COMPLETE", NOW)
    room.decide(bound, "WITHDRAWN", "native")
    assert not room.history().active(bound, "NATIVE_REVIEW_COMPLETE", NOW)


def test_owner_reinstatement_never_reactivates_old_approvals(room):
    room.publish(binding())
    room.admin("suspend_reviewer", "editor")
    room.admin("rotate_key", "editor", replacement="editor-replacement")
    room.admin("reinstate_reviewer", "editor")
    assert not room.history().active(binding(), "APPROVED", NOW)
    assert room.history().state(binding()) == "DISCOVERED"


def test_expired_grant_and_key_have_actionable_denials(room):
    room.publish(binding())
    record = room.history().decisions[-1]
    with pytest.raises(AuthorityError, match="Signing key is not currently active"):
        room.history().registry.authorize(record, NOW + timedelta(days=366))
    with pytest.raises(AuthorityError, match="authorization is not active"):
        room.history().registry.authorize(record, NOW + timedelta(days=91))


def test_real_concurrent_writers_preserve_exactly_one_transaction(room):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    records = [room.prepared(binding(story_id=story), "SOURCE_VALIDATED", "editor")
               for story in ["story-a", "story-b"]]
    barrier = Barrier(2)
    def write(record):
        barrier.wait(timeout=10)
        try:
            room.store(record)
            return True
        except (FileExistsError, AuthorityError):
            return False
    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(write, records))
    assert sum(results) == 1
    assert len(room.history().decisions) == 1


def test_fault_after_replacement_is_recovered_by_reading_the_committed_head(room, monkeypatch):
    import pipeline.filesystem
    before = room.journal().head_sha256
    old_anchor = room.anchor()
    def interrupted_sync(*args):
        raise OSError("Synthetic interruption after replacement, before directory sync")
    monkeypatch.setattr(pipeline.filesystem, "sync_directory", interrupted_sync)
    with pytest.raises(OSError):
        room.decide(binding(), "RETRACTED", "moderator")
    after = room.history()
    assert after.journal.head_sha256 != before
    assert after.blocked(binding())
    with pytest.raises(AuthorityError, match="truncated, ahead"):
        verify_anchor(after, old_anchor, NOW)


def test_signed_source_onboarding_uses_its_original_lifecycle(room):
    from pipeline.authority.service import AuthorityBundle, bind_candidate
    from pipeline.source_onboarding import authenticated_review
    from pipeline.tests.test_phase6_source_onboarding import candidate
    proposal = candidate(candidate_id="news-wire")
    bound = bind_candidate(proposal)
    for target, actor in [("TECHNICALLY_VALIDATED", "editor"), ("RIGHTS_REVIEW_REQUIRED", "rights"),
                          ("RIGHTS_EVIDENCE_RECORDED", "rights"), ("EDITORIAL_REVIEW_REQUIRED", "editor"),
                          ("ELIGIBLE_FOR_ACTIVATION", "publisher")]:
        room.decide(bound, target, actor)
    bundle = AuthorityBundle(canonical(room.pin.model_dump(mode="json")), journal_bytes(room.journal()),
                             room.anchor(), mode="synthetic")
    report = authenticated_review(proposal, bundle, NOW, mode="synthetic")
    assert report["rights_evidence_recorded"] and report["eligible_for_activation"]
    assert not report["activation_allowed"]
