"""Allowlisted local data backup/restore. This does not provision durable storage."""
import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from pipeline.filesystem import confined_file
from pipeline.generation import assert_stable, writer
from pipeline.models import Snapshot

FILES = {
    "content/generated/snapshot.json", "content/generated/run-report.json", "content/generated/briefing.md",
    ".cache/state-live.json", ".cache/last-snapshot-live.json", ".cache/provider-usage-live.json", ".cache/translations-live.json",
    ".cache/publication-receipt.json",
}


def allowed(name):
    return name in FILES or bool(re.fullmatch(r"content/archives/[0-9]{4}(?:-(?:0[1-9]|1[0-2]))?\.json", name))


def safe_file(root, name):
    if not allowed(name):
        raise ValueError("Backup contains a non-allowlisted path")
    return confined_file(root, name)


def live_snapshot(payload):
    snapshot = Snapshot.model_validate_json(payload)
    if snapshot.mode != "live":
        raise ValueError("Only live data can enter an operational backup")
    return snapshot


def archive_paths(snapshot):
    return {f"content/archives/{name}.json" for entry in snapshot.archive_index
            for name in (entry["key"], entry["key"][:4])}


def validate_archives(directory, snapshot, names):
    months = {}
    for entry in snapshot.archive_index:
        name = f"content/archives/{entry['key']}.json"
        if name not in names:
            raise ValueError("Referenced archive is missing from backup")
        bundle = json.loads(safe_file(directory, name).read_text(encoding="utf-8"))
        if bundle.get("key") != entry["key"] or len(bundle.get("stories", [])) != entry["count"]:
            raise ValueError("Archive identity/count mismatch")
        Snapshot(mode="live", generated_at=snapshot.generated_at, last_successful_fetch_at=snapshot.last_successful_fetch_at,
                 categories=snapshot.categories, stories=bundle["stories"], sources=bundle["sources"],
                 digests=[], offers=[], model_releases=[])
        months[entry["key"]] = entry
    for year in {key[:4] for key in months}:
        name = f"content/archives/{year}.json"
        if name not in names:
            raise ValueError("Referenced annual index is missing from backup")
        index = json.loads(safe_file(directory, name).read_text(encoding="utf-8"))
        expected = {key: value for key, value in months.items() if key.startswith(year)}
        if (index.get("year") != year or {entry.get("key"): entry for entry in index.get("months", [])} != expected
                or index.get("count") != sum(entry["count"] for entry in expected.values())):
            raise ValueError("Annual archive index mismatch")


def export_backup(root, destination):
    with writer(root):
        assert_stable(root)
        return export_stable_backup(root, destination)


def export_stable_backup(root, destination):
    root, destination = Path(root).absolute(), Path(destination).absolute()
    if destination.exists():
        raise ValueError("Use a new backup directory")
    snapshot = live_snapshot(safe_file(root, "content/generated/snapshot.json").read_bytes())
    for entry in snapshot.archive_index:
        if not safe_file(root, f"content/archives/{entry['key']}.json").is_file():
            raise ValueError("Referenced archive is missing from operational data")
        if not safe_file(root, f"content/archives/{entry['key'][:4]}.json").is_file():
            raise ValueError("Referenced annual index is missing from operational data")
    # Unreferenced files may be legacy fixtures or unrelated user state. Preserve
    # them locally, but never silently export them as a validated live archive.
    names = sorted(FILES | archive_paths(snapshot))
    entries = []
    for name in names:
        source = safe_file(root, name)
        if not source.exists():
            continue
        payload = source.read_bytes()
        if len(payload) > 50_000_000:
            raise ValueError("Backup file exceeds bounded size")
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        entries.append({"path": name, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})
    manifest = {"version": 1, "mode": "live", "created_at": datetime.now(UTC).isoformat(), "files": entries}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    verify_backup(destination)
    return manifest


def verify_backup(directory):
    directory = Path(directory).absolute()
    manifest = json.loads(confined_file(directory, "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("version") != 1 or manifest.get("mode") != "live" or not 1 <= len(manifest.get("files", [])) <= 1000:
        raise ValueError("Unsupported/empty backup manifest")
    names = set()
    for item in manifest["files"]:
        name = item["path"]
        if name in names or not isinstance(item["bytes"], int) or not 0 <= item["bytes"] <= 50_000_000:
            raise ValueError("Duplicate path or invalid size")
        names.add(name)
        payload = safe_file(directory, name).read_bytes()
        if len(payload) != item["bytes"] or hashlib.sha256(payload).hexdigest() != item["sha256"]:
            raise ValueError("Backup integrity check failed")
    if "content/generated/snapshot.json" not in names:
        raise ValueError("Backup snapshot is missing")
    snapshot = live_snapshot(safe_file(directory, "content/generated/snapshot.json").read_bytes())
    if names - FILES != archive_paths(snapshot):
        raise ValueError("Backup contains unreferenced archives or is missing referenced archives")
    if any(f"content/archives/{entry['key']}.json" not in names for entry in snapshot.archive_index):
        raise ValueError("Referenced archive is missing from backup")
    if any(f"content/archives/{entry['key'][:4]}.json" not in names for entry in snapshot.archive_index):
        raise ValueError("Referenced annual index is missing from backup")
    validate_archives(directory, snapshot, names)
    return manifest


def restore_backup(directory, destination):
    directory, destination = Path(directory).absolute(), Path(destination).absolute()
    manifest = verify_backup(directory)
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Restore requires an empty destination; existing data is never overwritten")
    for item in manifest["files"]:
        target = safe_file(destination, item["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(dir=target.parent)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(safe_file(directory, item["path"]).read_bytes())
            Path(temporary).replace(target)
        finally:
            Path(temporary).unlink(missing_ok=True)
    live_snapshot((destination / "content/generated/snapshot.json").read_bytes())
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["export", "verify", "restore"])
    parser.add_argument("directory", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    if args.action == "export":
        result = export_backup(args.root, args.directory)
    elif args.action == "verify":
        result = verify_backup(args.directory)
    else:
        if not args.destination:
            parser.error("restore needs --destination (an empty directory)")
        result = restore_backup(args.directory, args.destination)
    print(json.dumps({"mode": result["mode"], "files": len(result["files"]), "durable_storage_provisioned": False}))


if __name__ == "__main__":
    main()
