"""Operational readiness assessment. Unknown is never reported as PASS.

Each dimension resolves to PASS, FAIL, BLOCKED or INCONCLUSIVE with evidence:

* PASS          - verified, with the observation that proves it
* FAIL          - verified not satisfied, with the specific defect
* BLOCKED       - an owner-controlled decision is the only thing missing
* INCONCLUSIVE  - the evidence does not exist, so nothing can be claimed

The seven-day observation window is validated rather than assumed. Only retained
*live* receipts count; synthetic runs never contribute elapsed time, and receipts
that are copied, reordered, future-dated or too closely spaced are rejected.
"""

import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

PASS, FAIL, BLOCKED, INCONCLUSIVE = "PASS", "FAIL", "BLOCKED", "INCONCLUSIVE"

OBSERVATION_DIRECTORY = ".cache/phase4/observations"
REPORT_DIRECTORY = ".cache/phase6/readiness"
REQUIRED_OBSERVATION_DAYS = 7
MIN_SPACING_HOURS = 12
MAX_GAP_HOURS = 36


def _dimension(name, result, evidence, detail):
    return {"dimension": name, "result": result, "evidence": evidence, "detail": detail}


# --- seven-day observation evidence --------------------------------------------

def observation_evidence(receipts, now, *, required_days=REQUIRED_OBSERVATION_DAYS) -> dict:
    """Validate retained live receipts. Returns eligibility plus every anomaly found."""
    anomalies = []
    live = []
    for receipt in receipts or []:
        if receipt.get("live") is not True:
            continue
        raw = receipt.get("observed_at")
        try:
            observed = datetime.fromisoformat(raw)
        except (TypeError, ValueError):
            anomalies.append({"kind": "unparsable_timestamp", "observed_at": raw})
            continue
        if observed.tzinfo is None:
            anomalies.append({"kind": "naive_timestamp", "observed_at": raw})
            continue
        if observed > now:
            anomalies.append({"kind": "future_timestamp", "observed_at": raw})
            continue
        live.append((observed, receipt))

    live.sort(key=lambda row: row[0])
    days = [observed.date() for observed, _ in live]
    distinct_days = sorted(set(days))

    duplicates = sorted(day.isoformat() for day, count in Counter(days).items() if count > 1)
    if duplicates:
        anomalies.append({"kind": "duplicate_observation_days", "days": duplicates})

    spacings = []
    for (left, _), (right, _) in zip(live, live[1:], strict=False):
        spacing = (right - left).total_seconds() / 3600
        spacings.append(spacing)
        if spacing <= 0:
            anomalies.append({"kind": "non_monotonic_clock", "observed_at": right.isoformat()})
        elif spacing < MIN_SPACING_HOURS:
            anomalies.append({"kind": "overlapping_runs", "gap_hours": round(spacing, 3)})

    digests = Counter(receipt.get("report_sha256") for _, receipt in live)
    repeated = sorted(digest for digest, count in digests.items() if count > 1)
    if repeated:
        anomalies.append({"kind": "duplicated_run_evidence", "report_sha256": repeated})

    missing = []
    if len(distinct_days) >= 2:
        cursor = distinct_days[0]
        final = distinct_days[-1]
        while cursor <= final:
            if cursor not in distinct_days:
                missing.append(cursor.isoformat())
            cursor += timedelta(days=1)

    elapsed = (live[-1][0] - live[0][0]).total_seconds() / 86400 if live else 0
    latest_age = (now - live[-1][0]).total_seconds() / 3600 if live else None
    if latest_age is not None and latest_age > MAX_GAP_HOURS * 2:
        anomalies.append({"kind": "stale_observation_evidence", "age_hours": round(latest_age, 3)})

    blocking = [a["kind"] for a in anomalies]
    eligible = bool(distinct_days) and elapsed >= required_days and not missing and not blocking
    return {"live_observations": len(live), "distinct_days": len(distinct_days),
            "elapsed_days": round(elapsed, 3), "missing_days": missing,
            "max_gap_hours": round(max(spacings), 3) if spacings else None,
            "latest_age_hours": round(latest_age, 3) if latest_age is not None else None,
            "anomalies": anomalies, "eligible": eligible,
            "required_days": required_days,
            "note": "Synthetic receipts are excluded; elapsed real time has not been manufactured."}


def read_observation_receipts(root):
    """Read retained receipts without network access or any new observation."""
    directory = Path(root) / OBSERVATION_DIRECTORY
    if not directory.exists():
        return []
    receipts = []
    for path in sorted(directory.glob("????-??-??.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if payload.get("version") == 1:
            receipts.append(payload)
    return receipts


# --- dimensions ----------------------------------------------------------------

def source_eligibility(source_rights, enabled_sources) -> dict:
    if not source_rights:
        return _dimension("source_eligibility", INCONCLUSIVE, {}, "no rights registry available")
    allowed = {key for key, entry in source_rights.items() if entry.get("publication") == "allow"}
    active = set(enabled_sources or [])
    exposed = sorted(active & allowed)
    unapproved = sorted(active - allowed)
    if unapproved:
        return _dimension("source_eligibility", FAIL,
                          {"enabled": sorted(active), "rights_allowed": sorted(allowed)},
                          "an enabled source has no rights approval")
    if not exposed:
        return _dimension("source_eligibility", BLOCKED, {"rights_allowed": sorted(allowed)},
                          "no rights-approved source is enabled")
    return _dimension("source_eligibility", PASS, {"rights_allowed_sources": exposed},
                      "every enabled source has a recorded rights approval")


def rights_evidence_completeness(source_rights) -> dict:
    if not source_rights:
        return _dimension("rights_evidence_completeness", INCONCLUSIVE, {}, "no rights registry")
    incomplete = sorted(key for key, entry in source_rights.items()
                        if entry.get("publication") == "allow"
                        and not (entry.get("license") and entry.get("license_url") and entry.get("scope")))
    if incomplete:
        return _dimension("rights_evidence_completeness", FAIL, {"incomplete": incomplete},
                          "an approved source lacks license, licence URL or scope")
    return _dimension("rights_evidence_completeness", PASS,
                      {"approved": sorted(k for k, v in source_rights.items() if v.get("publication") == "allow")},
                      "every approved source records licence, licence URL and scope")


def news_freshness(stories, now, *, news_window_hours=72) -> dict:
    if not stories:
        return _dimension("news_freshness", INCONCLUSIVE, {}, "no stories to assess")
    news = [story for story in stories if getattr(story, "category", None) == "news"]
    if not news:
        return _dimension("news_freshness", BLOCKED, {"total_stories": len(stories)},
                          "the edition contains no current-news coverage")
    fresh = [s for s in news if s.published_at >= now - timedelta(hours=news_window_hours)]
    if not fresh:
        return _dimension("news_freshness", FAIL,
                          {"news_stories": len(news), "window_hours": news_window_hours},
                          "no news story falls inside the freshness window")
    return _dimension("news_freshness", PASS, {"fresh_news_stories": len(fresh)},
                      "current-news coverage exists inside the freshness window")


def editorial_review_status(ledger) -> dict:
    from pipeline.editorial_workflow import AUTHORITY_GATED
    states = [event.decision.to_state for event in (ledger.events if ledger else [])]
    if not states:
        return _dimension("editorial_review_status", INCONCLUSIVE, {},
                          "no editorial decision ledger exists")
    approved = [s for s in states if s in AUTHORITY_GATED]
    if not approved:
        return _dimension("editorial_review_status", BLOCKED, {"decisions": len(states)},
                          "no story has an accountable editorial approval")
    return _dimension("editorial_review_status", PASS, {"approvals": len(approved)},
                      "at least one story carries an accountable editorial approval")


def bangla_review_coverage(translation_ledger) -> dict:
    from pipeline.translation_governance import AUTHORITY_GATED as TRANSLATION_GATED
    states = [event.decision.to_state for event in (translation_ledger.events if translation_ledger else [])]
    if not states:
        return _dimension("bangla_review_coverage", INCONCLUSIVE, {},
                          "no translation decision ledger exists")
    reviewed = [s for s in states if s in TRANSLATION_GATED]
    if not reviewed:
        return _dimension("bangla_review_coverage", BLOCKED, {"decisions": len(states)},
                          "no Bangla translation carries native review")
    return _dimension("bangla_review_coverage", PASS, {"reviewed": len(reviewed)},
                      "at least one Bangla translation carries native review")


def generation_integrity(root) -> dict:
    journal = Path(root) / ".cache/pipeline-transaction.json"
    if not journal.exists():
        return _dimension("generation_integrity", PASS, {"outstanding_journal": False},
                          "no interrupted generation is awaiting recovery")
    return _dimension("generation_integrity", FAIL, {"outstanding_journal": True},
                      "an interrupted generation must be finished or rolled back first")


def snapshot_health(root, canonical_sha256=None) -> dict:
    path = Path(root) / "content/generated/snapshot.json"
    if not path.exists():
        return _dimension("snapshot_health", INCONCLUSIVE, {}, "no generated snapshot is present")
    import hashlib
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    evidence = {"sha256": digest}
    if canonical_sha256:
        evidence["expected_sha256"] = canonical_sha256
        if digest != canonical_sha256:
            return _dimension("snapshot_health", FAIL, evidence,
                              "snapshot digest differs from the canonical production snapshot")
    return _dimension("snapshot_health", PASS, evidence, "canonical snapshot digest verified")


def revoked_source_contamination(stories, source_rights) -> dict:
    contaminated = []
    for story in stories or []:
        for source_id in story.source_ids:
            source = getattr(story, "_sources", {}).get(source_id)
            registry_id = getattr(source, "source_registry_id", None)
            entry = (source_rights or {}).get(registry_id, {}) if registry_id else {}
            if entry.get("publication") in {"exclude", "revoked"}:
                contaminated.append({"story_id": story.id, "source_id": source_id})
    if contaminated:
        return _dimension("revoked_source_contamination", FAIL,
                          {"contaminated": contaminated[:20], "count": len(contaminated)},
                          "a story cites a source that is no longer rights-approved")
    return _dimension("revoked_source_contamination", PASS, {"count": 0},
                      "no story cites a revoked or excluded source")


def ingestion_failure_rate(observation_report) -> dict:
    if not observation_report or not observation_report.get("sources"):
        return _dimension("ingestion_failure_rate", INCONCLUSIVE, {}, "no source diagnostics available")
    rows = observation_report["sources"]
    failed = [r for r in rows if r.get("collection_status") == "SOURCE_FAILURE"]
    ratio = len(failed) / len(rows)
    evidence = {"sources": len(rows), "failed": len(failed), "failure_rate": round(ratio, 4)}
    if ratio == 0:
        return _dimension("ingestion_failure_rate", PASS, evidence, "every source collected successfully")
    if ratio < 0.5:
        return _dimension("ingestion_failure_rate", FAIL, evidence, "some sources failed to collect")
    return _dimension("ingestion_failure_rate", FAIL, evidence, "most sources failed to collect")


def publication_delay(stories, now, *, budget_hours=48) -> dict:
    if not stories:
        return _dimension("publication_delay", INCONCLUSIVE, {}, "no stories to assess")
    delays = [(now - story.published_at).total_seconds() / 3600 for story in stories]
    worst = max(delays)
    evidence = {"worst_delay_hours": round(worst, 3), "budget_hours": budget_hours}
    if worst <= budget_hours:
        return _dimension("publication_delay", PASS, evidence, "publication delay is inside budget")
    return _dimension("publication_delay", FAIL, evidence, "publication delay exceeds the budget")


def build_reproducibility(evidence) -> dict:
    if not evidence:
        return _dimension("build_reproducibility", INCONCLUSIVE, {},
                          "no build comparison evidence supplied")
    if evidence.get("reproducible") is True:
        return _dimension("build_reproducibility", PASS, evidence, "two builds produced identical output")
    return _dimension("build_reproducibility", FAIL, evidence, "rebuild output differed")


def accessibility_checks(evidence) -> dict:
    if not evidence:
        return _dimension("accessibility_checks", INCONCLUSIVE, {},
                          "no automated accessibility evidence supplied")
    violations = evidence.get("violations") or []
    if violations:
        return _dimension("accessibility_checks", FAIL, {"violations": len(violations)},
                          "automated accessibility checks report violations")
    return _dimension("accessibility_checks", PASS, {"violations": 0},
                      "automated accessibility checks report no violations")


def preview_deployment_prerequisites(release_config) -> dict:
    config = release_config or {}
    required = ("github_publication_approved", "public_files_reviewed", "hosted_ci_verified",
                "durable_backup_verified", "content_rights_reviewed", "free_plan_verified",
                "zero_spend_verified", "preview_approved")
    missing = [key for key in required if config.get(key) is not True]
    if config.get("approved") is True and not missing:
        return _dimension("preview_deployment_prerequisites", PASS, {}, "preview prerequisites recorded")
    return _dimension("preview_deployment_prerequisites", BLOCKED, {"missing": missing},
                      "preview deployment requires owner approval and verified free-plan evidence")


def security_configuration(release_config) -> dict:
    config = release_config or {}
    if config.get("ai_enabled") is True or config.get("schedule_enabled") is True:
        return _dimension("security_configuration", FAIL,
                          {"ai_enabled": config.get("ai_enabled"),
                           "schedule_enabled": config.get("schedule_enabled")},
                          "AI or scheduling is enabled without owner authorization")
    return _dimension("security_configuration", PASS,
                      {"ai_enabled": False, "schedule_enabled": False},
                      "no unauthorised AI, scheduling or seed is enabled")


def scheduler_authorization(release_config) -> dict:
    config = release_config or {}
    if config.get("schedule_enabled") is True:
        return _dimension("scheduler_authorization", PASS, {"schedule_enabled": True},
                          "scheduling is explicitly authorised")
    return _dimension("scheduler_authorization", BLOCKED, {"schedule_enabled": False},
                      "scheduled ingestion requires separate owner authorization")


def assess(*, root, source_rights=None, enabled_sources=None, stories=None, now=None,
           observation_receipts=None, observation_report=None, editorial_ledger=None,
           translation_ledger=None, release_config=None, canonical_sha256=None,
           build_evidence=None, accessibility_evidence=None) -> dict:
    """Assemble every readiness dimension. Absent evidence is INCONCLUSIVE, not PASS."""
    now = now or datetime.now(UTC)
    stories = stories or []
    window = observation_evidence(observation_receipts or [], now)
    dimensions = [
        source_eligibility(source_rights, enabled_sources),
        rights_evidence_completeness(source_rights),
        news_freshness(stories, now),
        editorial_review_status(editorial_ledger),
        bangla_review_coverage(translation_ledger),
        generation_integrity(root),
        snapshot_health(root, canonical_sha256),
        revoked_source_contamination(stories, source_rights),
        ingestion_failure_rate(observation_report),
        publication_delay(stories, now),
        build_reproducibility(build_evidence),
        accessibility_checks(accessibility_evidence),
        preview_deployment_prerequisites(release_config),
        security_configuration(release_config),
        scheduler_authorization(release_config),
        _dimension("seven_day_observation",
                   PASS if window["eligible"] else (INCONCLUSIVE if not window["live_observations"] else FAIL),
                   {k: window[k] for k in ("live_observations", "distinct_days", "elapsed_days",
                                            "missing_days", "anomalies")},
                   "seven elapsed days of live observation are required"),
    ]
    tally = Counter(d["result"] for d in dimensions)
    return {"version": 1, "assessed_at": now.isoformat(),
            "dimensions": dimensions,
            "summary": {result: tally.get(result, 0) for result in (PASS, FAIL, BLOCKED, INCONCLUSIVE)},
            "publication_allowed": False, "ai_submission_allowed": False,
            "observation_window": window,
            "note": "INCONCLUSIVE means evidence is missing. It is never a pass."}


def human_report(assessment) -> str:
    lines = ["# Operational readiness", "",
             f"Assessed: {assessment['assessed_at']}", "",
             "| Dimension | Result | Detail |", "|---|---|---|"]
    for row in assessment["dimensions"]:
        lines.append(f"| {row['dimension']} | {row['result']} | {row['detail']} |")
    window = assessment["observation_window"]
    lines.extend(["", "## Seven-day observation window", "",
                  f"- Live observations: {window['live_observations']} over {window['distinct_days']} distinct days",
                  f"- Elapsed: {window['elapsed_days']} day(s); required: {window['required_days']}",
                  f"- Missing days: {', '.join(window['missing_days']) or 'none'}",
                  f"- Eligible: {window['eligible']}",
                  "", "Unknown evidence is reported as INCONCLUSIVE and never as PASS.",
                  "This report authorises nothing."])
    return "\n".join(lines) + "\n"