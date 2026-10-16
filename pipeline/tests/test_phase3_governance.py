"""Synthetic operator evidence only; these records never grant real rights."""

import json
import os
import subprocess
from datetime import timedelta
from pathlib import Path

import pytest

from pipeline import review_governance as governance
from pipeline.models import SourceRegistry
from pipeline.normalize import normalize
from pipeline.pilot_attribution import attribution_contract
from pipeline.runner import config


def candidate(now, source_id="kubernetes", **changes):
    source = next(s for s in SourceRegistry.model_validate(config("sources")).sources if s.id == source_id)
    raw = {"url": "https://kubernetes.io/blog/techline-synthetic-fixture/",
           "title": "Synthetic Kubernetes fixture update", "text": "Synthetic engineering prose for local tests only.",
           "published_at": (now - timedelta(hours=1)).isoformat(), "is_demo": True,
           "approved": True, "reviewer_identity": "untrusted-feed"}
    if source_id == "cisa_kev":
        raw.update(url="https://www.cisa.gov/known-exploited-vulnerabilities-catalog?search_api_fulltext=CVE-2026-9999",
                   title="CVE-2026-9999: synthetic fixture only", external_id="CVE-2026-9999",
                   catalog_added_on=now.date().isoformat(),
                   remediation_due_on=(now + timedelta(days=7)).date().isoformat())
    raw.update(changes)
    item = normalize(raw, source, now)
    return source, raw, item, governance.bind_item(item, raw)


@pytest.fixture
def local_decision(now):
    source, _, _, binding = candidate(now)
    return governance.draft(binding, source.name, "synthetic-operator", now, synthetic=True)


def test_missing_review_denies_all(now):
    _, _, item, binding = candidate(now)
    result = governance.evaluate(binding, governance.ReviewLedger(), now)
    assert result == {"publication_allowed": False, "ai_submission_allowed": False,
                      "approval_path_active": False, "reason": "missing_record",
                      "policy_version": governance.POLICY_VERSION}
    assert not item.publication_eligible


def test_local_review_schema_matches_inactive_contract():
    path = Path(__file__).resolve().parents[2] / "schemas/local-rights-review.schema.json"
    expected = {"$schema": "https://json-schema.org/draft/2020-12/schema", **governance.ReviewLedger.model_json_schema()}
    assert json.loads(path.read_text(encoding="utf-8")) == expected


def test_synthetic_scoped_evidence_is_preserved_without_granting_rights(now, local_decision):
    source, _, item, binding = candidate(now)
    evidence = [governance.ReviewEvidence(url=f"https://rights.example/synthetic-{scope}", scope=scope,
                note="Synthetic evidence only; no real permission or attribution established.")
                for scope in ("license-grant", "creator", "original-publication")]
    record = governance.ReviewDecision.model_validate({**local_decision.model_dump(),
        "evidence": evidence, "applicable_license": "SYNTHETIC-NO-GRANT", "original_creator": "Synthetic Fixture Creator",
        "original_publication_url": "https://rights.example/synthetic-original-publication",
        "attribution_obligations": ["Synthetic credit obligation; not a real publisher instruction."],
        "license_exceptions": ["Synthetic exception for this test only."]})
    contract = attribution_contract(item, source, binding, now, decision=record)
    assert contract["original_creator"] == "Synthetic Fixture Creator"
    assert contract["license_status"] == "unapproved"
    assert contract["creator_evidence_status"] == "recorded-unapproved"
    assert not contract["rights_review"]["publication_allowed"]


@pytest.mark.parametrize("timestamp", ["2026-10-16", "2026-10-16T10:00:00", 1792144800, None])
def test_review_timestamp_ambiguity_is_rejected(local_decision, timestamp):
    with pytest.raises(ValueError):
        governance.ReviewDecision.model_validate({**local_decision.model_dump(mode="json"), "reviewed_at": timestamp})


@pytest.mark.parametrize("state", ["APPROVED", "APPROVED_WITH_EVIDENCE", "allow", True, None])
def test_forged_approval_states_are_invalid(local_decision, state):
    with pytest.raises(ValueError):
        governance.ReviewDecision.model_validate({**local_decision.model_dump(mode="json"), "review_status": state})


@pytest.mark.parametrize("field", ["approved", "signature", "ai_submission_allowed", "publication_allowed"])
def test_unknown_decision_fields_fail_closed(local_decision, field):
    with pytest.raises(ValueError):
        governance.ReviewDecision.model_validate({**local_decision.model_dump(mode="json"), field: True})


def test_feed_claims_do_not_create_operator_decisions(now):
    _, raw, item, binding = candidate(now)
    assert raw["approved"] and item.rights_review.state == "REVIEW_REQUIRED"
    assert governance.evaluate(binding, governance.ReviewLedger(), now)["reason"] == "missing_record"


def test_ledger_deterministic_atomic_and_nonpublishing(tmp_path, local_decision, now):
    first = governance.append_decision(tmp_path, local_decision)
    second_root = tmp_path / "other"
    assert governance.append_decision(second_root, local_decision).event_sha256 == first.event_sha256
    path = governance.local_path(tmp_path, ".cache/phase3/reviews/ledger.json")
    ledger = governance.load_ledger(path)
    assert ledger.head_sha256 == first.event_sha256
    assert governance.evaluate(local_decision.binding, ledger, now)["reason"] == "review_required"
    assert "Synthetic engineering prose" not in path.read_text()
    assert "untrusted-feed" not in path.read_text()
    assert not governance.evaluate(local_decision.binding, ledger, now)["publication_allowed"]


@pytest.mark.parametrize("mutation", ["binding", "event_hash", "previous_hash", "head", "sequence", "extra"])
def test_corrupted_ledger_rejected(tmp_path, local_decision, mutation):
    governance.append_decision(tmp_path, local_decision)
    path = governance.local_path(tmp_path, ".cache/phase3/reviews/ledger.json")
    data = json.loads(path.read_text())
    event = data["events"][0]
    if mutation == "binding":
        event["decision"]["binding"]["content_sha256"] = "a" * 64
    elif mutation == "event_hash":
        event["event_sha256"] = "b" * 64
    elif mutation == "previous_hash":
        event["previous_sha256"] = "c" * 64
    elif mutation == "head":
        data["head_sha256"] = "d" * 64
    elif mutation == "sequence":
        event["sequence"] = 8
    else:
        event["grant"] = True
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        governance.load_ledger(path)


def test_recomputed_forgery_still_cannot_approve(tmp_path, local_decision):
    event = governance.append_decision(tmp_path, local_decision).model_dump(mode="json")
    event["decision"]["review_status"] = "APPROVED"
    event["event_sha256"] = governance.digest({k: v for k, v in event.items() if k != "event_sha256"})
    with pytest.raises(ValueError):
        governance.ReviewLedger.model_validate({"version": 1, "events": [event], "head_sha256": event["event_sha256"]})


@pytest.mark.parametrize("change,reason", [({"policy_version": "obsolete-policy"}, "policy_changed"),
                                         ({"review_status": "REVOKED"}, "revoked"),
                                         ({"review_status": "REJECTED"}, "rejected")])
def test_policy_revocation_and_rejection_deny(tmp_path, local_decision, now, change, reason):
    governance.append_decision(tmp_path, local_decision.model_copy(update=change))
    ledger = governance.load_ledger(governance.local_path(tmp_path, ".cache/phase3/reviews/ledger.json"))
    assert governance.evaluate(local_decision.binding, ledger, now)["reason"] == reason


def test_stale_future_changed_and_revoked_records_fail_closed(tmp_path, local_decision, now):
    governance.append_decision(tmp_path, local_decision)
    path = governance.local_path(tmp_path, ".cache/phase3/reviews/ledger.json")
    ledger = governance.load_ledger(path)
    assert governance.evaluate(local_decision.binding, ledger, now + timedelta(days=31))["reason"] == "expired_review"
    assert governance.evaluate(local_decision.binding, ledger, now - timedelta(hours=1))["reason"] == "future_review"
    changed = local_decision.binding.model_copy(update={"evidence_sha256": "f" * 64})
    assert governance.evaluate(changed, ledger, now)["reason"] == "evidence_or_identity_changed"
    revocation = local_decision.model_copy(update={"review_status": "REVOKED", "reviewed_at": now + timedelta(minutes=1)})
    governance.append_decision(tmp_path, revocation)
    assert governance.evaluate(local_decision.binding, governance.load_ledger(path), now + timedelta(minutes=2))["reason"] == "revoked"


@pytest.mark.parametrize("changes", [{"item_id": "src_" + "0" * 20}, {"source_id": "other"},
                                     {"canonical_url": "https://kubernetes.io/other"},
                                     {"canonical_url": "https://127.0.0.1/private"},
                                     {"canonical_url": "javascript:alert(1)"}])
def test_mismatched_or_unsafe_identity_rejected(local_decision, changes):
    with pytest.raises(ValueError):
        governance.ItemBinding.model_validate({**local_decision.binding.model_dump(), **changes})


@pytest.mark.parametrize("changes", [{"original_creator": "Invented creator"},
                                     {"original_publication_url": "https://rights.example/original"},
                                     {"applicable_license": "Synthetic-Test-License"},
                                     {"publisher": "<script>bad</script>"},
                                     {"reviewer_identity": ""}])
def test_unestablished_attribution_and_markup_rejected(local_decision, changes):
    with pytest.raises(ValueError):
        governance.ReviewDecision.model_validate({**local_decision.model_dump(), **changes})


def test_duplicate_keys_and_oversized_local_json_rejected(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"events":[],"events":[{}]}')
    with pytest.raises(ValueError, match="Duplicate"):
        governance.bounded_json(path)
    path.write_bytes(b" " * 101)
    with pytest.raises(ValueError, match="size"):
        governance.bounded_json(path, limit=100)


@pytest.mark.parametrize("path", ["content/generated/snapshot.json", ".cache/phase3/../../../config/sources.yaml",
                                  ".cache/rights-review.json", "C:/private.json"])
def test_local_writes_cannot_escape_isolation(tmp_path, path):
    with pytest.raises(ValueError):
        governance.local_path(tmp_path, path)


def test_linked_state_directory_cannot_redirect_writes(tmp_path):
    target = tmp_path / "outside-state"
    target.mkdir()
    link = tmp_path / ".cache/phase3"
    link.parent.mkdir()
    if os.name == "nt":
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],  # noqa: S603,S607 - fixed local fixture command
                       check=True, capture_output=True)
    else:
        link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="Linked"):
        governance.local_path(tmp_path, ".cache/phase3/reviews/ledger.json")
    assert not list(target.iterdir())


def test_same_domain_different_item_cannot_inherit_review(tmp_path, local_decision, now):
    governance.append_decision(tmp_path, local_decision)
    _, _, _, other_binding = candidate(now, url="https://kubernetes.io/blog/different-synthetic-item/")
    ledger = governance.load_ledger(governance.local_path(tmp_path, ".cache/phase3/reviews/ledger.json"))
    assert governance.evaluate(other_binding, ledger, now)["reason"] == "missing_record"


def test_partial_write_and_busy_writer_preserve_previous_ledger(tmp_path, local_decision, monkeypatch):
    governance.append_decision(tmp_path, local_decision)
    path = governance.local_path(tmp_path, ".cache/phase3/reviews/ledger.json")
    before = path.read_bytes()
    def interrupted(*args):
        raise OSError("Synthetic interruption before commit")
    with monkeypatch.context() as patch:
        patch.setattr(governance, "atomic_json", interrupted)
        with pytest.raises(OSError):
            governance.append_decision(tmp_path, local_decision)
    assert path.read_bytes() == before
    lock = path.with_name("writer.lock")
    lock.write_text("synthetic interrupted writer")
    with pytest.raises(FileExistsError):
        governance.append_decision(tmp_path, local_decision)
    assert path.read_bytes() == before


@pytest.mark.parametrize("source_id", ["kubernetes", "cisa_kev"])
def test_attribution_contract_end_to_end_is_held(now, source_id):
    source, _, item, binding = candidate(now, source_id)
    contract = attribution_contract(item, source, binding, now)
    assert contract["internal_only"] and contract["synthetic"]
    assert not contract["rights_review"]["publication_allowed"]
    assert not contract["rights_review"]["ai_submission_allowed"]
    assert not contract["breaking_news"] and not contract["independently_verified"]
    assert contract["publisher"] == source.name and contract["required_attribution_link"] == item.canonical_url
    assert contract["original_creator"] is None and contract["applicable_license"] is None
    if source_id == "cisa_kev":
        assert contract["published_at"] is None
        assert len(contract["catalog_added_on"]) == 10 and len(contract["remediation_due_on"]) == 10
        assert "catalog" in contract["date_labels"]["catalog_added"]
        assert not contract["third_party_references"]["fetched"]


def test_cross_source_attribution_rejected(now):
    source, _, item, binding = candidate(now)
    other, _, _, _ = candidate(now, "cisa_kev")
    with pytest.raises(ValueError, match="Cross-source"):
        attribution_contract(item, other, binding, now)
    assert not source.enabled


@pytest.mark.parametrize("source_id", ["kubernetes", "cisa_kev"])
def test_internal_contract_is_rejected_by_existing_javascript_publication_gate(now, source_id):
    source, _, item, binding = candidate(now, source_id)
    contract = attribution_contract(item, source, binding, now)
    script = ("import fs from 'node:fs'; import {contentRightsErrors} from './scripts/content-rights.mjs'; "
              "const candidate=JSON.parse(fs.readFileSync(0,'utf8')); "
              "console.log(JSON.stringify(contentRightsErrors(candidate)));")
    # Argument list and stdin avoid shell interpolation of any source data.
    result = subprocess.run(["node", "--input-type=module", "-e", script],  # noqa: S603,S607 - fixed local executable/code
                            input=json.dumps({"mode": "live", "sources": {"one": contract}, "stories": []}),
                            text=True, capture_output=True, timeout=20, check=True)
    assert "Local-only" in " ".join(json.loads(result.stdout))
