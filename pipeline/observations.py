"""Manual, nonpublishing daily source-health receipts. No scheduler or AI."""

import argparse
import asyncio
import re
import time
from collections import Counter
from datetime import UTC, datetime, timedelta
from itertools import islice
from typing import Literal

from pipeline.authority.protocol import Identifier, Model
from pipeline.filesystem import confined_file
from pipeline.review_governance import bounded_json, digest, writer_lock
from pipeline.source_diagnostics import ROOT, run_diagnostics
from pipeline.storage import atomic_json

DIRECTORY = ".cache/phase4/observations"


class ObservationContext(Model):
    """Optional context in the existing v1 receipt; declarations are not trust."""

    version: Literal[1]
    environment_id: Identifier
    ledger_id: Identifier
    provenance: Literal["operator-local", "synthetic"]


def transport_evidence(row):
    statuses = [status for request in row.get("requests", []) for status in request["statuses"]]
    if any(type(status) is not int or not 100 <= status <= 599 for status in statuses):
        raise ValueError("Invalid HTTP observation status")
    error = row.get("error_type")
    if error is not None and (not isinstance(error, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,99}", error)):
        raise ValueError("Invalid diagnostic error category")
    # Only terminal exceptions are observed by the adapter boundary. Do not
    # infer timeout counts from attempts without a corresponding HTTP response.
    return {"http_status_counts": {str(status): count for status, count in sorted(Counter(statuses).items())},
            "terminal_error_type": error,
            "terminal_timeout": error in {"TimeoutException", "ConnectTimeout", "ReadTimeout", "WriteTimeout", "PoolTimeout", "TimeoutError"},
            "timeout_scope": "terminal-only"}


def compact_receipt(report, observed_at, *, context=None):
    payload = {key: value for key, value in report.items() if key != "report_sha256"}
    if (digest(payload) != report.get("report_sha256") or report.get("publication_allowed") is not False
            or report.get("ai_submission_allowed") is not False or report.get("raw_content_retained") is not False):
        raise ValueError("Invalid or non-isolated observation report")
    live = report.get("mode") == "live-research-only" and report.get("transport_kind") == "pinned-public-https"
    sources = [{**{key: row[key] for key in (
        "source_id", "collection_state", "rights_status", "editorial_status", "valid_items",
        "invalid_items", "duplicate_items", "duration_seconds", "freshness", "recovery")},
        "transport": transport_evidence(row)} for row in report["sources"]]
    result = {"version": 1, "observed_at": observed_at.isoformat(), "live": live,
            "run_id": report["run_id"], "report_sha256": report["report_sha256"],
            "collection_state": report["collection_state"], "publication_allowed": False,
            "ai_submission_allowed": False, "sources": sources}
    if context is not None:
        checked = ObservationContext.model_validate(context)
        if checked.provenance != ("operator-local" if live else "synthetic"):
            raise ValueError("Observation provenance declaration contradicts the transport")
        result["context"] = checked.model_dump(mode="json")
    return result


def summary(receipts, now):
    # Synthetic loops never add elapsed live evidence. Source coverage must be
    # stable; otherwise the observation period restarts for the changed set.
    live = sorted([row for row in receipts if row["live"]], key=lambda row: row["observed_at"])
    times = [datetime.fromisoformat(row["observed_at"]) for row in live]
    if any(time.tzinfo is None or time > now for time in times):
        raise ValueError("Invalid observation clock")
    span = (times[-1] - times[0]).total_seconds() / 86400 if times else 0
    gaps = [(right - left).total_seconds() / 3600 for left, right in zip(times, times[1:], strict=False)]
    source_sets = {tuple(sorted(row["source_id"] for row in receipt["sources"])) for receipt in live}
    samples = [source for receipt in live for source in receipt["sources"]]
    healthy = {"COLLECTION_SUCCESS", "COLLECTION_EMPTY"}
    rate = sum(row["collection_state"] in healthy for row in samples) / len(samples) if samples else 0
    latest_healthy = bool(live) and all(row["collection_state"] in healthy for row in live[-1]["sources"])
    ready = (span >= 7 and len(live) >= 8 and len(source_sets) == 1 and max(gaps, default=100) <= 36
             and now - times[-1] <= timedelta(hours=36) and rate >= .95 and latest_healthy)
    return {"live_observations": len(live), "elapsed_days": round(span, 3),
            "collection_health_rate": round(rate, 4), "max_gap_hours": max(gaps, default=None),
            "sustained_threshold_met": ready, "publication_allowed": False, "ai_submission_allowed": False,
            "scope": "Local metadata observations; does not establish hosted uptime, rights or production readiness"}


def read_receipts(root):
    parent = confined_file(root, f"{DIRECTORY}/index.json").parent
    receipts = []
    # Filesystem enumeration order is not collection order (notably on restore).
    # Daily UTC filenames provide deterministic order; the evaluator still
    # validates timestamps, duplicate days and clock regressions within it.
    paths = list(islice(parent.glob("????-??-??.json"), 32)) if parent.exists() else []
    if len(paths) > 31:
        raise ValueError("Observation retention capacity: archive metadata receipts before continuing")
    for path in sorted(paths):
        payload = bounded_json(confined_file(root, path.relative_to(root)), limit=100_000)
        if (payload.get("version") != 1 or type(payload.get("live")) is not bool
                or payload.get("receipt_sha256") != digest({key: value for key, value in payload.items()
                                                            if key != "receipt_sha256"})):
            raise ValueError("Corrupt observation receipt")
        receipts.append(payload)
    return receipts


async def observe(root=ROOT, *, live=False, context=None):
    if context is not None:
        checked = ObservationContext.model_validate(context)
        if checked.provenance != ("operator-local" if live else "synthetic"):
            raise ValueError("Observation provenance declaration contradicts the requested transport")
        context = checked.model_dump(mode="json")
    # No caller-supplied wall clock. Unit tests exercise pure summary separately.
    now = datetime.now(UTC)
    lock = confined_file(root, f"{DIRECTORY}/writer.lock")
    with writer_lock(lock):
        receipts = read_receipts(root)
        target = confined_file(root, f"{DIRECTORY}/{now.date().isoformat()}.json" if live else
                                f"{DIRECTORY}/synthetic-latest.json")
        if live and (target.exists() or len(receipts) >= 31):
            raise ValueError("At most one retained live observation per UTC day; preserve existing evidence")
        started = time.perf_counter()
        report = await run_diagnostics(root=root, live=live)
        receipt = compact_receipt(report, now, context=context)
        receipt["run_duration_seconds"] = round(time.perf_counter() - started, 6)
        if live and not receipt["live"]:
            raise ValueError("Synthetic transport cannot count as live observation")
        receipt["receipt_sha256"] = digest(receipt)
        atomic_json(target, receipt)
        result = summary([*receipts, receipt] if live else receipts, now)
        atomic_json(confined_file(root, f"{DIRECTORY}/index.json"), result)
        return result, report["exit_code"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="One bounded manual research observation; no activation")
    parser.add_argument("--summary", action="store_true", help="Read retained local metadata without network")
    parser.add_argument("--environment-id", help="Declared collection environment; not independent authentication")
    parser.add_argument("--ledger-id", help="Declared ledger identity; both identity options are required together")
    args = parser.parse_args()
    if bool(args.environment_id) != bool(args.ledger_id):
        parser.error("Supply both --environment-id and --ledger-id, or neither for a legacy unbound receipt")
    context = (ObservationContext(version=1, environment_id=args.environment_id, ledger_id=args.ledger_id,
                                  provenance="operator-local" if args.live else "synthetic").model_dump(mode="json")
               if args.environment_id else None)
    if args.summary:
        result, code = summary(read_receipts(ROOT), datetime.now(UTC)), 0
    else:
        result, code = asyncio.run(observe(live=args.live, context=context))
    import json
    print(json.dumps(result, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
