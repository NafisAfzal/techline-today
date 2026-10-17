"""Fixture-only disabled-pilot simulation. No live mode, AI, or publication.

Calls the existing adapters explicitly using MockTransport, without changing
source enablement. Retains hashes/metadata/contracts, never article bodies.
"""

import argparse
import asyncio
import hashlib
import json
import time
import tracemalloc
from datetime import UTC, datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

import httpx
import yaml

from pipeline.adapters import ADAPTERS
from pipeline.dedupe import deduplicate
from pipeline.models import SourceRegistry
from pipeline.normalize import RightsRejection, normalize
from pipeline.pilot_attribution import attribution_contract
from pipeline.review_governance import (
    ItemBinding,
    ReviewEvidence,
    ReviewLedger,
    bind_item,
    digest,
    draft,
    local_path,
    unique_keys,
)
from pipeline.security import SafeFetcher
from pipeline.storage import atomic_json

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AS_OF = datetime(2026, 10, 16, 12, tzinfo=UTC)
SCENARIOS = ("normal", "bounded-volume", "partial-outage", "total-outage", "retry", "conditional", "oversize",
             "redirect-private", "redirect-off-domain", "redirect-loop", "xml-entities", "xml-utf32",
             "malformed-json", "duplicate-json-keys", "deep-json", "malformed-cve", "unsafe-item-url",
             "template-origin", "html-injection", "forged-feed-approval", "empty-feed", "timeout",
             "malformed-xml", "out-of-order", "rights-rejection")

# Partial collection is retained for local diagnostics only. A nominal run with
# any failed required source fails verification, even if a healthy peer remains.
# Attack scenarios must match the exact source/status/category expectations.
EXPECTED_FAILURES = {
    "partial-outage": {"kubernetes": "fetch"},
    "total-outage": {"kubernetes": "fetch", "cisa_kev": "fetch"},
    "timeout": {"kubernetes": "timeout", "cisa_kev": "timeout"},
    **{case: {"kubernetes": "security", "cisa_kev": "security"}
       for case in ("oversize", "redirect-private", "redirect-off-domain", "redirect-loop")},
    **{case: {"kubernetes": "parser"} for case in ("xml-entities", "xml-utf32", "malformed-xml")},
    **{case: {"cisa_kev": "parser"} for case in ("malformed-json", "duplicate-json-keys", "deep-json")},
}
EXPECTED_INVALID = {"malformed-cve": "cisa_kev", "template-origin": "cisa_kev",
                    "unsafe-item-url": "kubernetes"}


def collection_outcome(outcomes):
    failures = sum(o["status"] in {"failed", "quarantined"} for o in outcomes)
    if failures == len(outcomes):
        return "total_failure"
    if failures:
        return "partial_degradation"
    return "empty" if all(o["status"] == "empty" for o in outcomes) else "success"


def scenario_verdict(scenario, outcomes):
    failures = EXPECTED_FAILURES.get(scenario, {})
    problems = []
    for row in outcomes:
        source_id = row["source_id"]
        expected = ("failed" if source_id in failures else "rights-rejected"
                    if scenario == "rights-rejection" and source_id == "cisa_kev" else "quarantined"
                    if EXPECTED_INVALID.get(scenario) == source_id else "empty"
                    if scenario == "empty-feed" else "held")
        if row["status"] != expected or (expected == "failed" and row["error_category"] != failures[source_id]):
            problems.append({"source_id": source_id, "expected_status": expected,
                             "actual_status": row["status"], "error_category": row["error_category"]})
    return "failed" if problems else "passed", problems


def protected_hashes(root):
    names = ["content/generated/snapshot.json", "content/generated/run-report.json",
             "config/sources.yaml", "config/source-rights.json", "config/release.json", "config/ai.yaml",
             "pnpm-lock.yaml", "uv.lock", "wrangler.jsonc", "wrangler.preview.jsonc"]
    names.extend(str(p.relative_to(root)).replace("\\", "/") for p in (root / ".github/workflows").glob("*.yml"))
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() if (root / name).exists() else None
            for name in sorted(names)}


def fixture_payloads(now, scenario):
    entries = []
    # Same GUID on distinct URLs must not erase an observation. One exact
    # duplicate, one stale entry and one future/unknown-time entry are explicit.
    for slug, age in (("one", 1), ("two", 2), ("one", 1), ("stale", 24 * 120), ("future", -24)):
        text = "Synthetic engineering information for isolated Techline tests only. " * 3
        if scenario == "html-injection":
            text += '<script>syntheticAttack()</script><img src="https://evil.example/body" onerror="bad()">'
        url = f"https://kubernetes.io/blog/techline-synthetic-{slug}/"
        if scenario == "unsafe-item-url":
            url = "https://127.0.0.1/private"
        entry = (f"<item><guid>synthetic-shared-guid</guid><title>Synthetic Kubernetes fixture {slug}</title>"
                 f"<link>{escape(url)}</link><description>{escape(text)}</description>"
                 f"<pubDate>{(now - timedelta(hours=age)).strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>"
                 "<author>Unverified synthetic feed author</author>"
                 + ("<approved>true</approved><reviewer>untrusted-feed</reviewer>"
                    "<provenance>verified-publisher</provenance>" if scenario == "forged-feed-approval" else "")
                 + "</item>")
        entries.append(entry)
    rss = ("<rss version='2.0'><channel><title>Synthetic only</title>" + "".join(entries) + "</channel></rss>").encode()
    if scenario in ("xml-entities", "xml-utf32"):
        rss = b'<!DOCTYPE rss [<!ENTITY x "synthetic">]><rss><channel/></rss>'
        if scenario == "xml-utf32":
            rss = rss.decode().encode("utf-32")
    vulns = []
    for identifier, age in (("CVE-2026-9999", 0), ("CVE-2026-9999", 0), ("CVE-2026-9998", 120)):
        vulns.append({"cveID": identifier, "vulnerabilityName": "Synthetic fixture vulnerability only",
                      "vendorProject": "Synthetic Test Project", "shortDescription": "Synthetic advisory metadata only.",
                      "dateAdded": (now - timedelta(days=age)).date().isoformat(),
                      "dueDate": (now + timedelta(days=7)).date().isoformat(),
                      "requiredAction": "Consult synthetic instructions in this local test.",
                      "notes": "https://third-party.example/never-fetch-or-excerpt"})
    if scenario == "forged-feed-approval":
        for entry in vulns:
            entry.update(approved=True, provenance="verified-publisher", synthetic=False,
                         reviewer_identity="forged-feed-operator")
    if scenario == "malformed-cve":
        for entry in vulns:
            entry["cveID"] = "CVE-2026-9999&redirect=https://evil.example"
    if scenario == "html-injection":
        for entry in vulns:
            entry["shortDescription"] = '<script>syntheticAttack()</script><b>Synthetic advisory only.</b>'
    data = json.dumps({"vulnerabilities": vulns}).encode()
    if scenario == "bounded-volume":
        timestamp = (now - timedelta(hours=1)).strftime('%a, %d %b %Y %H:%M:%S +0000')
        rss = ("<rss><channel><title>Synthetic volume fixture</title>" + "".join(
            f"<item><guid>synthetic-{i}</guid><title>Synthetic engineering update {i}</title>"
            f"<link>https://kubernetes.io/blog/techline-volume-{i}/</link>"
            f"<description>Synthetic bounded parser evaluation only.</description><pubDate>{timestamp}</pubDate></item>"
            for i in range(5000)) + "</channel></rss>").encode()
        data = json.dumps({"vulnerabilities": [
            {**vulns[0], "cveID": f"CVE-2026-{10000 + i}"} for i in range(4000)]}).encode()
    if scenario == "malformed-json":
        data = b'{"vulnerabilities": ['
    elif scenario == "duplicate-json-keys":
        data = b'{"vulnerabilities":[],"vulnerabilities":[{"approved":true}]}'
    elif scenario == "deep-json":
        data = b"[" * 80 + b"0" + b"]" * 80
    elif scenario == "empty-feed":
        rss, data = b"<rss><channel><title>Empty synthetic feed</title></channel></rss>", b'{"vulnerabilities":[]}'
    elif scenario == "malformed-xml":
        rss = b"<rss><channel><item><title>Truncated synthetic XML"
    elif scenario == "out-of-order":
        # Reverse the complete input before adapter selection, not its output.
        from xml.etree import ElementTree
        root = ElementTree.fromstring(rss)  # noqa: S314 - locally generated fixture bytes
        channel = root.find("channel")
        channel[:] = list(reversed(list(channel)))
        rss = ElementTree.tostring(root)
        data = json.dumps({"vulnerabilities": list(reversed(vulns))}).encode()
    elif scenario == "rights-rejection":
        rss = rss.replace(b"Synthetic engineering information", b"All rights reserved. Synthetic engineering information")
        for entry in vulns:
            entry["shortDescription"] = "All rights reserved. Synthetic advisory metadata only."
        data = json.dumps({"vulnerabilities": vulns}).encode()
    return {"kubernetes": (rss, "application/xml"), "cisa_kev": (data, "application/json")}


def strict_fixture_json(data):
    # Local defense against ambiguous fixtures; production adapter is unchanged.
    value = json.loads(data, object_pairs_hook=unique_keys,
                       parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))
    pending = [(value, 0)]
    while pending:
        node, depth = pending.pop()
        if depth > 32:
            raise ValueError("Fixture JSON nesting limit exceeded")
        if isinstance(node, dict):
            pending.extend((child, depth + 1) for child in node.values())
        elif isinstance(node, list):
            pending.extend((child, depth + 1) for child in node)


class FixtureFetcher(SafeFetcher):
    async def get(self, url, source, *, accept, conditional=True):
        started = time.perf_counter()
        if not hasattr(self, "error_categories"):
            self.error_categories = {}
        try:
            data = await super().get(url, source, accept=accept, conditional=conditional)
        except (httpx.TimeoutException, TimeoutError):
            self.error_categories[source.id] = "timeout"
            raise
        except httpx.HTTPError:
            self.error_categories[source.id] = "fetch"
            raise
        except ValueError:
            self.error_categories[source.id] = "security"
            raise
        finally:
            if not hasattr(self, "fixture_fetch_seconds"):
                self.fixture_fetch_seconds = {}
            self.fixture_fetch_seconds[source.id] = self.fixture_fetch_seconds.get(source.id, 0) + time.perf_counter() - started
        if data is not None and source.adapter == "json_api":
            try:
                strict_fixture_json(data)
            except (ValueError, RecursionError):
                self.error_categories[source.id] = "parser"
                raise
        return data


def freshness(item, now):
    if item.advisory:
        age = (now.date() - item.advisory.catalog_added_on).days
        return "future-date" if age < 0 else "recent-advisory-date" if age <= 3 else "stale"
    if item.missing_publication_time:
        return "unknown-publication-time"
    return "recent-announcement" if timedelta(0) <= now - item.published_at <= timedelta(hours=72) else "stale"


async def simulate(sources, now, scenario):
    payloads = fixture_payloads(now, scenario)
    endpoints = {s.endpoint: s for s in sources}
    attempts = {s.id: 0 for s in sources}
    requests, delivered_bytes, statuses = [], {}, {}

    def transport(request):
        url = str(request.url)
        if url not in endpoints:
            raise ValueError("Unexpected fixture request; no real network is available")
        source = endpoints[url]
        attempts[source.id] += 1
        requests.append({"source_id": source.id, "url": url,
                         "conditional": "if-none-match" in request.headers})
        if scenario == "timeout":
            raise httpx.ReadTimeout("Synthetic bounded timeout", request=request)
        code, headers, content = 200, {}, payloads[source.id][0]
        if scenario == "total-outage" or (scenario == "partial-outage" and source.id == "kubernetes"):
            code, content = 500, b""
        elif scenario == "retry" and attempts[source.id] == 1:
            code, content, headers = 429, b"", {"retry-after": "0"}
        elif scenario.startswith("redirect-"):
            location = {"redirect-private": "https://127.0.0.1/private",
                        "redirect-off-domain": "https://evil.example/feed",
                        "redirect-loop": source.endpoint}[scenario]
            code, content, headers = 302, b"", {"location": location}
        elif scenario == "conditional" and "if-none-match" in request.headers:
            code, content = 304, b""
        elif scenario == "oversize":
            content = b" " * (source.fetch_policy.max_response_bytes + 1)
        headers.update({"content-type": payloads[source.id][1], "etag": '"synthetic-fixture-v1"'})
        delivered_bytes[source.id] = delivered_bytes.get(source.id, 0) + len(content)
        statuses[str(code)] = statuses.get(str(code), 0) + 1
        return httpx.Response(code, headers=headers, content=content)

    outcomes, observations, contracts, timings, items = [], [], [], [], []
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport), trust_env=False) as client:
        fetcher = FixtureFetcher(client, {}, "Techline-Local-Synthetic-Simulation/1")
        for original in sources:
            source = original
            if scenario == "template-origin" and source.id == "cisa_kev":
                source = source.model_copy(update={"field_templates": {
                    **source.field_templates, "url": "https://evil.example/{cveID}"}})
            before = time.perf_counter()
            previous_fetch_seconds = getattr(fetcher, "fixture_fetch_seconds", {}).get(source.id, 0)
            phase = "collection"
            try:
                async with asyncio.timeout(120):
                    raw_items = await ADAPTERS[source.adapter].fetch(source, fetcher)
                if raw_items is None:
                    raise ValueError("Unchanged response without current-run fixture evidence")
                fetch_end = time.perf_counter()
                phase = "validation"
                valid, invalid, rights_rejected = [], 0, 0
                for raw in raw_items or []:
                    raw["is_demo"] = True
                    try:
                        item = normalize(raw, source, now)
                    except RightsRejection:
                        rights_rejected += 1
                        continue
                    except (ValueError, TypeError):
                        invalid += 1
                        continue
                    binding = bind_item(item, raw)
                    rights_rejected += bool(item.rights_review and item.rights_review.state == "REJECTED")
                    observation = {"binding": binding.model_dump(mode="json"), "synthetic": True,
                                   "review_status": item.rights_review.state if item.rights_review else "REVIEW_REQUIRED",
                                   "freshness": freshness(item, now)}
                    observations.append(observation)
                    contracts.append(attribution_contract(item, original, binding, now, ledger=ReviewLedger()))
                    valid.append(item)
                parse_seconds = fetch_end - before
                network_seconds = getattr(fetcher, "fixture_fetch_seconds", {}).get(source.id, 0) - previous_fetch_seconds
                parser_seconds = max(0, parse_seconds - network_seconds)
                normalization_seconds = time.perf_counter() - fetch_end
                items.extend(valid)
                if scenario == "conditional":
                    key = source.id + "|" + source.endpoint
                    fetcher.state[key]["item_ids"] = [item.id for item in valid]
                    assert await ADAPTERS[source.adapter].fetch(source, fetcher) is None
                    assert {item.id for item in valid} <= fetcher.revalidated_ids
                timings.append({"source_id": source.id, "fetch_and_parse_seconds": round(parse_seconds, 6),
                                "fixture_fetch_seconds": round(network_seconds, 6),
                                "parser_seconds": round(parser_seconds, 6),
                                "normalize_seconds": round(normalization_seconds, 6),
                                "items_per_second": round(len(valid) / max(parse_seconds + normalization_seconds, 1e-9), 2)})
                outcomes.append({"source_id": source.id, "attempted": True,
                                 "status": ("held" if valid else "quarantined" if invalid else
                                            "rights-rejected" if rights_rejected else "empty"),
                                 "error_category": "validation" if invalid else None,
                                 "rights_rejected": rights_rejected,
                                 "normalized": len(valid),
                                 "invalid": invalid, "raw": len(raw_items or [])})
            except (ValueError, TypeError, KeyError, RecursionError, httpx.HTTPError, TimeoutError) as error:
                category = ("timeout" if isinstance(error, (httpx.TimeoutException, TimeoutError))
                            else getattr(fetcher, "error_categories", {}).get(source.id,
                                 "validation" if phase == "validation" else "parser"))
                outcomes.append({"source_id": source.id, "attempted": True, "status": "failed",
                                 "error_category": category, "error_type": type(error).__name__})
        unique, duplicates = deduplicate(items)
        reversed_unique, _ = deduplicate(list(reversed(items)))
        assert [i.model_dump(mode="json") for i in unique] == [i.model_dump(mode="json") for i in reversed_unique]
        assert all(not i.publication_eligible for i in items)
    # Per-item observation identity retains changed evidence even with duplicate IDs.
    observations = sorted({digest(row): row for row in observations}.values(), key=digest)
    contracts = sorted({digest(row): row for row in contracts}.values(), key=digest)
    verdict, problems = scenario_verdict(scenario, outcomes)
    deterministic = {"scenario": scenario, "outcomes": outcomes, "observations": observations, "contracts": contracts,
                     "verdict": verdict, "unexpected_outcomes": problems, "outcome": collection_outcome(outcomes),
                     "unique_items": len(unique), "duplicates_removed": duplicates,
                     "requests": requests, "attempts": attempts, "status_counts": statuses,
                     "fixture_response_bytes": delivered_bytes, "publication_items": 0, "ai_calls": 0,
                     "source_enablement_changed": False, "post_selection_dedupe_stable": True,
                     "selection_scope": "newest entries within the fetched byte-bounded response; no pagination"}
    return deterministic, timings


def write_report(root, report):
    path = local_path(root, ".cache/phase3/staging/report.json")
    if report.get("status") == "passed":
        atomic_json(local_path(root, ".cache/phase3/staging/last-successful-report.json"), report)
    atomic_json(path, report)
    return path


async def run_staging(root=ROOT, *, scenarios=SCENARIOS, now=DEFAULT_AS_OF):
    root = Path(root)
    if now.tzinfo is None:
        raise ValueError("Simulation requires an aware clock")
    if not scenarios or any(s not in SCENARIOS for s in scenarios):
        raise ValueError("Unknown synthetic scenario")
    protected_before = protected_hashes(root)
    registry = SourceRegistry.model_validate(yaml.safe_load((root / "config/sources.yaml").read_text(encoding="utf-8")))
    sources = [s for s in registry.sources if s.id in {"kubernetes", "cisa_kev"}]
    rights = json.loads((root / "config/source-rights.json").read_text(encoding="utf-8")).get("sources", {})
    if not isinstance(rights, dict) or any(not isinstance(rights.get(s.id), dict) for s in sources):
        raise ValueError("Simulation requires disabled pilots with valid source-rights configuration")
    if len(sources) != 2 or any(s.enabled or rights.get(s.id, {}).get("publication") != "exclude"
                                or rights.get(s.id, {}).get("ai_submission_allowed") is not False for s in sources):
        raise ValueError("Simulation requires both pilots to remain disabled, excluded and AI denied")
    if tracemalloc.is_tracing():
        raise ValueError("Run allocation measurement in a dedicated process")
    started = time.perf_counter()
    tracemalloc.start()
    results, metrics = [], []
    try:
        for scenario in scenarios:
            result, timing = await simulate(sources, now, scenario)
            results.append(result)
            metrics.append({"scenario": scenario, "sources": timing})
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
        if protected_hashes(root) != protected_before:
            raise ValueError("Protected canonical/configuration files changed during local simulation")
    # A required normal scenario is authoritative for run health. Injected
    # adversarial scenarios cannot hide a nominal source failure.
    nominal = next((r for r in results if r["scenario"] == "normal"), None)
    status = "failed" if any(r["verdict"] == "failed" for r in results) else "passed"
    outcome = nominal["outcome"] if nominal else collection_outcome([
        o for row in results for o in row["outcomes"]])
    deterministic = {"version": 2, "mode": "synthetic-fixtures-only", "as_of": now.isoformat(),
                     "status": status, "outcome": outcome,
                     "live_requests": 0, "publication_allowed": False, "ai_submission_allowed": False,
                     "results": results, "protected_sha256": protected_before}
    report = {"status": status, "outcome": outcome,
              "partial_success_policy": "diagnostics retained; unexpected required-source degradation fails verification",
              "deterministic": deterministic, "deterministic_sha256": digest(deterministic),
              "measurements": {"total_seconds": round(time.perf_counter() - started, 6),
                               "traced_python_peak_bytes": peak, "sources": metrics},
              "limitations": ["Fixture response bytes and 304 outcomes are not live publisher observations.",
                              "Tracemalloc measures Python allocations, not complete process RSS.",
                              "No publisher terms, creator identity or reuse permission established.",
                              "Results are internal metadata and must never be public article inputs."]}
    # Fixed point includes the size field itself and the exact atomic_json
    # separators/newline, so the footprint is actual on-disk UTF-8 bytes.
    report["measurements"]["serialized_report_bytes"] = 0
    while True:
        actual_size = len(json.dumps(report, ensure_ascii=False, separators=(",", ":")).encode()) + 1
        if report["measurements"]["serialized_report_bytes"] == actual_size:
            break
        report["measurements"]["serialized_report_bytes"] = actual_size
    path = write_report(root, report)
    # Standalone binding and pending decision examples contain only synthetic
    # evidence, no approval. They are not loaded by production or the simulator.
    normal = next((r for r in results if r["scenario"] == "normal"), None)
    if normal and normal["verdict"] == "passed" and normal["observations"]:
        binding = ItemBinding.model_validate(normal["observations"][0]["binding"])
        source = next(s for s in sources if s.id == binding.source_id)
        atomic_json(local_path(root, ".cache/phase3/staging/binding-example.json"), binding)
        example = draft(binding, source.name, "synthetic-operator-not-a-rights-approval", now, synthetic=True)
        example = example.model_copy(update={"evidence": [ReviewEvidence(
            url="https://rights.example/synthetic-evidence-only", scope="specific-item",
            note="Synthetic fixture evidence only. This is not a real publisher record or permission grant.")]})
        atomic_json(local_path(root, ".cache/phase3/staging/review-example.json"),
                    example)
    return report, path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("all", *SCENARIOS), default="all")
    parser.add_argument("--as-of", default=DEFAULT_AS_OF.isoformat(), help="Explicit synthetic clock (timezone required)")
    args = parser.parse_args()
    try:
        report, path = asyncio.run(run_staging(scenarios=SCENARIOS if args.scenario == "all" else (args.scenario,),
                                           now=datetime.fromisoformat(args.as_of)))
        print(json.dumps({"status": report["status"], "outcome": report["outcome"],
                          "source_outcomes": [{"scenario": r["scenario"], "verdict": r["verdict"],
                                               "outcomes": r["outcomes"]} for r in report["deterministic"]["results"]],
                          "mode": "synthetic-fixtures-only", "scenarios": len(report["deterministic"]["results"]),
                          "deterministic_sha256": report["deterministic_sha256"],
                          "measurements": {k: v for k, v in report["measurements"].items() if k != "sources"},
                          "report": str(path), "publication_allowed": False,
                          "ai_submission_allowed": False}, indent=2))
        raise SystemExit(0 if report["status"] == "passed" else 1)
    except (ValueError, OSError, TypeError) as error:
        print(json.dumps({"status": "refused", "error_type": type(error).__name__, "publication_allowed": False}))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
