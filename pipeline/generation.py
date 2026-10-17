"""Staged multi-file promotion with an explicit, fail-closed recovery barrier.

The journal is the publication barrier, not a claim of atomic directory swap.
Supported builds share the writer lock and refuse an outstanding journal.
"""

import argparse
import hashlib
import json
import os
import re
from contextlib import contextmanager
from datetime import UTC, datetime
from itertools import islice
from pathlib import Path
from uuid import uuid4

from pipeline.filesystem import atomic_bytes, confined_file, regular_path, sync_directory
from pipeline.strict_json import strict_json

LOCK = ".cache/pipeline-writer.lock"
JOURNAL = ".cache/pipeline-transaction.json"
GENERATIONS = ".cache/pipeline-generations"
MAX_FILE_BYTES = 50_000_000
MAX_GENERATION_BYTES = 250_000_000


def encode(value):
    if isinstance(value, bytes):
        return value
    payload = value.model_dump(mode="json") if hasattr(value, "model_dump") else value
    return (json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode()


def allowed(name):
    return bool(re.fullmatch(
        r"(?:content/generated/(?:snapshot\.json|run-report\.json|briefing\.md)|"
        r"\.cache/(?:state|last-snapshot|translations)-(?:live|fixture)\.json|"
        r"\.cache/source-review(?:/[^/]+)*\.json|\.cache/source-review/(?:[^/]+/)*briefing\.md|"
        r"\.cache/briefing\.md|(?:content/archives|\.cache/fixture-archives)/\d{4}(?:-(?:0[1-9]|1[0-2]))?\.json|"
        r"schemas/(?:story|source-registry|claim|snapshot|offer|model-release|digest)\.schema\.json)", name))


def artifact_path(root, name):
    if not isinstance(name, str) or not allowed(name):
        raise ValueError("Non-allowlisted generation artifact")
    return confined_file(root, name)


def assert_stable(root):
    if confined_file(root, JOURNAL).exists():
        raise ValueError("Interrupted generation: recover finish or rollback before reading/building")


@contextmanager
def writer(root):
    lock = confined_file(root, LOCK)
    lock.parent.mkdir(parents=True, exist_ok=True)
    regular_path(lock)
    # A killed writer deliberately leaves evidence; never steal an old lock.
    stream = lock.open("x", encoding="utf-8")
    try:
        with stream:
            json.dump({"pid": os.getpid(), "kind": "pipeline", "started_at": datetime.now(UTC).isoformat()}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        yield
    finally:
        regular_path(lock).unlink()
        sync_directory(lock.parent)


def bounded_file(path, limit):
    with regular_path(path).open("rb") as stream:
        payload = stream.read(limit + 1)
    if len(payload) > limit:
        raise ValueError("Generation file byte limit exceeded")
    return payload


def promote(root, writes, *, generation=None):
    """Caller holds writer(root). Stage and check everything before mutation."""
    assert_stable(root)
    generation = generation or uuid4().hex
    if not re.fullmatch(r"[a-f0-9]{32}", generation):
        raise ValueError("Invalid generation identifier")
    base = Path(GENERATIONS) / generation
    # Bounded retention: never delete a prior recovery generation automatically.
    parent = confined_file(root, base / "manifest.json").parent.parent
    if parent.exists() and sum(1 for _ in islice(parent.iterdir(), 16)) >= 16:
        raise ValueError("Generation retention capacity: archive verified old generations before retrying")
    entries, names, total = [], set(), 0
    for index, (path, value) in enumerate(writes):
        name = Path(path).absolute().relative_to(Path(root).absolute()).as_posix()
        target = artifact_path(root, name)
        if name.casefold() in names or len(entries) >= 1000:
            raise ValueError("Duplicate artifact or generation item limit exceeded")
        names.add(name.casefold())
        after = encode(value)
        before = bounded_file(target, MAX_FILE_BYTES) if target.exists() else None
        total += len(after) + len(before or b"")
        if len(after) > MAX_FILE_BYTES or total > MAX_GENERATION_BYTES:
            raise ValueError("Generation byte limit exceeded")
        entry = {"path": name}
        for side, payload in (("before", before), ("after", after)):
            entry[side] = None if payload is None else {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
            if payload is not None:
                atomic_bytes(confined_file(root, base / f"{index}.{side}"), payload)
        entries.append(entry)
    if not entries:
        raise ValueError("Empty generation")
    manifest = encode({"version": 1, "generation": generation, "files": entries})
    atomic_bytes(confined_file(root, base / "manifest.json"), manifest)
    atomic_bytes(confined_file(root, JOURNAL), encode({"version": 1, "generation": generation,
                 "manifest_sha256": hashlib.sha256(manifest).hexdigest()}))
    recover(root, "finish")
    return generation


def recover(root, action):
    """Caller holds writer(root). Validate all paths/bytes before any write."""
    if action not in {"finish", "rollback"}:
        raise ValueError("Unknown recovery action")
    journal_path = confined_file(root, JOURNAL)
    journal = strict_json(bounded_file(journal_path, 1024), max_bytes=1024)
    if (not isinstance(journal, dict) or journal.get("version") != 1
            or not re.fullmatch(r"[a-f0-9]{32}", str(journal.get("generation")))):
        raise ValueError("Invalid generation journal")
    base = Path(GENERATIONS) / journal["generation"]
    payload = bounded_file(confined_file(root, base / "manifest.json"), 2_000_000)
    if hashlib.sha256(payload).hexdigest() != journal.get("manifest_sha256"):
        raise ValueError("Generation manifest integrity mismatch")
    manifest = strict_json(payload, max_bytes=2_000_000)
    if (manifest.get("version") != 1 or manifest.get("generation") != journal["generation"]
            or not isinstance(manifest.get("files"), list) or not 1 <= len(manifest["files"]) <= 1000):
        raise ValueError("Invalid generation manifest")
    checked, names, total = [], set(), 0
    for index, entry in enumerate(manifest["files"]):
        target = artifact_path(root, entry["path"])
        if entry["path"].casefold() in names:
            raise ValueError("Duplicate generation artifact")
        names.add(entry["path"].casefold())
        current = bounded_file(target, MAX_FILE_BYTES) if target.exists() else None
        if not any((current is None and info is None) or
                   (current is not None and isinstance(info, dict) and len(current) == info.get("bytes")
                    and hashlib.sha256(current).hexdigest() == info.get("sha256"))
                   for info in (entry["before"], entry["after"])):
            raise ValueError("Artifact changed outside the interrupted generation; preserve it before recovery")
        chosen = None
        for side in ("before", "after"):
            info = entry[side]
            if info is None and side == "before":
                continue
            if not isinstance(info, dict) or type(info.get("bytes")) is not int or not 0 <= info["bytes"] <= MAX_FILE_BYTES:
                raise ValueError("Invalid generation byte count")
            total += info["bytes"]
            if total > MAX_GENERATION_BYTES:
                raise ValueError("Generation byte limit exceeded")
            data = bounded_file(confined_file(root, base / f"{index}.{side}"), info["bytes"])
            if len(data) != info["bytes"] or hashlib.sha256(data).hexdigest() != info.get("sha256"):
                raise ValueError("Generation artifact integrity mismatch")
            if side == ("after" if action == "finish" else "before"):
                chosen = data
        checked.append((target, chosen))
    for target, data in checked:
        if data is None:
            regular_path(target).unlink(missing_ok=True)
            if target.parent.exists():
                sync_directory(target.parent)
        else:
            atomic_bytes(target, data)
    journal_path.unlink()
    sync_directory(journal_path.parent)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("finish", "rollback"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    with writer(args.root):
        recover(args.root, args.action)
    print(f"Generation recovery {args.action} complete; no deployment performed")


if __name__ == "__main__":
    main()
