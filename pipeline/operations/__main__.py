"""Offline preparation CLI. Operator-private reports go to stdout only."""

import argparse
import asyncio
import json
from pathlib import Path

from pipeline.filesystem import regular_path
from pipeline.generation import bounded_file
from pipeline.observations import ObservationContext
from pipeline.operations import ceremony, reports
from pipeline.operations.custodian import Challenge, Commitment, Receipt, read_receipt
from pipeline.operations.rehearsal import rehearse
from pipeline.strict_json import strict_json


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--format", choices=["json", "text"], default="json")
    sub = parser.add_subparsers(dest="action", required=True)
    c = sub.add_parser("ceremony", help="Inspect a proposal; never install a root or generate keys")
    selection = c.add_mutually_exclusive_group()
    selection.add_argument("--template", action="store_true")
    selection.add_argument("--proposal", type=Path)
    c.add_argument("--environment-id")
    p = sub.add_parser("appointment-packet", help="Blank human appointment packet; not a grant")
    p.add_argument("role")
    sub.add_parser("rehearse", help="Ephemeral synthetic roles, decisions, language and checkpoint exercise")
    sub.add_parser("console", help="Read-only integrated operational blockers and queues")
    r = sub.add_parser("rights-packets", help="Prepare existing candidate research for a human reviewer")
    r.add_argument("--candidate", action="append")
    sub.add_parser("observation-plan", help="Plan future evidence without generating observation receipts")
    o = sub.add_parser("observation-review", help="Validate retained receipt context and elapsed window; no collection")
    o.add_argument("--environment-id", required=True)
    o.add_argument("--ledger-id", required=True)
    sub.add_parser("preview", help="Nondeploying readiness; inaccessible account settings remain unknown")
    sub.add_parser("recovery", help="Run existing isolated synthetic disaster drills")
    sub.add_parser("source-reliability", help="Offline transport/parser fault matrix; no live polling")
    i = sub.add_parser("checkpoint-inspect", help="Validate wire shape only; never independent current trust")
    i.add_argument("path", type=Path)
    s = sub.add_parser("schema")
    s.add_argument("kind", choices=["ceremony", "challenge", "commitment", "receipt", "observation-context"])
    args = parser.parse_args(argv)
    try:
        if args.action == "schema":
            result = {"ceremony": ceremony.CeremonyProposal, "challenge": Challenge,
                      "commitment": Commitment, "receipt": Receipt,
                      "observation-context": ObservationContext}[args.kind].model_json_schema()
        elif args.action == "ceremony":
            proposal = strict_json(bounded_file(regular_path(args.proposal), 16_000), max_bytes=16_000) \
                if args.proposal else None
            result = ceremony.template() if args.template else ceremony.preflight(
                args.root, proposal, expected_environment=args.environment_id)
        elif args.action == "appointment-packet":
            result = ceremony.appointment_packet(args.role)
        elif args.action == "rehearse":
            result = rehearse()
        elif args.action == "console":
            result = reports.console(args.root)
        elif args.action == "rights-packets":
            result = reports.rights_packets(args.root, args.candidate)
        elif args.action == "observation-plan":
            result = reports.observation_plan(args.root)
        elif args.action == "observation-review":
            from pipeline.operations.observation import review_observations
            result = review_observations(args.root, environment_id=args.environment_id, ledger_id=args.ledger_id)
        elif args.action == "preview":
            result = reports.preview_report(args.root)
        elif args.action == "recovery":
            from pipeline.recovery.drills import drill_report, run_all_drills
            result = drill_report(run_all_drills())
            result["status"] = "FAIL" if result["failed"] else "BLOCKED" if result["blocked"] else "PASS"
        elif args.action == "source-reliability":
            from pipeline.operations.reliability import source_rehearsal
            result = asyncio.run(source_rehearsal(args.root))
        else:
            parsed = read_receipt(bounded_file(regular_path(args.path), 16_000))
            result = {"status": "BLOCKED", "structure": "PASS", "protocol": parsed.payload.protocol,
                      "independently_trusted": False, "publication_allowed": False,
                      "note": "Shape validation is not signature, provenance or current-head verification."}
    except (ValueError, OSError, TypeError, KeyError) as error:
        result = {"status": "FAIL", "code": getattr(error, "code", type(error).__name__),
                  "publication_allowed": False, "note": "Inspect invalid input privately; no authority was granted."}
    if args.format == "text":
        print("Techline Today offline operations: " + result.get("status", "TEMPLATE"))
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("This report authorizes nothing.")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if result.get("status") == "FAIL" else 2 if result.get("status") in {"BLOCKED", "INCONCLUSIVE"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
