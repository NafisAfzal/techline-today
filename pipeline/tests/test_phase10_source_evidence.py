"""Source candidate rights-evidence checks. A gap is reported; it is never granted."""

import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from pipeline.source_evidence import (
    BLOCKED,
    REVIEW_REQUIRED,
    EvidencePolicy,
    candidate_status,
    check_candidate,
    evidence_report,
    load_dossiers,
    read_candidate_document,
    research_candidates,
)
from pipeline.source_onboarding import (
    SourceCandidate,
    register,
    transition,
)

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)


def candidate(**overrides):
    base = {"candidate_id": "example_tech", "name": "Example Technology Newsroom",
            "website": "https://news.example.org/", "endpoint": "https://news.example.org/feed.xml",
            "fetch_method": "rss", "category": "ai", "language": "en",
            "scope": "Independent technology reporting for verification.",
            "terms_url": "https://news.example.org/terms", "discovered_on": date(2026, 10, 18)}
    return SourceCandidate.model_validate({**base, **overrides})


def codes(findings):
    return {row.code for row in findings}


def test_an_unreviewed_candidate_reports_every_outstanding_gap():
    findings = check_candidate(candidate(), now=NOW)
    assert "license_evidence_missing" in codes(findings)
    assert "rights_reviewer_missing" in codes(findings)
    assert "article_body_reuse_unsupported" in codes(findings)
    assert "image_rights_unknown" in codes(findings)
    assert "ai_permissions_unclear" in codes(findings)
    assert "attribution_unverified" in codes(findings)
    assert "terms_never_reviewed" in codes(findings)
    assert "endpoint_unvalidated" in codes(findings)
    assert "retention_policy_unresolved" in codes(findings)
    assert "rights_status_not_evidence_recorded" in codes(findings)
    assert candidate_status(findings) == BLOCKED


def test_an_unknown_is_never_reported_as_satisfied():
    findings = check_candidate(candidate(), now=NOW)
    blocking = {row.code for row in findings if row.severity == "blocking"}
    assert "image_rights_unknown" in blocking
    assert "ai_permissions_unclear" in blocking


def test_a_recorded_refusal_is_advisory_not_blocking():
    reviewed = candidate(rights_evidence_status="EVIDENCE_RECORDED",
                         evidence=[{"url": "https://news.example.org/license", "kind": "license",
                                    "note": "Excerpts only, with attribution."}],
                         reviewer_reference="owner-designated-reviewer", review_decision_at=NOW,
                         verified_on=date(2026, 10, 19), last_fetch_outcome="SUCCESS",
                         last_fetch_observed_at=NOW, reproduction_allowed=False, image_allowed=False,
                         ai_submission_allowed=False, archive_retention_allowed=False,
                         attribution_required=True)
    findings = check_candidate(reviewed, now=NOW)
    assert "image_reuse_refused" in codes(findings)
    assert "ai_submission_refused" in codes(findings)
    assert "article_body_reuse_unsupported" in codes(findings)
    assert candidate_status(findings) == REVIEW_REQUIRED


def test_a_stale_terms_review_is_blocking():
    reviewed = candidate(discovered_on=date(2026, 1, 1),
                         rights_evidence_status="EVIDENCE_RECORDED",
                         evidence=[{"url": "https://news.example.org/license", "kind": "license",
                                    "note": "Excerpts only."}],
                         reviewer_reference="owner-designated-reviewer", review_decision_at=NOW,
                         verified_on=date(2026, 1, 1))
    findings = check_candidate(reviewed, now=NOW)
    assert "terms_review_stale" in codes(findings)


def test_the_freshness_policy_is_operator_defined():
    reviewed = candidate(discovered_on=date(2026, 9, 1),
                         rights_evidence_status="EVIDENCE_RECORDED",
                         evidence=[{"url": "https://news.example.org/license", "kind": "license",
                                    "note": "Excerpts only."}],
                         reviewer_reference="owner-designated-reviewer", review_decision_at=NOW,
                         verified_on=date(2026, 10, 1))
    assert "terms_review_stale" not in codes(check_candidate(reviewed, now=NOW))
    strict = EvidencePolicy(max_terms_age_days=7)
    assert "terms_review_stale" in codes(check_candidate(reviewed, now=NOW, policy=strict))


def test_the_report_names_the_role_that_must_decide():
    findings = check_candidate(candidate(), now=NOW)
    assert all(row.required_role == "source-rights" for row in findings)
    assert all(row.required_decision.strip() for row in findings)


def test_the_report_never_claims_activation_or_publication():
    report = evidence_report([candidate()], now=NOW)
    assert report["publication_allowed"] is False
    assert report["activation_allowed"] is False
    assert report["ai_submission_allowed"] is False
    assert report["candidates"][0]["publication_allowed"] is False


def test_a_candidate_with_every_field_populated_is_still_not_approved():
    complete = candidate(rights_evidence_status="EVIDENCE_RECORDED",
                         evidence=[{"url": "https://news.example.org/license", "kind": "license",
                                    "note": "Excerpts only."}],
                         reviewer_reference="owner-designated-reviewer", review_decision_at=NOW,
                         verified_on=date(2026, 10, 19), last_fetch_outcome="SUCCESS",
                         last_fetch_observed_at=NOW, reproduction_allowed=False, image_allowed=False,
                         ai_submission_allowed=False, archive_retention_allowed=False,
                         attribution_required=True)
    report = evidence_report([complete], now=NOW)
    assert report["evidence_complete"] == []
    assert report["candidates"][0]["status"] == REVIEW_REQUIRED


def test_authority_gated_transitions_stay_refused_after_a_complete_record(root):
    register(candidate(), actor="phase10-source-research", now=NOW, root=root)
    with pytest.raises(Exception, match="authenticated reviewer authority"):
        transition(candidate(), "RIGHTS_EVIDENCE_RECORDED", actor="phase10-source-research", now=NOW,
                   reason="Attempted.", root=root)


def test_the_dossier_is_written_for_review_but_grants_nothing(root):
    register(candidate(), actor="phase10-source-research", now=NOW, root=root)
    dossiers = load_dossiers(root)
    assert len(dossiers) == 1
    assert dossiers[0].rights_evidence_status == "RIGHTS_UNVERIFIED"
    assert dossiers[0].summary_allowed is None
    report = evidence_report(dossiers, now=NOW)
    assert report["candidates"][0]["status"] == BLOCKED


def test_an_unsafe_dossier_name_is_refused(root):
    from pipeline.source_onboarding import dossier_path

    with pytest.raises(ValueError, match="Unsafe candidate dossier name"):
        dossier_path(root, "../escape")


def test_the_recorded_research_shortlist_is_unreviewed_proposals(tmp_path):
    root = Path(tmp_path)
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "config/source-research.json").write_text(json.dumps({
        "version": 1, "status": "RESEARCH_ONLY",
        "candidates": [{
            "candidate_id": "sample_wire", "name": "Sample Wire",
            "website": "https://wire.example.org/", "endpoint": "https://wire.example.org/feed.xml",
            "fetch_method": "rss", "category": "ai", "language": "en",
            "scope": "A synthetic research entry.",
            "terms_url": "https://wire.example.org/terms", "discovered_on": "2026-10-20",
            "verified_on": "2026-10-20", "last_fetch_outcome": "NOT_PERFORMED",
            "evidence": [{"url": "https://wire.example.org/license", "kind": "license",
                          "note": "Retrieved on the access date."}],
            "verification": {"unresolved_legal_questions": ["Attribution is unresolved."]},
        }]}), encoding="utf-8")
    proposals = research_candidates(root)
    assert len(proposals) == 1
    assert proposals[0].rights_evidence_status == "RIGHTS_UNVERIFIED"
    assert proposals[0].summary_allowed is None
    assert proposals[0].last_fetch_outcome == "NEVER_OBSERVED"
    assert proposals[0].coverage_gaps == ["Attribution is unresolved."]


def test_a_malformed_dossier_document_is_refused(tmp_path):
    with pytest.raises(ValueError):
        read_candidate_document(b"{not json")
