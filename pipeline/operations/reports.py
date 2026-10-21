"""Read-only views over existing newsroom components; no parallel registries."""

from datetime import UTC, datetime, timedelta

from pipeline.editorial_workflow import review_queue
from pipeline.filesystem import confined_file
from pipeline.generation import bounded_file
from pipeline.newsroom_readiness import newsroom_readiness
from pipeline.operations.ceremony import preflight
from pipeline.readiness import observation_evidence, read_observation_receipts
from pipeline.recovery.inventory import inventory_report
from pipeline.source_evidence import candidate_from_research, candidate_row
from pipeline.strict_json import strict_json
from pipeline.translation_governance import backlog


def rights_packets(root, candidate_ids=None, *, now=None):
    """Convert the existing research shortlist into bounded human review packets."""
    data = strict_json(bounded_file(confined_file(root, "config/source-research.json"), 200_000),
                       max_bytes=200_000)
    entries = data.get("candidates") if isinstance(data, dict) and data.get("version") == 1 else None
    if not isinstance(entries, list) or len(entries) > 20:
        raise ValueError("Invalid or oversized existing source research shortlist")
    indexed = {e["candidate_id"]: e for e in entries}
    if len(indexed) != len(entries):
        raise ValueError("Duplicate source identity in research shortlist")
    requested = candidate_ids if candidate_ids is not None else ["cisa_kev", "ubuntu_usn", "bd_cert"]
    if not 1 <= len(requested) <= 5 or len(set(requested)) != len(requested) or set(requested) - indexed.keys():
        raise ValueError("Choose one to five distinct existing candidate IDs")
    packets = []
    for ident in requested:
        entry = indexed[ident]
        proposal = candidate_from_research(entry)
        findings = candidate_row(proposal, now=now)
        packets.append({"candidate": proposal.model_dump(mode="json"), "findings": findings,
                        "requested_permission": "Identifiers, dates and links only after human review; "
                                                "no article text, image or AI permission inferred",
                        "historical_research": entry.get("verification", {}),
                        "research_updates": entry.get("review_updates", []),
                        "existing_record": entry.get("onboarding", "proposal"),
                        "reviewer_identity": None, "reviewer_signature": None,
                        "questions": findings["required_decisions"],
                        "required_authority": "Owner-appointed source-rights reviewer with exact source scope",
                        "publication_allowed": False, "activation_allowed": False, "ai_submission_allowed": False})
    return {"version": 1, "status": "BLOCKED", "packets": packets,
            "publication_allowed": False, "note": "Packet completeness is not a rights grant or source activation."}


def observation_plan(root, *, now=None):
    at = now or datetime.now(UTC)
    window = observation_evidence(read_observation_receipts(root), at)
    return {"version": 1, "status": "INCONCLUSIVE", "existing_window": window,
            "genuinely_authenticated_days": 0, "environment_binding": "NOT_INDEPENDENTLY_VERIFIED",
            "planned_utc_dates": [(at.date() + timedelta(days=i)).isoformat() for i in range(8)],
            "dimensions": ["fetch_availability", "http_status", "retry_timeout", "schema_changes",
                           "pipeline_duration", "rights_blocks", "editorial_backlog", "translation_staleness",
                           "build_reproducibility", "publication_refusal", "credential_errors", "queue_recovery"],
            "daily_template": {"kind": "TEMPLATE_NOT_RECEIPT", "environment_id": None, "observed_at": None,
                               "run_id": None, "report_sha256": None, "receipt_sha256": None,
                               "independent_provenance_reference": None, "operator_notes": []},
            "context_schema": "python -m pipeline.operations schema observation-context",
            "requirements": ["Separate owner authorization before any real collection or schedule",
                             "At least eight genuine observations spanning seven elapsed days",
                             "Existing validator checks duplicate runs/days, gaps, timestamps and integrity",
                             "Authenticate environment, clock and provenance outside local operator control"],
            "receipt_created": False, "live_collection_started": False, "publication_allowed": False,
            "note": "Planned dates and synthetic tests never count as observed days. "
                    "Existing local receipt integrity cannot establish independent provenance."}


def console(root, *, now=None):
    at = now or datetime.now(UTC)
    sections = {}
    failures = []
    for name, inspect in [
        ("readiness", lambda: newsroom_readiness(root, at)),
        ("ceremony", lambda: preflight(root, now=at)),
        ("rights_packets", lambda: rights_packets(root, now=at)),
        ("editorial_queue", lambda: review_queue(root=root)),
        ("bangla_queue", lambda: backlog(root=root)),
        ("observations", lambda: observation_plan(root, now=at)),
        ("recovery_inventory", inventory_report),
    ]:
        try:
            sections[name] = inspect()
        except (ValueError, OSError, TypeError, KeyError) as error:
            sections[name] = {"status": "FAIL", "code": type(error).__name__,
                              "action": "Preserve and inspect invalid input; never treat it as empty or healthy"}
            failures.append(name)
    return {"version": 1, "status": "FAIL" if failures else "BLOCKED", "sections": sections,
            "unreadable_sections": failures, "publication_allowed": False,
            "note": "Local transition queues are work lists, not authenticated appointments or publication approval. "
                    "The existing readiness report remains authoritative for each production blocker."}


def preview_report(root, *, now=None):
    readiness = newsroom_readiness(root, now)
    names = {"preview_readiness", "trusted_checkpoint", "source_rights_coverage", "security_configuration",
             "publication_eligibility", "production_launch_readiness"}
    return {"version": 1, "status": "BLOCKED", "checks": [r for r in readiness["items"] if r["item"] in names],
            "account_settings": "INCONCLUSIVE", "spend_controls": "INCONCLUSIVE",
            "access_control": "INCONCLUSIVE", "owner_release_approval": "BLOCKED",
            "technical_verification": ["Build noindex fixture and verify security headers/robots/provenance",
                                       "Verify separate preview origin, rollback and privacy exclusions",
                                       "Run supported build/site/security/budget checks and Wrangler dry-run"],
            "network_access": False, "deployment_performed": False, "publication_allowed": False,
            "note": "Local flags cannot authenticate Cloudflare account, billing or access settings. "
                    "This evaluator neither checks credentials nor deploys."}
