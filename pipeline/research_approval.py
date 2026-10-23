"""Research Edition adapter for the existing editorial authority and publication gate.

No new trust root, key store, approval ledger or checkpoint custodian. A local
checkpoint claim never grants publication. Historical review checkpoints prove
the exact pre-decision journal position; the publication checkpoint must cover
the resulting journal and use a new independent challenge.
"""

import hashlib
from dataclasses import replace
from datetime import UTC, datetime

from pipeline.authority.ledger import (
    Anchor,
    Journal,
    decode_journal,
    replay,
    verify_anchor,
    verify_local_anchor,
)
from pipeline.authority.protocol import (
    MAX_RECORD,
    RESEARCH_POLICY,
    RESEARCH_STAGES,
    ZERO,
    AuthorityError,
    Envelope,
    ResearchBinding,
    ResearchDecision,
    clock,
    envelope_bytes,
)
from pipeline.authority.registry import TrustPin
from pipeline.authority.service import (
    AuthorityBundle,
    bind_story,
    checkpoint_status,
    load_authority,
    source_registry,
)
from pipeline.filesystem import confined_file
from pipeline.generation import bounded_file
from pipeline.publication_gate import evaluate
from pipeline.review_governance import digest
from pipeline.strict_json import strict_json

STAGES = (*RESEARCH_STAGES, "RESEARCH_BANGLA_APPROVED")


def record_kind(story, sources):
    cited = [sources.get(sid) for sid in story.source_ids]
    if not cited or any(source is None for source in cited):
        return "out-of-scope"
    if story.category == "research" and all(source.source_registry_id == "arxiv" for source in cited):
        return "research"
    if all(source.source_registry_id == "cloudflare_ai_terms" and source.source_type == "github_document"
           for source in cited):
        return "reference"
    return "out-of-scope"


def bind_research(story, source, rights, sources, *, language="en"):
    kind = record_kind(story, sources)
    if kind == "out-of-scope":
        raise AuthorityError("research_scope", "Only research and reference records enter this workflow")
    original = bind_story(story, source, rights, sources=sources,
                          language=language, workflow="research").model_dump(mode="json")
    # Unlike the legacy English binding, research always binds every translation
    # too. Adding/removing/changing Bangla invalidates every research stage.
    original.update(story_kind=kind.upper(), content_sha256=digest({
        "story": story.model_dump(mode="json"),
        "sources": {sid: sources[sid].model_dump(mode="json") for sid in story.source_ids}}))
    return ResearchBinding(**original, research_policy=RESEARCH_POLICY,
                           publication_scope="metadata-extractive:en-bn" if "bn" in story.translations
                           else "metadata-extractive:en")


def rights_blockers(story, sources, rights):
    reasons = []
    for sid in story.source_ids:
        source = sources.get(sid)
        if source is None:
            reasons.append("missing_source:" + sid)
            continue
        entry = rights.get(source.source_registry_id, {})
        if entry.get("publication") != "allow":
            reasons.append("rights_not_allowed:" + source.source_registry_id)
        if not all(entry.get(key) for key in ("license", "license_url", "scope")):
            reasons.append("rights_evidence_incomplete:" + source.source_registry_id)
        if source.rights_review is not None:
            reasons.append("item_held_for_review:" + sid)
        raw = source.model_dump(mode="json")
        if raw.get("internal_only") or raw.get("provenance") is not None:
            reasons.append("private_source_evidence:" + sid)
    return reasons


def review_anchor(decision):
    envelope = Envelope(algorithm="Ed25519", payload=decision.review_checkpoint,
                        signature=decision.checkpoint_signature, proof=None)
    return Anchor(envelope_bytes(envelope), decision.checkpoint_sha256, decision.review_checkpoint.challenge)


def verify_review_checkpoint(history, decision, now, *, historical=False):
    cp = decision.review_checkpoint
    if cp.challenge in history.research_challenges:
        raise AuthorityError("research_checkpoint_replay", "This review challenge was already consumed")
    anchor = review_anchor(decision)
    # During replay history.journal holds the entire journal, while the registry
    # and decision projections are at this event. Compare its checkpoint with
    # exactly the signed prefix, never with events that had not happened yet.
    events = history.journal.events[:decision.sequence - 1]
    prefix = Journal(version=1, events=events, head_sha256=events[-1].event_sha256 if events else ZERO)
    prior = replace(history, journal=prefix)
    if decision.decision == "RESEARCH_REVOKED":
        # Signed risk reduction remains possible without granting custody trust.
        verify_local_anchor(prior, anchor, now)
    elif historical and not history.registry.pin.synthetic:
        # An archived independently signed receipt proves acceptance at the
        # decision's signed issuance time. It is not current publication trust.
        from pathlib import Path

        from pipeline.authority.manual_custodian import configured_proof

        verify_local_anchor(prior, anchor, now)
        proof = configured_proof(Path.cwd(), historical=True)
        if proof is None:
            raise AuthorityError("custodian_archive_missing", "Historical independent receipt archive is required")
        proof.verify(prior, anchor, now, historical=True)
    else:
        verify_anchor(prior, anchor, now)
    history.research_challenges.add(cp.challenge)


def validate_decision(history, envelope, story, sources, rights, now, *, mode="production"):
    """Inspect a proposed transaction; never writes or treats a packet as proof."""
    from pipeline.authority.ledger import stage
    from pipeline.authority.protocol import read_envelope

    envelope = read_envelope(envelope_bytes(envelope))
    decision = envelope.payload
    if not isinstance(decision, ResearchDecision):
        raise AuthorityError("research_type", "Expected a typed signed research decision")
    if decision.decision == "RESEARCH_REVOKED":
        target = history.by_id.get(decision.supersedes)
        if (target is None or not isinstance(target.payload, ResearchDecision) or
                target.payload.binding != decision.binding or decision.binding.story_id != story.id):
            raise AuthorityError("research_revocation_target", "Revocation must bind the exact historical decision and item")
        stage(history.journal, envelope, history.registry.pin, now, mode=mode)
        return {"record_id": decision.record_id, "stage": decision.decision, "signature_and_scope_valid": True,
                "stored": False, "publication_allowed": False}
    source = next((sources[sid] for sid in story.source_ids if sid in sources and
                   sources[sid].source_registry_id == decision.binding.source_id and
                   digest(sources[sid].model_dump(mode="json")) == decision.binding.source_sha256), None)
    if source is None or decision.binding != bind_research(
            story, source, rights, sources, language=decision.binding.language):
        raise AuthorityError("research_binding", "Decision does not bind this exact item, content, source, rights and scope")
    if decision.decision != "RESEARCH_REVOKED":
        blockers = rights_blockers(story, sources, rights)
        if blockers:
            raise AuthorityError("research_rights", "; ".join(blockers))
        if decision.binding.rights_sha256 not in decision.evidence:
            raise AuthorityError("research_rights_reference", "Every research stage must reference the bound rights digest")
        if mode == "production" and (story.is_demo or any(sources[sid].is_demo for sid in story.source_ids)):
            raise AuthorityError("synthetic", "Synthetic records cannot receive real publication authority")
    stage(history.journal, envelope, history.registry.pin, now, mode=mode)
    return {"record_id": decision.record_id, "stage": decision.decision, "signature_and_scope_valid": True,
            "stored": False, "publication_allowed": False}


def evaluate_item(story, sources, rights, *, authority=None, now=None, registry=None, mode="production",
                  history=None, editorial_ledger=None):
    now = clock(now or datetime.now(UTC))
    # All existing dimensions remain mandatory. Research adds restrictions only.
    base = evaluate(story, sources, rights, authority=authority, now=now,
                    source_registry=registry, authority_mode=mode, editorial_ledger=editorial_ledger)
    blockers = [f"existing_gate:{dimension['dimension']}:{reason}"
                for dimension in base["dimensions"] for reason in dimension["reasons"]]
    blockers.extend(rights_blockers(story, sources, rights))
    kind = record_kind(story, sources)
    if kind == "out-of-scope":
        blockers.append("outside-research-reference-scope")
    error = None
    if history is None and isinstance(authority, AuthorityBundle):
        try:
            history = authority.verify(now, expected_mode=mode, anchored=False)
        except (ValueError, TypeError, OSError) as failure:
            error = getattr(failure, "code", type(failure).__name__)
    stages = []
    for sid in story.source_ids:
        if sid not in sources or kind == "out-of-scope":
            continue
        for language in (["en", "bn"] if "bn" in story.translations else ["en"]):
            bound = bind_research(story, sources[sid], rights, sources, language=language)
            needed = RESEARCH_STAGES if language == "en" else ("RESEARCH_BANGLA_APPROVED",)
            for name in needed:
                record_id = history.active(bound, name, now) if history else None
                detail, evidence = "missing", None
                if history:
                    candidates = [record for record in history.decisions if record.payload.binding.story_id == story.id
                                  and record.payload.decision == name and record.payload.binding.source_id == bound.source_id]
                    exact = [record for record in candidates if record.payload.binding == bound]
                    if exact:
                        latest = exact[-1]
                        payload = latest.payload
                        evidence = {"record_id": payload.record_id, "reviewer": payload.signer_id,
                                    "role": payload.role, "key_id": payload.key_id, "grant_id": payload.grant_id,
                                    "issued_at": payload.issued_at, "expires_at": payload.expires_at,
                                    "policy_version": payload.policy_version, "research_policy": bound.research_policy,
                                    "revocation_state": history.blocked(bound),
                                    "checkpoint_sha256": payload.checkpoint_sha256}
                        detail = history.blocked(bound) or ("superseded" if payload.record_id in history.withdrawn else "active")
                        if detail == "active":
                            try:
                                history.registry.authorize(latest, now)
                            except AuthorityError as failure:
                                detail = failure.code
                    elif candidates:
                        detail = "binding_mismatch"
                if not record_id:
                    blockers.append(f"missing_active_decision:{sid}:{name}")
                    if detail != "missing":
                        blockers.append(f"inactive_decision:{sid}:{name}:{detail}")
                stages.append({"source_item_id": sid, "stage": name, "language": language,
                               "record_id": record_id, "status": "ACTIVE" if record_id else "MISSING",
                               "detail": detail, "evidence": evidence})
    checkpoint = "unprovisioned"
    if authority is not None:
        try:
            final_history = authority.verify(now, expected_mode=mode)
            if authority.anchor.expected_challenge in final_history.research_challenges:
                raise AuthorityError("research_checkpoint_replay", "Publication requires a fresh unused challenge")
            checkpoint = "synthetic-current" if mode == "synthetic" else "CURRENTLY_TRUSTED"
        except (ValueError, TypeError, OSError) as failure:
            checkpoint = getattr(failure, "code", type(failure).__name__)
    if checkpoint not in {"synthetic-current", "CURRENTLY_TRUSTED"}:
        blockers.append("no-current-trusted-research-checkpoint:" + checkpoint)
    if error:
        blockers.append("authority_history:" + error)
    return {"id": story.id, "kind": kind, "stages": stages, "reasons": sorted(set(blockers)),
            "existing_gate": base, "checkpoint": checkpoint,
            "synthetic_eligible": mode == "synthetic" and not blockers,
            "publication_allowed": mode == "production" and not blockers}


def readiness(root, snapshot, rights, *, now=None):
    policy = read_policy(root)
    now = now or datetime.now(UTC)
    authority, authority_error = None, None
    try:
        authority = load_authority(root)
    except (ValueError, OSError, TypeError) as failure:
        authority_error = getattr(failure, "code", type(failure).__name__)
    registry = source_registry(root)
    from pipeline.editorial_workflow import load_ledger
    local_editorial = load_ledger(root)
    history = None
    if authority is not None:
        try:
            pin = TrustPin.model_validate(strict_json(authority.pin_bytes, max_bytes=MAX_RECORD))
            history = replay(decode_journal(authority.journal_bytes), pin, now)
        except (ValueError, OSError, TypeError) as failure:
            authority_error = getattr(failure, "code", type(failure).__name__)
    rows = [evaluate_item(story, snapshot.sources, rights, authority=authority, now=now,
                          registry=registry, history=history, editorial_ledger=local_editorial) for story in snapshot.stories]
    custody = checkpoint_status(root, now)
    # Consume only the checkpoint verifier's recomputed result, never a report
    # supplied by a caller. Today its adapters cannot establish current custody.
    current = custody.get("status") == "PASS" and custody.get("trust_level") == "CURRENTLY_TRUSTED" and \
        custody.get("independently_trusted") is True and custody.get("current") is True
    for row in rows:
        if policy.get("publication_enabled") is not True:
            row["publication_allowed"] = False
            row["reasons"].append("research_publication_disabled_by_policy")
        if not current:
            row["publication_allowed"] = False
            row["reasons"] = sorted(set([*row["reasons"], "checkpoint_custody:" + custody["code"]]))
        if snapshot.mode != "live":
            row["publication_allowed"] = False
            row["reasons"].append("synthetic_edition_in_real_selection")
    selected = [row["id"] for row in rows if row["publication_allowed"]]
    return {"version": 1, "policy": RESEARCH_POLICY, "record_count": len(rows),
            "snapshot_sha256": hashlib.sha256(confined_file(root, "content/generated/snapshot.json").read_bytes()).hexdigest(),
            "eligible": selected, "eligible_count": len(selected), "items": rows,
            "excluded": [row for row in rows if not row["publication_allowed"]],
            "checkpoint_custody": custody, "authority_error": authority_error,
            "publication_allowed": bool(selected) and current, "ai_submission_allowed": False}


def read_policy(root):
    raw = bounded_file(confined_file(root, "config/research-edition.json"), MAX_RECORD)
    policy = strict_json(raw, max_bytes=MAX_RECORD)
    if policy.get("policy") != RESEARCH_POLICY or policy.get("approval_adapter") != "editorial-authority-research-v1":
        raise AuthorityError("research_policy", "Unrecognized Research Edition policy or adapter")
    return policy
