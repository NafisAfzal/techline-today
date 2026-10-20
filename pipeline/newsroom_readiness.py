"""One honest launch-readiness report for the operator.

Every item resolves to PASS, FAIL, BLOCKED or INCONCLUSIVE with the specific
evidence that produced it and the specific thing that is missing. Nothing here
invents a progress percentage, an approval or a reviewer identity.

The report reuses the existing gates - ``pipeline.readiness``, the authority
status, the composite publication gate, the candidate ledger and the Phase 10
checkpoint verifier - so it cannot drift away from the systems it describes.
"""

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pipeline.readiness import (
    BLOCKED,
    FAIL,
    INCONCLUSIVE,
    PASS,
    bangla_review_coverage,
    editorial_review_status,
    observation_evidence,
    preview_deployment_prerequisites,
    rights_evidence_completeness,
    security_configuration,
    source_eligibility,
)

MAX_TRANSLATION_AGE_DAYS = 30
ADVISORY_FILE = "config/security-advisories.json"


def _item(name, result, detail, evidence=None, missing=None) -> dict:
    return {"item": name, "result": result, "detail": detail, "evidence": evidence or {},
            "missing": missing or []}


def _snapshot(root):
    from pipeline.filesystem import confined_file
    from pipeline.models import Snapshot

    path = Path(root) / "content/generated/snapshot.json"
    if not path.is_file():
        return None
    try:
        return Snapshot.model_validate_json(confined_file(root, "content/generated/snapshot.json").read_bytes())
    except (ValueError, OSError):
        return None


def _release_config(root) -> dict:
    path = Path(root) / "config/release.json"
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def _rights_policy(root) -> dict:
    path = Path(root) / "config/source-rights.json"
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    sources = value.get("sources") if isinstance(value, dict) else None
    return sources if isinstance(sources, dict) else {}


def _source_registry(root):
    import yaml

    from pipeline.models import SourceRegistry

    path = Path(root) / "config/sources.yaml"
    if not path.is_file():
        return None
    try:
        return SourceRegistry.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    except (ValueError, OSError, TypeError):
        return None


def _news_stories(snapshot) -> list:
    from pipeline.editorial_workflow import classify_kind

    news = []
    for story in snapshot.stories:
        primary = snapshot.sources.get(story.primary_source_id)
        if primary is None:
            continue
        kind = classify_kind(source_type=primary.source_type, source_class=primary.source_class,
                             editorial_kind=primary.editorial_kind)
        if kind == "NEWS":
            news.append(story)
    return news


def _translation_rows(snapshot) -> list[dict]:
    rows = []
    for story in snapshot.stories:
        translation = story.translations.get("bn")
        if translation is None:
            continue
        rows.append({"story_id": story.id, "generated_at": translation.generated_at,
                     "review_status": translation.review_status})
    return rows


def security_advisory_status(root, now=None) -> dict:
    """Report the recorded advisory mitigation state from the operator record."""
    at = now or datetime.now(UTC)
    path = Path(root) / ADVISORY_FILE
    if not path.is_file():
        return _item("security_advisory", INCONCLUSIVE,
                     "No structured advisory record is present; mitigation state cannot be assessed.",
                     missing=["config/security-advisories.json"])
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return _item("security_advisory", INCONCLUSIVE,
                     "The advisory record is unreadable.", missing=["readable advisory record"])
    advisories = record.get("advisories") if isinstance(record, dict) else None
    if not isinstance(advisories, list) or not advisories:
        return _item("security_advisory", INCONCLUSIVE, "The advisory record lists no advisories.",
                     missing=["advisory entries"])
    rows = []
    overdue = []
    for advisory in advisories:
        if not isinstance(advisory, dict):
            continue
        artifact = Path(root) / str(advisory.get("mitigation_artifact", ""))
        present = artifact.is_file()
        locked = str(advisory.get("locked_version", ""))
        observed = _locked_package_version(Path(root) / "pnpm-lock.yaml",
                                           str(advisory.get("package", "")))
        due = advisory.get("reassessment_due")
        deadline_passed = False
        dates_valid = False
        if due:
            try:
                deadline_passed = datetime.strptime(due, "%Y-%m-%d").replace(tzinfo=UTC) < at
                reviewed = datetime.strptime(advisory.get("last_reassessed", ""), "%Y-%m-%d").replace(tzinfo=UTC)
                dates_valid = reviewed <= at and advisory["last_reassessed"] <= due
            except (TypeError, ValueError):
                deadline_passed = False
        if deadline_passed:
            overdue.append(advisory.get("id"))
        rows.append({"id": advisory.get("id"), "package": advisory.get("package"),
                     "locked_version": locked, "observed_locked_version": observed,
                     "mitigation": advisory.get("mitigation"),
                     "mitigation_present": present,
                     "patched_versions": advisory.get("patched_versions"),
                     "dates_valid": dates_valid,
                     "reassessment_due": due, "last_reassessed": advisory.get("last_reassessed"),
                     "exposure": advisory.get("exposure")})
    missing = []
    if not rows or len(rows) != len(advisories):
        return _item("security_advisory", INCONCLUSIVE, "Advisory entries are malformed.",
                     missing=["Complete dated advisory records"])
    for row in rows:
        if not row["mitigation_present"]:
            missing.append(f"missing mitigation artifact for {row['id']}")
        if row["observed_locked_version"] != row["locked_version"]:
            missing.append(f"lockfile version for {row['package']} differs from the recorded version")
        if not row["dates_valid"]:
            missing.append(f"missing, invalid or future advisory review dates for {row['id']}")
    if missing:
        return _item("security_advisory", FAIL,
                     "A recorded advisory mitigation is not in place as documented.", evidence={"advisories": rows},
                     missing=missing)
    if overdue:
        return _item("security_advisory", BLOCKED,
                     "A recorded advisory is past its reassessment deadline.",
                     evidence={"advisories": rows, "overdue": overdue},
                     missing=[f"reassess {item}" for item in overdue])
    return _item("security_advisory", PASS,
                 "Every recorded advisory has its documented mitigation in place and is inside its "
                 "reassessment window.",
                 evidence={"advisories": rows},
                 missing=["A clean registry audit is not proof of a behavioural fix"])


def _locked_package_version(lock_path: Path, package: str) -> str | None:
    if not lock_path.is_file() or not package:
        return None
    try:
        text = lock_path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(rf"^\s*{re.escape(package)}@(\d+\.\d+\.\d+)", text, re.MULTILINE)
    return match.group(1) if match else None


def newsroom_readiness(root, now=None, *, canonical_sha256=None) -> dict:
    """Assemble the full launch-readiness report."""
    at = now or datetime.now(UTC)
    root = Path(root)
    items: list[dict] = []

    # --- authority provisioning -----------------------------------------------------
    from pipeline.authority.service import checkpoint_status, status

    authority = status(root, at)
    if authority.get("status") == "VERIFIED":
        items.append(_item("authority_provisioning", PASS,
                            "An independently pinned owner trust root verifies the signed history.",
                            evidence={k: authority.get(k) for k in
                                      ("registry_revision", "event_count", "head_sha256")}))
    elif authority.get("status") == "UNPROVISIONED":
        items.append(_item("authority_provisioning", BLOCKED,
                            "No independently pinned owner trust root is configured.",
                            evidence=authority,
                            missing=["Provision an owner trust root outside the checkout and record its "
                                     "fingerprint through an independent channel"]))
    else:
        items.append(_item("authority_provisioning", BLOCKED,
                            "The configured authority evidence did not verify.",
                            evidence=authority,
                            missing=[authority.get("reason", "inspect the authority evidence")]))

    # --- current trusted checkpoint --------------------------------------------------
    checkpoint = checkpoint_status(root, at)
    checkpoint_map = {"PASS": PASS, "FAIL": FAIL, "BLOCKED": BLOCKED, "INCONCLUSIVE": INCONCLUSIVE}
    items.append(_item("trusted_checkpoint", checkpoint_map.get(checkpoint.get("status"), INCONCLUSIVE),
                        checkpoint.get("detail", "No checkpoint custodian is configured."),
                        evidence={k: checkpoint.get(k) for k in
                                  ("code", "trust_level", "independently_trusted", "current", "custodian")},
                        missing=[] if checkpoint.get("status") == "PASS" else
                        ["An independently held, unexpired checkpoint whose digest was obtained "
                         "out of band"]))

    # --- source rights ---------------------------------------------------------------
    rights = _rights_policy(root)
    registry = _source_registry(root)
    enabled = [entry.id for entry in registry.sources if entry.enabled] if registry else []
    eligibility = source_eligibility(rights, enabled)
    completeness = rights_evidence_completeness(rights)
    approved = sorted(key for key, value in rights.items() if value.get("publication") == "allow")
    items.append(_item("source_rights_coverage", eligibility["result"], eligibility["detail"],
                        evidence={**eligibility["evidence"], "approved_source_count": len(approved)},
                        missing=[] if eligibility["result"] == PASS else
                        ["A rights-approved source that is actually enabled"]))
    # These policy fields describe historical decisions, not retained evidence.
    # No authenticated historical-rights archive verifier is currently available.
    rights_result = INCONCLUSIVE if completeness["result"] == PASS else completeness["result"]
    items.append(_item("rights_evidence_completeness", rights_result,
                        "Licence fields are recorded; historical rights archives and their authenticated "
                        "review have not been verified." if rights_result == INCONCLUSIVE else completeness["detail"],
                        evidence=completeness["evidence"],
                        missing=["Retained rights evidence and authenticated review for every approved source"]))

    # --- candidate backlog -------------------------------------------------------------
    from pipeline.source_evidence import evidence_report, load_dossiers
    from pipeline.source_onboarding import candidates as candidate_rows

    candidate_error = False
    try:
        candidate_state = candidate_rows(root)
    except (ValueError, OSError, TypeError):
        candidate_state = []
        candidate_error = True
    dossiers = load_dossiers(root)
    evidence = evidence_report(dossiers, now=at)
    pending = sorted(set(row["candidate_id"] for row in candidate_state
                         if row["state"] not in {"REVOKED"})) if candidate_state else []
    items.append(_item("source_candidate_backlog",
                        FAIL if candidate_error else PASS if not pending else BLOCKED,
                        "Candidate history is invalid or unreadable." if candidate_error else
                        "No candidate is awaiting a rights decision." if not pending else
                        f"{len(pending)} source candidate(s) are awaiting a rights decision.",
                        evidence={"candidates": candidate_state, "evidence_status": {
                            "blocked": evidence["blocked"], "review_required": evidence["review_required"],
                            "evidence_complete": evidence["evidence_complete"]}},
                        missing=["Repair candidate history from verified evidence"] if candidate_error else
                        [] if not pending else
                        ["A named human rights reviewer decision for each pending candidate"]))

    # --- edition content ---------------------------------------------------------------
    snapshot = _snapshot(root)
    if snapshot is None:
        items.append(_item("current_news_coverage", INCONCLUSIVE,
                           "No generated edition is present, so current-news coverage cannot be counted.",
                           missing=["A generated live edition"]))
        items.append(_item("editorial_backlog", INCONCLUSIVE,
                           "No generated edition is present, so the editorial backlog cannot be counted.",
                           missing=["A generated live edition"]))
        items.append(_item("publication_eligibility", INCONCLUSIVE,
                           "No generated edition is present, so publication cannot be evaluated.",
                           missing=["A generated live edition"]))
        items.append(_item("translation_staleness", INCONCLUSIVE,
                           "No generated edition is present, so translation freshness cannot be assessed.",
                           missing=["A generated live edition"]))
    else:
        news = _news_stories(snapshot)
        items.append(_item("current_news_coverage", PASS if news else BLOCKED,
                           f"{len(news)} verified current-news article(s) in the edition." if news else
                           "The edition contains no verified current-news coverage.",
                           evidence={"story_count": len(snapshot.stories), "news_count": len(news),
                                     "edition_mode": snapshot.mode},
                           missing=[] if news else
                           ["At least one rights-cleared current-news article"]))
        backlog = [story.id for story in snapshot.stories]
        items.append(_item("editorial_backlog", PASS if not backlog else BLOCKED,
                           "Every stored story carries an authenticated editorial approval." if not backlog else
                           f"{len(backlog)} stored stories have no authenticated editorial approval.",
                           evidence={"story_ids": backlog},
                           missing=[] if not backlog else
                           ["An authenticated editorial review for each stored story"]))

        # --- publication eligibility -----------------------------------------------
        from pipeline.authority.service import load_authority, source_registry
        from pipeline.publication_gate import evaluate_snapshot

        try:
            bundle = load_authority(root)
        except (ValueError, OSError, TypeError):
            bundle = None
        evaluation = evaluate_snapshot(snapshot, rights, authority=bundle, now=at,
                                       source_registry=source_registry(root))
        denied = evaluation["blocked"]
        denied_ids = {row["story_id"] for row in denied}
        cleared_news = [story for story in news if snapshot.mode == "live"
                        and story.category != "research" and story.id not in denied_ids
                        and at - timedelta(hours=72) <= story.published_at <= at
                        and not snapshot.sources[story.primary_source_id].missing_publication_time]
        coverage = next(row for row in items if row["item"] == "current_news_coverage")
        coverage.update(result=PASS if cleared_news else BLOCKED,
                        detail=f"{len(cleared_news)} fresh, publication-eligible live news article(s).",
                        missing=[] if cleared_news else ["Rights-cleared, reviewed current news within 72 hours"])
        coverage["evidence"]["news_count"] = len(cleared_news)
        items.append(_item("publication_eligibility", PASS if evaluation["publication_allowed"] else FAIL,
                           "Every story in the edition satisfies every publication dimension." if
                           evaluation["publication_allowed"] else
                           f"{len(denied)} of {evaluation['story_count']} stories are refused by at "
                           "least one publication dimension.",
                           evidence={"blocked": denied[:20], "blocked_count": evaluation["blocked_count"],
                                     "story_count": evaluation["story_count"]},
                           missing=[] if evaluation["publication_allowed"] else
                           sorted({reason for row in denied for reason in row["denied_dimensions"]})))

        # --- translation staleness -------------------------------------------------
        rows = _translation_rows(snapshot)
        if not rows:
            items.append(_item("translation_staleness", INCONCLUSIVE,
                               "The edition contains no Bangla translation, so freshness cannot be "
                               "assessed.", missing=["A Bangla translation with a recorded review"]))
        else:
            oldest = min(row["generated_at"] for row in rows)
            newest = max(row["generated_at"] for row in rows)
            age = (at - oldest).days
            stale = age > MAX_TRANSLATION_AGE_DAYS or newest > at
            items.append(_item("translation_staleness", FAIL if stale else PASS,
                               f"Bangla translation age is invalid or exceeds the limit ({age} days)." if stale else
                               f"Oldest Bangla translation is {age} day(s) old, inside the "
                               f"{MAX_TRANSLATION_AGE_DAYS}-day limit.",
                               evidence={"translation_count": len(rows), "newest_generated_at":
                                         newest.isoformat(), "age_days": age,
                                         "max_age_days": MAX_TRANSLATION_AGE_DAYS,
                                         "review_statuses": sorted({row["review_status"]
                                                                    for row in rows})},
                               missing=[] if not stale else
                               ["A refreshed and natively reviewed Bangla translation"]))

    # --- editorial and language authority -------------------------------------------
    from pipeline.editorial_workflow import load_ledger as editorial_ledger
    from pipeline.translation_governance import load_ledger as translation_ledger

    try:
        editorial = editorial_review_status(editorial_ledger(root))
    except (ValueError, OSError, TypeError):
        editorial = _item("english_editorial_approval", FAIL, "The editorial ledger could not be read.")
    items.append(_item("english_editorial_approval", editorial["result"], editorial["detail"],
                        evidence=editorial["evidence"],
                        missing=[] if editorial["result"] == PASS else
                        ["An appointed English editor and a signed editorial approval"]))
    try:
        bangla = bangla_review_coverage(translation_ledger(root))
    except (ValueError, OSError, TypeError):
        bangla = _item("native_bangla_review", FAIL, "The translation ledger could not be read.")
    items.append(_item("native_bangla_review", bangla["result"], bangla["detail"],
                        evidence=bangla["evidence"],
                        missing=[] if bangla["result"] == PASS else
                        ["An appointed native Bangla reviewer and a native review signature"]))

    # --- operational observation -------------------------------------------------------
    from pipeline.readiness import read_observation_receipts

    try:
        receipts = read_observation_receipts(root)
        window = observation_evidence(receipts, at)
    except (ValueError, OSError, TypeError):
        window = {"live_observations": 0, "distinct_days": 0, "elapsed_days": 0, "missing_days": [],
                  "anomalies": [], "elapsed_window_satisfied": False}
    items.append(_item("operational_observation_coverage",
                        INCONCLUSIVE,
                        f"{window['live_observations']} retained live observation(s) over "
                        f"{window['distinct_days']} distinct day(s).",
                        evidence={k: window[k] for k in ("live_observations", "distinct_days",
                                                        "elapsed_days", "missing_days", "anomalies")},
                        missing=["Independently attested observation provenance covering at least "
                                 "seven elapsed days; local hashes and live labels do not authenticate provenance"]))

    # --- release gates -------------------------------------------------------------------
    release = _release_config(root)
    preview = preview_deployment_prerequisites(release)
    items.append(_item("preview_readiness", preview["result"], preview["detail"],
                        evidence=preview["evidence"], missing=preview["evidence"].get("missing", [])))
    security = security_configuration(release)
    items.append(_item("security_configuration", security["result"], security["detail"],
                        evidence=security["evidence"], missing=[]))

    # --- security advisories ---------------------------------------------------------------
    items.append(security_advisory_status(root, at))

    # --- production launch readiness ---------------------------------------------------------
    results = {row["result"] for row in items}
    if FAIL in results:
        launch = FAIL
    elif BLOCKED in results:
        launch = BLOCKED
    elif INCONCLUSIVE in results:
        launch = INCONCLUSIVE
    else:
        launch = PASS
    blockers = [row["item"] for row in items if row["result"] in {FAIL, BLOCKED, INCONCLUSIVE}]
    items.append(_item("production_launch_readiness", launch,
                        "Production launch is blocked until every item above is satisfied." if
                        launch != PASS else "Every readiness item is satisfied.",
                        evidence={"blocking_items": blockers,
                                  "item_count": len(items)},
                        missing=blockers))

    summary = {result: sum(1 for row in items if row["result"] == result)
               for result in (PASS, FAIL, BLOCKED, INCONCLUSIVE)}
    return {"version": 1, "assessed_at": at.isoformat(), "items": items, "summary": summary,
            "publication_allowed": False, "ai_submission_allowed": False,
            "note": "BLOCKED means a required operational prerequisite or authorization is missing. "
                    "INCONCLUSIVE means available evidence is insufficient. Neither is a pass."}


def human_report(report: dict) -> str:
    """A compact operator-facing rendering of the readiness report."""
    lines = ["# Newsroom launch readiness", "", f"Assessed: {report['assessed_at']}", "",
             "| Item | Result | Detail |", "|---|---|---|"]
    for row in report["items"]:
        lines.append(f"| {row['item']} | {row['result']} | {row['detail']} |")
    lines.extend(["", "## Blockers", ""])
    for row in report["items"]:
        for missing in row["missing"]:
            lines.append(f"- **{row['item']}**: {missing}")
    lines.extend(["", "Unknown evidence is reported as INCONCLUSIVE and never as PASS.",
                  "This report authorises nothing."])
    return "\n".join(lines) + "\n"


def main(argv=None):
    """Local operator command. Read-only; it authorises nothing."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    args = parser.parse_args(argv)
    try:
        report = newsroom_readiness(args.root, datetime.now(UTC).replace(microsecond=0))
    except (ValueError, OSError, TypeError):
        print(json.dumps({"status": "REFUSED",
                          "detail": "The readiness report could not be assembled; inspect the local "
                                    "state and configuration.",
                          "publication_allowed": False, "ai_submission_allowed": False}))
        return 1
    if args.format == "markdown":
        print(human_report(report))
    else:
        print(json.dumps(report, ensure_ascii=True, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
