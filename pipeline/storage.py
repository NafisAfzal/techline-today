import io
import json
from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from jsonschema import Draft202012Validator, FormatChecker

from pipeline.filesystem import atomic_bytes, confined_file, regular_path
from pipeline.models import Digest, Fact, ModelRelease, Offer, Snapshot, SourceRegistry, Story
from pipeline.verification import validate_story


def atomic_json(path: Path, value):
    payload = value.model_dump(mode="json") if hasattr(value, "model_dump") else value
    stream = io.StringIO()
    json.dump(payload, stream, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    atomic_bytes(path, (stream.getvalue() + "\n").encode())


def read_json(path: Path, default=None):
    path = regular_path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write_schemas(root, pending_writes=None):
    for name, model in (("story", Story), ("source-registry", SourceRegistry), ("claim", Fact), ("snapshot", Snapshot),
                        ("offer", Offer), ("model-release", ModelRelease), ("digest", Digest)):
        schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", **model.model_json_schema()}
        path = root / "schemas" / f"{name}.schema.json"
        if pending_writes is None:
            atomic_json(path, schema)
        else:
            pending_writes.append((path, schema))


def validate_snapshot(snapshot, root):
    schema = read_json(root / "schemas/snapshot.schema.json", Snapshot.model_json_schema())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(snapshot.model_dump(mode="json"))
    return Snapshot.model_validate(snapshot.model_dump(mode="json"))


def compact(stories, sources, root, now, config, previous_index, pending_writes=None):
    def stage(path, payload):
        if pending_writes is None:
            atomic_json(path, payload)
        else:
            pending_writes.append((path, payload))

    active = []
    groups = {}
    for story in stories:
        validate_story(story, sources, now)
        if story.published_at >= now - timedelta(days=config["retain_individual_days"]):
            active.append(story)
        else:
            key = story.published_at.astimezone(ZoneInfo("Asia/Dhaka")).strftime("%Y-%m")
            groups.setdefault(key, []).append(story)
    if len(active) > config.get("max_individual_stories", 4000):
        active.sort(key=lambda story: story.published_at, reverse=True)
        for story in active[config.get("max_individual_stories", 4000):]:
            groups.setdefault(story.published_at.astimezone(ZoneInfo("Asia/Dhaka")).strftime("%Y-%m"), []).append(story)
        active = active[:config.get("max_individual_stories", 4000)]
    index = {entry["key"]: entry for entry in previous_index}
    for key, archived in groups.items():
        directory = config.get("archive_directory", "content/archives")
        if directory not in {"content/archives", ".cache/fixture-archives"}:
            raise ValueError("Archive directory is not an approved output boundary")
        path = confined_file(root, f"{directory}/{key}.json")
        previous = read_json(path, {"stories": [], "sources": {}})
        merged = {story["id"]: story for story in previous["stories"]}
        for story in archived:
            old = merged.get(story.id)
            if old and story.first_seen_at.isoformat() != old["first_seen_at"]:
                prior = Story.model_validate(old)
                story.first_seen_at, story.slug = prior.first_seen_at, prior.slug
                if story.ai_metadata.evidence_hash == prior.ai_metadata.evidence_hash:
                    story.updated_at, story.change_log = prior.updated_at, prior.change_log
                else:
                    story.change_log[-1].text = "Archived evidence refreshed from its cited sources."
                    story.change_log = [*prior.change_log, story.change_log[-1]]
        merged.update({story.id: story.model_dump(mode="json") for story in archived})
        archive_sources = previous["sources"]
        archive_sources.update({source_id: sources[source_id].model_dump(mode="json") for story in archived
                                for source_id in set(story.source_ids) | {key for change in story.change_log for key in change.source_ids}})
        stage(path, {"key": key, "stories": list(merged.values()), "sources": archive_sources})
        index[key] = {"key": key, "count": len(merged), "url": f"/archives/{key}/"}
    ordered_index = sorted(index.values(), key=lambda entry: entry["key"], reverse=True)
    for year in {entry["key"][:4] for entry in ordered_index}:
        months = [entry for entry in ordered_index if entry["key"].startswith(year)]
        stage(root / config.get("archive_directory", "content/archives") / f"{year}.json",
                    {"year": year, "months": months, "count": sum(month["count"] for month in months)})
    return active, ordered_index
