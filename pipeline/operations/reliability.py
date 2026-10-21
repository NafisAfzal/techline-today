"""Offline fault matrix through the existing fetcher, adapters and diagnostics."""

from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx

from pipeline.filesystem import confined_file
from pipeline.generation import bounded_file
from pipeline.source_diagnostics import FIXTURE_CLOCK, fixture_response, research_sources, run_diagnostics

CASES = ("control", "dns", "timeout", "malformed-json", "malformed-xml", "encoding", "mime", "oversized",
         "redirect", "rate-limit", "outage", "duplicates", "schema", "missing-date", "stale", "future")


async def source_rehearsal(root):
    results = []
    with TemporaryDirectory(prefix="techline-source-faults-") as directory:
        base = Path(directory)
        for case in CASES:
            work = base / case
            (work / "config").mkdir(parents=True)
            for name in ["phase4-research-sources.yaml", "source-rights.json", "sources.yaml", "release.json", "ai.yaml"]:
                (work / "config" / name).write_bytes(bounded_file(confined_file(root, "config/" + name), 200_000))
            registry = research_sources(work)
            source = next(s for s in registry if s.id == (
                "research_rust_blog" if case == "malformed-xml" else "research_pytorch"))

            def handler(request, fault=case, selected=source):
                if fault == "dns":
                    raise httpx.ConnectError("Synthetic DNS failure", request=request)
                if fault == "timeout":
                    raise httpx.ReadTimeout("Synthetic timeout", request=request)
                if fault in {"rate-limit", "outage"}:
                    return httpx.Response(429 if fault == "rate-limit" else 503, headers={"retry-after": "0"})
                if fault == "redirect":
                    return httpx.Response(302, headers={"location": "https://untrusted.example/poison"})
                if fault in {"malformed-json", "encoding", "oversized", "mime", "malformed-xml"}:
                    payload, mime = {
                        "malformed-json": (b"{invalid", "application/json"),
                        "encoding": (b"\xff\xfe", "application/json"),
                        "oversized": (b"x" * (selected.fetch_policy.max_response_bytes + 1), "application/json"),
                        "mime": (b"{}", "text/html"),
                        "malformed-xml": (b"<rss><unclosed", "application/rss+xml"),
                    }[fault]
                    return httpx.Response(200, content=payload, headers={"content-type": mime})
                data = fixture_response(request).json()
                if fault == "duplicates":
                    data.append(dict(data[0]))
                elif fault == "schema":
                    data = {"unexpected_schema": data}
                elif fault == "missing-date":
                    data[0].pop("published_at")
                elif fault in {"stale", "future"}:
                    data[0]["published_at"] = (FIXTURE_CLOCK + timedelta(days=3 if fault == "future" else -10)).isoformat()
                return httpx.Response(200, json=data)

            report = await run_diagnostics(root=work, source_ids=[source.id], transport=httpx.MockTransport(handler))
            row = report["sources"][0]
            if case == "control":
                detected = report["outcome"] == "RIGHTS_BLOCKED"
            elif case == "duplicates":
                detected = row["duplicate_items"] == 1
            elif case == "missing-date":
                detected = row["timestamp_quality"].get("missing", 0) == 1 or row["invalid_items"] == 1
            elif case == "stale":
                detected = row["freshness"].get("older_than_72h", 0) == 1
            elif case == "future":
                detected = (row["timestamp_quality"].get("invalid_or_future", 0) == 1
                            and row["freshness"].get("unknown", 0) == 1)
            else:
                detected = row["collection_status"] in {"SOURCE_FAILURE", "VALIDATION_FAILURE", "PARTIAL_DEGRADATION"}
            isolated = (not report["publication_allowed"] and not report["ai_submission_allowed"]
                        and not row["source_enabled"] and not report["raw_content_retained"]
                        and not row["recovery"]["canonical_replacement_attempted"])
            results.append({"case": case, "passed": detected and isolated,
                            "collection": row["collection_status"], "rights": row["rights_status"],
                            "timestamp_quality": row["timestamp_quality"], "freshness": row["freshness"],
                            "error_type": row.get("error_type"), "requests": row["recovery"]["http_attempts"]})
    return {"version": 1, "status": "PASS" if all(r["passed"] for r in results) else "FAIL", "cases": results,
            "synthetic_only": True, "network_access": False, "raw_content_retained": False,
            "publication_allowed": False, "ai_submission_allowed": False,
            "note": "Mock transport exercises software failure handling, not real DNS, publisher uptime or rights."}
