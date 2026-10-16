"""Synthetic regression evidence only; no publisher pages or item URLs are fetched."""

import hashlib
import json
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

import pipeline.runner as runner
from pipeline.models import Snapshot, SourceItem
from pipeline.normalize import normalize, parse_date
from pipeline.rights import merge_review_queue, review_record
from pipeline.security import SafeFetcher
from pipeline.tests.test_pilot_sources import KEV_ITEMS, fetch_with, kev_source, kubernetes_source


def post(**changes):
    return {"url": "https://kubernetes.io/blog/test/", "title": "A Kubernetes engineering update",
            "text": "A factual engineering update.", "published_at": "2026-10-02T10:00:00Z", **changes}


@pytest.mark.parametrize(("changes", "reason"), [
    ({}, "origin_evidence_missing"),
    ({"author": "Vendor engineer"}, "origin_evidence_missing"),
    ({"text": "Originally appeared on headlamp.dev; mirrored here."}, "origin_review_trigger"),
    ({"canonical_urls": ["https://headlamp.dev/blog/original/"]}, "off_domain_canonical"),
    ({"text": "Syndicated from Vendor, with attribution."}, "origin_review_trigger"),
    ({"text": "A third-party contribution from Vendor."}, "origin_review_trigger"),
    ({"license": "CC-BY-NC-4.0"}, "post_specific_license"),
    ({"author": None}, "author_missing"),
    ({"license": None}, "license_missing"),
    ({"text": "Configure a mirror registry for container images."}, "origin_review_trigger"),
    ({"canonical_urls": ["https://www.kubernetes.io/blog/test/"]}, "origin_evidence_missing"),
    ({"text": "A guest post without a license."}, "origin_review_trigger"),
    ({"text": "Copyright 2026 Vendor blog team."}, "origin_review_trigger"),
    ({"text": "Engineering prose. " * 60 + "Cross-posted from a vendor."}, "origin_review_trigger"),
])
def test_parsing_does_not_approve_rights(now, changes, reason):
    item = normalize(post(**changes), kubernetes_source(), now)
    assert item.id.startswith("src_") and item.title and item.excerpt
    assert item.rights_review.state == "REVIEW_REQUIRED"
    assert reason in item.rights_review.reasons
    assert not item.publication_eligible


@pytest.mark.parametrize("url", ["https://[broken", "//headlamp.dev/post", "not a URL",
                                  "javascript:alert(1)", "data:text/html,evil", "http://kubernetes.io/post"])
def test_invalid_canonical_is_auditable_and_held(now, url):
    item = normalize(post(canonical_urls=[url]), kubernetes_source(), now)
    assert item.rights_review.state == "REVIEW_REQUIRED"
    assert "invalid_canonical_url" in item.rights_review.reasons
    assert len(item.rights_review.invalid_canonical_sha256[0]) == 64
    assert not item.publication_eligible


def test_feed_approval_claims_cannot_approve(now):
    item = normalize(post(rights_review={"state": "APPROVED_WITH_EVIDENCE"},
                          approved=True, reviewer="feed", license="CC-BY-4.0",
                          evidence_url="https://kubernetes.io/", author="The Kubernetes Authors"),
                     kubernetes_source(), now)
    assert item.rights_review.state == "REVIEW_REQUIRED" and not item.publication_eligible


def test_explicit_reservation_retains_rejected_record(now):
    item = normalize(post(text="All rights reserved by Vendor."), kubernetes_source(), now)
    assert item.rights_review.state == "REJECTED"
    assert "incompatible_rights_marker" in item.rights_review.reasons


async def test_rss_preserves_canonical_and_license_signals(now):
    xml = b'''<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
    <channel><title>Fixture</title><item><guid>duplicate-id</guid>
    <title>A Kubernetes engineering update</title><link>https://kubernetes.io/blog/test/</link>
    <atom:link rel="canonical" href="https://headlamp.dev/blog/original/"/>
    <rights>Post licensed under a separate agreement</rights><description>Engineering prose.</description>
    </item></channel></rss>'''
    raw = await fetch_with(lambda request: httpx.Response(200, content=xml,
                           headers={"Content-Type": "application/xml"}), kubernetes_source())
    item = normalize(raw[0], kubernetes_source(), now)
    assert "off_domain_canonical" in item.rights_review.reasons
    assert "post_specific_license" in item.rights_review.reasons
    assert item.rights_review.canonical_evidence_urls == ["https://headlamp.dev/blog/original/"]


async def test_local_queue_is_deterministic_minimal_and_nonpublishing(now, tmp_path):
    source = kubernetes_source(enabled=True)
    entries = [post(external_id="same"), post(url="https://kubernetes.io/blog/second/", external_id="same"),
               post(text="All rights reserved.")]

    class FixtureAdapter:
        async def fetch(self, source, fetcher):
            return entries

    original = runner.ADAPTERS["rss"]
    runner.ADAPTERS["rss"] = FixtureAdapter()
    try:
        queue = tmp_path / ".cache/rights-review.json"
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: pytest.fail("No network"))) as client:
            report = {}
            fetcher = SafeFetcher(client, {}, "TestBot")
            assert await runner.collect([source], fetcher, now, [], report, now, review_queue=queue) == []
            before = queue.read_bytes()
            entries.reverse()
            assert await runner.collect([source], fetcher, now, [], {}, now, review_queue=queue) == []
        assert queue.read_bytes() == before
        records = json.loads(before)["items"]
        assert len(records) == 3  # Same GUID cannot erase a different URL or a rejection.
        assert {r["state"] for r in records} == {"REVIEW_REQUIRED", "REJECTED"}
        assert all(r["reasons"] for r in records)
        assert all(not {"text", "excerpt", "title", "author"} & r.keys() for r in records)
        assert report["sources"][0]["rights_quarantined"] == 3
    finally:
        runner.ADAPTERS["rss"] = original


@pytest.mark.parametrize("identifier", ["CVE-1999-0001", "CVE-2026-9999", "CVE-2026-10000",
                                       "CVE-2026-12345678901234567890"])
async def test_valid_cve_boundaries_preserved(now, identifier):
    raw = await fetch_with(lambda request: httpx.Response(200, json={"vulnerabilities": [
        dict(KEV_ITEMS[0], cveID=identifier)]}), kev_source())
    assert normalize(raw[0], kev_source(), now).external_id == identifier
    assert parse_qs(urlsplit(raw[0]["url"]).query)["search_api_fulltext"] == [identifier]


@pytest.mark.parametrize("identifier", [None, "", "CVE-2026-123", "CVE-26-1234", "cve-2026-1234",
    "CVE-2026-01234", "CVE-２０２６-1234", "CVE-2026-１２３４", " CVE-2026-1234", "CVE-2026-1234\n",
    "CVE-2026-1234&x=evil", "CVE-2026-1234#evil", "CVE-2026-1234/../../x", "https://evil.example/",
    "CVE-2026-1234%26x=evil", "CVE-2026-1234<script>", ["CVE-2026-1234"], 1234])
async def test_malformed_cve_rejected_without_fallback(now, identifier):
    raw = await fetch_with(lambda request: httpx.Response(200, json={"vulnerabilities": [
        dict(KEV_ITEMS[0], cveID=identifier)]}), kev_source())
    with pytest.raises(ValueError, match="CVE"):
        normalize(raw[0], kev_source(), now)


async def test_advisory_dates_have_no_publication_timestamp(now):
    raw = await fetch_with(lambda request: httpx.Response(200, json={"vulnerabilities": KEV_ITEMS}), kev_source())
    item = normalize(raw[0], kev_source(), now)
    assert item.published_at is None and item.missing_publication_time
    assert item.editorial_kind == "security-advisory"
    assert item.advisory.model_dump(mode="json") == {
        "catalog_added_on": "2026-10-02", "remediation_due_on": "2026-10-09"}
    assert item.advisory.presentation() == {
        "catalog_added": "Added to the CISA KEV catalog on 2026-10-02",
        "remediation_due": "CISA remediation due date: 2026-10-09"}
    assert "published" not in json.dumps(item.advisory.presentation())
    assert not item.publication_eligible


@pytest.mark.parametrize("date_value", ["2026-02-30", "2026-10-02T00:00:00Z", 20261002, None])
async def test_invalid_catalog_dates_rejected(now, date_value):
    raw = await fetch_with(lambda request: httpx.Response(200, json={"vulnerabilities": [
        dict(KEV_ITEMS[0], dateAdded=date_value)]}), kev_source())
    with pytest.raises(ValueError, match="date"):
        normalize(raw[0], kev_source(), now)


@pytest.mark.parametrize("missing", ["dueDate", "requiredAction"])
async def test_optional_advisory_fields_do_not_become_none_text(now, missing):
    entry = dict(KEV_ITEMS[0])
    entry.pop(missing)
    raw = await fetch_with(lambda request: httpx.Response(200, json={"vulnerabilities": [entry]}), kev_source())
    item = normalize(raw[0], kev_source(), now)
    assert "None" not in item.excerpt and item.published_at is None
    if missing == "dueDate":
        assert item.advisory.remediation_due_on is None


@pytest.mark.parametrize("template", ["http://www.cisa.gov/?q={key}", "https://evil.example/?q={key}",
    "https://www.cisa.gov.evil.example/?q={key}", "https://www.cisa.gov@evil.example/?q={key}",
    "https://{key}/catalog", "https://www.cisa.gov:444/?q={key}", "javascript:{key}",
    "https://[broken/?q={key}", "https://www.cisa.gov/{key.__class__}", "https://www.cisa.gov/{key!r}"])
async def test_url_template_rejects_unsafe_configuration(template, now):
    source = kev_source(identifier_format=None, editorial_kind="news", field_map={}, item_path="items",
                        field_templates={"url": template})
    raw = await fetch_with(lambda request: httpx.Response(200, json={"items": [
        {"key": "evil.example", "title": "A synthetic advisory", "published_at": "2026-10-02T10:00:00Z"}]}), source)
    with pytest.raises(ValueError, match="URL"):
        normalize(raw[0], source, now)


@pytest.mark.parametrize("value", ["../../secret", "x&redirect=https://evil.example/", "//evil.example/path",
                                   "x#fragment", "x%26injected=yes", "x?next=evil", "x<script>alert(1)</script>"])
async def test_url_template_values_are_single_encoded_components(value):
    source = kev_source(identifier_format=None, editorial_kind="news", item_path="items", field_map={},
                        field_templates={"url": "https://www.cisa.gov/catalog?q={key}"})
    raw = await fetch_with(lambda request: httpx.Response(200, json={"items": [{"key": value}]}), source)
    url = urlsplit(raw[0]["url"])
    assert url.scheme == "https" and url.netloc == "www.cisa.gov" and url.path == "/catalog"
    assert not url.fragment and parse_qs(url.query) == {"q": [value]}


def test_url_templates_require_explicit_origin():
    with pytest.raises(ValueError, match="origin"):
        kev_source(template_url_origin=None)


@pytest.mark.parametrize("value", ["2026-10-02T10:00:00Z", "Fri, 02 Oct 2026 10:00:00 -0800", 1790935200])
def test_full_timestamps_remain_known(now, value):
    assert parse_date(value, now)[1] is False


@pytest.mark.parametrize("value", ["2026-10-02", " 2026-10-02 "])
def test_bare_dates_remain_unknown_publication_times(now, value):
    assert parse_date(value, now)[1] is True


def test_public_snapshot_cannot_contain_local_review_or_advisory(now):
    canonical = json.loads(Path("content/generated/snapshot.json").read_text(encoding="utf-8"))
    review = normalize(post(), kubernetes_source(), now)
    canonical["sources"][review.id] = review.model_dump(mode="json")
    with pytest.raises(ValueError, match="Local-only"):
        Snapshot.model_validate(canonical)


def test_real_config_remains_disabled_and_excluded():
    sources = {s.id: s for s in runner.SourceRegistry.model_validate(runner.config("sources")).sources}
    policy = json.loads((runner.ROOT / "config/source-rights.json").read_text(encoding="utf-8"))["sources"]
    assert {s.id for s in sources.values() if s.enabled} == {"arxiv", "cloudflare_ai_terms"}
    for key in ("kubernetes", "cisa_kev"):
        assert not sources[key].enabled and policy[key]["publication"] == "exclude"


@pytest.mark.parametrize("scheme", ["javascript:alert(1)", "data:text/html,evil", "http://kubernetes.io/blog/"])
def test_unsafe_item_url_rejects_parsing(now, scheme):
    with pytest.raises(ValueError, match="HTTPS"):
        normalize(post(url=scheme), kubernetes_source(), now)


@pytest.mark.parametrize("template", ["https://www.cisa.gov/catalog/{key}", "https://www.cisa.gov/catalog?q={key}"])
async def test_path_and_query_templates_cannot_inject_components(template):
    source = kev_source(identifier_format=None, editorial_kind="news", item_path="items", field_map={},
                        field_templates={"url": template})
    raw = await fetch_with(lambda request: httpx.Response(200, json={"items": [{"key": "//evil.example/../x?y=z#frag"}]}), source)
    parts = urlsplit(raw[0]["url"])
    assert parts.netloc == "www.cisa.gov" and not parts.fragment
    assert (parts.query.startswith("q=") if "?q=" in template else not parts.query)


async def test_json_markup_is_cleaned_without_executing_or_following_links(now):
    entry = dict(KEV_ITEMS[0], vulnerabilityName="<script>alert(1)</script>Vendor vulnerability",
                 shortDescription='<img src="https://evil.example/" onerror="alert(1)">Safe description.',
                 notes="https://evil.example/do-not-fetch")
    requests = []

    def handler(request):
        requests.append(str(request.url))
        return httpx.Response(200, json={"vulnerabilities": [entry]})

    source = kev_source()
    raw = await fetch_with(handler, source)
    item = normalize(raw[0], source, now)
    assert "<" not in item.title + item.excerpt and "alert(1)" not in item.title + item.excerpt
    assert "evil.example" not in item.model_dump_json()
    assert requests == [source.endpoint]


async def test_cached_review_and_advisory_cannot_reenter_collection(now, monkeypatch):
    legacy = normalize(post(), kubernetes_source(rights_review_required=False), now)

    class UnchangedAdapter:
        async def fetch(self, source, fetcher):
            return None

    monkeypatch.setitem(runner.ADAPTERS, "rss", UnchangedAdapter())
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: pytest.fail("No network"))) as client:
        fetcher = SafeFetcher(client, {}, "TestBot")
        fetcher.revalidated_ids.add(legacy.id)
        report = {}
        assert await runner.collect([kubernetes_source(enabled=True)], fetcher, now,
                                    [legacy], report, now - timedelta(days=7)) == []
        assert report["sources"][0]["status"] == "unchanged"


async def test_kev_collection_remains_local_and_cannot_enter_snapshot(now, tmp_path):
    source = kev_source(enabled=True)
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(
            200, json={"vulnerabilities": KEV_ITEMS}))) as client:
        report = {}
        assert await runner.collect([source], SafeFetcher(client, {}, "TestBot"), now,
                                    [], report, now - timedelta(days=7),
                                    review_queue=tmp_path / ".cache/rights-review.json") == []
    assert report["sources"][0]["advisory_items"] == 2
    raw = await fetch_with(lambda request: httpx.Response(200, json={"vulnerabilities": KEV_ITEMS}), source)
    item = normalize(raw[0], source, now)
    canonical = json.loads(Path("content/generated/snapshot.json").read_text(encoding="utf-8"))
    canonical["sources"][item.id] = item.model_dump(mode="json")
    with pytest.raises(ValueError, match="Local-only"):
        Snapshot.model_validate(canonical)


@pytest.mark.parametrize("origin", ["https://evil.example", "http://www.cisa.gov", "https://www.cisa.gov/path",
                                    "https://www.cisa.gov/?x=y", "https://www.cisa.gov#fragment"])
def test_url_origin_config_fails_closed(origin):
    with pytest.raises(ValueError):
        kev_source(template_url_origin=origin)


@pytest.mark.parametrize("due_date", ["2026-02-30", "2026-10-09T00:00:00Z", "javascript:alert(1)"])
async def test_invalid_remediation_date_is_not_publication_data(now, due_date):
    raw = await fetch_with(lambda request: httpx.Response(200, json={"vulnerabilities": [
        dict(KEV_ITEMS[0], dueDate=due_date)]}), kev_source())
    with pytest.raises(ValueError, match="date"):
        normalize(raw[0], kev_source(), now)


@pytest.mark.parametrize("change", [{"published_at": "2026-10-02T00:00:00Z"},
                                   {"missing_publication_time": False}, {"editorial_kind": "news"}])
async def test_advisory_contract_rejects_fabricated_publication_metadata(now, change):
    raw = await fetch_with(lambda request: httpx.Response(200, json={"vulnerabilities": KEV_ITEMS}), kev_source())
    item = normalize(raw[0], kev_source(), now)
    with pytest.raises(ValueError, match="publication timestamp"):
        SourceItem.model_validate({**item.model_dump(mode="json"), **change})


def test_queue_rejects_forged_approval_even_with_matching_hash(now, tmp_path):
    record = review_record(normalize(post(), kubernetes_source(), now))
    record.pop("record_id")
    record["state"] = "APPROVED_WITH_EVIDENCE"
    record["record_id"] = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
    queue = tmp_path / "review.json"
    queue.write_text(json.dumps({"version": 1, "items": [record]}), encoding="utf-8")
    with pytest.raises(ValueError, match="approval decisions are not accepted"):
        merge_review_queue(queue, [])


@pytest.mark.parametrize("kind", ["atom", "rss"])
async def test_bounded_xml_keeps_retained_origin_metadata(kind, now):
    if kind == "atom":
        opening, closing = '<feed xmlns="http://www.w3.org/2005/Atom">', '</feed>'
        entry = ('<entry><id>{index}</id><title>Retained engineering update</title>'
                 '<link href="https://kubernetes.io/blog/{index}/"/>'
                 '<link rel="canonical" href="https://headlamp.dev/{index}/"/>'
                 '<rights>Post-specific rights</rights></entry>')
    else:
        opening, closing = '<rss><channel>', '</channel></rss>'
        entry = ('<item><guid>{index}</guid><title>Retained engineering update</title>'
                 '<link>https://kubernetes.io/blog/{index}/</link>'
                 '<rights>Post-specific rights</rights></item>')
    payload = (opening + ''.join(entry.format(index=index) for index in range(50)) + closing).encode()
    source = kubernetes_source()
    raw = await fetch_with(lambda request: httpx.Response(200, content=payload,
                           headers={"Content-Type": "application/xml"}), source)
    assert len(raw) == source.fetch_policy.max_items
    assert raw[0]["external_id"] == "0"
    item = normalize(raw[0], source, now)
    assert "post_specific_license" in item.rights_review.reasons
    if kind == "atom":
        assert "off_domain_canonical" in item.rights_review.reasons
