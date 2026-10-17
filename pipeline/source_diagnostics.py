"""Local, nonpublishing source diagnostics. Default transport is synthetic.

Live mode uses only the checked-in research registry, without credentials, AI,
canonical state, response caches, approval decisions or upstream pagination.
"""

import argparse
import asyncio
import hashlib
import json
import time
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import yaml

from pipeline.adapters import ADAPTERS
from pipeline.editorial_intake import intake_assessment
from pipeline.models import SourceRegistry
from pipeline.normalize import RightsRejection, normalize, parse_date
from pipeline.pilot_staging import protected_hashes
from pipeline.review_governance import bind_item, digest, writer_lock
from pipeline.security import SafeFetcher, public_transport
from pipeline.storage import atomic_json

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_CLOCK = datetime(2026, 10, 17, 12, tzinfo=UTC)
FAILURES = {"SOURCE_FAILURE", "VALIDATION_FAILURE", "PARTIAL_DEGRADATION"}


def research_sources(root=ROOT):
    registry = SourceRegistry.model_validate(yaml.safe_load(
        (root / "config/phase4-research-sources.yaml").read_text(encoding="utf-8")))
    if not registry.sources or len(registry.sources) > 8:
        raise ValueError("Research registry exceeds local request budget")
    for source in registry.sources:
        if (source.enabled or not source.rights_review_required or not source.rights_guard
                or source.fetch_policy.conditional_requests
                or source.adapter not in {"rss", "github_releases"}
                or (source.adapter == "github_releases" and len(source.repositories) != 1)):
            raise ValueError("Research sources must remain disabled, review-held and single-endpoint")
    return registry.sources


def diagnostic_path(root, name):
    # No user-supplied output path. Refuse linked ancestors and targets.
    root = Path(root).resolve()
    if name not in {"fixture-report.json", "fixture-report.md", "live-report.json", "live-report.md", "writer.lock"}:
        raise ValueError("Unknown diagnostic filename")
    target = root / ".cache/phase4" / name
    for candidate in (target, *target.parents):
        if candidate == root:
            break
        if candidate.is_symlink() or candidate.is_junction():
            raise ValueError("Linked diagnostic paths are forbidden")
    if not target.resolve().is_relative_to(root / ".cache/phase4"):
        raise ValueError("Diagnostic output escaped isolation")
    return target


class DiagnosticFetcher(SafeFetcher):
    def __init__(self, client):
        super().__init__(client, {}, "TechlineToday-Research/0.1 (local bounded diagnostics)")
        self.requests = []
        self.transport_failures = set()

    async def get(self, url, source, *, accept, conditional=True):
        try:
            return await super().get(url, source, accept=accept, conditional=conditional)
        except (ValueError, httpx.HTTPError, OSError, TimeoutError):
            self.transport_failures.add(source.id)
            raise

    async def request(self, url, headers, source, accept):
        start = time.perf_counter()
        statuses = []
        attempts = 0
        # SafeFetcher's retry/rate/redirect/DNS/size behavior remains authoritative.
        # Client response hook records actual attempts, including exhausted retries.
        async def response_hook(response):
            statuses.append(response.status_code)
        async def request_hook(request):
            nonlocal attempts
            attempts += 1
        self.client.event_hooks["response"].append(response_hook)
        self.client.event_hooks["request"].append(request_hook)
        try:
            status, response_headers, body = await super().request(url, headers, source, accept)
            return status, response_headers, body
        finally:
            self.client.event_hooks["response"].remove(response_hook)
            self.client.event_hooks["request"].remove(request_hook)
            self.requests.append({"source_id": source.id, "statuses": statuses, "attempts": attempts,
                                  "duration_seconds": round(time.perf_counter() - start, 6)})


def fixture_response(request):
    if request.url.host == "api.github.com":
        repo = "/".join(request.url.path.split("/")[2:4])
        return httpx.Response(200, json=[{
            "id": 1, "tag_name": "v0.0.1", "name": "Synthetic release fixture",
            "html_url": f"https://github.com/{repo}/releases/tag/v0.0.1",
            "published_at": (FIXTURE_CLOCK - timedelta(hours=2)).isoformat(),
            "body": "Synthetic source prose, never a real release or publication approval.",
            "author": {"login": "synthetic-fixture-not-a-reviewer"}}])
    return httpx.Response(200, headers={"content-type": "application/rss+xml"}, content=(
        b'<rss version="2.0"><channel><title>Synthetic</title><item>'
        b'<title>Synthetic Rust project update</title><link>https://blog.rust-lang.org/synthetic/</link>'
        b'<pubDate>Sat, 17 Oct 2026 10:00:00 GMT</pubDate>'
        b'<description>Synthetic text only. No permission is asserted.</description>'
        b'</item></channel></rss>'))


def timestamp_quality(raw, item, now):
    value = raw.get("published_at")
    if not value:
        return "missing"
    if isinstance(value, str) and len(value) == 10:
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return "date_only"
        except ValueError:
            return "invalid"
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            # RFC feed dates carry an explicit numeric/GMT timezone.
            from email.utils import parsedate_to_datetime
            try:
                parsed = parsedate_to_datetime(value)
            except (ValueError, TypeError):
                return "invalid_or_future" if item.missing_publication_time else "invalid"
        if parsed.tzinfo is None:
            return "timezone_missing"
    if item.missing_publication_time:
        return "invalid_or_future"
    return "validated_timestamp"


def aggregate(rows, field):
    states = [row[field] for row in rows]
    if not states:
        return "VALIDATION_FAILURE"
    if all(state == "SOURCE_FAILURE" for state in states):
        return "SOURCE_FAILURE"
    if all(state == "VALIDATION_FAILURE" for state in states):
        return "VALIDATION_FAILURE"
    if any(state in FAILURES for state in states):
        return "PARTIAL_DEGRADATION"
    if all(state == "EMPTY" for state in states):
        return "EMPTY"
    return "RIGHTS_BLOCKED" if "RIGHTS_BLOCKED" in states else "SUCCESS"


def date_evidence(value, now):
    """Local date evidence only; never promote an update/creation to publication."""
    parsed, missing = parse_date(value, now)
    if not missing:
        return {"timestamp": parsed.isoformat(), "date": None, "precision": "timestamp"}
    if isinstance(value, str) and len(value) == 10:
        try:
            calendar = datetime.strptime(value, "%Y-%m-%d").date().isoformat()
            return {"timestamp": None, "date": calendar, "precision": "date"}
        except ValueError:
            pass
    return {"timestamp": None, "date": None, "precision": "unknown"}


async def inspect_source(source, fetcher, now, *, synthetic, policy):
    start = time.perf_counter()
    row = {"source_id": source.id, "publisher": source.name, "attempted": True,
           "collection_status": "SOURCE_FAILURE", "outcome": "SOURCE_FAILURE",
           "source_enabled": source.enabled, "source_policy": policy.get("publication", "absent"),
           "item_review": "REVIEW_REQUIRED", "publication_allowed": False, "ai_submission_allowed": False,
           "raw_items": 0, "valid_items": 0, "duplicate_items": 0, "invalid_items": 0,
           "parse_failures": 0, "rights_blocked_items": 0, "rights_excluded_items": 0,
           "rejections": {}, "freshness": {},
           "transport_validation_failures": 0,
           "timestamp_quality": {}, "attribution": {"publisher_identified": 0, "author_observed": 0,
                                                      "original_creator_verified": 0},
           "observations": [], "pagination": "one fetched page only; no upstream links followed",
           "editorial_kind": "official-release-announcement" if source.adapter == "github_releases"
                             else "official-project-update; item editorial review required"}
    try:
        async with asyncio.timeout(120):
            raw_items = await ADAPTERS[source.adapter].fetch(source, fetcher)
        if raw_items is None:
            raise ValueError("Diagnostics have no cached evidence for 304")
        row["raw_items"] = len(raw_items)
        seen, freshness, quality, rejected = set(), Counter(), Counter(), Counter()
        for raw in raw_items:
            try:
                item = normalize(raw, source, now)
                if item.rights_review is None:
                    raise ValueError("Research item lost mandatory review hold")
                binding = bind_item(item, raw).model_copy(update={"provenance": "synthetic" if synthetic else "unknown"})
                identity = (item.id, item.content_hash, binding.evidence_sha256)
                if identity in seen:
                    row["duplicate_items"] += 1
                    continue
                seen.add(identity)
                row["valid_items"] += 1
                row["rights_blocked_items"] += 1
                row["rights_excluded_items"] += item.rights_review.state == "REJECTED"
                rejected.update(item.rights_review.reasons)
                stamp_quality = timestamp_quality(raw, item, now)
                quality[stamp_quality] += 1
                age = (now - item.published_at).total_seconds() / 3600
                freshness["unknown" if stamp_quality != "validated_timestamp" else
                          "within_24h" if age <= 24 else "within_72h" if age <= 72 else "older_than_72h"] += 1
                row["attribution"]["publisher_identified"] += bool(item.publisher)
                row["attribution"]["author_observed"] += bool(item.author)
                row["observations"].append({"binding": binding.model_dump(mode="json"),
                    "editorial_intake": intake_assessment(item, now),
                    "review_state": item.rights_review.state, "timestamp_quality": stamp_quality,
                    "dates": {"source_published": date_evidence(raw.get("published_at"), now),
                              "source_updated": date_evidence(raw.get("updated_at"), now),
                              "release_created": date_evidence(raw.get("release_created_at"), now)},
                    "published_at": item.published_at.isoformat() if stamp_quality == "validated_timestamp" else None,
                    "publication_date_only": str(raw["published_at"]) if stamp_quality == "date_only" else None})
            except RightsRejection:
                row["rights_blocked_items"] += 1
                row["rights_excluded_items"] += 1
                rejected["incompatible_rights_marker"] += 1
            except (ValueError, TypeError, OverflowError):
                row["invalid_items"] += 1
                rejected["normalization_failure"] += 1
        row["freshness"], row["timestamp_quality"], row["rejections"] = dict(freshness), dict(quality), dict(rejected)
        row["observations"].sort(key=lambda entry: digest(entry))
        collection = ("EMPTY" if not raw_items else "VALIDATION_FAILURE" if row["invalid_items"] == len(raw_items)
                      else "PARTIAL_DEGRADATION" if row["invalid_items"] else "SUCCESS")
        row["collection_status"] = collection
        row["outcome"] = "RIGHTS_BLOCKED" if collection == "SUCCESS" else collection
    except (ValueError, KeyError, TypeError, UnicodeError) as error:
        transport_failure = source.id in fetcher.transport_failures
        row.update(collection_status="VALIDATION_FAILURE", outcome="VALIDATION_FAILURE",
                   parse_failures=int(not transport_failure), transport_validation_failures=int(transport_failure),
                   error_type=type(error).__name__)
    except (httpx.HTTPError, TimeoutError, OSError) as error:
        row["error_type"] = type(error).__name__
    except Exception as error:
        # Unexpected adapter bugs fail the run and retain only the exception type.
        row["error_type"] = type(error).__name__
    finally:
        row["duration_seconds"] = round(time.perf_counter() - start, 6)
        row["requests"] = [record for record in fetcher.requests if record["source_id"] == source.id]
        statuses = [status for record in row["requests"] for status in record["statuses"]]
        row["recovery"] = {"http_attempts": sum(record["attempts"] for record in row["requests"]),
                           "http_response_count": len(statuses),
                           "recovered_after_http_retry": any(s >= 400 for s in statuses) and bool(statuses)
                                                         and 200 <= statuses[-1] < 300,
                           "last_known_good_used": False, "canonical_replacement_attempted": False}
    return row


def human_report(report):
    lines = ["# Local source diagnostics", "", f"Mode: {report['mode']}; outcome: {report['outcome']}.",
             f"Collection: {report['collection_status']}; as of: {report['as_of']}.",
             f"Report digest: {report['report_sha256']}", "",
             "Publication and AI submission denied. No retained titles, prose or response bodies.", "",
             "| Source | Collection | Disposition | Valid | Invalid | Duplicates | Seconds |",
             "|---|---|---|---:|---:|---:|---:|"]
    for row in report["sources"]:
        lines.append(f"| {row['source_id']} | {row['collection_status']} | {row['outcome']} | "
                     f"{row['valid_items']} | {row['invalid_items']} | {row['duplicate_items']} | {row['duration_seconds']} |")
    lines.extend(["", "Single-run observations do not establish availability history or publisher rights.",
                  "Only fetched pages are measured. Source selection is bounded before diagnostics.",
                  "JSON is authoritative for timestamps, attribution, rejection reasons and recovery."])
    return "\n".join(lines) + "\n"


async def run_diagnostics(*, root=ROOT, live=False, source_ids=None, now=None, transport=None):
    # One writer also prevents concurrent operators from multiplying the local
    # request budget. Abrupt termination leaves a lock: never steal it by age.
    with writer_lock(diagnostic_path(root, "writer.lock")):
        return await _run_diagnostics(root=root, live=live, source_ids=source_ids, now=now, transport=transport)


async def _run_diagnostics(*, root, live, source_ids, now, transport):
    if transport is not None and not isinstance(transport, httpx.MockTransport):
        raise ValueError("Only synthetic MockTransport overrides are accepted")
    now = now or (datetime.now(UTC) if live else FIXTURE_CLOCK)
    if now.tzinfo is None:
        raise ValueError("Aware diagnostic clock required")
    sources = research_sources(root)
    if source_ids:
        if not set(source_ids) <= {s.id for s in sources}:
            raise ValueError("Unknown research source")
        sources = [s for s in sources if s.id in source_ids]
    # Validate both paths before any network operation or write.
    stem = "live" if live else "fixture"
    paths = [diagnostic_path(root, f"{stem}-report.{extension}") for extension in ("json", "md")]
    before = protected_hashes(root)
    before["config/phase4-research-sources.yaml"] = hashlib.sha256(
        (root / "config/phase4-research-sources.yaml").read_bytes()).hexdigest()
    rights = json.loads((root / "config/source-rights.json").read_text(encoding="utf-8"))["sources"]
    selected_transport = transport if transport is not None else public_transport() if live else httpx.MockTransport(fixture_response)
    try:
        async with httpx.AsyncClient(transport=selected_transport, timeout=10, trust_env=False,
                                     limits=httpx.Limits(max_connections=1)) as client:
            fetcher = DiagnosticFetcher(client)
            rows = []
            # Sequential, shared per-host rate budget; never fan out public probes.
            for source in sources:
                rows.append(await inspect_source(source, fetcher, now, synthetic=not live,
                                                 policy=rights.get(source.id, {})))
    finally:
        after = protected_hashes(root)
        after["config/phase4-research-sources.yaml"] = hashlib.sha256(
            (root / "config/phase4-research-sources.yaml").read_bytes()).hexdigest()
        if after != before:
            raise ValueError("Protected production state changed during diagnostics")
    collection = aggregate(rows, "collection_status")
    outcome = aggregate(rows, "outcome")
    states = {"SUCCESS": "COLLECTION_SUCCESS", "EMPTY": "COLLECTION_EMPTY",
              "PARTIAL_DEGRADATION": "COLLECTION_DEGRADED", "SOURCE_FAILURE": "COLLECTION_FAILED",
              "VALIDATION_FAILURE": "COLLECTION_FAILED"}
    for row in rows:
        rights_state = ("RIGHTS_EXCLUDED" if row["raw_items"] and
                        row["rights_excluded_items"] == row["raw_items"] else "RIGHTS_REVIEW_REQUIRED")
        parse_outcome = ("failed" if row["parse_failures"] else "not_completed"
                         if row["collection_status"] == "SOURCE_FAILURE" or row["transport_validation_failures"]
                         else "partial" if row["invalid_items"] else "empty" if not row["raw_items"] else "validated")
        row.update(collection_state=states[row["collection_status"]], rights_status=rights_state,
                   editorial_status="EDITORIAL_PENDING", observed_at=now.isoformat(),
                   parse_outcome=parse_outcome,
                   provenance_quality="synthetic" if not live else "unknown")
    report = {"version": 2, "run_id": str(uuid4()),
              "mode": "live-research-only" if live else "synthetic-fixtures-only",
              "transport_kind": "synthetic-mock" if transport is not None or not live else "pinned-public-https",
              "as_of": now.isoformat(), "collection_status": collection, "collection_state": states[collection],
              "rights_status": "RIGHTS_EXCLUDED" if all(row["rights_status"] == "RIGHTS_EXCLUDED" for row in rows)
                               else "RIGHTS_REVIEW_REQUIRED", "editorial_status": "EDITORIAL_PENDING",
              "exit_code": int(outcome in FAILURES),
              "outcome": outcome, "publication_allowed": False, "ai_submission_allowed": False,
              "canonical_sha256": before["content/generated/snapshot.json"], "sources": rows,
              "protected_sha256": before, "raw_content_retained": False}
    report["report_sha256"] = digest(report)
    atomic_json(paths[0], report)
    # Atomic replacement for Markdown too; paired files share a digest, not a transaction.
    import os
    import tempfile
    handle, temporary = tempfile.mkstemp(dir=paths[1].parent, suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(human_report(report))
        Path(temporary).replace(paths[1])
    finally:
        Path(temporary).unlink(missing_ok=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Bounded research requests; never publication")
    parser.add_argument("--source", action="append", choices=[s.id for s in research_sources()])
    args = parser.parse_args()
    try:
        report = asyncio.run(run_diagnostics(live=args.live, source_ids=args.source))
        print(json.dumps({k: report[k] for k in ("mode", "collection_status", "outcome", "report_sha256",
                                                "publication_allowed", "ai_submission_allowed")}, indent=2))
        return 1 if report["outcome"] in FAILURES else 0
    except (ValueError, OSError, TypeError):
        print(json.dumps({"outcome": "VALIDATION_FAILURE", "publication_allowed": False}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
