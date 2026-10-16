"""Independent-audit regressions. Every write and decision is a temporary fixture."""

import json
import random
import shutil
import sys
from datetime import timedelta

import pytest

from pipeline import pilot_staging as staging
from pipeline import review_governance as governance
from pipeline.adapters import ADAPTERS
from pipeline.dedupe import deduplicate
from pipeline.models import Snapshot, SourceItem, SourceRegistry
from pipeline.normalize import normalize
from pipeline.pilot_attribution import attribution_contract
from pipeline.runner import ROOT, config
from pipeline.tests.test_phase3_governance import candidate


@pytest.fixture
def isolated(tmp_path):
    shutil.copytree(ROOT / "config", tmp_path / "config")
    return tmp_path


def pilots():
    return [s for s in SourceRegistry.model_validate(config("sources")).sources
            if s.id in {"kubernetes", "cisa_kev"}]


@pytest.mark.parametrize("broken,aggregate", [(2, "total_failure"), (1, "partial_degradation"), (0, "success")])
async def test_normal_failure_verdict_and_last_good(isolated, monkeypatch, broken, aggregate):
    good, path = await staging.run_staging(isolated, scenarios=("normal",))
    before = path.read_bytes()

    async def fail(*args):
        raise ValueError("Unexpected adapter failure; body must not be retained")

    for source in pilots()[:broken]:
        monkeypatch.setattr(ADAPTERS[source.adapter], "fetch", fail)
    report, path = await staging.run_staging(isolated, scenarios=("normal", "total-outage"))
    assert report["outcome"] == aggregate
    assert report["status"] == ("failed" if broken else "passed")
    assert json.loads(path.read_text())["status"] == report["status"]
    if broken:
        assert (path.parent / "last-successful-report.json").read_bytes() == before
    assert good["status"] == "passed"
    normal = report["deterministic"]["results"][0]
    assert all(o["attempted"] and o["source_id"] and "error_category" in o for o in normal["outcomes"])
    assert "body must not be retained" not in path.read_text()


@pytest.mark.parametrize("scenario,outcome", [("empty-feed", "empty"), ("timeout", "total_failure"),
                                             ("malformed-xml", "partial_degradation"),
                                             ("malformed-json", "partial_degradation")])
async def test_expected_source_outcomes(isolated, scenario, outcome):
    report, _ = await staging.run_staging(isolated, scenarios=(scenario,))
    assert report["status"] == "passed"
    assert report["outcome"] == outcome
    assert all(o["attempted"] for o in report["deterministic"]["results"][0]["outcomes"])
    if scenario == "timeout":
        assert report["deterministic"]["results"][0]["attempts"] == {"kubernetes": 3, "cisa_kev": 3}


@pytest.mark.parametrize("broken,exit_code", [(True, 1), (False, 0)])
def test_staging_cli_signals_actual_outcome(isolated, monkeypatch, capsys, broken, exit_code):
    original = staging.run_staging

    async def run(**kwargs):
        return await original(isolated, **kwargs)

    async def fail(*args):
        raise TimeoutError("Synthetic timeout")

    monkeypatch.setattr(staging, "run_staging", run)
    if broken:
        for source in pilots():
            monkeypatch.setattr(ADAPTERS[source.adapter], "fetch", fail)
    monkeypatch.setattr(sys, "argv", ["pilot_staging", "--scenario", "normal"])
    with pytest.raises(SystemExit) as error:
        staging.main()
    assert error.value.code == exit_code
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == ("failed" if broken else "passed")
    assert data["outcome"] == ("total_failure" if broken else "success")


@pytest.mark.parametrize("missing", ["config/sources.yaml", "config/source-rights.json"])
def test_missing_configuration_cli_refuses(isolated, monkeypatch, capsys, missing):
    (isolated / missing).unlink()
    original = staging.run_staging

    async def run(**kwargs):
        return await original(isolated, **kwargs)

    monkeypatch.setattr(staging, "run_staging", run)
    monkeypatch.setattr(sys, "argv", ["pilot_staging", "--scenario", "normal"])
    with pytest.raises(SystemExit) as error:
        staging.main()
    assert error.value.code == 1
    assert json.loads(capsys.readouterr().out)["status"] == "refused"


async def test_stable_failure_with_old_cached_data(isolated, monkeypatch):
    await staging.run_staging(isolated, scenarios=("normal",))
    cache = isolated / ".cache/phase3/staging/old-items.json"
    cache.write_text('{"items":[{"approved":true}]}')

    async def fail(*args):
        raise ValueError("Synthetic failure")

    for source in pilots():
        monkeypatch.setattr(ADAPTERS[source.adapter], "fetch", fail)
    first, _ = await staging.run_staging(isolated, scenarios=("normal",))
    second, _ = await staging.run_staging(isolated, scenarios=("normal",))
    assert first["status"] == second["status"] == "failed"
    assert first["deterministic_sha256"] == second["deterministic_sha256"]
    assert not first["deterministic"]["results"][0]["observations"]


def test_synthetic_binding_roundtrip_and_default_draft(now):
    source, _, item, binding = candidate(now)
    serialized = json.loads(binding.model_dump_json())
    assert serialized["provenance"] == "synthetic"
    restored = governance.ItemBinding.model_validate(serialized)
    decision = governance.draft(restored, source.name, "Synthetic operator", now)
    assert decision.synthetic
    assert decision.binding.provenance == "synthetic"
    assert attribution_contract(SourceItem.model_validate_json(item.model_dump_json()), source,
                                restored, now, decision=decision)["provenance"] == "synthetic"


@pytest.mark.parametrize("origin", [None, True, "verified", {}, "", "collected"])
def test_malformed_or_unattested_provenance_rejected(now, origin):
    *_, binding = candidate(now)
    with pytest.raises(ValueError):
        governance.ItemBinding.model_validate({**binding.model_dump(), "provenance": origin})


def test_missing_and_feed_supplied_origin_remain_unknown(now):
    source, raw, item, _ = candidate(now, is_demo=False, provenance="verified-publisher")
    binding = governance.bind_item(item, raw)
    assert binding.provenance == "unknown"
    data = binding.model_dump()
    del data["provenance"]
    assert governance.ItemBinding.model_validate(data).provenance == "unknown"
    contract = attribution_contract(item, source, binding, now)
    assert contract["provenance"] == "unknown" and not contract["rights_review"]["publication_allowed"]


def test_contradictory_synthetic_decision_and_item_rejected(now):
    source, _, item, binding = candidate(now)
    decision = governance.draft(binding, source.name, "Synthetic operator", now)
    with pytest.raises(ValueError):
        governance.ReviewDecision.model_validate({**decision.model_dump(), "synthetic": False})
    with pytest.raises(ValueError):
        attribution_contract(item.model_copy(update={"is_demo": False}), source, binding, now, decision=decision)


def test_governance_cli_preserves_origin_without_flag(isolated, now, monkeypatch, capsys):
    source, _, _, binding = candidate(now)
    path = isolated / "binding.json"
    path.write_text(binding.model_dump_json())
    monkeypatch.setattr(governance, "__file__", str(isolated / "pipeline/review_governance.py"))
    monkeypatch.setattr(sys, "argv", ["review", "draft", "--file", str(path),
                                     "--publisher", source.name, "--reviewer", "Synthetic operator"])
    governance.main()
    data = json.loads(capsys.readouterr().out)
    assert data["synthetic"] and data["binding"]["provenance"] == "synthetic"
    assert json.loads((isolated / ".cache/phase3/reviews/draft.json").read_text()) == data


def scoped(now, **changes):
    source, raw, item, binding = candidate(now, **changes)
    decision = governance.draft(binding, source.name, "Synthetic operator", now)
    data = {**decision.model_dump(), "original_creator": "Synthetic creator", "applicable_license": "TEST-NO-GRANT",
            "permitted_fields": ["title"], "permitted_transformations": ["translation"],
            "attribution_obligations": ["Synthetic credit"],
            "evidence": [governance.ReviewEvidence(url="https://rights.example/synthetic", scope=scope,
                         note="Synthetic-only evidence") for scope in ("creator", "license-grant")]}
    return source, raw, item, binding, governance.ReviewDecision.model_validate(data)


def test_scope_and_review_share_authoritative_record(tmp_path, now):
    source, _, item, binding, decision = scoped(now)
    event = governance.append_decision(tmp_path, decision)
    ledger = governance.load_ledger(tmp_path / ".cache/phase3/reviews/ledger.json")
    contract = json.loads(json.dumps(attribution_contract(item, source, binding, now, ledger=ledger)))
    assert contract["permitted_fields"] == ["title"]
    assert contract["permitted_transformations"] == ["translation"]
    assert contract["rights_review"]["reason"] == "review_required"
    assert contract["review_decision"]["event_sha256"] == event.event_sha256
    assert contract["applicable_license"] == "TEST-NO-GRANT" and contract["license_status"] == "unapproved"
    assert not contract["rights_review"]["publication_allowed"]


@pytest.mark.parametrize("change,offset,reason", [({}, 31, "expired_review"),
    ({"review_status": "REVOKED"}, 0, "revoked"), ({"review_status": "REJECTED"}, 0, "rejected"),
    ({"policy_version": "obsolete"}, 0, "policy_changed")])
def test_stale_claims_are_quarantined(tmp_path, now, change, offset, reason):
    source, _, item, binding, decision = scoped(now)
    governance.append_decision(tmp_path, decision.model_copy(update=change))
    ledger = governance.load_ledger(tmp_path / ".cache/phase3/reviews/ledger.json")
    contract = attribution_contract(item, source, binding, now + timedelta(days=offset), ledger=ledger)
    assert contract["rights_review"]["reason"] == reason
    assert contract["applicable_license"] is None and contract["original_creator"] is None
    assert contract["permitted_fields"] == [] and contract["license_status"] == "unresolved"
    assert contract["quarantined_review"]["applicable_license"] == "TEST-NO-GRANT"


def test_cached_review_cannot_override_revocation(tmp_path, now):
    source, _, item, binding, decision = scoped(now)
    governance.append_decision(tmp_path, decision)
    governance.append_decision(tmp_path, decision.model_copy(update={"review_status": "REVOKED"}))
    ledger = governance.load_ledger(tmp_path / ".cache/phase3/reviews/ledger.json")
    contract = attribution_contract(item, source, binding, now, ledger=ledger, decision=decision)
    assert contract["rights_review"]["reason"] == "revoked"
    assert contract["cached_decision_status"] == "superseded"
    assert contract["applicable_license"] is None


def test_untrusted_decision_only_is_proposal(now):
    source, _, item, binding, decision = scoped(now)
    contract = attribution_contract(item, source, binding, now, decision=decision)
    assert contract["rights_review"]["reason"] == "missing_record"
    assert contract["review_decision"] is None
    assert contract["proposed_review"]["review_status"] == "REVIEW_REQUIRED"
    assert contract["license_status"] == "unapproved"
    assert contract["permitted_fields"] == ["title"]


@pytest.mark.parametrize("synthetic", [True, False])
def test_modified_content_loses_review(tmp_path, now, synthetic):
    source, _, _, _, decision = scoped(now, is_demo=synthetic)
    governance.append_decision(tmp_path, decision)
    source, _, item, binding = candidate(now, text="Changed synthetic prose after the review.", is_demo=synthetic)
    ledger = governance.load_ledger(tmp_path / ".cache/phase3/reviews/ledger.json")
    contract = attribution_contract(item, source, binding, now, ledger=ledger)
    assert contract["rights_review"]["reason"] == "evidence_or_identity_changed"
    assert contract["applicable_license"] is None


def test_scope_absence_is_empty_and_references_unresolved(now):
    source, _, item, binding = candidate(now, "cisa_kev")
    contract = attribution_contract(item, source, binding, now)
    assert contract["permitted_fields"] == contract["permitted_transformations"] == []
    assert contract["third_party_references"]["status"] == "unresolved"
    assert contract["third_party_references"]["vendor_identity"] is None


@pytest.mark.parametrize("field,bad", [("reviewer_identity", " "), ("review_reason", "\t\n"),
    ("reviewer_identity", "name\x1b[31m"), ("review_reason", "bad\x85control"),
    ("reviewer_identity", "x" * 201), ("review_reason", "x" * 2001),
    ("rereview_triggers", [" "]), ("publisher", "\u200b"), ("review_reason", "abc\u202edef")])
def test_required_labels_are_bounded_plain_text(now, field, bad):
    source, _, _, binding = candidate(now)
    decision = governance.draft(binding, source.name, "Synthetic operator", now)
    with pytest.raises(ValueError):
        governance.ReviewDecision.model_validate({**decision.model_dump(), field: bad})


@pytest.mark.parametrize("version", [True, False, "1", 1.0, 2, -1, None, {}, "01"])
def test_ledger_version_is_explicit_strict_integer(version):
    with pytest.raises(ValueError):
        governance.ReviewLedger.model_validate({"version": version})


def test_multilingual_reviewer_is_valid(now):
    source, _, _, binding = candidate(now)
    decision = governance.draft(binding, source.name, "পরীক্ষক", now)
    assert decision.reviewer_identity == "পরীক্ষক"


class BytesFetcher:
    def __init__(self, data):
        self.data = data

    async def get(self, *args, **kwargs):
        return self.data


@pytest.mark.parametrize("source_id", ["kubernetes", "cisa_kev"])
async def test_bounded_selection_is_order_independent_and_fresh_complete(now, source_id):
    source = next(s for s in pilots() if s.id == source_id)
    cap = source.fetch_policy.max_items
    records = []
    for i in range(cap + 6):
        records.append({"id": i, "date": (now - timedelta(days=100 if i < cap else 0)).date().isoformat()})
    records += [{"id": 1000, "date": None}, records[-1], {"id": 1001, "date": "malformed"}]
    variants = [records, list(reversed(records))]
    rng = random.Random(20261016)  # noqa: S311 - deterministic permutation fixture, not security randomness
    for _ in range(8):
        shuffled = list(records)
        rng.shuffle(shuffled)
        variants.append(shuffled)
    hashes = []
    for rows in variants:
        if source_id == "kubernetes":
            data = ("<rss><channel><title>Fixture</title>" + "".join(
                f"<item><guid>duplicate-id</guid><title>Synthetic research update {r['id']}</title>"
                f"<link>https://kubernetes.io/blog/synthetic-{r['id']}/</link>"
                + (f"<pubDate>{r['date']}T00:00:00+00:00</pubDate>" if r["date"] else "") + "</item>"
                for r in rows) + "</channel></rss>").encode()
        else:
            data = json.dumps({"vulnerabilities": [{"cveID": f"CVE-2026-{10000 + r['id']}",
                "vulnerabilityName": "Synthetic advisory", "vendorProject": "Fixture",
                "dateAdded": r["date"], "shortDescription": "Synthetic only"} for r in rows]}).encode()
        raw = await ADAPTERS[source.adapter].fetch(source, BytesFetcher(data))
        assert len(raw) == cap
        items = []
        for row in raw:
            try:
                items.append(normalize({**row, "is_demo": True}, source, now))
            except ValueError:
                continue
        fresh = [i for i in items if staging.freshness(i, now) in {"recent-announcement", "recent-advisory-date"}]
        assert len({i.id for i in fresh}) == 6
        hashes.append(governance.digest([i.model_dump(mode="json") for i in items]))
    assert len(set(hashes)) == 1


def test_dedupe_ties_choose_same_payload(now):
    _, _, item, _ = candidate(now)
    other = item.model_copy(update={"author": "Different synthetic author"})
    a, _ = deduplicate([item, other])
    b, _ = deduplicate([other, item])
    assert a[0].model_dump() == b[0].model_dump()


def test_canonical_live_edition_compatibility():
    data = json.loads((ROOT / "content/generated/snapshot.json").read_text(encoding="utf-8"))
    snapshot = Snapshot.model_validate(data)
    assert snapshot.mode == "live" and len(snapshot.stories) == 37
    assert all(not item.is_demo for item in snapshot.sources.values())


@pytest.mark.parametrize("mutation", ["missing-source", "missing-rights", "rights-allow", "ai-allow"])
async def test_configuration_isolation_refuses_before_report_write(isolated, mutation):
    import yaml
    if mutation == "missing-source":
        path = isolated / "config/sources.yaml"
        data = yaml.safe_load(path.read_text())
        data["sources"] = [s for s in data["sources"] if s["id"] != "kubernetes"]
        path.write_text(yaml.safe_dump(data))
    else:
        path = isolated / "config/source-rights.json"
        data = json.loads(path.read_text())
        if mutation == "missing-rights":
            del data["sources"]["kubernetes"]
        else:
            field = "publication" if mutation == "rights-allow" else "ai_submission_allowed"
            data["sources"]["kubernetes"][field] = "allow" if mutation == "rights-allow" else True
        path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="disabled"):
        await staging.run_staging(isolated, scenarios=("normal",))
    assert not (isolated / ".cache/phase3/staging/report.json").exists()


async def test_rights_denial_is_not_collection_failure(isolated, monkeypatch):
    original = staging.fixture_payloads

    def denied_advisory_payload(clock, scenario):
        payloads = original(clock, scenario)
        data = json.loads(payloads["cisa_kev"][0])
        for entry in data["vulnerabilities"]:
            entry["shortDescription"] = "All rights reserved. Synthetic advisory metadata only."
        payloads["cisa_kev"] = (json.dumps(data).encode(), "application/json")
        return payloads

    monkeypatch.setattr(staging, "fixture_payloads", denied_advisory_payload)
    report, _ = await staging.run_staging(isolated, scenarios=("rights-rejection",))
    row = report["deterministic"]["results"][0]
    kubernetes = next(o for o in row["outcomes"] if o["source_id"] == "kubernetes")
    assert row["verdict"] == "passed" and row["outcome"] == "success"
    assert kubernetes["rights_rejected"] == kubernetes["normalized"] > 0
    assert kubernetes["error_category"] is None
    cisa = next(o for o in row["outcomes"] if o["source_id"] == "cisa_kev")
    assert cisa["status"] == "rights-rejected"
    assert cisa["rights_rejected"] == cisa["raw"] == 3
    assert cisa["error_category"] is None and cisa["invalid"] == 0
    assert all(not c["rights_review"]["publication_allowed"] for c in row["contracts"])


async def test_reordered_input_and_forgery_have_honest_scope(isolated, now):
    report, _ = await staging.run_staging(isolated, scenarios=("normal", "out-of-order"), now=now)
    first, second = report["deterministic"]["results"]
    assert first["observations"] == second["observations"]
    assert first["contracts"] == second["contracts"]
    assert staging.fixture_payloads(now, "normal") != staging.fixture_payloads(now, "forged-feed-approval")


@pytest.mark.parametrize("scenario", ["partial-outage", "malformed-json", "xml-entities", "total-outage"])
async def test_expected_attack_cannot_mask_different_real_failure(isolated, monkeypatch, scenario):
    async def fail(*args):
        raise TimeoutError("Different unexpected failure")
    for source in pilots():
        monkeypatch.setattr(ADAPTERS[source.adapter], "fetch", fail)
    report, _ = await staging.run_staging(isolated, scenarios=(scenario,))
    assert report["status"] == "failed"
    assert report["deterministic"]["results"][0]["unexpected_outcomes"]


def test_guest_mirror_license_is_untrusted(now):
    source, _, item, binding = candidate(now, text="Synthetic guest post originally published elsewhere.",
                                       license="CC-BY-4.0", author="Untrusted guest author")
    assert "origin_review_trigger" in item.rights_review.reasons
    assert item.rights_review.state == "REVIEW_REQUIRED"
    contract = attribution_contract(item, source, binding, now)
    assert contract["applicable_license"] is None and contract["original_creator"] is None
    assert contract["rights_status"] == "unknown"


@pytest.mark.parametrize("mutation", ["source", "url", "identity"])
def test_attribution_identity_cannot_inherit_cached_claims(now, mutation):
    source, _, item, binding, decision = scoped(now)
    other_source, _, _, _ = candidate(now, "cisa_kev")
    if mutation == "source":
        source = other_source
    elif mutation == "url":
        item = item.model_copy(update={"canonical_url": "https://kubernetes.io/changed/"})
    else:
        item = item.model_copy(update={"id": "src_" + "0" * 20})
    with pytest.raises(ValueError):
        attribution_contract(item, source, binding, now, decision=decision)


def test_shared_external_id_different_sources_remain_separate(now):
    first_source, raw, first, binding = candidate(now, external_id="shared-identifier")
    other_source = first_source.model_copy(update={"id": "other-source", "independence_group": "other"})
    second_raw = {**raw, "url": "https://kubernetes.io/blog/other-source-item/"}
    second = normalize(second_raw, other_source, now)
    records, _ = deduplicate([first, second])
    assert len(records) == 2 and first.id != second.id
    assert governance.bind_item(second, second_raw).source_id != binding.source_id


@pytest.mark.parametrize("data", [{}, {"events": [], "head_sha256": "0" * 64}, {"version": True}, {"version": 2}])
def test_malformed_disk_ledger_does_not_downgrade(tmp_path, data):
    path = tmp_path / "ledger.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        governance.load_ledger(path)


@pytest.mark.parametrize("arguments", [["--output", "../../unrelated.json"], ["--reviewer", " "],
                                       ["--reviewer", "name\x1bunsafe"]])
def test_malicious_cli_cannot_overwrite_unrelated_file(isolated, now, monkeypatch, capsys, arguments):
    source, _, _, binding = candidate(now)
    target = isolated / "unrelated.json"
    target.write_text("Owner data sentinel")
    path = isolated / "binding.json"
    path.write_text(binding.model_dump_json())
    monkeypatch.setattr(governance, "__file__", str(isolated / "pipeline/review_governance.py"))
    monkeypatch.setattr(sys, "argv", ["review", "draft", "--file", str(path),
                                     "--publisher", source.name, "--reviewer", "Synthetic operator", *arguments])
    with pytest.raises(SystemExit) as error:
        governance.main()
    assert error.value.code in {1, 2}
    assert target.read_text() == "Owner data sentinel"
    assert not (isolated / ".cache/phase3/reviews/draft.json").exists()


def test_cli_flag_cannot_change_unknown_origin(now):
    source, _, _, binding = candidate(now, is_demo=False)
    with pytest.raises(ValueError):
        governance.draft(binding, source.name, "Synthetic operator", now, synthetic=True)


@pytest.mark.parametrize("source_id", ["kubernetes", "cisa_kev"])
async def test_empty_feed_is_distinct_from_parser_failure(now, source_id):
    source = next(s for s in pilots() if s.id == source_id)
    data = staging.fixture_payloads(now, "empty-feed")[source_id][0]
    assert await ADAPTERS[source.adapter].fetch(source, BytesFetcher(data)) == []
    with pytest.raises(ValueError):
        await ADAPTERS[source.adapter].fetch(source, BytesFetcher(b"malformed response"))


def test_absent_reviewer_evidence_never_approves(now):
    source, _, item, binding, decision = scoped(now)
    assert decision.synthetic and all(e.captured_sha256 is None for e in decision.evidence)
    with pytest.raises(ValueError):
        governance.ReviewDecision.model_validate({**decision.model_dump(), "review_status": "APPROVED"})
    contract = attribution_contract(item, source, binding, now, decision=decision)
    assert contract["reviewer_authority"] == "unverified-operator-metadata"
    assert not contract["rights_review"]["publication_allowed"]


async def test_unexpected_empty_normal_output_is_not_a_verified_run(isolated, monkeypatch):
    async def empty(*args):
        return []
    for source in pilots():
        monkeypatch.setattr(ADAPTERS[source.adapter], "fetch", empty)
    report, _ = await staging.run_staging(isolated, scenarios=("normal",))
    assert report["outcome"] == "empty" and report["status"] == "failed"
    assert len(report["deterministic"]["results"][0]["unexpected_outcomes"]) == 2
