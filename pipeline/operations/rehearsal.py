"""Integrated ephemeral rehearsal using the existing registry and state machines."""

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

from pipeline.authority.ledger import Anchor, emergency_hold, journal_bytes
from pipeline.authority.protocol import Admin, canonical, sign
from pipeline.authority.service import AuthorityBundle, bind_candidate, bind_story
from pipeline.operations.article_fixture import article, bangla_fixture
from pipeline.operations.ceremony import CONFIRMATIONS, preflight, template
from pipeline.operations.custodian import MockCustodian, MockVerificationSession, wire
from pipeline.publication_gate import evaluate
from pipeline.recovery.fixtures import (
    SYNTHETIC_NOW,
    SyntheticNewsroom,
    synthetic_key,
    synthetic_private,
)
from pipeline.source_onboarding import (
    SourceCandidate,
    authenticated_review,
    candidates,
    load_ledger,
    register,
    signed_candidate_allowed,
    transition,
)
from pipeline.translation_governance import integrity_findings


def rehearse():
    """No operator-supplied destination, credentials, network or persistent output."""
    checks = []
    with TemporaryDirectory(prefix="techline-operator-rehearsal-") as directory:
        base = Path(directory)
        proposal = template("synthetic-ceremony", "synthetic-ledger")
        proposal["confirmations"] = list(CONFIRMATIONS)
        ceremony = preflight(base / "empty", proposal, expected_environment="synthetic-ceremony", now=SYNTHETIC_NOW)
        checks.append({"case": "ceremony_dry_run", "passed": ceremony["status"] == "READY_FOR_HUMAN_CEREMONY"})
        room = SyntheticNewsroom(base / "newsroom").team()
        room.appoint("native", "native-bn", workflows=["translation"], languages=["bn"])

        def refused(name, operation):
            before = journal_bytes(room.journal())
            try:
                operation()
                rejected = False
            except ValueError:
                rejected = True
            checks.append({"case": name, "passed": rejected and journal_bytes(room.journal()) == before})

        story, sources, rights = article()
        bound = bind_story(story, sources[story.primary_source_id], rights)
        def bundle():
            raw = room.checkpoint_bytes()
            return AuthorityBundle(canonical(room.pin.model_dump(mode="json")), journal_bytes(room.journal()),
                                   Anchor(raw, hashlib.sha256(raw).hexdigest(), "synthetic-recovery-challenge"),
                                   mode="synthetic")
        proposal = SourceCandidate(candidate_id="news-wire", name="Synthetic rehearsal publisher",
                                   website="https://example.com/", endpoint="https://example.com/synthetic-feed",
                                   fetch_method="rss", category="ai", language="en",
                                   scope="Authored synthetic metadata only; no real publisher licence",
                                   terms_url="https://example.com/synthetic-permission",
                                   discovered_on=SYNTHETIC_NOW.date(), verified_on=SYNTHETIC_NOW.date())
        register(proposal, actor="synthetic-operator", now=SYNTHETIC_NOW, root=room.root)
        candidate_binding = bind_candidate(proposal)
        for state, reviewer in [("TECHNICALLY_VALIDATED", "editor"), ("RIGHTS_REVIEW_REQUIRED", "rights"),
                                ("RIGHTS_EVIDENCE_RECORDED", "rights"), ("EDITORIAL_REVIEW_REQUIRED", "editor"),
                                ("ELIGIBLE_FOR_ACTIVATION", "publisher")]:
            room.decide(candidate_binding, state, reviewer)
        candidate_report = authenticated_review(proposal, bundle(), SYNTHETIC_NOW, mode="synthetic")
        checks.append({"case": "existing_candidate_lifecycle_and_signed_review",
                       "passed": candidate_report["eligible_for_activation"] and not candidate_report["activation_allowed"]
                       and signed_candidate_allowed(candidates(room.root)[0], load_ledger(room.root),
                                                    room.history(), SYNTHETIC_NOW)})
        checks.append({"case": "metadata_adapter_normalization_without_activation",
                       "passed": sources[story.primary_source_id].title.startswith("Synthetic")
                       and not sources[story.primary_source_id].missing_publication_time})
        refused("missing_rights_blocks_editorial_progression",
                lambda: room.decide(bound, "RIGHTS_ELIGIBLE", "rights"))
        room.publish(bound)
        accepted = evaluate(story, sources, rights, authority=bundle(), authority_mode="synthetic", now=SYNTHETIC_NOW)
        checks.append({"case": "existing_composite_gate_accepts_explicit_synthetic_path",
                       "passed": accepted["publication_allowed"]})
        checks.append({"case": "same_fixture_cannot_authorize_production",
                       "passed": not evaluate(story, sources, rights, authority=bundle(),
                                              now=SYNTHETIC_NOW)["publication_allowed"]})
        changed_sources = {sid: value.model_copy(update={"content_hash": "f" * 64}) for sid, value in sources.items()}
        checks.append({"case": "changed_metadata_invalidates_composite_gate",
                       "passed": not evaluate(story, changed_sources, rights, authority=bundle(),
                                              authority_mode="synthetic", now=SYNTHETIC_NOW)["publication_allowed"]})
        checks.append({"case": "missing_source_rights_blocks_composite_gate",
                       "passed": not evaluate(story, sources, {}, authority=bundle(),
                                              authority_mode="synthetic", now=SYNTHETIC_NOW)["publication_allowed"]})
        checks.append({"case": "signed_synthetic_editorial_path",
                       "passed": bool(room.history().active(bound, "PUBLISHED", SYNTHETIC_NOW))})
        bilingual = bangla_fixture(story)
        translated = bind_story(bilingual, sources[story.primary_source_id], rights, language="bn",
                                workflow="translation")
        checks.append({"case": "bangla_structural_binding_and_honest_fallback",
                       "passed": not any(row["severity"] == "fail" for row in
                                          integrity_findings(bilingual, bilingual.translations["bn"]))
                       and any(row["check"] == "translation_absent" for row in integrity_findings(story))})
        for state, reviewer in [("DRAFT_TRANSLATION", "native"), ("LANGUAGE_REVIEW_PENDING", "native"),
                                ("NATIVE_REVIEW_COMPLETE", "native"), ("APPROVED_TRANSLATION", "publisher"),
                                ("PUBLISHED_TRANSLATION", "publisher")]:
            room.decide(translated, state, reviewer)
        checks.append({"case": "signed_synthetic_bangla_path",
                       "passed": bool(room.history().active(translated, "PUBLISHED_TRANSLATION", SYNTHETIC_NOW))})
        for field, value in [("source_id", "other-wire"), ("story_id", "other-story"),
                             ("content_sha256", "f" * 64), ("rights_sha256", "f" * 64),
                             ("story_kind", "RESEARCH")]:
            checks.append({"case": "stale_or_cross_" + field,
                           "passed": not room.history().active(bound.model_copy(update={field: value}),
                                                                "PUBLISHED", SYNTHETIC_NOW)})
        original = bilingual.translations["bn"]
        changed = original.model_copy(update={"content": original.content.model_copy(update={
            "headline": "পরিবর্তিত সিন্থেটিক পরীক্ষামূলক অনুবাদ"})})
        rebound = bind_story(bilingual.model_copy(update={"translations": {"bn": changed}}),
                             sources[story.primary_source_id], rights, language="bn", workflow="translation")
        checks.append({"case": "changed_translation_requires_new_review",
                       "passed": not room.history().active(rebound, "PUBLISHED_TRANSLATION", SYNTHETIC_NOW)})
        refused("rights_reviewer_cannot_approve_bangla",
                lambda: room.decide(translated, "NATIVE_REVIEW_COMPLETE", "rights"))
        refused("native_reviewer_cannot_grant_rights",
                lambda: room.decide(bound.model_copy(update={"workflow": "rights"}), "RIGHTS_APPROVED", "native"))
        refused("wrong_source_scope",
                lambda: room.decide(bound.model_copy(update={"source_id": "other-wire"}), "SOURCE_VALIDATED", "editor"))

        def forged_owner():
            payload = Admin(**room.base("forged-owner", "editor", "editor"), kind="admin", role="owner-admin",
                            operation="enroll", target_id="fake-owner", key=synthetic_key("fake-owner"), grant=None)
            room.store(sign(payload, synthetic_private("editor"), possession_key=synthetic_private("fake-owner")))
        refused("ordinary_editor_cannot_enroll_owner", forged_owner)
        history = room.history()
        checkpoint = room.checkpoint()
        custodian = MockCustodian(checkpoint)
        session = MockVerificationSession(custodian.key)
        challenge = session.issue(history, SYNTHETIC_NOW)
        receipt = custodian.answer(challenge, SYNTHETIC_NOW)
        verified = session.verify(wire(receipt), checkpoint, history, SYNTHETIC_NOW)
        checks.append({"case": "mock_current_head_round_trip", "passed": verified["status"] == "PASS"
                       and not verified["publication_allowed"] and not verified["independently_trusted"]})
        checks.append({"case": "mock_receipt_replay_refused",
                       "passed": session.verify(wire(receipt), checkpoint, history, SYNTHETIC_NOW)["status"] != "PASS"})
        unanchored = AuthorityBundle(canonical(room.pin.model_dump(mode="json")), journal_bytes(room.journal()),
                                     None, mode="synthetic")
        refused("missing_checkpoint_blocks_final_gate",
                lambda: unanchored.verify(SYNTHETIC_NOW, expected_mode="synthetic"))
        previous = room.history().active(bound, "PUBLISHED", SYNTHETIC_NOW)
        room.decide(bound, "CORRECTED", "moderator", supersedes=previous)
        checks.append({"case": "correction_withdraws_previous_publication",
                       "passed": not room.history().active(bound, "PUBLISHED", SYNTHETIC_NOW)})
        room.decide(bound, "RETRACTED", "moderator")
        checks.append({"case": "signed_retraction_preserved", "passed": room.history().state(bound) == "RETRACTED"})
        another = bound.model_copy(update={"story_id": "story-two"})
        room.publish(another)
        checks.append({"case": "second_story_approved_before_revocation",
                       "passed": bool(room.history().active(another, "PUBLISHED", SYNTHETIC_NOW))})
        transition(proposal, "SUSPENDED", actor="synthetic-operator", now=SYNTHETIC_NOW,
                   reason="Synthetic source withdrawal", root=room.root)
        checks.append({"case": "source_suspension_overrides_signed_readiness",
                       "passed": not signed_candidate_allowed(candidates(room.root)[0], load_ledger(room.root),
                                                               room.history(), SYNTHETIC_NOW)})
        room.admin("revoke_reviewer", "editor")
        checks.append({"case": "revocation_invalidates_prior_publication",
                       "passed": not room.history().active(another, "PUBLISHED", SYNTHETIC_NOW)})
        refused("revoked_editor_cannot_sign_new_decision", lambda: room.decide(bound, "SOURCE_VALIDATED", "editor"))
        room.admin("rotate_root", room.pin.owner_id, replacement="replacement-owner")
        checks.append({"case": "planned_root_rotation_replays",
                       "passed": room.history().registry.root_key.key_id == synthetic_key("replacement-owner").key_id})
        raw = room.checkpoint_bytes()
        anchor = Anchor(raw, hashlib.sha256(raw).hexdigest(), "synthetic-recovery-challenge")
        emergency_hold(room.root, "Synthetic rehearsal freeze", SYNTHETIC_NOW)
        frozen = AuthorityBundle(canonical(room.pin.model_dump(mode="json")), journal_bytes(room.journal()),
                                 anchor, mode="synthetic", stopped=True)
        refused("emergency_freeze_blocks_final_gate", lambda: frozen.verify(SYNTHETIC_NOW, expected_mode="synthetic"))
    return {"version": 1, "status": "PASS" if all(c["passed"] for c in checks) else "FAIL", "checks": checks,
            "synthetic_only": True, "roles_exercised": ["owner-admin", "source-rights", "fact-checker",
                                                        "english-editor", "native-bn", "publisher"],
            "real_reviewers_appointed": False, "production_credentials_created": False,
            "external_checkpoint_written": False, "publication_allowed": False,
            "limitations": ["Authored RSS and in-memory article/translation; not real ingestion or a publisher licence",
                            "Mock receipt does not establish independent current custody",
                            "Lost owner credentials still require human recovery; not automatically recoverable"]}
