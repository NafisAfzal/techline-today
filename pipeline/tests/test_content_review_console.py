"""Private exports and operator evidence boundaries, using synthetic content only."""

import csv
import hashlib
import io
import json
import shutil
from pathlib import Path

import pytest

from pipeline import content_review, launch_console
from pipeline.authority.ledger import JOURNAL, STOP
from pipeline.authority.protocol import AuthorityError, read_envelope
from pipeline.models import Snapshot
from pipeline.recovery.fixtures import SYNTHETIC_NOW as NOW
from pipeline.research_demo import content
from pipeline.review_governance import digest

ROOT = Path(__file__).resolve().parents[2]


def credential_marker(prefix, length):
    """Keep public fake tokens out of source and constant-folded bytecode."""
    return prefix + "A" * length


@pytest.fixture
def room(tmp_path, monkeypatch):
    root = tmp_path / "room"
    (root / "config").mkdir(parents=True)
    for name in ("source-rights.json", "research-edition.json", "sources.yaml", "release.json",
                 "security-advisories.json"):
        shutil.copyfile(ROOT / "config" / name, root / "config" / name)
    # Freeze recorded mitigation dates to the synthetic assessment instant.
    advisory = json.loads((root / "config/security-advisories.json").read_bytes())
    for entry in advisory["advisories"]:
        entry["last_reassessed"] = NOW.date().isoformat()
    (root / "config/security-advisories.json").write_text(json.dumps(advisory), encoding="utf-8")
    shutil.copyfile(ROOT / "pnpm-lock.yaml", root / "pnpm-lock.yaml")
    (root / "patches").mkdir()
    shutil.copyfile(ROOT / "patches/http-cache-semantics@4.3.0.patch",
                    root / "patches/http-cache-semantics@4.3.0.patch")
    story, sources, _ = content()
    edition = Snapshot(generated_at=NOW, last_successful_fetch_at=NOW, mode="live", stories=[story],
                       sources=sources, categories={}, digests=[], offers=[], model_releases=[])
    target = root / "content/generated/snapshot.json"
    target.parent.mkdir(parents=True)
    target.write_text(edition.model_dump_json(), encoding="utf-8")
    for key in ("TECHLINE_AUTHORITY_TRUST_FILE", "TECHLINE_EXTERNAL_CHECKPOINT_FILE"):
        monkeypatch.delenv(key, raising=False)
    return root


def test_inventory_binds_exact_original_and_existing_decisions_without_mutation(room):
    path = room / "content/generated/snapshot.json"
    before = path.read_bytes()
    report = content_review.inventory(room, now=NOW, expected_sha256=hashlib.sha256(before).hexdigest())
    assert report["record_count"] == 1 and report["eligible_count"] == 0
    row = report["items"][0]
    assert row["canonical_record_sha256"] == digest(json.loads(before)["stories"][0])
    assert len(row["missing_decisions"]) == 5
    assert all(stage["required_role"] for stage in row["missing_decisions"])
    assert row["bindings"][0]["story_id"] == row["id"]
    assert row["human_decision"] is None and row["signature"] is None and row["unsigned"]
    with pytest.raises(ValueError):
        read_envelope(json.dumps(row).encode())
    assert path.read_bytes() == before and not (room / JOURNAL).exists()


def test_inventory_refuses_wrong_expected_digest_and_duplicate_item_ids(room):
    with pytest.raises(AuthorityError, match="differs"):
        content_review.inventory(room, now=NOW, expected_sha256="0" * 64)
    target = room / "content/generated/snapshot.json"
    data = json.loads(target.read_bytes())
    data["stories"].append(data["stories"][0])
    target.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        content_review.inventory(room, now=NOW)


def test_export_contains_each_packet_csv_and_verifiable_manifest(room, tmp_path):
    report = content_review.inventory(room, now=NOW)
    target = tmp_path / "private-export"
    result = content_review.export_inventory(report, target, root=room)
    assert result["exported_records"] == 1 and not result["publication_allowed"]
    assert (target / "item-001.md").is_file() and (target / "item-001.json").is_file()
    rows = list(csv.DictReader(io.StringIO((target / "inventory.csv").read_text(encoding="utf-8"))))
    assert rows[0]["id"] == report["items"][0]["id"]
    manifest = json.loads((target / "MANIFEST.json").read_bytes())
    for name, expected in manifest["files"].items():
        assert hashlib.sha256((target / name).read_bytes()).hexdigest() == expected
    with pytest.raises(FileExistsError):
        content_review.export_inventory(report, target, root=room)


@pytest.mark.parametrize("relative", ["apps/web/public/packets", ".cache/private-packets", "docs/packets"])
def test_private_exports_refuse_any_checkout_destination(room, relative):
    with pytest.raises(AuthorityError, match="outside Git"):
        content_review.export_inventory({"items": []}, room / relative, root=room)


def test_private_exports_refuse_another_git_checkout(room, tmp_path):
    other = tmp_path / "other-checkout"
    other.mkdir()
    (other / ".git").write_text("gitdir: unrelated", encoding="utf-8")
    with pytest.raises(AuthorityError, match="outside Git"):
        content_review.export_inventory({"items": []}, other / "review", root=room)


def test_spreadsheet_and_markdown_metadata_are_inert():
    for value in ("=HYPERLINK(1)", "+formula", "-formula", "@formula", " \t=FORMULA"):
        assert content_review.csv_cell(value).startswith("'")
    text = content_review.markdown_text("[click](javascript:alert(1)) | <script>\n`code`")
    assert "<script>" not in text and "[click]" not in text and "|" not in text and "\n" not in text
    assert "\u202e" not in content_review.markdown_text("visible\u202ehidden")


def test_content_cli_refusal_does_not_echo_unsafe_input(room, capsys):
    assert content_review.main(["--root", str(room), "--expected-snapshot-sha256", "secret-shaped-input"]) == 1
    output = capsys.readouterr().out
    assert "secret-shaped-input" not in output and json.loads(output)["publication_allowed"] is False


def test_console_read_only_distinguishes_missing_human_decisions_and_unknown_accounts(room):
    before = {p.relative_to(room): p.read_bytes() for p in room.rglob("*") if p.is_file()}
    report = launch_console.launch_report(room, now=NOW)
    rows = {row["item"]: row for row in report["checks"]}
    assert report["status"] == "BLOCKED"
    assert rows["owner_authority"]["status"] == "BLOCKED"
    assert rows["research_publication_eligibility"]["status"] == "BLOCKED"
    assert rows["research_publication_eligibility"]["evidence"]["eligible_count"] == 0
    assert rows["cloudflare_account"]["status"] == rows["github_open_advisories"]["status"] == "INCONCLUSIVE"
    assert rows["recovery"]["status"] == "INCONCLUSIVE"
    assert not report["network_access"] and not report["content_or_authority_mutated"]
    assert not report["security_state_may_advance"] and not report["publication_allowed"]
    assert before == {p.relative_to(room): p.read_bytes() for p in room.rglob("*") if p.is_file()}


def test_local_cloudflare_flags_cannot_verify_account(room):
    path = room / "config/release.json"
    config = json.loads(path.read_bytes())
    config.update(free_plan_verified=True, zero_spend_verified=True, preview_approved=True)
    path.write_text(json.dumps(config), encoding="utf-8")
    report = launch_console.launch_report(room, now=NOW)
    assert next(row for row in report["checks"] if row["item"] == "cloudflare_account")["status"] == "INCONCLUSIVE"


def test_clean_checkout_with_no_snapshot_is_inconclusive_not_faked_zero(room):
    (room / "content/generated/snapshot.json").unlink()
    report = launch_console.launch_report(room, now=NOW)
    row = next(row for row in report["checks"] if row["item"] == "research_inventory")
    assert row["status"] == "INCONCLUSIVE" and "record_count" not in row["evidence"]


def test_malformed_snapshot_and_emergency_stop_remain_visible(room):
    (room / "content/generated/snapshot.json").write_bytes(b'{"stories":')
    stop = room / STOP
    stop.parent.mkdir(parents=True)
    stop.write_text("test emergency suspension", encoding="utf-8")
    report = launch_console.launch_report(room, now=NOW)
    rows = {row["item"]: row for row in report["checks"]}
    assert report["status"] == "FAIL" and rows["research_inventory"]["status"] == "FAIL"
    assert rows["emergency_suspension"]["status"] == "BLOCKED"
    assert not report["publication_allowed"]


def test_console_cli_exit_status_and_human_table(room, monkeypatch, capsys):
    original = launch_console.launch_report
    monkeypatch.setattr(launch_console, "launch_report", lambda root, now: original(root, now=NOW))
    assert launch_console.main(["--root", str(room)]) == 2
    assert "Techline Today local launch: BLOCKED" in capsys.readouterr().out
    assert launch_console.main(["--root", str(room), "--json"]) == 2
    assert json.loads(capsys.readouterr().out)["publication_allowed"] is False


@pytest.mark.parametrize("json_mode", [True, False])
@pytest.mark.parametrize("location", ["key", "value"])
def test_console_refuses_credential_shaped_keys_and_values(room, monkeypatch, capsys, location, json_mode):
    synthetic_credential = credential_marker("ghp_", 36)
    payload = {synthetic_credential: "ordinary"} if location == "key" else {"reviewer": synthetic_credential}
    monkeypatch.setattr(launch_console, "launch_report", lambda root, now: payload)
    assert launch_console.main(["--root", str(room), *(["--json"] if json_mode else [])]) == 1
    output = capsys.readouterr().out
    assert synthetic_credential not in output and json.loads(output)["code"] == "sensitive_output_refused"


def test_export_and_content_stdout_refuse_credentials_before_writing(room, tmp_path, monkeypatch, capsys):
    synthetic_credential = credential_marker("sk-", 30)
    payload = {"field": {synthetic_credential: "unsafe input"}}
    destination = tmp_path / "must-not-exist"
    with pytest.raises(AuthorityError, match="Credential-shaped"):
        content_review.export_inventory(payload, destination, root=room)
    assert not destination.exists()
    monkeypatch.setattr(content_review, "inventory", lambda *args, **kwargs: payload)
    assert content_review.main(["--root", str(room)]) == 1
    output = capsys.readouterr().out
    assert synthetic_credential not in output and json.loads(output)["code"] == "sensitive_output_refused"


def test_unknown_arguments_never_echo_credential_values(capsys):
    credential = credential_marker("ghp_", 36)
    with pytest.raises(SystemExit):
        launch_console.main(["--unknown", credential])
    assert credential not in capsys.readouterr().err


def test_active_scoped_custody_is_reported_as_possible_local_security_write(room, monkeypatch):
    # No real credentials or state are supplied; only the truthful report flag is exercised.
    monkeypatch.setenv("TECHLINE_CUSTODIAN_RUN_TOKEN", "synthetic-scope")
    report = launch_console.launch_report(room, now=NOW)
    assert report["security_state_may_advance"] and not report["content_or_authority_mutated"]
