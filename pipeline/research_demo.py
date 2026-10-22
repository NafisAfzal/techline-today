"""Explicit synthetic-only Research Edition exercise. No real authority or I/O survives."""

import hashlib
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from pipeline.authority.ledger import Anchor, journal_bytes, stage
from pipeline.authority.protocol import (
    CAPABILITIES,
    RESEARCH_STAGES,
    Grant,
    ResearchDecision,
    canonical,
    envelope_bytes,
    sign,
    stamp,
)
from pipeline.authority.service import AuthorityBundle, bind_story
from pipeline.operations.article_fixture import article
from pipeline.recovery.fixtures import SYNTHETIC_NOW, SyntheticNewsroom, synthetic_private
from pipeline.research_approval import bind_research, evaluate_item, validate_decision


def content():
    story, sources, rights = article()
    sources = {sid: source.model_copy(update={"source_registry_id": "arxiv", "source_type": "arxiv",
                                             "category": "research"}) for sid, source in sources.items()}
    story = story.model_copy(update={"category": "research"})
    return story, sources, {"arxiv": rights["news-wire"]}


class SyntheticResearchRoom(SyntheticNewsroom):
    """Reuses the existing drill journal and explicitly synthetic published keys."""

    def appoint(self, name, role, *, workflows=None, languages=None):
        self.admin("enroll", name, replacement=name)
        permission = Grant(grant_id="g-" + name, role=role, decisions=sorted(CAPABILITIES[role]),
                           sources=["arxiv"], stories=["story-one"], languages=languages or ["en"],
                           workflows=workflows or ["research"], active_at=stamp(SYNTHETIC_NOW),
                           expires_at=stamp(SYNTHETIC_NOW + timedelta(days=1)))
        self.admin("grant", name, permission=permission)

    def team(self):
        for name, role, workflows, languages in (
            ("editor", "english-editor", ["editorial", "research"], ["en"]),
            ("rights", "source-rights", ["editorial", "rights", "research"], ["en"]),
            ("fact", "fact-checker", ["editorial", "research"], ["en"]),
            ("publisher", "publisher", ["editorial", "translation", "research"], ["en", "bn"]),
            ("native", "native-bn", ["translation", "research"], ["bn"]),
            ("moderator", "suspension", ["editorial", "research"], ["en"]),
        ):
            self.appoint(name, role, workflows=workflows, languages=languages)
        return self

    def prepared(self, bound, decision, signer, *, checkpoint=None, **changes):
        history = self.history()
        cp = checkpoint or self.checkpoint(challenge="synthetic-review-" + str(len(history.journal.events)))
        values = dict(**self.base("research-" + str(len(history.journal.events) + 1), signer, signer),
                      kind="research-decision", role=history.registry.grants["g-" + signer][1].role,
                      grant_id="g-" + signer, registry_revision=history.registry.revision, binding=bound,
                      decision=decision, from_state=history.state(bound), to_state=decision,
                      evidence=[bound.rights_sha256], supersedes=None, review_checkpoint=cp.payload,
                      checkpoint_signature=cp.signature, checkpoint_sha256=hashlib.sha256(envelope_bytes(cp)).hexdigest())
        values.update(changes)
        return sign(ResearchDecision(**values), synthetic_private(signer))

    def bundle(self, *, challenge="synthetic-final-publication"):
        cp = self.checkpoint(challenge=challenge)
        raw = envelope_bytes(cp)
        return AuthorityBundle(canonical(self.pin.model_dump(mode="json")), journal_bytes(self.journal()),
                               Anchor(raw, hashlib.sha256(raw).hexdigest(), challenge), mode="synthetic")

    def review_all(self, story, sources, rights):
        bound = bind_research(story, sources[story.primary_source_id], rights, sources)
        for name, signer in zip(RESEARCH_STAGES, ["rights", "editor", "fact", "editor", "publisher"], strict=True):
            record = self.prepared(bound, name, signer)
            validate_decision(self.history(), record, story, sources, rights, SYNTHETIC_NOW, mode="synthetic")
            self.store(record)
        return bound


def demonstrate():
    def rejected(action):
        try:
            action()
        except (ValueError, TypeError) as error:
            return {"rejected": True, "code": getattr(error, "code", type(error).__name__)}
        return {"rejected": False, "code": "UNEXPECTED_ACCEPTANCE"}

    with TemporaryDirectory(prefix="techline-synthetic-research-") as directory:
        room = SyntheticResearchRoom(Path(directory)).team()
        story, sources, rights = content()
        bound = bind_research(story, sources[story.primary_source_id], rights, sources)
        good = room.prepared(bound, RESEARCH_STAGES[0], "rights")
        def validate(record=good, item=story, evidence=rights, at=SYNTHETIC_NOW):
            return validate_decision(room.history(), record, item, sources, evidence, at, mode="synthetic")
        checks = {"properly_scoped_signed_decision": {"accepted": validate()["signature_and_scope_valid"]}}
        forged_payload = ResearchDecision.model_validate({**good.payload.model_dump(mode="json"),
                                                          "signer_id": "unappointed-reviewer"})
        forged = sign(forged_payload, synthetic_private("rights"))
        checks["forged_reviewer"] = rejected(lambda: validate(forged))
        checks["invalid_signature"] = rejected(lambda: validate(good.model_copy(update={"signature": "A" * 86})))
        checks["cross_item"] = rejected(lambda: validate(item=story.model_copy(update={"id": "other-item"})))
        checks["stale_content"] = rejected(lambda: validate(item=story.model_copy(update={
            "headline": "Changed synthetic content invalidates the approval"})))
        checks["missing_rights"] = rejected(lambda: validate(evidence={}))
        checks["expired_signature"] = rejected(lambda: validate(at=SYNTHETIC_NOW + timedelta(days=2)))
        room.store(good)
        reused = room.prepared(bound, RESEARCH_STAGES[1], "editor", checkpoint=room.checkpoint(
            challenge=good.payload.review_checkpoint.challenge))
        checks["replayed_checkpoint"] = rejected(lambda: stage(room.journal(), reused, room.pin,
                                                                SYNTHETIC_NOW, mode="synthetic"))
        # Review remaining stages and all pre-existing editorial/rights stages.
        for name, signer in zip(RESEARCH_STAGES[1:], ["editor", "fact", "editor", "publisher"], strict=True):
            room.store(room.prepared(bound, name, signer))
        room.publish(bind_story(story, sources[story.primary_source_id], rights, sources=sources))
        synthetic = evaluate_item(story, sources, rights, authority=room.bundle(), now=SYNTHETIC_NOW,
                                  mode="synthetic")
        checks["complete_synthetic_workflow"] = {"accepted": synthetic["synthetic_eligible"],
                                                 "existing_gate_passed": synthetic["existing_gate"]["publication_allowed"]}
        checks["synthetic_in_real_build"] = {"rejected": not evaluate_item(
            story, sources, rights, authority=room.bundle(), now=SYNTHETIC_NOW)["publication_allowed"]}
        revoke = room.prepared(bound, "RESEARCH_REVOKED", "moderator", supersedes=good.payload.record_id)
        room.store(revoke)
        checks["revoked_decision"] = {"rejected": not room.history().active(bound, RESEARCH_STAGES[0], SYNTHETIC_NOW)}
        passed = all(check.get("accepted", check.get("rejected", False)) for check in checks.values())
        return {"status": "PASS" if passed else "FAIL", "synthetic_only": True, "checks": checks,
                "credentials_persisted": False, "real_reviewers_appointed": False,
                "production_authority_available": False, "publication_allowed": False}
