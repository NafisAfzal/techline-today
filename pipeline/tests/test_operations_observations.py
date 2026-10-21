import json
from datetime import timedelta

import pytest

from pipeline import observations
from pipeline.operations.observation import review_observations
from pipeline.recovery.fixtures import SYNTHETIC_NOW
from pipeline.review_governance import digest

CONTEXT = {"version": 1, "environment_id": "synthetic-test", "ledger_id": "synthetic-ledger",
           "provenance": "operator-local"}


def receipts(root, *, mutate=None, context=True):
    directory = root / observations.DIRECTORY
    directory.mkdir(parents=True)
    for i in range(8):
        at = SYNTHETIC_NOW - timedelta(days=7 - i)
        row = {"version": 1, "live": True, "observed_at": at.isoformat(), "run_id": f"synthetic-{i}",
               "report_sha256": digest({"synthetic_run": i}), "collection_state": "COLLECTION_SUCCESS",
               "publication_allowed": False, "ai_submission_allowed": False,
               "sources": [{"source_id": "synthetic", "collection_state": "COLLECTION_SUCCESS",
                            "rights_status": "RIGHTS_REVIEW_REQUIRED"}]}
        if context:
            row["context"] = dict(CONTEXT)
        if mutate:
            mutate(row, i)
        row["receipt_sha256"] = digest(row)
        (directory / f"{at.date().isoformat()}.json").write_text(json.dumps(row), encoding="utf-8")


def review(root):
    return review_observations(root, environment_id="synthetic-test", ledger_id="synthetic-ledger",
                               now=SYNTHETIC_NOW)


def test_locally_forged_seven_day_window_cannot_become_authenticated(tmp_path):
    receipts(tmp_path)
    result = review(tmp_path)
    assert result["window"]["elapsed_window_satisfied"]
    assert result["local_context_consistent"] and result["status"] == "BLOCKED"
    assert result["genuinely_authenticated_days"] == 0
    assert not result["eligible"] and not result["independent_provenance_verified"]


def test_legacy_unbound_receipts_remain_readable_but_not_context_verified(tmp_path):
    receipts(tmp_path, context=False)
    result = review(tmp_path)
    assert result["unbound_receipts"] == list(range(8))
    assert not result["local_context_consistent"] and not result["publication_allowed"]


@pytest.mark.parametrize("field,value", [("environment_id", "other"), ("ledger_id", "other"),
                                         ("provenance", "synthetic")])
def test_rehashed_wrong_context_is_rejected(tmp_path, field, value):
    receipts(tmp_path, mutate=lambda row, i: row["context"].update({field: value}) if i == 3 else None)
    result = review(tmp_path)
    assert result["status"] == "FAIL" and result["mismatched_receipts"] == [3]
    assert not result["eligible"]


@pytest.mark.parametrize("attack", ["missing", "duplicate", "future", "synthetic"])
def test_observation_attack_preserves_existing_window_denials(tmp_path, attack):
    def mutate(row, i):
        if i == 3:
            if attack == "duplicate":
                row["run_id"] = "synthetic-0"
            elif attack == "future":
                row["observed_at"] = (SYNTHETIC_NOW + timedelta(days=1)).isoformat()
            elif attack == "synthetic":
                row["live"] = False
                row["context"]["provenance"] = "synthetic"
    receipts(tmp_path, mutate=mutate)
    if attack == "missing":
        (tmp_path / observations.DIRECTORY / "2026-10-16.json").unlink()
    result = review(tmp_path)
    assert not result["window"]["elapsed_window_satisfied"] and not result["eligible"]


async def test_invalid_context_refused_before_transport_or_writes(tmp_path, monkeypatch):
    async def forbidden(**kwargs):
        pytest.fail("Invalid context reached collection")
    monkeypatch.setattr(observations, "run_diagnostics", forbidden)
    with pytest.raises(ValueError, match="contradicts"):
        await observations.observe(tmp_path, live=True, context={**CONTEXT, "provenance": "synthetic"})
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("invalid", [{**CONTEXT, "version": True}, {**CONTEXT, "environment_id": "bad\n"},
                                    {**CONTEXT, "independently_trusted": True}])
def test_context_strictly_rejects_forged_trust_fields(invalid):
    with pytest.raises(ValueError):
        observations.ObservationContext.model_validate(invalid)
