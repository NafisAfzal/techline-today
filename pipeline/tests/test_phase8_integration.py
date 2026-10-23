import json
from datetime import timedelta

import pytest

from pipeline.authority.cli import main
from pipeline.authority.ledger import STOP, emergency_hold, journal_bytes
from pipeline.authority.protocol import AuthorityError, canonical
from pipeline.authority.service import AuthorityBundle, bind_story, load_authority, status
from pipeline.editorial_workflow import load_ledger, record
from pipeline.publication_gate import evaluate
from pipeline.tests.authority_support import NOW, Newsroom, key
from pipeline.tests.test_phase6_editorial_gate import SID, source, story

RIGHTS = {"news-wire": {"publication": "allow", "license": "CC-BY-4.0",
                        "license_url": "https://creativecommons.org/licenses/by/4.0/",
                        "scope": "Synthetic test permission only"}}


def content():
    item = source(source_registry_id="news-wire", source_type="rss", category="ai")
    item_story = story()
    return item_story, {SID: item}


def bundle(room):
    return AuthorityBundle(canonical(room.pin.model_dump(mode="json")), journal_bytes(room.journal()),
                           room.anchor(), mode="synthetic")


@pytest.fixture
def prepared(tmp_path):
    room = Newsroom(tmp_path).team()
    item, sources = content()
    bound = bind_story(item, sources[SID], RIGHTS)
    room.publish(bound)
    return room, item, sources, bound


def test_existing_composite_gate_accepts_only_complete_synthetic_authority(prepared):
    room, item, sources, _ = prepared
    result = evaluate(item, sources, RIGHTS, authority=bundle(room), authority_mode="synthetic", now=NOW)
    assert result["publication_allowed"], result
    assert result["ai_submission_allowed"] is False
    # The same evidence cannot authorize a real-environment build/evaluation.
    assert not evaluate(item, sources, RIGHTS, authority=bundle(room), now=NOW)["publication_allowed"]
    assert not evaluate(item, sources, RIGHTS, now=NOW, require_approval=False)["publication_allowed"]


@pytest.mark.parametrize("field,value", [
    ("headline", "Changed evidence invalidates signed editorial decisions"),
    ("published_at", NOW - timedelta(hours=1)), ("updated_at", NOW - timedelta(minutes=1)),
])
def test_content_version_changes_invalidate_real_gate(prepared, field, value):
    room, item, sources, _ = prepared
    changed = item.model_copy(update={field: value})
    assert not evaluate(changed, sources, RIGHTS, authority=bundle(room), authority_mode="synthetic",
                        now=NOW)["publication_allowed"]


def test_changed_rights_or_source_identity_invalidates_real_gate(prepared):
    room, item, sources, _ = prepared
    for changed_sources, changed_rights in [
        ({SID: sources[SID].model_copy(update={"content_hash": "8" * 64})}, RIGHTS),
        (sources, {"news-wire": {**RIGHTS["news-wire"], "scope": "Changed permission evidence"}}),
        (sources, {"news-wire": {**RIGHTS["news-wire"], "publication": "exclude"}}),
    ]:
        assert not evaluate(item, changed_sources, changed_rights, authority=bundle(room),
                            authority_mode="synthetic", now=NOW)["publication_allowed"]


def test_local_unprivileged_retraction_still_overrides_signed_publication(prepared):
    room, item, sources, _ = prepared
    record(item.id, "DISCOVERED", "RETRACTED", actor="local-operator", now=NOW,
           reason="Synthetic risk reduction", retraction_reason="Independent concern", root=room.root)
    result = evaluate(item, sources, RIGHTS, authority=bundle(room), authority_mode="synthetic", now=NOW,
                      editorial_ledger=load_ledger(room.root))
    assert not result["publication_allowed"]


def test_fake_editable_approval_fields_do_not_authorize_anything():
    item, sources = content()
    forged = item.model_copy(update={"approved": True, "reviewer": "owner", "publication_allowed": True})
    assert not evaluate(forged, sources, RIGHTS, now=NOW)["publication_allowed"]


def test_missing_checkpoint_keeps_valid_signatures_inactive(prepared):
    room, item, sources, _ = prepared
    unanchored = AuthorityBundle(canonical(room.pin.model_dump(mode="json")), journal_bytes(room.journal()),
                                None, mode="synthetic")
    result = evaluate(item, sources, RIGHTS, authority=unanchored, authority_mode="synthetic", now=NOW)
    assert not result["publication_allowed"]
    assert any("checkpoint_missing" in reason for reason in result["dimensions"][2]["reasons"])


def test_old_ledger_with_current_trusted_checkpoint_is_not_publishable(prepared):
    room, item, sources, _ = prepared
    old = journal_bytes(room.journal())
    room.admin("revoke_source", "news-wire")
    replayed = AuthorityBundle(canonical(room.pin.model_dump(mode="json")), old, room.anchor(), mode="synthetic")
    assert not evaluate(item, sources, RIGHTS, authority=replayed, authority_mode="synthetic", now=NOW)["publication_allowed"]


def test_future_or_expired_grant_cannot_append_a_positive_decision(tmp_path):
    from pipeline.authority.ledger import append
    room = Newsroom(tmp_path).team()
    item, sources = content()
    record = room.prepared(bind_story(item, sources[SID], RIGHTS), "SOURCE_VALIDATED", "editor")
    with pytest.raises(AuthorityError, match="validity period"):
        append(room.root, record, room.pin, NOW + timedelta(days=2), mode="synthetic")


def test_unprovisioned_environment_ignores_fake_repository_owner_config(tmp_path, monkeypatch):
    monkeypatch.delenv("TECHLINE_AUTHORITY_TRUST_FILE", raising=False)
    fake = tmp_path / "config/editorial-owner.json"
    fake.parent.mkdir()
    fake.write_text(json.dumps({"owner": "attacker", "approved": True, "public_key": key("attacker").public_key}))
    assert status(tmp_path, NOW)["status"] == "UNPROVISIONED"
    assert load_authority(tmp_path) is None
    assert not status(tmp_path, NOW)["production_authority_available"]


def test_production_loader_refuses_repository_pin_and_external_synthetic_pin(tmp_path, monkeypatch):
    room = Newsroom(tmp_path / "checkout")
    inside = room.root / "config/pin.json"
    inside.parent.mkdir(parents=True)
    inside.write_bytes(canonical(room.pin.model_dump(mode="json")))
    monkeypatch.setenv("TECHLINE_AUTHORITY_TRUST_FILE", str(inside))
    assert status(room.root, NOW)["reason"] == "trust_location"
    outside = tmp_path / "synthetic-pin.json"
    outside.write_bytes(inside.read_bytes())
    monkeypatch.setenv("TECHLINE_AUTHORITY_TRUST_FILE", str(outside))
    assert status(room.root, NOW)["reason"] == "synthetic"


def test_emergency_marker_and_interrupted_writer_fail_closed(tmp_path):
    emergency_hold(tmp_path, "Synthetic hold", NOW)
    assert status(tmp_path, NOW)["reason"] == "emergency_hold"
    (tmp_path / STOP).unlink()  # Only isolated test teardown, never a recovery API.
    lock = tmp_path / ".cache/pipeline-writer.lock"
    lock.write_text('{"kind":"pipeline"}')
    assert status(tmp_path, NOW)["reason"] == "writer_pending"


def test_build_owner_token_can_read_but_stale_lock_cannot(tmp_path, monkeypatch):
    cache = tmp_path / ".cache"
    cache.mkdir()
    (cache / "pipeline-writer.lock").write_text('{"kind":"build","token":"synthetic-only"}')
    monkeypatch.setenv("TECHLINE_BUILD_TOKEN", "wrong")
    assert status(tmp_path, NOW)["status"] == "BLOCKED"
    monkeypatch.setenv("TECHLINE_BUILD_TOKEN", "synthetic-only")
    assert status(tmp_path, NOW)["status"] == "UNPROVISIONED"


def test_cli_demo_never_writes_keys_or_journal_in_project(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "demo"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["scoped_signature_accepted"]
    assert result["version_mismatch_rejected"] and result["revoked_grant_rejected"]
    assert not result["publication_allowed"] and not result["credentials_persisted"]
    assert not list(tmp_path.iterdir())


def test_cli_refuses_unprovisioned_validation_and_unsafe_hold(tmp_path, capsys):
    assert main(["--root", str(tmp_path), "validate"]) == 1
    assert json.loads(capsys.readouterr().out)["code"] == "unprovisioned"
    assert main(["--root", str(tmp_path), "hold", "--reason", "Synthetic emergency", "--confirm", "wrong"]) == 1
    capsys.readouterr()
    assert not (tmp_path / STOP).exists()
    assert main(["--root", str(tmp_path), "hold", "--reason", "Synthetic emergency",
                 "--confirm", "STOP_PUBLICATION"]) == 0
    assert (tmp_path / STOP).exists()


def test_encrypted_key_material_is_not_an_argument_or_repository_file(tmp_path):
    from pipeline.authority.cli import protected_key
    inside = tmp_path / "private.pem"
    inside.write_text("not a credential")
    with pytest.raises(AuthorityError, match="outside"):
        protected_key(inside, tmp_path)


def test_authenticated_translation_bridge_and_stale_english_version(tmp_path):
    from pipeline.translation_governance import record_authenticated
    room = Newsroom(tmp_path).team()
    bound = bind_story(content()[0], content()[1][SID], RIGHTS).model_copy(update={
        "language": "bn", "workflow": "translation", "language_sha256": "e" * 64})
    prepared = room.prepared(bound, "DRAFT_TRANSLATION", "native")
    record_authenticated(prepared, trust_pin=room.pin, root=room.root, now=NOW, mode="synthetic")
    assert room.history().state(bound) == "DRAFT_TRANSLATION"


def test_authenticated_editorial_bridge_uses_original_transition_semantics(tmp_path):
    from pipeline.editorial_workflow import record_authenticated
    room = Newsroom(tmp_path).team()
    bound = bind_story(content()[0], content()[1][SID], RIGHTS)
    record_authenticated(room.prepared(bound, "SOURCE_VALIDATED", "editor"), trust_pin=room.pin,
                         root=room.root, now=NOW, mode="synthetic")
    assert room.history().state(bound) == "SOURCE_VALIDATED"
    with pytest.raises(AuthorityError):
        room.decide(bound, "APPROVED", "editor")


def test_native_signature_is_separate_from_editorial_and_version_bound(prepared):
    from pipeline.models import StoryTranslation
    from pipeline.tests.test_phase6_translation_governance import FakeTranslation
    from pipeline.translation import canonical_hash
    room, item, sources, _ = prepared
    item.translations["bn"] = StoryTranslation(language="bn", content=FakeTranslation().content.__dict__,
        canonical_hash=canonical_hash(item), cache_key="f" * 64, provider="synthetic-test", model="synthetic-test",
        generated_at=NOW, review_status="automated")
    assert not evaluate(item, sources, RIGHTS, authority=bundle(room), authority_mode="synthetic", now=NOW)["publication_allowed"]
    translated = bind_story(item, sources[SID], RIGHTS, language="bn", workflow="translation")
    for state, actor in [("DRAFT_TRANSLATION", "native"), ("LANGUAGE_REVIEW_PENDING", "native"),
                         ("NATIVE_REVIEW_COMPLETE", "native"), ("APPROVED_TRANSLATION", "publisher"),
                         ("PUBLISHED_TRANSLATION", "publisher")]:
        room.decide(translated, state, actor)
    assert evaluate(item, sources, RIGHTS, authority=bundle(room), authority_mode="synthetic", now=NOW)["publication_allowed"]
    from pipeline.translation_governance import edition_language_report
    native_report = edition_language_report([item], authority=bundle(room), sources=sources,
                                            source_rights=RIGHTS, now=NOW, authority_mode="synthetic")
    assert native_report["native_reviewed_count"] == 1
    assert edition_language_report([item])["native_reviewed_count"] == 0
    changed = item.model_copy(deep=True)
    changed.translations["bn"].content.headline += " সংশোধন"
    assert not evaluate(changed, sources, RIGHTS, authority=bundle(room), authority_mode="synthetic", now=NOW)["publication_allowed"]
    changed_source = {SID: sources[SID].model_copy(update={"content_hash": "9" * 64})}
    assert not evaluate(item, changed_source, RIGHTS, authority=bundle(room), authority_mode="synthetic", now=NOW)["publication_allowed"]


def test_research_cannot_reuse_news_signatures_or_claim_source_kind(prepared):
    room, item, sources, _ = prepared
    research = sources[SID].model_copy(update={"source_type": "arxiv"})
    assert bind_story(item, research, RIGHTS).story_kind == "RESEARCH"
    assert not evaluate(item, {SID: research}, RIGHTS, authority=bundle(room), authority_mode="synthetic",
                        now=NOW)["publication_allowed"]


def test_return_to_translation_review_cannot_reactivate_older_native_or_publication_approvals(tmp_path):
    room = Newsroom(tmp_path).team()
    from pipeline.tests.authority_support import binding
    translated = binding(workflow="translation", language="bn", language_sha256="e" * 64)
    for state, actor in [("DRAFT_TRANSLATION", "native"), ("LANGUAGE_REVIEW_PENDING", "native"),
                         ("NATIVE_REVIEW_COMPLETE", "native"), ("APPROVED_TRANSLATION", "publisher"),
                         ("PUBLISHED_TRANSLATION", "publisher")]:
        room.decide(translated, state, actor)
    room.decide(translated, "LANGUAGE_REVIEW_PENDING", "native")
    assert not room.history().active(translated, "NATIVE_REVIEW_COMPLETE", NOW)
    room.decide(translated, "NATIVE_REVIEW_COMPLETE", "native")
    assert not room.history().active(translated, "PUBLISHED_TRANSLATION", NOW)
    room.decide(translated, "APPROVED_TRANSLATION", "publisher")
    room.decide(translated, "PUBLISHED_TRANSLATION", "publisher")
    assert room.history().active(translated, "PUBLISHED_TRANSLATION", NOW)


def test_encrypted_synthetic_key_can_be_loaded_without_secret_output(tmp_path, monkeypatch, capsys):
    from secrets import token_urlsafe

    from cryptography.hazmat.primitives import serialization

    from pipeline.authority.cli import protected_key
    from pipeline.tests.authority_support import private, protect_fixture_directory
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    secret = token_urlsafe(32)
    custody_directory = tmp_path / "custody"
    custody_directory.mkdir()
    protect_fixture_directory(custody_directory)
    key_file = custody_directory / "synthetic-encrypted.pem"
    key_file.write_bytes(private("editor").private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                        serialization.BestAvailableEncryption(secret.encode())))
    key_file.chmod(0o600)
    monkeypatch.setattr("getpass.getpass", lambda _: secret)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stderr.isatty", lambda: True)
    loaded = protected_key(key_file, checkout)
    assert loaded.public_key().public_bytes_raw() == private("editor").public_key().public_bytes_raw()
    assert secret not in capsys.readouterr().out


@pytest.mark.parametrize("schema", ["envelope", "trust-pin", "journal", "grant"])
def test_cli_contract_export_never_provisions_authority(tmp_path, capsys, schema):
    assert main(["--root", str(tmp_path), "schema", "--type", schema]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("mutation", ["disabled", "wrong-adapter"])
def test_signed_reviews_cannot_enable_sources_or_relabel_configured_adapters(prepared, mutation):
    from pipeline.models import SourceRegistry
    room, item, sources, _ = prepared
    config = SourceRegistry.model_validate({"version": 1, "sources": [{
        "id": "news-wire", "name": "Synthetic source configuration", "adapter": "rss", "source_class": "primary",
        "enabled": True, "endpoint": "https://news.example.org/feed", "allowed_hosts": ["news.example.org"],
        "categories": ["ai"], "independence_group": "synthetic", "terms_url": "https://news.example.org/terms",
        "verified_at": "2026-10-20"}]})
    assert evaluate(item, sources, RIGHTS, authority=bundle(room), authority_mode="synthetic", now=NOW,
                    source_registry=config)["publication_allowed"]
    if mutation == "disabled":
        config.sources[0].enabled = False
    else:
        config.sources[0].adapter = "arxiv"
    assert not evaluate(item, sources, RIGHTS, authority=bundle(room), authority_mode="synthetic", now=NOW,
                        source_registry=config)["publication_allowed"]


def test_english_review_cannot_prepare_an_original_bangla_story():
    item, sources = content()
    with pytest.raises(AuthorityError, match="English canonical"):
        bind_story(item.model_copy(update={"language": "bn"}), sources[SID], RIGHTS)


def test_signed_source_review_reconciles_preserved_proposal_but_never_erases_old_suspension(tmp_path):
    from pipeline.authority.service import bind_candidate
    from pipeline.source_onboarding import candidates, register, signed_candidate_allowed, transition
    from pipeline.source_onboarding import load_ledger as source_ledger
    from pipeline.tests.test_phase6_source_onboarding import candidate
    room = Newsroom(tmp_path).team()
    proposal = candidate(candidate_id="news-wire", verified_on=NOW.date(), reproduction_allowed=False,
                         summary_allowed=False, image_allowed=False, archive_retention_allowed=False,
                         ai_submission_allowed=False)
    register(proposal, actor="synthetic-operator", now=NOW, root=tmp_path)
    bound = bind_candidate(proposal)
    for target, actor in [("TECHNICALLY_VALIDATED", "editor"), ("RIGHTS_REVIEW_REQUIRED", "rights"),
                          ("RIGHTS_EVIDENCE_RECORDED", "rights"), ("EDITORIAL_REVIEW_REQUIRED", "editor"),
                          ("ELIGIBLE_FOR_ACTIVATION", "publisher")]:
        room.decide(bound, target, actor)
    assert signed_candidate_allowed(candidates(tmp_path)[0], source_ledger(tmp_path), room.history(), NOW)
    updated, _ = transition(proposal, "SUSPENDED", actor="synthetic-operator", now=NOW,
                            reason="Risk reduction", root=tmp_path)
    transition(updated, "RIGHTS_REVIEW_REQUIRED", actor="synthetic-operator", now=NOW,
               reason="Unsigned resumption cannot erase a denial", root=tmp_path)
    assert source_ledger(tmp_path).events[-1].transition.to_candidate_sha256 == bound.content_sha256
    assert not signed_candidate_allowed(candidates(tmp_path)[0], source_ledger(tmp_path), room.history(), NOW)
