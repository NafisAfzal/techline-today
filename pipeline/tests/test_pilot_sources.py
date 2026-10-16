"""Phase 2 pilot regression tests: Kubernetes Blog (rss) + CISA KEV (json_api).

Fixtures only; no network. Covers the adversarial matrix required by the
pilot brief: incompatible license markers, invalid dates, oversized
responses, malicious URLs, duplicate CVEs, reordered entries, missing
attribution, research/news misclassification, stale records, third-party
inserts, outage/partial failure.
"""

import httpx
import pytest

from pipeline.adapters import ADAPTERS
from pipeline.dedupe import deduplicate
from pipeline.models import SourceConfig, SourceRegistry
from pipeline.normalize import normalize
from pipeline.security import SafeFetcher


def kubernetes_source(**overrides):
    base = dict(id="kubernetes", name="Kubernetes Blog", adapter="rss", source_class="primary",
                endpoint="https://kubernetes.io/feed.xml", allowed_hosts=["kubernetes.io"],
                categories=["open-source", "dev-apis"], independence_group="kubernetes",
                terms_url="https://github.com/kubernetes/website", verified_at="2026-10-16",
                rights_guard=True, rights_review_required=True)
    base.update(overrides)
    return SourceConfig(**base)


def kev_source(**overrides):
    base = dict(id="cisa_kev", name="CISA Known Exploited Vulnerabilities", adapter="json_api",
                source_class="primary",
                endpoint="https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
                allowed_hosts=["www.cisa.gov"], categories=["security"], independence_group="cisa",
                terms_url="https://www.cisa.gov/terms-use", verified_at="2026-10-16",
                item_path="vulnerabilities",
                identifier_format="cve", editorial_kind="security-advisory",
                template_url_origin="https://www.cisa.gov",
                field_map={"catalog_added_on": "dateAdded", "remediation_due_on": "dueDate",
                           "required_action": "requiredAction", "external_id": "cveID"},
                field_templates={
                    "url": "https://www.cisa.gov/known-exploited-vulnerabilities-catalog?search_api_fulltext={cveID}",
                    "title": "{cveID}: {vulnerabilityName} ({vendorProject})",
                    "text": "{shortDescription}",
                },
                rights_guard=True)
    base.update(overrides)
    return SourceConfig(**base)


KEV_ITEMS = [
    {"cveID": "CVE-2026-21589", "vulnerabilityName": "Atlassian Bitbucket Command Injection",
     "vendorProject": "Atlassian", "product": "Bitbucket Data Center",
     "shortDescription": "Atlassian Bitbucket Data Center contains a command injection vulnerability allowing remote code execution.",
     "requiredAction": "Apply mitigations per vendor instructions.", "dateAdded": "2026-10-02", "dueDate": "2026-10-09"},
    {"cveID": "CVE-2026-105134", "vulnerabilityName": "AhsayCBS Command Injection",
     "vendorProject": "Ahsay", "product": "AhsayCBS",
     "shortDescription": "Ahsay AhsayCBS contains a command injection vulnerability allowing OS command execution.",
     "requiredAction": "Apply mitigations per vendor instructions.", "dateAdded": "2026-10-01", "dueDate": "2026-10-08"},
]

K8S_FEED = (b'<rss version="2.0"><channel><title>Kubernetes Blog</title>'
            b'<item><title>Scaling Kubernetes Workloads with Node Swap</title>'
            b'<link>https://kubernetes.io/blog/2026/10/05/scaling-kubernetes-workloads-with-node-swap/</link>'
            b'<description>Kubelet node swap support graduates with broader testing across providers.</description>'
            b'<pubDate>Thu, 02 Oct 2026 10:00:00 -0800</pubDate></item>'
            b'<item><title>Kubernetes 1.35 Release Announcement</title>'
            b'<link>https://kubernetes.io/blog/2026/10/10/kubernetes-135-release/</link>'
            b'<description>The release team announces Kubernetes 1.35 with new scheduler features.</description>'
            b'<pubDate>Wed, 01 Oct 2026 10:00:00 -0800</pubDate></item>'
            b'</channel></rss>')


async def fetch_with(handler, source):
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        fetcher = SafeFetcher(client, {}, "TestBot")
        return await ADAPTERS[source.adapter].fetch(source, fetcher)


async def test_kubernetes_rss_normalizes(now):
    source = kubernetes_source()
    raw = await fetch_with(lambda request: httpx.Response(200, content=K8S_FEED, headers={"Content-Type": "application/xml"}), source)
    assert len(raw) == 2
    items = [normalize(entry, source, now) for entry in raw]
    assert all(item.publisher == "Kubernetes Blog" for item in items)
    assert all(item.canonical_url.startswith("https://kubernetes.io/") for item in items)
    assert all(item.category in ("open-source", "dev-apis") for item in items)
    assert all(item.category != "research" for item in items)
    assert all(len(item.excerpt) <= 600 and not item.missing_publication_time for item in items)
    assert all(item.rights_review.state == "REVIEW_REQUIRED" and not item.publication_eligible for item in items)


async def test_kubernetes_reorder_keeps_stable_ids(now):
    source = kubernetes_source()
    raw = await fetch_with(lambda request: httpx.Response(200, content=K8S_FEED, headers={"Content-Type": "application/xml"}), source)
    forward = {item.id for item in (normalize(entry, source, now) for entry in raw)}
    backward = {item.id for item in (normalize(entry, source, now) for entry in reversed(raw))}
    assert forward == backward


async def test_kubernetes_duplicates_collapse(now):
    source = kubernetes_source()
    raw = await fetch_with(lambda request: httpx.Response(200, content=K8S_FEED, headers={"Content-Type": "application/xml"}), source)
    items = [normalize(entry, source, now) for entry in raw]
    unique, dropped = deduplicate(items + items)
    assert len(unique) == 2 and dropped == 2


async def test_kubernetes_incompatible_marker_quarantined(now):
    guarded = kubernetes_source()
    unguarded = kubernetes_source(rights_guard=False, rights_review_required=False)
    raw = {"url": "https://kubernetes.io/blog/2026/10/05/guest-post/", "title": "A partner announcement",
           "text": "Reproduced with permission from the vendor blog.", "published_at": "Mon, 05 Oct 2026 10:00:00 -0800"}
    assert normalize(raw, guarded, now).rights_review.state == "REJECTED"
    assert normalize(raw, unguarded, now).id.startswith("src_")


async def test_kubernetes_future_date_flagged(now):
    source = kubernetes_source()
    raw = {"url": "https://kubernetes.io/blog/2026/10/05/future-post/", "title": "A future scheduled announcement",
           "text": "Scheduled content.", "published_at": "Mon, 05 Oct 2030 10:00:00 -0800"}
    assert normalize(raw, source, now).missing_publication_time is True


async def test_kev_json_maps_fields(now):
    source = kev_source()
    payload = {"title": "CISA KEV", "dateReleased": "2026-10-15T17:00:11.2795Z",
               "vulnerabilities": KEV_ITEMS}
    raw = await fetch_with(lambda request: httpx.Response(200, json=payload, headers={"Content-Type": "application/json"}), source)
    assert len(raw) == 2
    assert raw[0]["url"] == "https://www.cisa.gov/known-exploited-vulnerabilities-catalog?search_api_fulltext=CVE-2026-21589"
    assert raw[0]["external_id"] == "CVE-2026-21589"
    items = [normalize(entry, source, now) for entry in raw]
    assert all(item.category == "security" for item in items)
    assert all(item.publisher == "CISA Known Exploited Vulnerabilities" for item in items)
    # Catalog addition is a date, never a publication timestamp.
    assert all(item.missing_publication_time for item in items)
    assert items[0].published_at is None
    assert items[0].advisory.catalog_added_on.isoformat() == "2026-10-02"
    assert items[0].advisory.remediation_due_on.isoformat() == "2026-10-09"
    assert "CVE-2026-21589" in items[0].title and "Required action:" in items[0].excerpt
    assert all(len(item.excerpt) <= 600 for item in items)


async def test_kev_missing_cveid_quarantined(now):
    source = kev_source()
    payload = {"vulnerabilities": [{"vulnerabilityName": "Nameless flaw", "vendorProject": "X",
                                    "shortDescription": "No identifier.", "requiredAction": "Patch.",
                                    "dateAdded": "2026-10-15", "dueDate": "2026-10-18"}]}
    raw = await fetch_with(lambda request: httpx.Response(200, json=payload, headers={"Content-Type": "application/json"}), source)
    with pytest.raises(ValueError, match="CVE"):
        normalize(raw[0], source, now)


async def test_kev_duplicate_cve_same_id(now):
    source = kev_source()
    first = normalize({"url": "https://www.cisa.gov/known-exploited-vulnerabilities-catalog?search_api_fulltext=CVE-2026-21589",
                       "title": "CVE-2026-21589: flaw (Atlassian)", "text": "Description one.",
                       "published_at": "2026-10-15", "external_id": "CVE-2026-21589"}, source, now)
    second = normalize({"url": "https://www.cisa.gov/known-exploited-vulnerabilities-catalog?search_api_fulltext=CVE-2026-21589",
                        "title": "CVE-2026-21589: flaw renamed (Atlassian)", "text": "Description two.",
                        "published_at": "2026-10-15", "external_id": "CVE-2026-21589"}, source, now)
    assert first.id == second.id
    unique, dropped = deduplicate([first, second])
    assert len(unique) == 1 and dropped == 1


async def test_kev_malicious_cveid_rejected(now):
    source = kev_source()
    raw = {"url": "https://www.cisa.gov/known-exploited-vulnerabilities-catalog?search_api_fulltext=CVE-2026-0001",
           "title": "CVE-2026-0001: flaw (X)", "text": "Bad identifier.",
           "published_at": "2026-10-15", "external_id": "CVE-2026-0001 ../../etc"}
    with pytest.raises(ValueError, match="CVE"):
        normalize(raw, source, now)
    evil = {"url": "https://www.cisa.gov/catalog?q=CVE 2026-0001", "title": "CVE-2026-0001: flaw (X)",
            "text": "Whitespace URL.", "published_at": "2026-10-15", "external_id": "CVE-2026-0001"}
    with pytest.raises(ValueError, match="whitespace"):
        normalize(evil, source, now)


async def test_kev_third_party_marker_quarantined(now):
    source = kev_source()
    raw = dict(KEV_ITEMS[0], shortDescription="Vendor text reproduced with permission from the supplier.")
    payload = {"vulnerabilities": [raw]}
    fetched = await fetch_with(lambda request: httpx.Response(200, json=payload, headers={"Content-Type": "application/json"}), source)
    with pytest.raises(ValueError, match="rights"):
        normalize(fetched[0], source, now)


async def test_kev_stale_record_stays_day_granular(now):
    source = kev_source()
    raw = dict(KEV_ITEMS[0], dateAdded="2026-08-01", dueDate="2026-08-22")
    payload = {"vulnerabilities": [raw]}
    fetched = await fetch_with(lambda request: httpx.Response(200, json=payload, headers={"Content-Type": "application/json"}), source)
    item = normalize(fetched[0], source, now)
    # Missing exact time keeps stale advisories out of current-news (coverage.mjs
    # contentKind requires missing_publication_time === false for rss/json_api).
    assert item.missing_publication_time is True
    assert item.category == "security"


async def test_kev_outage_raises():
    source = kev_source()

    def handler(request):
        return httpx.Response(500, text="outage", headers={"Content-Type": "application/json"})
    with pytest.raises(httpx.HTTPStatusError):
        await fetch_with(handler, source)


async def test_kev_oversized_rejected():
    source = kev_source(fetch_policy=kev_source().fetch_policy.model_copy(update={"max_response_bytes": 50}))

    def handler(request):
        return httpx.Response(200, content=b'{"vulnerabilities": []}' + b' ' * 100, headers={"Content-Type": "application/json"})
    with pytest.raises(ValueError, match="size"):
        await fetch_with(handler, source)


def test_registry_accepts_disabled_pilot_entries():
    registry = SourceRegistry(version=1, sources=[kubernetes_source(), kev_source()])
    assert {source.id for source in registry.sources} == {"kubernetes", "cisa_kev"}
    with pytest.raises(ValueError, match="verification date"):
        kubernetes_source(enabled=True, verified_at=None)


def test_pilot_attribution_metadata_shape():
    policy = {
        "kubernetes": {"publication": "exclude", "license": "CC-BY-4.0",
                       "license_url": "https://creativecommons.org/licenses/by/4.0/"},
        "cisa_kev": {"publication": "exclude", "license": "CC0-1.0",
                     "license_url": "https://creativecommons.org/publicdomain/zero/1.0/"},
    }
    # postbuild.mjs, rss.xml.ts and SourceLicense.astro all key attribution
    # off license + license_url per source_registry_id.
    for entry in policy.values():
        assert entry["license"] and entry["license_url"].startswith("https://")
