"""Offline Research Edition review tools. Packets and reports never grant rights."""

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from pipeline.authority.cli import (
    ROOT,
    common,
    output,
    policy,
    require_confirmation,
    snapshot,
    trusted_history,
)
from pipeline.authority.ledger import append, load
from pipeline.authority.protocol import (
    MAX_RECORD,
    RESEARCH_STAGES,
    AuthorityError,
    Checkpoint,
    ResearchDecision,
    read_envelope,
)
from pipeline.filesystem import regular_path
from pipeline.generation import bounded_file
from pipeline.research_approval import STAGES, bind_research, read_policy, readiness, validate_decision


def find_story(edition, identity):
    found = next((story for story in edition.stories if story.id == identity), None)
    if found is None:
        raise AuthorityError("story", "Unknown canonical record ID")
    return found


def execute(args, now):
    root = args.root
    if args.action == "demo":
        from pipeline.research_demo import demonstrate
        return demonstrate()
    read_policy(root)
    edition, rights = snapshot(root), policy(root)
    if args.action == "select-stdin":
        from pipeline.models import Snapshot
        from pipeline.strict_json import strict_json
        raw = sys.stdin.buffer.read(50_000_001)
        supplied = Snapshot.model_validate(strict_json(raw, max_bytes=50_000_000))
        if supplied != edition:
            raise AuthorityError("snapshot_mismatch", "Selection input differs from the current local edition")
        return readiness(root, edition, rights, now=now)
    if args.action in {"report", "inspect", "blockers", "packet"}:
        report = readiness(root, edition, rights, now=now)
        if args.action == "report":
            if args.output:
                report["output"] = output(root, args.output, report)
            return report
        story = find_story(edition, args.story)
        row = next(row for row in report["items"] if row["id"] == story.id)
        if args.action != "packet":
            return row
        bindings = [bind_research(story, edition.sources[sid], rights, edition.sources,
                                  language=language).model_dump(mode="json")
                    for sid in story.source_ids for language in
                    (["en", "bn"] if "bn" in story.translations else ["en"])]
        packet = {"format": "techline.research.unsigned-review-packet/v1", "unsigned": True,
                  "story_id": story.id, "bindings": bindings, "required_stages": list(RESEARCH_STAGES) +
                  (["RESEARCH_BANGLA_APPROVED"] if "bn" in story.translations else []),
                  "stage_roles": {"metadata_reuse": "source-rights", "extractive_summary": "english-editor",
                                  "factual_review": "fact-checker", "classification": "english-editor",
                                  "publication": "publisher", "bangla": "native-bn"},
                  "journal_head_sha256": load(root).head_sha256, "eligibility": row,
                  "checkpoint_custody": report["checkpoint_custody"], "publication_allowed": False,
                  "instructions": "Review exact canonical content privately; supply evidence digests. Prepare one "
                  "decision at a time against a new checkpoint. This unsigned packet is never accepted as authority."}
        target = output(root, args.output, packet)
        return {"unsigned": True, "story_id": story.id, "output": target, "publication_allowed": False}
    pin, history = trusted_history(root, now)
    if args.action in {"validate", "record"}:
        envelope = read_envelope(bounded_file(regular_path(args.input), MAX_RECORD))
        story = find_story(edition, args.story)
        result = validate_decision(history, envelope, story, edition.sources, rights, now)
        if args.action == "record":
            require_confirmation(args, envelope.payload.record_id)
            append(root, envelope, pin, now)
            result["stored"] = True
        return result
    story = find_story(edition, args.story)
    source = edition.sources.get(args.source or story.primary_source_id)
    if source is None:
        raise AuthorityError("source", "Unknown source item ID")
    language = "bn" if args.stage == "RESEARCH_BANGLA_APPROVED" else "en"
    bound = bind_research(story, source, rights, edition.sources, language=language)
    if args.action == "revoke":
        target = history.by_id.get(args.supersedes)
        if target is None or not isinstance(target.payload, ResearchDecision) or target.payload.binding.story_id != story.id:
            raise AuthorityError("research_revocation_target", "Choose the exact historical research decision for this item")
        bound = target.payload.binding
    checkpoint = read_envelope(bounded_file(regular_path(args.checkpoint), MAX_RECORD))
    if not isinstance(checkpoint.payload, Checkpoint) or checkpoint.proof is not None:
        raise AuthorityError("checkpoint", "Supply an existing signed owner checkpoint envelope")
    member = history.registry.member(args.reviewer)
    grant = history.registry.grants.get(args.grant)
    if grant is None or grant[0] != args.reviewer:
        raise AuthorityError("grant", "Grant does not belong to this reviewer")
    from pipeline.authority.protocol import envelope_bytes
    from pipeline.research_approval import review_anchor

    # Preparation checks position and signature without claiming independent
    # custody. Signing, validating and recording remain separate human acts.
    payload = ResearchDecision(**common(history, args.reviewer, member["key_id"], now),
                               kind="research-decision", role=grant[1].role, grant_id=args.grant,
                               registry_revision=history.registry.revision, binding=bound, decision=args.stage,
                               from_state=history.state(bound), to_state=args.stage, evidence=args.evidence,
                               supersedes=args.supersedes, review_checkpoint=checkpoint.payload,
                               checkpoint_signature=checkpoint.signature,
                               checkpoint_sha256=hashlib.sha256(envelope_bytes(checkpoint)).hexdigest())
    from pipeline.authority.ledger import verify_local_anchor
    verify_local_anchor(history, review_anchor(payload), now)
    # Inspect scope without signing or manufacturing a signature.
    assigned = grant[1]
    if (payload.role != assigned.role or payload.decision not in assigned.decisions or
            bound.source_id not in assigned.sources or bound.workflow not in assigned.workflows or
            bound.language not in assigned.languages or
            bound.story_id not in assigned.stories and "*" not in assigned.stories):
        raise AuthorityError("scope", "Prepared decision exceeds the human reviewer's signed grant")
    target = output(root, args.output, payload.model_dump(mode="json"))
    return {"unsigned": True, "prepared_record_id": payload.record_id, "stage": payload.decision,
            "output": target, "publication_allowed": False}


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--root", type=Path, default=ROOT)
    sub = result.add_subparsers(dest="action", required=True)
    sub.add_parser("demo")
    sub.add_parser("select-stdin", help="Internal exact-snapshot bridge for Research Edition selection")
    report = sub.add_parser("report")
    report.add_argument("--output", help="Private machine-readable export under .cache/authority/outbox/")
    for name in ("inspect", "blockers", "packet"):
        item = sub.add_parser(name)
        item.add_argument("--story", required=True)
        if name == "packet":
            item.add_argument("--output", required=True)
    for name in ("validate", "record"):
        item = sub.add_parser(name)
        item.add_argument("--input", type=Path, required=True)
        item.add_argument("--story", required=True)
        if name == "record":
            item.add_argument("--confirm", required=True)
    for name in ("prepare", "revoke", "supersede"):
        item = sub.add_parser(name, help="Prepare an unsigned decision for the existing authority signer")
        for field in ("story", "reviewer", "grant", "output", "checkpoint"):
            item.add_argument("--" + field, required=True)
        item.add_argument("--source")
        item.add_argument("--evidence", action="append", required=True, help="Evidence SHA-256; include rights digest")
        item.add_argument("--supersedes", required=name in {"revoke", "supersede"})
        if name == "revoke":
            item.set_defaults(stage="RESEARCH_REVOKED")
        else:
            item.add_argument("--stage", choices=STAGES, required=True)
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        data = execute(args, datetime.now(UTC).replace(microsecond=0))
        print(json.dumps(data, ensure_ascii=True, indent=2))
        return 0
    except (ValueError, OSError, TypeError, EOFError) as error:
        print(json.dumps({"status": "REFUSED", "code": getattr(error, "code", type(error).__name__),
                          "detail": str(error) if isinstance(error, AuthorityError) else
                          "Malformed input or inaccessible file; inspect schemas and paths.",
                          "publication_allowed": False}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
