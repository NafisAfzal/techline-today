"""Stage only verified, referenced live state in an isolated Actions checkout."""
import argparse
import json
import os
from pathlib import Path

from pipeline.backup import export_backup, safe_file, verify_backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["restore", "save"])
    args = parser.parse_args()
    if os.getenv("GITHUB_ACTIONS") != "true":
        parser.error("Use pipeline.backup locally; this helper only modifies an isolated Actions checkout")
    root = Path.cwd()
    pack = root / ".cache/published-state"
    if args.action == "save":
        if pack.exists():
            # Preserve the restored generation rather than overwriting/deleting it.
            pack.rename(root / ".cache/previous-published-state")
        manifest = export_backup(root, pack)
    else:
        manifest = verify_backup(pack)
        for item in manifest["files"]:
            target = safe_file(root, item["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(safe_file(pack, item["path"]).read_bytes())
    print(json.dumps({"action": args.action, "files": len(manifest["files"])}))


if __name__ == "__main__":
    main()
