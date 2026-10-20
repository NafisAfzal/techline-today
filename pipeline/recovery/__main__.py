"""Local newsroom recovery tools. No network, no credential, no activation."""

import argparse
import json
from pathlib import Path

from pipeline.authority.checkpoint import MAX_DOCUMENT_BYTES
from pipeline.filesystem import regular_path
from pipeline.generation import bounded_file
from pipeline.recovery.drills import drill_report, run_all_drills, run_drill
from pipeline.recovery.inventory import inventory_report
from pipeline.recovery.verify import build_recovery_pack, verify_recovery_pack


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("inventory")
    export = sub.add_parser("export")
    export.add_argument("--destination", type=Path, required=True)
    export.add_argument("--root", type=Path, default=Path.cwd())
    verify = sub.add_parser("verify")
    verify.add_argument("pack", type=Path)
    verify.add_argument("--expected-ledger-id")
    verify.add_argument("--expected-environment")
    verify.add_argument("--expected-owner-id")
    verify.add_argument("--checkpoint", type=Path)
    verify.add_argument("--expected-checkpoint-sha256")
    verify.add_argument("--challenge")
    drill = sub.add_parser("drill")
    drill.add_argument("drill_id", nargs="?", help="A single drill id such as DR-04")
    sub.add_parser("drills")
    args = parser.parse_args(argv)
    try:
        if args.action == "inventory":
            result = inventory_report()
        elif args.action == "export":
            result = build_recovery_pack(args.root, args.destination)
            result = {"created_at": result["created_at"], "members": len(result["files"]),
                      "contains_private_keys": result["contains_private_keys"],
                      "durable_storage_provisioned": False,
                      "note": "A recovery pack is transport, not trust. Independent currency still "
                              "requires an externally held checkpoint."}
        elif args.action == "verify":
            expected = {"ledger_id": args.expected_ledger_id, "environment": args.expected_environment,
                        "owner_id": args.expected_owner_id}
            expected = {key: value for key, value in expected.items() if value}
            checkpoint = bounded_file(regular_path(args.checkpoint), MAX_DOCUMENT_BYTES) if args.checkpoint else None
            result = verify_recovery_pack(args.pack, expected=expected, checkpoint_bytes=checkpoint,
                                          expected_checkpoint_sha256=args.expected_checkpoint_sha256,
                                          challenge=args.challenge).model_dump(mode="json")
        elif args.action == "drill":
            result = run_drill(args.drill_id).as_dict() if args.drill_id else {
                "status": "refused", "detail": "A single drill id is required"} | {}
        else:
            result = drill_report(run_all_drills())
    except (ValueError, OSError, TypeError) as error:
        print(json.dumps({"status": "REFUSED", "code": getattr(error, "code", type(error).__name__),
                          "detail": str(error) if type(error).__name__ == "AuthorityError"
                          else "Malformed input or inaccessible file; inspect paths and formats.",
                          "publication_allowed": False, "ai_submission_allowed": False}))
        return 1
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
