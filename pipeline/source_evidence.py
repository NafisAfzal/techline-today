"""Source candidate rights-evidence checks for a human rights reviewer.

This module never grants rights, never activates a source and never approves a
candidate. It answers one question for each candidate: *what evidence is still
missing, and who has to decide it?*

Every unknown is reported as unknown. A field that is present but unset is a
gap, not a permission. A candidate that has every metadata field populated is
still not approved: promotion requires an authenticated reviewer authority and
a named human rights decision, which this project does not have.
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pipeline.authority.protocol import Model
from pipeline.source_onboarding import SourceCandidate

PASS, REVIEW_REQUIRED, BLOCKED = "PASS", "REVIEW_REQUIRED", "BLOCKED"

LICENSE_EVIDENCE_MISSING = "license_evidence_missing"
RIGHTS_REVIEWER_MISSING = "rights_reviewer_missing"
ARTICLE_BODY_REUSE_UNSUPPORTED = "article_body_reuse_unsupported"
IMAGE_RIGHTS_UNKNOWN = "image_rights_unknown"
AI_PERMISSIONS_UNCLEAR = "ai_permissions_unclear"
ATTRIBUTION_UNVERIFIED = "attribution_unverified"
STABLE_IDENTITY_MISSING = "stable_identity_missing"
TERMS_REVIEW_STALE = "terms_review_stale"
TERMS_NEVER_REVIEWED = "terms_never_reviewed"
ENDPOINT_UNVALIDATED = "endpoint_unvalidated"
RETENTION_POLICY_UNRESOLVED = "retention_policy_unresolved"
RIGHTS_STATUS_NOT_EVIDENCE_RECORDED = "rights_status_not_evidence_recorded"
IMAGE_REUSE_REFUSED = "image_reuse_refused"
AI_SUBMISSION_REFUSED = "ai_submission_refused"

ROLE_RIGHTS = "source-rights"
ROLE_OWNER = "owner-admin"
ROLE_PUBLISHER = "publisher"

RESEARCH_FILE = "config/source-research.json"


@dataclass(frozen=True)
class EvidencePolicy:
    """Operator-defined review policy. Defaults are conservative, not permissive."""

    max_terms_age_days: int = 180
    require_endpoint_confirmation: bool = True
    max_candidates: int = 200


class EvidenceFinding(Model):
    """One missing or unresolved piece of rights evidence."""

    code: str
    severity: Literal["blocking", "advisory"]
    field: str
    detail: str
    required_decision: str
    required_role: str
    candidate_id: str | None = None


def _finding(code, severity, field, detail, decision, role, candidate_id) -> EvidenceFinding:
    return EvidenceFinding(code=code, severity=severity, field=field, detail=detail,
                           required_decision=decision, required_role=role, candidate_id=candidate_id)


def check_candidate(candidate, *, now=None, policy: EvidencePolicy | None = None) -> list[EvidenceFinding]:
    """Return every unresolved rights-evidence gap for one candidate."""
    policy = policy or EvidencePolicy()
    at = now or datetime.now(UTC)
    candidate = SourceCandidate.model_validate(candidate.model_dump(mode="json"))
    identifier = candidate.candidate_id
    findings: list[EvidenceFinding] = []

    # --- licence evidence ---------------------------------------------------------
    licence_evidence = [item for item in candidate.evidence
                        if item.kind in {"terms", "license"}]
    if not licence_evidence:
        findings.append(_finding(
            LICENSE_EVIDENCE_MISSING, "blocking", "evidence",
            "No publisher terms or licence document has been recorded for this source.",
            "Obtain and record the publisher's own reuse terms, then re-check the scope that will be "
            "reused.", ROLE_RIGHTS, identifier))
    elif not any(item.captured_sha256 for item in licence_evidence):
        findings.append(_finding(
            LICENSE_EVIDENCE_MISSING, "advisory", "evidence.captured_sha256",
            "The recorded licence reference has no captured digest, so drift cannot be detected.",
            "Capture a digest of the retained licence document at review time.",
            ROLE_RIGHTS, identifier))

    # --- human rights reviewer -----------------------------------------------------
    if not candidate.reviewer_reference:
        findings.append(_finding(
            RIGHTS_REVIEWER_MISSING, "blocking", "reviewer_reference",
            "No human rights reviewer is named for this candidate.",
            "A named human with rights expertise must review the recorded evidence and decide.",
            ROLE_RIGHTS, identifier))
    elif candidate.review_decision_at is None:
        findings.append(_finding(
            RIGHTS_REVIEWER_MISSING, "blocking", "review_decision_at",
            "A reviewer is referenced but no decision time was recorded.",
            "Record the review decision time once the reviewer has decided.",
            ROLE_RIGHTS, identifier))

    # --- article body reuse --------------------------------------------------------
    if candidate.reproduction_allowed is None:
        findings.append(_finding(
            ARTICLE_BODY_REUSE_UNSUPPORTED, "blocking", "reproduction_allowed",
            "Whether article bodies may be reproduced is unknown.",
            "Decide and record whether full article text may be republished; an unknown is never "
            "treated as permission.", ROLE_RIGHTS, identifier))
    elif candidate.reproduction_allowed is False:
        findings.append(_finding(
            ARTICLE_BODY_REUSE_UNSUPPORTED, "advisory", "reproduction_allowed",
            "Full article-body reproduction is not permitted for this source.",
            "Keep to metadata, links, excerpts and summaries that the recorded terms allow.",
            ROLE_RIGHTS, identifier))

    # --- image rights ---------------------------------------------------------------
    if candidate.image_allowed is None:
        findings.append(_finding(
            IMAGE_RIGHTS_UNKNOWN, "blocking", "image_allowed",
            "Image reuse rights are unknown for this source.",
            "Decide whether images may be reused; an unknown must never become media-publishable.",
            ROLE_RIGHTS, identifier))
    elif candidate.image_allowed is False:
        findings.append(_finding(
            IMAGE_REUSE_REFUSED, "advisory", "image_allowed",
            "Image reuse is not permitted for this source.",
            "Publish without source images and link to the original instead.",
            ROLE_RIGHTS, identifier))

    # --- AI processing ---------------------------------------------------------------
    if candidate.ai_submission_allowed is None:
        findings.append(_finding(
            AI_PERMISSIONS_UNCLEAR, "blocking", "ai_submission_allowed",
            "Whether this source's material may be submitted to a paid AI provider is unknown.",
            "Decide the AI-processing permission explicitly; until then no third-party text may be "
            "submitted to a paid model.", ROLE_RIGHTS, identifier))
    elif candidate.ai_submission_allowed is False:
        findings.append(_finding(
            AI_SUBMISSION_REFUSED, "advisory", "ai_submission_allowed",
            "AI submission is not permitted for this source.",
            "Keep source-derived text out of paid AI processing and use local extraction only.",
            ROLE_RIGHTS, identifier))

    # --- attribution ------------------------------------------------------------------
    if candidate.attribution_required is None:
        findings.append(_finding(
            ATTRIBUTION_UNVERIFIED, "blocking", "attribution_required",
            "Whether attribution is required has not been verified.",
            "Verify the publisher's attribution requirement and record it.", ROLE_RIGHTS, identifier))

    # --- stable identity ----------------------------------------------------------------
    try:
        identity = candidate.identity
    except (ValueError, TypeError):
        identity = ""
    if not identity:
        findings.append(_finding(
            STABLE_IDENTITY_MISSING, "blocking", "website",
            "The candidate has no stable publisher identity.",
            "Record the publisher's canonical host so the candidate can be deduplicated.",
            ROLE_RIGHTS, identifier))

    # --- terms review freshness -----------------------------------------------------------
    if candidate.verified_on is None:
        findings.append(_finding(
            TERMS_NEVER_REVIEWED, "blocking", "verified_on",
            "The publisher terms have never been reviewed for this candidate.",
            "Read the publisher's current terms and record the review date.", ROLE_RIGHTS, identifier))
    else:
        age = (at.date() - candidate.verified_on).days
        if age > policy.max_terms_age_days:
            findings.append(_finding(
                TERMS_REVIEW_STALE, "blocking", "verified_on",
                f"The recorded terms review is {age} days old; the policy limit is "
                f"{policy.max_terms_age_days} days.",
                "Re-read the publisher's terms and record a fresh review date.",
                ROLE_RIGHTS, identifier))

    # --- endpoint validation ---------------------------------------------------------------
    if policy.require_endpoint_confirmation and candidate.last_fetch_outcome in {"NEVER_OBSERVED",
                                                                                "UNKNOWN"}:
        findings.append(_finding(
            ENDPOINT_UNVALIDATED, "blocking", "last_fetch_outcome",
            "The feed endpoint has never been confirmed to work.",
            "Observe the endpoint once over HTTPS and record the outcome before any use.",
            ROLE_RIGHTS, identifier))

    # --- retention -------------------------------------------------------------------------
    if candidate.archive_retention_allowed is None:
        findings.append(_finding(
            RETENTION_POLICY_UNRESOLVED, "blocking", "archive_retention_allowed",
            "How long this source's material may be archived is unresolved.",
            "Decide the permitted retention period; unknown retention blocks archiving.",
            ROLE_RIGHTS, identifier))

    # --- rights status ---------------------------------------------------------------------
    if candidate.rights_evidence_status != "EVIDENCE_RECORDED":
        findings.append(_finding(
            RIGHTS_STATUS_NOT_EVIDENCE_RECORDED, "blocking", "rights_evidence_status",
            f"The candidate's rights status is {candidate.rights_evidence_status}, not recorded evidence.",
            "A rights reviewer must record the evidence and its decision.", ROLE_RIGHTS, identifier))

    return findings


def candidate_status(findings: list[EvidenceFinding]) -> str:
    """PASS only when nothing is outstanding. Unknowns are never a pass."""
    if any(row.severity == "blocking" for row in findings):
        return BLOCKED
    if findings:
        return REVIEW_REQUIRED
    return PASS


def candidate_row(candidate, *, now=None, policy: EvidencePolicy | None = None) -> dict:
    """One reviewer-facing row: the candidate, its gaps and the decision required."""
    findings = check_candidate(candidate, now=now, policy=policy)
    return {
        "candidate_id": candidate.candidate_id,
        "name": candidate.name,
        "website": candidate.website,
        "endpoint": candidate.endpoint,
        "fetch_method": candidate.fetch_method,
        "language": candidate.language,
        "identity": candidate.identity,
        "rights_evidence_status": candidate.rights_evidence_status,
        "status": candidate_status(findings),
        "blocking_findings": [row.code for row in findings if row.severity == "blocking"],
        "advisory_findings": [row.code for row in findings if row.severity == "advisory"],
        "findings": [row.model_dump(mode="json") for row in findings],
        "required_decisions": sorted({row.required_decision for row in findings}),
        "required_roles": sorted({row.required_role for row in findings}),
        "publication_allowed": False,
        "activation_allowed": False,
        "ai_submission_allowed": False,
    }


def evidence_report(candidates, *, now=None, policy: EvidencePolicy | None = None) -> dict:
    """Operator-facing evidence report over a list of candidates."""
    policy = policy or EvidencePolicy()
    at = now or datetime.now(UTC)
    rows = [candidate_row(candidate, now=at, policy=policy) for candidate in candidates]
    rows.sort(key=lambda row: row["candidate_id"])
    blocked = [row["candidate_id"] for row in rows if row["status"] == BLOCKED]
    review = [row["candidate_id"] for row in rows if row["status"] == REVIEW_REQUIRED]
    clear = [row["candidate_id"] for row in rows if row["status"] == PASS]
    return {
        "version": 1,
        "assessed_at": at.isoformat(),
        "candidate_count": len(rows),
        "candidates": rows,
        "blocked": blocked,
        "review_required": review,
        "evidence_complete": clear,
        "policy": {"max_terms_age_days": policy.max_terms_age_days,
                   "require_endpoint_confirmation": policy.require_endpoint_confirmation},
        "publication_allowed": False,
        "activation_allowed": False,
        "ai_submission_allowed": False,
        "note": "A candidate with every metadata field populated is still not approved. Promotion "
                "requires an authenticated reviewer authority and a named human rights decision.",
    }


def load_research(root) -> dict:
    """Read the recorded research shortlist. It is evidence, never an approval."""
    path = Path(root) / RESEARCH_FILE
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def _fetch_outcome(value) -> str:
    """Map a research fetch outcome onto the onboarding contract's vocabulary.

    A feed that was not exercised in this session is *never observed* here.
    The prior release configuration may record an earlier verification; that is
    a separate fact and does not upgrade the current observation.
    """
    mapping = {"SUCCESS": "SUCCESS", "EMPTY": "EMPTY", "FAILED": "FAILED", "UNKNOWN": "UNKNOWN"}
    return mapping.get(value, "NEVER_OBSERVED")


def candidate_from_research(entry: dict) -> SourceCandidate:
    """Convert a research entry into an *unreviewed* candidate proposal.

    Every permission stays unknown. The research records what the official
    documents say; only a named human rights reviewer may turn that into a
    permission, and this project has no such reviewer.
    """
    verification = entry.get("verification") if isinstance(entry.get("verification"), dict) else {}
    evidence = [{"url": item["url"], "kind": item["kind"], "note": item["note"]}
                for item in entry.get("evidence", []) if isinstance(item, dict)
                and isinstance(item.get("url"), str) and isinstance(item.get("kind"), str)
                and isinstance(item.get("note"), str)]
    values = {
        "candidate_id": entry["candidate_id"], "name": entry["name"], "website": entry["website"],
        "fetch_method": entry["fetch_method"], "category": entry["category"],
        "language": entry["language"], "scope": entry["scope"], "terms_url": entry["terms_url"],
        "discovered_on": entry["discovered_on"], "verified_on": entry.get("verified_on"),
        "rights_evidence_status": "RIGHTS_UNVERIFIED",
        "last_fetch_outcome": _fetch_outcome(entry.get("last_fetch_outcome")),
        "evidence": evidence,
        "coverage_gaps": list(verification.get("unresolved_legal_questions", [])),
    }
    if entry.get("endpoint"):
        values["endpoint"] = entry["endpoint"]
    return SourceCandidate.model_validate(values)


def research_candidates(root, *, include_configured: bool = False) -> list[SourceCandidate]:
    """Every researched candidate as an unreviewed proposal.

    Sources that are already present in the registry are skipped by default:
    they are research updates to an existing rights decision, not new
    onboarding proposals, and registering them again would put a live,
    rights-approved source back into a rights-pending state.
    """
    research = load_research(root)
    candidates = []
    for entry in research.get("candidates", []):
        if not isinstance(entry, dict):
            continue
        if not include_configured and entry.get("onboarding") == "already-configured":
            continue
        try:
            candidates.append(candidate_from_research(entry))
        except (ValueError, TypeError, KeyError):
            continue
    return candidates


def edition_identities(root) -> set[str]:
    """Candidate-style identities of the sources already in the generated edition.

    This mirrors the publication gate's own comparison rule, so a candidate
    that would collide with a published source is detected before it is
    registered rather than after.
    """
    import hashlib
    from urllib.parse import urlsplit

    from pipeline.models import Snapshot

    path = Path(root) / "content/generated/snapshot.json"
    if not path.is_file():
        return set()
    try:
        snapshot = Snapshot.model_validate_json(path.read_bytes())
    except (ValueError, OSError):
        return set()
    identities = set()
    for source in snapshot.sources.values():
        host = (urlsplit(source.canonical_url).hostname or "").lower().removeprefix("www.")
        identities.add(hashlib.sha256(f"{host}|{source.source_type}|{source.language}".encode()).hexdigest())
    return identities


def configured_source_ids(root) -> set[str]:
    """Source IDs already present in the configured registry."""
    import yaml

    path = Path(root) / "config/sources.yaml"
    if not path.is_file():
        return set()
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (ValueError, OSError, yaml.YAMLError):
        return set()
    sources = value.get("sources") if isinstance(value, dict) else None
    if not isinstance(sources, list):
        return set()
    return {str(entry.get("id")) for entry in sources if isinstance(entry, dict) and entry.get("id")}


def read_candidate_document(payload: bytes) -> SourceCandidate:
    """Parse a candidate dossier supplied by the operator for review."""
    from pipeline.strict_json import strict_json

    value = strict_json(payload, max_bytes=1_000_000, max_depth=16, max_tokens=50_000)
    return SourceCandidate.model_validate(value)


def dossier_directory(root) -> Path:
    from pipeline.source_onboarding import DOSSIER

    return Path(root) / DOSSIER


def load_dossiers(root, *, limit: int = 200) -> list[SourceCandidate]:
    """Read every locally stored candidate dossier for review."""
    directory = dossier_directory(root)
    if not directory.is_dir():
        return []
    found = []
    for path in sorted(directory.glob("*.json"))[:limit]:
        try:
            found.append(read_candidate_document(path.read_bytes()))
        except (ValueError, OSError):
            continue
    return found
