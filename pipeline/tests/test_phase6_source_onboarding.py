"""Fixture-based onboarding tests. Every prohibited transition must fail closed."""

import json
from datetime import UTC, date, datetime, timedelta

import pytest

from pipeline.source_onboarding import (
    AUTHORITY_GATED,
    DuplicateCandidate,
    SourceCandidate,
    candidate_identity,
    current_state,
    load_ledger,
    missing_evidence,
    readiness,
    register,
    report,
    transition,
)

NOW = datetime(2026, 10, 19, 9, tzinfo=UTC)


def candidate(**overrides):
    base = {"candidate_id": "example_tech", "name": "Example Technology Newsroom",
            "website": "https://news.example.org/", "endpoint": "https://news.example.org/feed.xml",
            "fetch_method": "rss", "category": "ai", "language": "en",
            "scope": "Independent technology reporting for verification.",
            "terms_url": "https://news.example.org/terms", "discovered_on": date(2026, 10, 18)}
    return SourceCandidate.model_validate({**base, **overrides})


# --- valid and invalid metadata ------------------------------------------------

def test_valid_candidate_carries_a_stable_identity():
    assert candidate_identity(candidate().model_dump(mode="json")) == candidate().identity
    assert len(candidate().identity) == 64


@pytest.mark.parametrize("override", [
    {"candidate_id": "Uppercase"}, {"website": "http://news.example.org/"},
    {"website": "https://news.example.org/\x00"}, {"language": "fr"},
    {"category": "AI"}, {"fetch_method": "scraping"},
])
def test_invalid_metadata_is_refused(override):
    with pytest.raises(ValueError):
        candidate(**override)


def test_verification_cannot_precede_discovery():
    with pytest.raises(ValueError, match="Verification cannot precede discovery"):
        candidate(verified_on=date(2026, 1, 1))


def test_http_endpoint_is_refused():
    with pytest.raises(ValueError):
        candidate(endpoint="http://news.example.org/feed.xml")


# --- rights states -------------------------------------------------------------

def test_technically_valid_but_rights_unknown_stays_unverified(root):
    register(candidate(), actor="owner-researcher", now=NOW, root=root)
    ledger = load_ledger(root)
    assert current_state(ledger, "example_tech") == ("DISCOVERED", candidate().identity)
    assert readiness(candidate()) == "RIGHTS_UNVERIFIED"
    assert "rights_evidence_missing" in missing_evidence(candidate())


def test_permissions_cannot_be_asserted_without_evidence(root):
    with pytest.raises(ValueError, match="Permissions cannot be asserted"):
        candidate(summary_allowed=True)


def test_permissions_require_recorded_evidence_and_reviewer(root):
    with pytest.raises(ValueError, match="Permission claims require recorded"):
        candidate(summary_allowed=True, rights_evidence_status="EVIDENCE_RECORDED")
    with pytest.raises(ValueError, match="Permission claims require recorded"):
        candidate(summary_allowed=True, rights_evidence_status="EVIDENCE_RECORDED", evidence=[])
    permitted = candidate(
        summary_allowed=True, rights_evidence_status="EVIDENCE_RECORDED",
        evidence=[{"url": "https://news.example.org/license", "kind": "license",
                   "note": "Publisher states excerpts may be summarised with attribution."}],
        reviewer_reference="owner-designated-reviewer", review_decision_at=NOW)
    assert permitted.summary_allowed is True


def test_denied_rights_cannot_permit_ai_submission(root):
    with pytest.raises(ValueError, match="Permissions cannot be asserted"):
        candidate(rights_evidence_status="RIGHTS_DENIED", ai_submission_allowed=True)
    assert readiness(candidate(rights_evidence_status="RIGHTS_DENIED")) == "EXCLUDED"


def test_revoked_candidate_reports_revoked(root):
    assert readiness(candidate(rights_evidence_status="REVOKED")) == "REVOKED"


def test_metadata_permission_does_not_imply_reproduction(root):
    partial = candidate(summary_allowed=True, rights_evidence_status="EVIDENCE_RECORDED",
                        evidence=[{"url": "https://news.example.org/terms", "kind": "terms",
                                   "note": "Summaries permitted; full text reuse is not."}],
                        reviewer_reference="owner-designated-reviewer", review_decision_at=NOW)
    assert partial.summary_allowed is True
    assert partial.reproduction_allowed is None
    assert "reproduction_allowed" not in partial.model_dump(exclude_none=True)


# --- reviewer evidence ---------------------------------------------------------

def test_missing_reviewer_evidence_is_reported_not_guessed(root):
    gaps = missing_evidence(candidate())
    assert "no_human_reviewer_reference" in gaps
    assert "reviewer_reference_without_decision_time" not in gaps


def test_reviewer_reference_without_decision_time_is_reported(root):
    gaps = missing_evidence(candidate(reviewer_reference="owner-designated-reviewer"))
    assert "reviewer_reference_without_decision_time" in gaps


def test_control_characters_in_reviewer_identity_are_refused(root):
    with pytest.raises(ValueError):
        candidate(reviewer_reference="owner\u202ereviewer")


def test_unconfirmed_fetch_outcome_is_a_gap(root):
    assert "no_confirmed_fetch_outcome" in missing_evidence(candidate())
    observed = candidate(last_fetch_outcome="FAILED", last_fetch_observed_at=NOW)
    assert "no_confirmed_fetch_outcome" not in missing_evidence(observed)


# --- identity and endpoint drift ----------------------------------------------

def test_duplicate_source_identity_is_refused(root):
    register(candidate(), actor="owner-researcher", now=NOW, root=root)
    with pytest.raises(DuplicateCandidate, match="already exists"):
        register(candidate(candidate_id="example_tech_two"), actor="owner-researcher", now=NOW, root=root)
    with pytest.raises(ValueError, match="already registered"):
        register(candidate(), actor="owner-researcher", now=NOW, root=root)


def test_same_publisher_different_language_is_a_distinct_candidate(root):
    register(candidate(), actor="owner-researcher", now=NOW, root=root)
    register(candidate(candidate_id="example_tech_bn", language="bn"), actor="owner-researcher", now=NOW, root=root)
    assert len(load_ledger(root).events) == 2


def test_changed_feed_url_requires_revalidation(root):
    register(candidate(), actor="owner-researcher", now=NOW, root=root)
    moved = candidate(endpoint="https://news.example.org/feed-v2.xml")
    moved, _ = transition(moved, "TECHNICALLY_VALIDATED", actor="owner-researcher", now=NOW,
                          reason="Feed reachable over HTTPS.", root=root)
    with pytest.raises(ValueError, match="Feed endpoint must be served"):
        candidate(endpoint="https://cdn.other.example.net/feed.xml")
    # The changed URL is accepted as a new observation but does not silently
    # inherit rights evidence recorded against the previous endpoint.
    assert moved.verified_on == NOW.date()


def test_candidate_identity_change_is_refused(root):
    register(candidate(), actor="owner-researcher", now=NOW, root=root)
    renamed = candidate(fetch_method="json_api", endpoint="https://news.example.org/api.json")
    with pytest.raises(ValueError, match="identity changed"):
        transition(renamed, "TECHNICALLY_VALIDATED", actor="owner-researcher", now=NOW, reason="x", root=root)


# --- authority boundary --------------------------------------------------------

@pytest.mark.parametrize("target", sorted(AUTHORITY_GATED))
def test_authority_gated_transitions_are_blocked(root, target):
    register(candidate(), actor="owner-researcher", now=NOW, root=root)
    with pytest.raises(Exception, match="authenticated reviewer authority"):
        transition(candidate(), target, actor="owner-researcher", now=NOW, reason="Attempted.", root=root)


def test_accidental_activation_attempt_is_refused(root):
    register(candidate(), actor="owner-researcher", now=NOW, root=root)
    with pytest.raises(ValueError):
        transition(candidate(), "ACTIVATED", actor="owner-researcher", now=NOW, reason="Enable now.", root=root)
    assert current_state(load_ledger(root), "example_tech")[0] == "DISCOVERED"


def test_legal_forward_transitions_succeed(root):
    register(candidate(), actor="owner-researcher", now=NOW, root=root)
    validated, _ = transition(candidate(), "TECHNICALLY_VALIDATED", actor="owner-researcher", now=NOW,
                              reason="Feed reachable and parsed.", root=root)
    assert validated.verified_on == NOW.date()
    held, _ = transition(validated, "RIGHTS_REVIEW_REQUIRED", actor="owner-researcher",
                         now=NOW + timedelta(hours=1), reason="Held for rights review.", root=root)
    assert held.candidate_id == "example_tech"
    assert current_state(load_ledger(root), "example_tech")[0] == "RIGHTS_REVIEW_REQUIRED"


def test_illegal_transition_is_refused(root):
    register(candidate(), actor="owner-researcher", now=NOW, root=root)
    with pytest.raises(ValueError, match="Illegal candidate transition"):
        transition(candidate(), "EDITORIAL_REVIEW_REQUIRED", actor="owner-researcher", now=NOW, reason="Skip.", root=root)


def test_revocation_is_reachable_from_any_non_terminal_state(root):
    register(candidate(), actor="owner-researcher", now=NOW, root=root)
    _, _ = transition(candidate(), "TECHNICALLY_VALIDATED", actor="owner-researcher", now=NOW,
                      reason="Reachable.", root=root)
    validated = candidate(verified_on=NOW.date())
    _, _ = transition(validated, "RIGHTS_REVIEW_REQUIRED", actor="owner-researcher",
                      now=NOW + timedelta(hours=1), reason="Held.", root=root)
    _, _ = transition(validated, "REVOKED", actor="owner-researcher", now=NOW + timedelta(hours=2),
                      reason="Publisher withdrew permission.", root=root)
    assert current_state(load_ledger(root), "example_tech")[0] == "REVOKED"


def test_terminal_state_accepts_no_further_transition(root):
    register(candidate(), actor="owner-researcher", now=NOW, root=root)
    transition(candidate(), "REVOKED", actor="owner-researcher", now=NOW, reason="Withdrawn.", root=root)
    with pytest.raises(ValueError, match="Illegal candidate transition"):
        transition(candidate(), "TECHNICALLY_VALIDATED", actor="owner-researcher",
                   now=NOW + timedelta(hours=1), reason="Reactivate.", root=root)


# --- tamper evidence -----------------------------------------------------------

def test_tampered_candidate_record_is_detected(root):
    register(candidate(), actor="owner-researcher", now=NOW, root=root)
    path = root / ".cache/phase6/source-candidates.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["events"][0]["candidate_sha256"] = "0" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="Corrupted or reordered"):
        load_ledger(root)


def test_forged_ledger_claiming_activation_is_rejected(root):
    register(candidate(), actor="owner-researcher", now=NOW, root=root)
    path = root / ".cache/phase6/source-candidates.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    previous = payload["head_sha256"]
    from pipeline.review_governance import digest
    from pipeline.source_onboarding import TransitionRecord
    forged = TransitionRecord(from_state="DISCOVERED", to_state="ELIGIBLE_FOR_ACTIVATION",
                              actor="owner-designated-reviewer", at=NOW, reason="Approved by the owner.",
                              evidence_sha256=None, from_candidate_sha256=None, to_candidate_sha256="0" * 64)
    event_body = {"sequence": 2, "candidate_id": "example_tech", "identity": candidate().identity,
                  "previous_sha256": previous, "registered": False, "transition": forged.model_dump(mode="json"),
                  "candidate_sha256": None}
    event = {**event_body, "event_sha256": digest(event_body)}
    payload["events"].append(event)
    payload["head_sha256"] = event["event_sha256"]
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="cannot authorise"):
        load_ledger(root)


def test_reordered_events_are_rejected(root):
    register(candidate(), actor="owner-researcher", now=NOW, root=root)
    validated = candidate(verified_on=NOW.date())
    transition(validated, "TECHNICALLY_VALIDATED", actor="owner-researcher", now=NOW, reason="Reachable.", root=root)
    path = root / ".cache/phase6/source-candidates.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["events"].reverse()
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="Corrupted or reordered"):
        load_ledger(root)


def test_aware_clock_is_required(root):
    register(candidate(), actor="owner-researcher", now=NOW, root=root)
    with pytest.raises(ValueError, match="aware clock"):
        transition(candidate(), "TECHNICALLY_VALIDATED", actor="owner-researcher",
                   now=datetime(2026, 10, 19, 9), reason="Naive clock.", root=root)


# --- reporting -----------------------------------------------------------------

def test_report_never_claims_activation(root):
    register(candidate(), actor="owner-researcher", now=NOW, root=root)
    result = report(root)
    assert result["publication_allowed"] is False
    assert result["ai_submission_allowed"] is False
    assert result["activable_candidates"] == []
    assert result["authority_gated_states"] == sorted(AUTHORITY_GATED)