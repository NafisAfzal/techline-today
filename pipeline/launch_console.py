"""One local launch report; no content/authority changes or external writes."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from pipeline.authority.cli import ROOT, policy, snapshot
from pipeline.authority.ledger import STOP, decode_journal, replay
from pipeline.authority.protocol import MAX_RECORD, instant
from pipeline.authority.registry import TrustPin
from pipeline.authority.service import checkpoint_status, load_authority
from pipeline.filesystem import confined_file
from pipeline.newsroom_readiness import newsroom_readiness
from pipeline.operations.redaction import refusal, scan_payload
from pipeline.recovery.inventory import inventory_report
from pipeline.research_approval import readiness
from pipeline.strict_json import strict_json

STATUSES = ("PASS", "FAIL", "BLOCKED", "INCONCLUSIVE")


def check(name, status, detail, evidence=None, action=None):
    return {"item": name, "status": status, "detail": detail, "evidence": evidence or {},
            "next_action": action, "publication_allowed": False}


def authority_overview(root, at):
    """Verify local signed history separately from independent-current custody."""
    bundle = load_authority(root, allow_stopped=True)
    if bundle is None:
        return [check("owner_authority", "BLOCKED", "UNPROVISIONED: no external owner trust pin",
                      action="Owner personally verifies identity, custody and fingerprint in the offline ceremony"),
                check("reviewer_provisioning", "BLOCKED", "No authenticated owner-appointed reviewers")]
    pin = TrustPin.model_validate(strict_json(bundle.pin_bytes, max_bytes=MAX_RECORD))
    history = replay(decode_journal(bundle.journal_bytes), pin, at)
    registry = history.registry
    active = []
    for grant_id, (reviewer, grant) in registry.grants.items():
        member = registry.reviewers.get(reviewer, {})
        key = registry.keys.get(member.get("key_id"), {})
        if (grant_id in registry.revoked_grants or member.get("suspended") or member.get("revoked") or
                key.get("disabled", True) or not instant(grant.active_at) <= at < instant(grant.expires_at)):
            continue
        if instant(key["key"].active_at) <= at < instant(key["key"].expires_at):
            active.append({"reviewer_id": reviewer, "role": grant.role, "grant_id": grant_id,
                           "workflows": grant.workflows, "expires_at": grant.expires_at})
    root_active = instant(registry.root_key.active_at) <= at < instant(registry.root_key.expires_at)
    return [check("owner_authority", "PASS" if root_active else "BLOCKED",
                  "Production pin and signed local history verify; human identity and independent freshness "
                  "remain separate" if root_active else "Current owner root is outside its validity interval",
                  {"environment": pin.environment, "registry_revision": registry.revision,
                   "journal_head_sha256": history.journal.head_sha256}),
            check("reviewer_provisioning", "PASS" if active else "BLOCKED",
                  f"{len(active)} currently active signed grant(s); per-item stage checks enforce actual scope",
                  {"active_grants": active, "independent_checkpoint_required": True})]


def launch_report(root, *, now=None):
    at = now or datetime.now(UTC)
    root = Path(root)
    checks = []
    try:
        checks.extend(authority_overview(root, at))
    except (ValueError, OSError, TypeError, KeyError) as error:
        checks.extend([check("owner_authority", "FAIL", "Configured authority input failed verification",
                             {"code": getattr(error, "code", type(error).__name__)}),
                       check("reviewer_provisioning", "INCONCLUSIVE", "Invalid authority prevents reviewer evaluation")])
    try:
        stopped = confined_file(root, STOP).exists()
        checks.append(check("emergency_suspension", "BLOCKED" if stopped else "PASS",
                            "Persistent publication STOP is present; owner-reviewed recovery required" if stopped else
                            "No local STOP marker; signed revocations are evaluated by the authority gate"))
    except (ValueError, OSError):
        checks.append(check("emergency_suspension", "FAIL", "Emergency STOP path cannot be inspected safely"))
    try:
        custody = checkpoint_status(root, at)
        checks.append(check("independent_checkpoint", custody.get("status", "INCONCLUSIVE"),
                            custody.get("detail", custody.get("code", "Unavailable evidence")), custody))
    except (ValueError, OSError, TypeError):
        checks.append(check("independent_checkpoint", "FAIL", "Checkpoint verifier could not inspect input"))
    try:
        newsroom = newsroom_readiness(root, at)
        for row in newsroom["items"]:
            if row["item"] in {"source_rights_coverage", "rights_evidence_completeness", "security_configuration",
                               "security_advisory", "current_news_coverage", "operational_observation_coverage"}:
                checks.append(check(row["item"], row["result"], row["detail"], row["evidence"]))
    except (ValueError, OSError, TypeError, KeyError):
        checks.append(check("newsroom_inputs", "FAIL", "Existing newsroom readiness could not inspect local input"))
    path = confined_file(root, "content/generated/snapshot.json")
    if not path.exists():
        checks.append(check("research_inventory", "INCONCLUSIVE", "No local snapshot; no item count or decisions inferred",
                            action="Restore the independently hash-verified canonical snapshot privately"))
        for name in ("research_rights", "research_editorial", "native_bangla", "research_publication_eligibility"):
            checks.append(check(name, "INCONCLUSIVE", "No local snapshot for exact-item evaluation"))
    else:
        try:
            edition = snapshot(root)
            research = readiness(root, edition, policy(root), now=at)
            checks.append(check("research_inventory", "PASS", f"{len(edition.stories)} exact local item(s) inspected",
                                {"snapshot_sha256": research["snapshot_sha256"], "record_count": len(edition.stories)},
                                "Use pipeline.content_review for private per-item packets and CSV"))
            for name, stages in [
                ("research_rights", {"RESEARCH_METADATA_APPROVED"}),
                ("research_editorial", {"RESEARCH_EXTRACTIVE_APPROVED", "RESEARCH_FACTUAL_APPROVED",
                                         "RESEARCH_CLASSIFICATION_APPROVED", "RESEARCH_PUBLICATION_APPROVED"}),
                ("native_bangla", {"RESEARCH_BANGLA_APPROVED"}),
            ]:
                decisions = [stage for item in research["items"] for stage in item["stages"] if stage["stage"] in stages]
                missing = [stage for stage in decisions if stage["status"] != "ACTIVE"]
                checks.append(check(name, "BLOCKED" if missing else "PASS" if decisions else "INCONCLUSIVE",
                                    f"{len(missing)} of {len(decisions)} required signed stage(s) missing/inactive" if
                                    decisions else "No Bangla content in this snapshot; no native approval inferred",
                                    {"required_stage_count": len(decisions), "missing_stage_count": len(missing),
                                     "content_binding_required": True}))
            checks.append(check("research_publication_eligibility", "PASS" if research["eligible_count"] else "BLOCKED",
                                f"{research['eligible_count']}/{research['record_count']} real eligible item(s)",
                                {"eligible_count": research["eligible_count"], "record_count": research["record_count"],
                                 "publication_authorized_by_this_report": False}))
        except (ValueError, OSError, TypeError, KeyError) as error:
            checks.append(check("research_inventory", "FAIL", "Exact-item evaluation refused malformed or unsafe input",
                                {"code": getattr(error, "code", type(error).__name__)}))
    recovery = inventory_report()
    checks.extend([
        check("cloudflare_account", "INCONCLUSIVE", "Account identity, 2FA, plan, billing, integrations and spending "
              "controls cannot be verified from local config", action="Owner completes account checklist; do not deploy"),
        check("github_open_advisories", "INCONCLUSIVE", "Local advisory record does not authenticate current "
              "GitHub CodeQL/Dependabot state", action="Consult dated private read-only GitHub evidence"),
        check("recovery", "INCONCLUSIVE", "Recovery inventory is available; this command does not authenticate a "
              "real encrypted backup or completed restore drill", {"asset_count": recovery["asset_count"],
              "credential_count": recovery["credential_count"]}),
        check("research_preview", "BLOCKED", "Local preparation only; account verification, eligible exact content "
              "and separate exact-artifact owner deployment approval remain required"),
        check("publication_authorization", "BLOCKED", "This local report never authorizes GitHub mutation or deployment"),
    ])
    status = "FAIL" if any(row["status"] == "FAIL" for row in checks) else "BLOCKED"
    first = next((row for row in checks if row["item"] == "owner_authority" and row["status"] != "PASS"), None)
    return {"version": 1, "status": status, "assessed_at": at.isoformat(), "checks": checks,
            "summary": {name: sum(row["status"] == name for row in checks) for name in STATUSES},
            "next_human_action": first["next_action"] if first and first["next_action"] else
                                 "Review exact-item blockers, establish independent custody and complete scoped human review",
            "publication_allowed": False, "network_access": False, "content_or_authority_mutated": False,
            "security_state_may_advance": bool(os.environ.get("TECHLINE_CUSTODIAN_RUN_TOKEN")),
            "note": "PASS is scoped to its stated evidence. Missing human decisions are BLOCKED; unknown external "
                    "facts are INCONCLUSIVE; malformed/failed local verification is FAIL. No readiness percentage."}


def human_report(report):
    from pipeline.content_review import markdown_text
    lines = [f"Techline Today local launch: {report['status']}", f"Assessed: {report['assessed_at']}", "",
             "| Check | Result | Evidence / limit |", "|---|---|---|"]
    lines.extend("| " + " | ".join(markdown_text(row[key]) for key in ("item", "status", "detail")) + " |"
                 for row in report["checks"])
    lines.extend(["", "Next human action: " + report["next_human_action"], "", report["note"],
                  "No content or authority changes. No external account queried or publication authorized.",
                  "Custody verifier may advance its local clock floor during an active scoped operation: " +
                  str(report["security_state_may_advance"])])
    return "\n".join(lines)


def main(argv=None):
    from pipeline.content_review import ReportArgumentParser
    parser = ReportArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true", help="Machine-readable evidence and status")
    args = parser.parse_args(argv)
    try:
        report = launch_report(args.root, now=datetime.now(UTC).replace(microsecond=0))
    except (ValueError, OSError, TypeError, KeyError) as error:
        report = {"status": "FAIL", "code": getattr(error, "code", type(error).__name__),
                  "detail": "Launch report refused unsafe or unreadable local input", "publication_allowed": False}
        print(json.dumps(report))
        return 1
    try:
        detections = scan_payload(report)
        if detections:
            print(json.dumps(refusal(detections), ensure_ascii=True))
            return 1
        rendered = json.dumps(report, ensure_ascii=True, indent=2, allow_nan=False) if args.json else human_report(report)
    except (ValueError, TypeError, KeyError):
        print('{"status":"FAIL","code":"invalid_output","publication_allowed":false}')
        return 1
    print(rendered)
    return 1 if report["status"] == "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
