import argparse
import asyncio
import hashlib
import json
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import yaml
from dotenv import load_dotenv

from pipeline.adapters import ADAPTERS
from pipeline.ai import AIRouter, configured_providers, evidence_hash
from pipeline.dedupe import cluster, deduplicate
from pipeline.digests import build_digests
from pipeline.filesystem import confined_file, regular_path
from pipeline.fixtures import fixture_data, fixture_trackers
from pipeline.generation import assert_stable, promote, writer
from pipeline.models import (
    AnnouncedEvent,
    Change,
    ModelRelease,
    Offer,
    Snapshot,
    SourceItem,
    SourceRegistry,
    Story,
)
from pipeline.normalize import RightsRejection, discovery_relevant, normalize
from pipeline.ranking import novelty, rank
from pipeline.rights import merge_review_queue, review_record
from pipeline.security import SafeFetcher, public_transport
from pipeline.storage import atomic_json, compact, read_json, validate_snapshot, write_schemas
from pipeline.translation import translate_stories
from pipeline.verification import evidence_state, offer_status

ROOT = Path(__file__).resolve().parent.parent


def config(name):
    return yaml.safe_load((ROOT / "config" / f"{name}.yaml").read_text(encoding="utf-8"))


def providers_enabled(mode):
    return mode == "live" and os.getenv("PIPELINE_AI_ENABLED") == "true"


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:100].rstrip("-") or "story"


def is_model_announcement(headline):
    return bool(re.search(r"\b(releases?|introduc\w*|launch\w*|open[- ]sourc\w*)\b", headline, re.I)
                and re.search(r"\b(model|llm|weights)\b", headline, re.I))


def snapshot_output(output):
    """Accept the canonical target or a local JSON review file, never config/code."""
    root = ROOT.resolve()
    try:
        target = regular_path(output)
    except ValueError as error:
        raise ValueError(f"Invalid snapshot output: {error}") from error
    if not target.is_relative_to(root):
        raise ValueError("Snapshot output must remain inside the repository")
    relative = target.relative_to(root)
    review = (relative == Path(".cache/source-review.json") or
              relative.is_relative_to(".cache/source-review") and relative.suffix == ".json")
    if relative != Path("content/generated/snapshot.json") and not review:
        raise ValueError("Snapshot output must be canonical or an isolated source-review JSON file")
    for candidate in (target, *target.parents):
        if candidate == root:
            break
        if candidate.is_symlink() or candidate.is_junction():
            raise ValueError("Linked snapshot output paths are forbidden")
    return target


async def collect(registry, fetcher, now, previous_items, report, since, *, review_queue=None):
    local_only = {source.id for source in registry
                  if source.rights_review_required or source.editorial_kind == "security-advisory"}
    previous_items = [item for item in previous_items
                      if item.publication_eligible and item.source_registry_id not in local_only]
    previous_ids = {item.id for item in previous_items}
    reviews = []
    async def fetch_one(source):
        result = {"id": source.id, "status": "failed", "collection_state": "COLLECTION_FAILED", "items": 0}
        try:
            async with asyncio.timeout(120):
                raw = await ADAPTERS[source.adapter].fetch(source, fetcher)
            if raw is None:
                existing = [item.model_copy(update={"fetched_at": now}) for item in previous_items if item.source_registry_id == source.id and item.id in fetcher.revalidated_ids]
                result.update(status="unchanged", collection_state="COLLECTION_SUCCESS", items=len(existing))
                return existing, result
            items = []
            for item in raw:
                try:
                    normalized = normalize(item, source, now)
                    if normalized.rights_review is not None:
                        reviews.append(review_record(normalized))
                        result["rights_quarantined"] = result.get("rights_quarantined", 0) + 1
                        continue
                    if not normalized.publication_eligible:
                        result["advisory_items"] = result.get("advisory_items", 0) + 1
                        continue
                    if not discovery_relevant(normalized.title, normalized.excerpt, source.discovery_keywords):
                        result["filtered_items"] = result.get("filtered_items", 0) + 1
                        continue
                    if normalized.published_at >= since or normalized.id in previous_ids:
                        items.append(normalized)
                        keys = {source.id + "|" + item["_fetch_url"]} if item.get("_fetch_url") else fetcher.modified_keys.get(source.id, set())
                        for key in keys:
                            if key in fetcher.state:
                                fetcher.state[key]["item_ids"].append(normalized.id)
                except RightsRejection:
                    result["rights_excluded"] = result.get("rights_excluded", 0) + 1
                except Exception:
                    result["invalid_items"] = result.get("invalid_items", 0) + 1
            if raw and result.get("invalid_items", 0) == len(raw):
                raise ValueError("All returned source items failed validation")
            seen = {item.id for item in items}
            items.extend(item.model_copy(update={"fetched_at": now}) for item in previous_items
                         if item.source_registry_id == source.id and item.id in fetcher.revalidated_ids and item.id not in seen)
            collection = ("COLLECTION_EMPTY" if not raw else "COLLECTION_DEGRADED"
                          if result.get("invalid_items") else "COLLECTION_SUCCESS")
            result.update(status="success", collection_state=collection, items=len(items), raw_items=len(raw))
            return items, result
        except Exception as error:
            for key in list(fetcher.state):
                if key.startswith(source.id + "|"):
                    fetcher.state.pop(key, None)
            result["error_type"] = type(error).__name__
            return [], result

    results = await asyncio.gather(*(fetch_one(source) for source in registry if source.enabled))
    report["sources"] = [status for _, status in results]
    states = [status["collection_state"] for _, status in results]
    report["collection_state"] = ("COLLECTION_FAILED" if not states or all(
        state == "COLLECTION_FAILED" for state in states) else "COLLECTION_DEGRADED" if any(
        state in {"COLLECTION_FAILED", "COLLECTION_DEGRADED"} for state in states) else
        "COLLECTION_EMPTY" if all(state == "COLLECTION_EMPTY" for state in states) else "COLLECTION_SUCCESS")
    if reviews:
        merge_review_queue(review_queue or ROOT / ".cache/rights-review.json", reviews)
    if not results or not any(status["status"] in ("success", "unchanged") for _, status in results):
        raise ValueError("All configured sources failed; previous snapshot preserved")
    return [item for items, _ in results for item in items]


async def run(mode, output, now=None):
    # Validate before schema generation, environment loading, fetching or writes.
    output = snapshot_output(output)
    with writer(ROOT):
        assert_stable(ROOT)
        try:
            return await generate(mode, output, now)
        except Exception as error:
            try:
                atomic_json(confined_file(ROOT, ".cache/pipeline-attempt.json"), {
                    "mode": mode, "status": "failed", "error_type": type(error).__name__,
                    "completed_at": datetime.now(UTC).isoformat()})
            except OSError:
                pass  # Full disk must not mask the original failure/recovery journal.
            raise


async def generate(mode, output, now=None):
    now = now or datetime.now(UTC)
    load_dotenv(ROOT / ".env", override=False)
    ranking, ai_config, archive_config = config("ranking"), config("ai"), config("archive")
    source_rights = read_json(ROOT / "config/source-rights.json", {}).get("sources", {})
    if mode == "fixture":
        archive_config["archive_directory"] = ".cache/fixture-archives"
    timezone = os.getenv("PIPELINE_TIMEZONE", "Asia/Dhaka")
    categories = config("categories")["categories"]
    pending_writes = []
    write_schemas(ROOT, pending_writes)
    last_snapshot_path = ROOT / ".cache" / f"last-snapshot-{mode}.json"
    previous_data = read_json(output)
    if previous_data and previous_data.get("mode") in ("live", "fixture") and previous_data["mode"] != mode:
        prior_mode = Snapshot.model_validate(previous_data)
        pending_writes.append((ROOT / ".cache" / f"last-snapshot-{prior_mode.mode}.json", prior_mode))
    if not previous_data or previous_data.get("mode") != mode:
        previous_data = read_json(last_snapshot_path)
    previous = Snapshot.model_validate(previous_data) if previous_data else None
    if previous and previous.mode != mode:
        previous = None
    state_path = ROOT / ".cache" / f"state-{mode}.json"
    state = read_json(state_path, {"fetch": {}, "providers": {}, "items": []})
    usage_path = ROOT / ".cache" / f"provider-usage-{mode}.json"
    state["providers"] = read_json(usage_path, state["providers"])
    old_items = [SourceItem.model_validate(item) for item in state["items"]] if mode == "live" else []
    registry = SourceRegistry.model_validate(config("sources")).sources
    active_registry = {source.id for source in registry if source.enabled and (
        mode == "fixture" or source_rights.get(source.id, {}).get("publication") == "allow")}
    local_only_registry = {source.id for source in registry
                           if source.rights_review_required or source.editorial_kind == "security-advisory"}
    if mode == "live":
        registry = [source.model_copy(update={"enabled": source.id in active_registry}) for source in registry]
        # Disabling or denying reuse also excludes retained evidence and summaries that
        # cite it. Never reuse mixed-source wording through a surviving citation.
        old_items = [item for item in old_items if item.source_registry_id in active_registry - local_only_registry
                     and item.publication_eligible and not item.is_demo]
        state["fetch"] = {key: value for key, value in state["fetch"].items() if key.split("|", 1)[0] in active_registry}
        if previous:
            eligible = {key: item for key, item in previous.sources.items()
                        if item.source_registry_id in active_registry - local_only_registry
                        and item.publication_eligible and not item.is_demo}
            previous = previous.model_copy(update={"sources": eligible, "stories": [story for story in previous.stories
                if set(story.source_ids) | {key for change in story.change_log for key in change.source_ids}
                | {key for change in story.change_log for fact in change.previous_facts for key in fact.source_ids} <= eligible.keys()]})
    discovery_rules = {source.id: source.discovery_keywords for source in registry}
    report = {"mode": mode, "started_at": now.isoformat(), "sources": [], "validation_failures": 0,
              "deployment_status": "not-attempted", "status": "running", "stories": 0,
              "cached_summaries": 0, "generation_modes": {}, "provider_health": {}}
    atomic_json(confined_file(ROOT, ".cache/pipeline-attempt.json"), report)
    timeout = httpx.Timeout(25, connect=10)
    async with httpx.AsyncClient(transport=public_transport(), timeout=timeout, trust_env=False) as client:
        fetcher = SafeFetcher(client, state["fetch"], os.getenv("PIPELINE_USER_AGENT") or "TechIntelligenceBot/1.0 (RSS/API aggregation)")
        if mode == "fixture":
            fresh = fixture_data(now)
        else:
            overlap = timedelta(hours=ranking["limits"]["fetch_lookback_hours"])
            since = min(now - overlap, previous.last_successful_fetch_at - overlap) if previous else now - timedelta(days=7)
            fresh = await collect(registry, fetcher, now, old_items, report, since)
            fresh = [item for item in fresh if item.source_registry_id in active_registry - local_only_registry
                     and item.publication_eligible and not item.is_demo]
        report["raw_items"] = len(fresh)
        merged = {item.id: item for item in old_items}
        for item in fresh[:ranking["limits"]["max_raw_items_per_run"]]:
            old = merged.get(item.id)
            if old and item.missing_publication_time:
                # Keep a stable storage/sort placeholder, never upgrade unknown
                # current evidence using an older parser's publication flag.
                item = item.model_copy(update={"published_at": old.published_at})
            merged[item.id] = item
        if previous:
            for item in previous.sources.values():
                merged.setdefault(item.id, item)
        relevant = [item for item in merged.values() if discovery_relevant(item.title, item.excerpt, discovery_rules.get(item.source_registry_id, []))]
        report["filtered_cached_items"] = len(merged) - len(relevant)
        items, duplicate_count = deduplicate(relevant)
        report["duplicates"] = duplicate_count
        previous_sources = previous.sources if previous else {}
        def importance(group):
            return rank(group, ranking, categories, now, novelty(group, previous_sources))
        grouped = cluster(items, ranking["limits"]["recent_cluster_window_hours"])
        grouped.sort(key=lambda group: (-importance(group), group[0].id))
        router = AIRouter(configured_providers(ai_config, client) if providers_enabled(mode) else [], ai_config, state["providers"], ROOT / "prompts/story_summary.md",
                          persist_usage=lambda: atomic_json(usage_path, state["providers"]))
        previous_by_source = {source_id: story for story in previous.stories for source_id in story.source_ids} if previous else {}
        stories, used_ids = [], set()
        llm_budget = min(int(os.getenv("PIPELINE_MAX_LLM_STORIES_PER_RUN", "50")), ranking["limits"]["max_llm_clusters_per_run"])
        llm_candidates = 0
        cached = 0
        for group in grouped:
            prior = next((previous_by_source[item.id] for item in group if item.id in previous_by_source and previous_by_source[item.id].id not in used_ids), None)
            digest = evidence_hash(group, ai_config, router.prompt)
            if prior and prior.ai_metadata.evidence_hash == digest:
                stories.append(prior.model_copy(update={
                    "importance_score_internal": importance(group),
                    "novelty_score_internal": novelty(group, previous_sources),
                    "last_verified_at": max(prior.last_verified_at, min(item.fetched_at for item in group)),
                }))
                used_ids.add(prior.id)
                cached += 1
                continue
            allow_ai = llm_candidates < llm_budget and (mode == "fixture" or all(
                source_rights.get(item.source_registry_id, {}).get("ai_submission_allowed") is True for item in group))
            # Reserve a candidate before processing: invalid output must not
            # create additional AI attempts beyond the per-run allowance.
            llm_candidates += int(allow_ai)
            try:
                summary, metadata = await router.summarize(group, allow_ai=allow_ai)
            except (ValueError, TypeError):
                # Quarantine unusable evidence without sacrificing healthy stories or prior validated claims.
                report["validation_failures"] += 1
                for source in group:
                    for key in list(fetcher.state):
                        if key.startswith(source.source_registry_id + "|"):
                            fetcher.state.pop(key, None)
                if prior:
                    stories.append(prior)
                    used_ids.add(prior.id)
                    preserved = {key: previous.sources[key] for key in prior.source_ids}
                    items = [preserved.get(item.id, item) for item in items]
                    items.extend(value for key, value in preserved.items() if key not in {item.id for item in items})
                continue
            representative = min(group, key=lambda item: (item.source_class != "primary", item.published_at, item.id))
            story_id = prior.id if prior else "story_" + hashlib.sha256(representative.id.encode()).hexdigest()[:16]
            change = Change(at=now, text="Source evidence updated; earlier claims should be read with the correction below." if prior else "First published from the cited source evidence.", source_ids=[item.id for item in group])
            history = [*prior.change_log, change] if prior else [change]
            if prior:
                removed = [fact.model_copy(update={"status": "retracted/updated"}) for fact in prior.key_facts if fact.text not in {fact.text for fact in summary.key_facts}]
                if removed:
                    change.text = "Updated source evidence. Earlier wording: " + "; ".join(fact.text for fact in removed)[:600]
                    change.previous_facts = removed
            story = Story(**summary.model_dump(), id=story_id, slug=prior.slug if prior else slugify(summary.headline) + "-" + story_id[-6:],
                          canonical_topic=slugify(representative.title), source_ids=[item.id for item in group],
                          primary_source_id=next((item.id for item in group if item.source_class == "primary"), None),
                          evidence_state=evidence_state(group), published_at=prior.published_at if prior else min(item.published_at for item in group),
                          first_seen_at=prior.first_seen_at if prior else now, updated_at=now, last_verified_at=min(item.fetched_at for item in group),
                          importance_score_internal=importance(group), novelty_score_internal=novelty(group, previous_sources), change_log=history,
                          ai_metadata=metadata, language=representative.language, is_demo=mode == "fixture")
            stories.append(story)
            used_ids.add(story.id)
    if not stories:
        raise ValueError("No valid stories; refusing to replace snapshot with an empty feed")
    sources = {item.id: item for item in items}
    if previous:
        for story in stories:
            for change in story.change_log:
                for key in change.source_ids:
                    if key in previous.sources:
                        sources.setdefault(key, previous.sources[key])
    for story in stories:
        for fact in [*story.key_facts, *story.claim_map]:
            fact.id = "claim_" + hashlib.sha256((story.id + fact.text + "|".join(fact.source_ids)).encode()).hexdigest()[:16]
            fact.story_id = story.id
    # Keep curated tracker records separate from free-text inference: unknown constraints stay unknown.
    if mode == "fixture":
        offers, releases = fixture_trackers(stories, now)
    else:
        trackers = config("trackers")
        offers = [Offer.model_validate(value) for value in trackers["offers"]]
        releases = [ModelRelease.model_validate(value) for value in trackers["model_releases"]]
        for setting in trackers.get("auto_offers", []):
            item = next((item for item in sources.values() if item.source_registry_id == setting["source_registry_id"]), None)
            if item is None:
                continue
            allowance = re.search(setting["allowance_pattern"], item.excerpt)
            linked = next((story for story in stories if item.id in story.source_ids), None)
            offers.append(Offer(id="offer-" + setting["source_registry_id"], story_id=linked.id if linked else None,
                                provider=setting["provider"], title=setting["title"], offer_type=setting["offer_type"],
                                value_text=allowance.group(0) if allowance else "Allowance needs review",
                                eligibility=setting["eligibility"], regions=[], card_required=None,
                                claim_steps=setting["claim_steps"], last_verified_at=item.fetched_at,
                                status="active" if allowance else "unverified", official_source_url=item.original_url,
                                source_ids=[item.id], integration_notes=setting["integration_notes"]))
        for offer in offers:
            offer.status = offer_status(offer, now)
        known = {release.story_id for release in releases}
        for story in stories:
            if story.category == "ai" and story.primary_source_id and story.id not in known and is_model_announcement(story.headline):
                releases.append(ModelRelease(id=story.id, story_id=story.id, provider=sources[story.primary_source_id].publisher,
                                              model=story.headline, release_date=story.published_at, modality=[],
                                              key_change=story.summary_bullets[0], source_ids=story.source_ids))
    pending_archives = []
    translation_path = ROOT / ".cache" / f"translations-{mode}.json"
    translation_report, translation_cache = await translate_stories(
        stories, router, ai_config, read_json(translation_path, {}), ROOT / "prompts/story_translation.md",
        now, fixture=mode == "fixture", eligible_story_ids={
            story.id for story in stories if all(
                source_rights.get(sources[key].source_registry_id, {}).get("ai_submission_allowed") is True
                for key in story.source_ids)})
    report["translation"] = translation_report
    stories, archive_index = compact(stories, sources, ROOT, now, archive_config, previous.archive_index if previous else [], pending_archives)
    events = [AnnouncedEvent.model_validate(event) for event in config("trackers").get("announced_events", [])] if mode == "live" else []
    needed = ({key for story in stories for key in story.source_ids} | {key for offer in offers for key in offer.source_ids}
              | {key for event in events for key in event.fact.source_ids}
              | {key for story in stories for change in story.change_log for key in change.source_ids})
    sources = {key: value for key, value in sources.items() if key in needed}
    for event in events:
        if not set(event.fact.source_ids) <= sources.keys():
            raise ValueError("Announced event contains missing evidence")
        evidence = " ".join(sources[key].title + " " + sources[key].excerpt for key in event.fact.source_ids)
        if event.evidence_date_text not in evidence or event.fact.text not in evidence:
            raise ValueError("Watch-next event text and date must be quoted from provided evidence")
    expiring_story_ids = {offer.story_id for offer in offers if offer.status == "expiring"}
    for story in stories:
        if story.id in expiring_story_ids:
            story.importance_score_internal = min(1, story.importance_score_internal + ranking["boosts"]["actively_expiring_offer"])
    stories.sort(key=lambda story: (-story.importance_score_internal, story.id))
    snapshot = Snapshot(mode=mode, generated_at=now, last_successful_fetch_at=now, categories=categories, stories=stories,
                        sources=sources, digests=build_digests(stories, now, timezone, events), offers=offers,
                        model_releases=[release for release in releases if release.story_id in {story.id for story in stories}], archive_index=archive_index)
    validate_snapshot(snapshot, ROOT)
    report.update(stories=len(stories), clusters=len(grouped), cached_summaries=cached,
                  new_stories=sum(story.first_seen_at == now for story in stories),
                  updated_stories=sum(story.updated_at == now and story.first_seen_at != now for story in stories),
                  generation_modes={"extractive": sum(story.ai_metadata.generation_mode == "extractive" for story in stories), "ai": sum(story.ai_metadata.generation_mode == "ai" for story in stories)},
                  provider_health=state["providers"], status="success", completed_at=datetime.now(UTC).isoformat())
    report["generation_id"] = uuid4().hex
    state["items"] = [item.model_dump(mode="json") for item in items if item.id in sources]
    markdown = "# Generated editorial snapshot\n\n" + ("Synthetic demonstration data.\n\n" if mode == "fixture" else "Source-derived summaries.\n\n") + "\n\n".join(f"## {story.headline}\n\n" + "\n".join(f"- {bullet}" for bullet in story.summary_bullets) for story in stories)
    pending_writes.extend(pending_archives)
    pending_writes.extend([(output, snapshot), (translation_path, translation_cache),
                          (last_snapshot_path, snapshot), (state_path, state),
                          (ROOT / "content/generated/run-report.json", report),
                          (output.parent / "briefing.md", markdown.encode("utf-8"))])
    promote(ROOT, pending_writes, generation=report["generation_id"])
    atomic_json(confined_file(ROOT, ".cache/pipeline-attempt.json"), report)
    print(json.dumps(report, indent=2))
    return snapshot


def main():
    parser = argparse.ArgumentParser(description="Build validated technology intelligence snapshots")
    parser.add_argument("--mode", choices=("fixture", "live"), default="fixture")
    parser.add_argument("--output", type=Path, default=ROOT / "content/generated/snapshot.json")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.validate:
        with writer(ROOT):
            assert_stable(ROOT)
            snapshot = Snapshot.model_validate(read_json(snapshot_output(args.output)))
            validate_snapshot(snapshot, ROOT)
        print(f"Validated {len(snapshot.stories)} stories and {len(snapshot.digests)} digests")
    else:
        try:
            asyncio.run(run(args.mode, args.output))
        except Exception as error:
            print(f"Pipeline failed ({type(error).__name__}); no publication attempted. Inspect the recovery journal before building.")
            raise SystemExit(1) from None
