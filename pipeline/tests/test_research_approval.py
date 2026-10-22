"""Research adapter unit, integration and adversarial tests; synthetic identities only."""

import hashlib
import json
import shutil
from datetime import timedelta
from pathlib import Path

import pytest

from pipeline.authority.checkpoint import (
    IndependentExpectation,
    build_attestation,
    digest_attestation,
    verify_external_checkpoint,
)
from pipeline.authority.ledger import JOURNAL, journal_bytes, replay, stage
from pipeline.authority.protocol import (
    RESEARCH_STAGES,
    AuthorityError,
    Decision,
    ResearchDecision,
    canonical,
    envelope_bytes,
    read_envelope,
    sign,
)
from pipeline.authority.service import bind_story, load_authority
from pipeline.operations.article_fixture import bangla_fixture
from pipeline.recovery.fixtures import SYNTHETIC_NOW as NOW
from pipeline.recovery.fixtures import synthetic_private
from pipeline.research_approval import bind_research, evaluate_item, readiness, validate_decision
from pipeline.research_cli import main
from pipeline.research_demo import SyntheticResearchRoom, content, demonstrate

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def prepared(tmp_path):
    room = SyntheticResearchRoom(tmp_path / "room").team()
    story, sources, rights = content()
    bound = bind_research(story, sources[story.primary_source_id], rights, sources)
    record = room.prepared(bound, RESEARCH_STAGES[0], "rights")
    return room, story, sources, rights, bound, record


def test_synthetic_end_to_end():
    result = demonstrate()
    assert result["status"] == "PASS", result
    assert result["checks"]["complete_synthetic_workflow"]["existing_gate_passed"]
    assert not result["publication_allowed"] and not result["credentials_persisted"]


def test_canonical_wire_and_narrow_signed_scope(prepared):
    room, story, sources, rights, bound, record = prepared
    assert read_envelope(envelope_bytes(record)) == record
    assert record.payload.binding.publication_scope == "metadata-extractive:en"
    assert record.payload.review_checkpoint.head_sha256 == room.journal().head_sha256
    assert record.payload.binding.story_id == story.id
    assert validate_decision(room.history(), record, story, sources, rights, NOW, mode="synthetic")["signature_and_scope_valid"]
    with pytest.raises(AuthorityError):
        stage(room.journal(), record, room.pin, NOW)  # synthetic pin in real build


@pytest.mark.parametrize("field,value", [
    ("id", "another-canonical-item"), ("headline", "Changed synthetic summary for an adversarial test"),
    ("published_at", NOW - timedelta(days=3)), ("category", "ai"),
])
def test_changed_item_or_content_refused(prepared, field, value):
    room, story, sources, rights, _, record = prepared
    with pytest.raises(AuthorityError):
        validate_decision(room.history(), record, story.model_copy(update={field: value}), sources, rights,
                          NOW, mode="synthetic")


@pytest.mark.parametrize("field,value", [("publisher", "Forged publisher"), ("content_hash", "9" * 64),
                                         ("canonical_url", "https://example.com/different-source")])
def test_changed_source_refused(prepared, field, value):
    room, story, sources, rights, _, record = prepared
    changed = {sid: source.model_copy(update={field: value}) for sid, source in sources.items()}
    with pytest.raises(AuthorityError, match="exact item"):
        validate_decision(room.history(), record, story, changed, rights, NOW, mode="synthetic")


@pytest.mark.parametrize("change", [{}, {"publication": "exclude"}, {"publication": "allow", "scope": "Changed"}])
def test_missing_or_changed_rights_refused(prepared, change):
    room, story, sources, _, _, record = prepared
    with pytest.raises(AuthorityError):
        validate_decision(room.history(), record, story, sources, {"arxiv": change}, NOW, mode="synthetic")


def test_matching_digest_of_empty_rights_is_still_not_evidence(prepared):
    room, story, sources, _, _, _ = prepared
    bound = bind_research(story, sources[story.primary_source_id], {}, sources)
    record = room.prepared(bound, RESEARCH_STAGES[0], "rights")
    with pytest.raises(AuthorityError, match="rights_"):
        validate_decision(room.history(), record, story, sources, {}, NOW, mode="synthetic")


@pytest.mark.parametrize("field,value", [("signer_id", "unappointed-reviewer"), ("ledger_id", "another-ledger"),
                                         ("environment", "production"), ("key_id", "9" * 64),
                                         ("grant_id", "forged-grant"), ("registry_revision", 1)])
def test_forged_context_and_reviewer_refused(prepared, field, value):
    room, _, _, _, _, record = prepared
    payload = ResearchDecision.model_validate({**record.payload.model_dump(mode="json"), field: value})
    forged = sign(payload, synthetic_private("rights"))
    with pytest.raises(AuthorityError):
        stage(room.journal(), forged, room.pin, NOW, mode="synthetic")


def test_unsigned_expired_and_invalid_signature_refused(prepared):
    room, story, sources, rights, _, record = prepared
    with pytest.raises(ValueError):
        read_envelope(canonical(record.payload.model_dump(mode="json")))
    with pytest.raises(AuthorityError, match="signature"):
        validate_decision(room.history(), record.model_copy(update={"signature": "A" * 86}),
                          story, sources, rights, NOW, mode="synthetic")
    with pytest.raises(AuthorityError, match="validity"):
        validate_decision(room.history(), record, story, sources, rights, NOW + timedelta(days=2), mode="synthetic")
    with pytest.raises(AuthorityError, match="stale"):
        validate_decision(room.history(), record, story, sources, rights, NOW + timedelta(hours=2), mode="synthetic")


def test_out_of_role_and_ordinary_envelope_cannot_smuggle_research(prepared):
    room, _, _, _, bound, record = prepared
    with pytest.raises(ValueError):
        room.prepared(bound, RESEARCH_STAGES[0], "editor")
    raw = record.payload.model_dump(mode="json")
    for key in ("review_checkpoint", "checkpoint_signature", "checkpoint_sha256"):
        raw.pop(key)
    raw["binding"].pop("publication_scope")
    raw["binding"].pop("research_policy")
    raw["kind"] = "decision"
    smuggled = sign(Decision.model_validate(raw), synthetic_private("rights"))
    with pytest.raises(AuthorityError, match="typed research"):
        stage(room.journal(), smuggled, room.pin, NOW, mode="synthetic")


def test_duplicate_decision_and_checkpoint_replay_refused(prepared):
    room, _, _, _, bound, record = prepared
    room.store(record)
    with pytest.raises(AuthorityError):
        room.store(record)
    reused = room.prepared(bound, RESEARCH_STAGES[1], "editor", checkpoint=room.checkpoint(
        challenge=record.payload.review_checkpoint.challenge))
    with pytest.raises(AuthorityError, match="consumed"):
        room.store(reused)
    old = room.prepared(bound, RESEARCH_STAGES[1], "editor", checkpoint=room.checkpoint(event_count=1))
    with pytest.raises(AuthorityError):
        room.store(old)


def test_signed_supersession_invalidates_downstream_and_revocation_is_sticky(prepared):
    room, story, sources, rights, bound, record = prepared
    room.review_all(story, sources, rights)
    old = room.history().active(bound, RESEARCH_STAGES[0], NOW)
    update = room.prepared(bound, RESEARCH_STAGES[0], "rights", supersedes=old)
    room.store(update)
    history = room.history()
    assert history.active(bound, RESEARCH_STAGES[0], NOW) == update.payload.record_id
    assert all(not history.active(bound, name, NOW) for name in RESEARCH_STAGES[1:])
    room.store(room.prepared(bound, "RESEARCH_REVOKED", "moderator", supersedes=update.payload.record_id))
    assert not room.history().active(bound, RESEARCH_STAGES[0], NOW)
    with pytest.raises(AuthorityError, match="withdrawn"):
        room.store(room.prepared(bound, RESEARCH_STAGES[0], "rights"))
    assert not evaluate_item(story, sources, rights, authority=room.bundle(), now=NOW,
                             mode="synthetic")["synthetic_eligible"]


def test_reviewer_revocation_and_registry_epoch_invalidate_approvals(prepared):
    room, story, sources, rights, bound, record = prepared
    room.store(record)
    room.admin("revoke_grant", "g-rights")
    assert not room.history().active(bound, RESEARCH_STAGES[0], NOW)
    result = evaluate_item(story, sources, rights, authority=room.bundle(), now=NOW, mode="synthetic")
    assert any("grant" in reason for reason in result["reasons"])


def test_historical_decision_can_be_revoked_after_content_and_rights_change(prepared):
    room, story, sources, _, bound, record = prepared
    room.store(record)
    revoke = room.prepared(bound, "RESEARCH_REVOKED", "moderator", supersedes=record.payload.record_id)
    changed = story.model_copy(update={"headline": "Changed synthetic content after an earlier approval"})
    assert validate_decision(room.history(), revoke, changed, sources, {}, NOW,
                             mode="synthetic")["signature_and_scope_valid"]
    room.store(revoke)
    assert not room.history().active(bound, RESEARCH_STAGES[0], NOW)


def test_bangla_is_separate_and_translation_changes_invalidate_all_stages(prepared):
    room, story, sources, rights, bound, _ = prepared
    translated = bangla_fixture(story)
    new_binding = bind_research(translated, sources[story.primary_source_id], rights, sources)
    assert new_binding.content_sha256 != bound.content_sha256
    assert new_binding.publication_scope == "metadata-extractive:en-bn"
    room.review_all(translated, sources, rights)
    result = evaluate_item(translated, sources, rights, authority=room.bundle(), now=NOW, mode="synthetic")
    assert any("RESEARCH_BANGLA_APPROVED" in reason for reason in result["reasons"])
    bn = bind_research(translated, sources[story.primary_source_id], rights, sources, language="bn")
    room.store(room.prepared(bn, "RESEARCH_BANGLA_APPROVED", "native"))
    assert room.history().active(bn, "RESEARCH_BANGLA_APPROVED", NOW)
    assert not room.history().active(bound, RESEARCH_STAGES[0], NOW)


def test_research_stages_do_not_bypass_existing_editorial_or_rights_gate(prepared):
    room, story, sources, rights, _, _ = prepared
    room.review_all(story, sources, rights)
    before = evaluate_item(story, sources, rights, authority=room.bundle(), now=NOW, mode="synthetic")
    assert not before["synthetic_eligible"]
    assert any("missing_active_signed_rights_review" in reason for reason in before["reasons"])
    assert any("missing_active_signed_editorial_reviews" in reason for reason in before["reasons"])
    room.publish(bind_story(story, sources[story.primary_source_id], rights, sources=sources))
    assert evaluate_item(story, sources, rights, authority=room.bundle(), now=NOW, mode="synthetic")["synthetic_eligible"]
    assert not evaluate_item(story, sources, rights, authority=room.bundle(), now=NOW)["publication_allowed"]


def test_fabricated_currently_trusted_custody_never_grants_authority(prepared):
    room, _, _, _, _, _ = prepared
    cp = room.checkpoint()
    document = build_attestation(cp, custody="operator-offline-file", authentication="independently-signed",
                                 captured_at=NOW, challenge=cp.payload.challenge, verified_by="CURRENTLY_TRUSTED")
    result = verify_external_checkpoint(document=document, document_bytes=None,
                                        expectation=IndependentExpectation(document_sha256=digest_attestation(document),
                                                                           challenge=cp.payload.challenge,
                                                                           source="synthetic-test"),
                                        pin=room.pin, history=room.history(), now=NOW, custody="operator-offline-file")
    assert result.status == "BLOCKED" and not result.current and not result.independently_trusted


def test_real_loader_rejects_synthetic_pin_even_outside_checkout(prepared, tmp_path, monkeypatch):
    room, *_ = prepared
    pin = tmp_path / "synthetic-pin.json"
    pin.write_bytes(canonical(room.pin.model_dump(mode="json")))
    monkeypatch.setenv("TECHLINE_AUTHORITY_TRUST_FILE", str(pin))
    with pytest.raises(AuthorityError, match="synthetic"):
        load_authority(room.root)


def test_clean_checkout_cli_reports_zero_and_packets_are_unsigned(tmp_path, capsys, monkeypatch):
    from pipeline.models import Snapshot
    for name in ("TECHLINE_AUTHORITY_TRUST_FILE", "TECHLINE_EXTERNAL_CHECKPOINT_FILE"):
        monkeypatch.delenv(name, raising=False)
    for name in ("source-rights.json", "research-edition.json", "sources.yaml"):
        target = tmp_path / "config" / name
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(ROOT / "config" / name, target)
    story, sources, _ = content()
    edition = Snapshot(generated_at=NOW, last_successful_fetch_at=NOW, mode="live", stories=[story], sources=sources,
                       categories={}, digests=[], offers=[], model_releases=[])
    target = tmp_path / "content/generated/snapshot.json"
    target.parent.mkdir(parents=True)
    target.write_text(edition.model_dump_json(), encoding="utf-8")
    before = hashlib.sha256(target.read_bytes()).hexdigest()
    assert main(["--root", str(tmp_path), "report", "--output", ".cache/authority/outbox/readiness.json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["eligible_count"] == 0 and not result["publication_allowed"]
    assert result["checkpoint_custody"]["status"] == "BLOCKED"
    assert main(["--root", str(tmp_path), "packet", "--story", story.id,
                 "--output", ".cache/authority/outbox/item.json"]) == 0
    assert json.loads(capsys.readouterr().out)["unsigned"]
    packet = json.loads((tmp_path / ".cache/authority/outbox/item.json").read_bytes())
    with pytest.raises(ValueError):
        read_envelope(canonical(packet))
    assert before == hashlib.sha256(target.read_bytes()).hexdigest()
    assert not (tmp_path / JOURNAL).exists()
    assert not readiness(tmp_path, edition, {"arxiv": {}}, now=NOW)["eligible"]


def test_historical_journal_serialization_remains_unchanged(prepared):
    room, *_ = prepared
    wire = journal_bytes(room.journal())
    history = replay(room.journal(), room.pin, NOW, mode="synthetic")
    assert journal_bytes(history.journal) == wire
