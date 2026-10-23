"""Custody preparation uses only published synthetic keys; no real appointments."""

import json
import os
import shutil
import subprocess
from datetime import timedelta
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives import serialization

from pipeline.authority.custody import _windows_acl, protected_file
from pipeline.authority.protocol import POLICY, PROTOCOL, AuthorityError, stamp
from pipeline.operations.ceremony import CONFIRMATIONS, template
from pipeline.operations.onboarding import (
    ReviewerProposal,
    main,
    owner_preflight,
    public_fingerprint,
    reviewer_packet,
)
from pipeline.tests.authority_support import NOW, grant, key, private, protect_fixture_directory


def proposal():
    permission = grant().model_copy(update={"stories": ["story-one"]})
    return {"version": 1, "protocol": PROTOCOL, "policy_version": POLICY, "environment": "production",
            "ledger_id": "owner-selected-ledger", "reviewer_id": "editor", "intended_identity": "Synthetic Person",
            "key": key("editor").model_dump(mode="json"), "grant": permission.model_dump(mode="json"),
            "issued_at": stamp(NOW), "expires_at": stamp(NOW + timedelta(days=90)),
            "revocation_contact": "Synthetic owner contact", "conflict_of_interest_disclosure": "None declared",
            "acceptance_evidence_sha256": "a" * 64}


def packet(value, **kwargs):
    return reviewer_packet(value, environment_id="production", ledger_id="owner-selected-ledger", now=NOW, **kwargs)


def test_unsigned_packet_is_exact_existing_admin_request_without_authority():
    result = packet(proposal())
    assert result["status"] == "PASS"
    assert [request["operation"] for request in result["owner_requests"]] == ["enroll", "grant"]
    assert all(set(request) == {"operation", "target_id", "key", "grant"} for request in result["owner_requests"])
    assert not result["appointment_valid"] and not result["production_credentials_created"]
    assert not result["publication_allowed"] and "declarations" in result["note"]


@pytest.mark.parametrize("change", [
    {"environment": "synthetic"}, {"expires_at": stamp(NOW + timedelta(days=91))},
    {"unexpected_consent": True}, {"intended_identity": ""},
])
def test_packet_refuses_invalid_or_unbounded_proposal(change):
    with pytest.raises(ValueError):
        packet({**proposal(), **change})


@pytest.mark.parametrize("field,value", [
    ("stories", ["*"]), ("decisions", ["PUBLISHED"]), ("sources", ["*"]),
    ("languages", ["bn"]), ("expires_at", stamp(NOW + timedelta(days=91))),
])
def test_preparation_reuses_existing_grant_least_privilege_checks(field, value):
    data = proposal()
    data["grant"][field] = value
    with pytest.raises(ValueError):
        ReviewerProposal.model_validate(data)


def test_wrong_ledger_expired_packet_and_missing_acceptance_stay_blocked():
    data = proposal()
    assert reviewer_packet(data, environment_id="production", ledger_id="other", now=NOW)["status"] == "BLOCKED"
    assert reviewer_packet(data, environment_id="production", ledger_id="owner-selected-ledger",
                           now=NOW + timedelta(days=90))["status"] == "BLOCKED"
    data["acceptance_evidence_sha256"] = None
    assert packet(data)["status"] == "BLOCKED"


def test_public_key_formats_and_algorithm_are_checked(tmp_path):
    public = private("editor").public_key()
    path = tmp_path / "public.pem"
    path.write_bytes(public.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    assert public_fingerprint(path) == key("editor").key_id
    path.write_text(key("editor").public_key, encoding="ascii")
    assert public_fingerprint(path) == key("editor").key_id
    path.write_text("A" * 43, encoding="ascii")
    with pytest.raises(ValueError):
        public_fingerprint(path)


def test_owner_requires_custody_evidence_and_exact_production_context(tmp_path):
    data = template("production", "production-ledger")
    data["confirmations"] = list(CONFIRMATIONS)
    result = owner_preflight(tmp_path, data, environment_id="production", ledger_id="production-ledger", now=NOW)
    assert result["status"] == "BLOCKED"
    assert not result["identity_authenticated"] and not result["publication_allowed"]
    result = owner_preflight(tmp_path, data, environment_id="other", ledger_id="production-ledger", now=NOW)
    assert result["status"] == "BLOCKED" and not list(tmp_path.iterdir())


def test_owner_rejects_mismatch_duplicate_backup_and_plaintext(tmp_path, monkeypatch):
    import pipeline.operations.onboarding as onboarding
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    data = template("production", "production-ledger")
    data["confirmations"] = list(CONFIRMATIONS)
    public = tmp_path / "public.txt"
    public.write_text(key("editor").public_key, encoding="ascii")
    custody, backup = tmp_path / "custody.pem", tmp_path / "backup.pem"
    # ACL behavior is exercised separately; these bytes are explicitly non-secret.
    monkeypatch.setattr(onboarding, "protected_file", lambda path, root: path)
    custody.write_bytes(b"-----BEGIN ENCRYPTED PRIVATE KEY-----\nSYNTHETIC\n-----END ENCRYPTED PRIVATE KEY-----\n")
    backup.write_bytes(custody.read_bytes())
    options = dict(environment_id="production", ledger_id="production-ledger", public_file=public,
                   expected_fingerprint=key("editor").key_id, custody_file=custody, backup_file=backup, now=NOW)
    good = owner_preflight(checkout, data, **options)
    assert good["status"] == "READY_FOR_HUMAN_CEREMONY"
    assert not good["actual_signing_algorithm_verified"] and not good["encrypted_file_public_key_match_verified"]
    assert owner_preflight(checkout, data, **{**options, "expected_fingerprint": "f" * 64})["status"] == "BLOCKED"
    assert owner_preflight(checkout, data, **{**options, "backup_file": custody})["status"] == "BLOCKED"
    backup.write_bytes(b"-----BEGIN ENCRYPTED PRIVATE KEY-----\nDIFFERENT\n-----END ENCRYPTED PRIVATE KEY-----\n")
    assert owner_preflight(checkout, data, **options)["status"] == "BLOCKED"
    custody.write_bytes(b"SYNTHETIC PLAINTEXT")
    with pytest.raises(ValueError):
        owner_preflight(checkout, data, **options)


@pytest.mark.parametrize("other", ["S-1-1-0", "S-1-5-32-545", "S-1-5-21-other"])
def test_windows_acl_refuses_broad_or_unknown_principals(tmp_path, monkeypatch, other):
    from pipeline.authority import custody
    current = "S-1-5-21-current"
    safe = {"owner": current, "rules": [{"sid": current, "allow": True}]}
    checked = {"current": current, "checks": [safe, safe]}
    monkeypatch.setattr(custody.shutil, "which", lambda name: "powershell.exe")
    monkeypatch.setattr(custody.subprocess, "run", lambda *a, **kw: SimpleNamespace(stdout=json.dumps(checked).encode()))
    _windows_acl(tmp_path / "synthetic.pem")
    checked["checks"] = [safe, {"owner": current, "rules": [*safe["rules"], {"sid": other, "allow": True}]}]
    with pytest.raises(AuthorityError, match="unsafe or unverifiable"):
        _windows_acl(tmp_path / "synthetic.pem")


def test_windows_acl_failure_and_missing_dacl_fail_closed(tmp_path, monkeypatch):
    from pipeline.authority import custody
    monkeypatch.setattr(custody.shutil, "which", lambda name: None)
    with pytest.raises(AuthorityError):
        _windows_acl(tmp_path / "synthetic.pem")
    monkeypatch.setattr(custody.shutil, "which", lambda name: "powershell.exe")
    value = {"current": "S-1-5-21-current", "checks": [{"owner": "S-1-5-21-current", "rules": []}] * 2}
    monkeypatch.setattr(custody.subprocess, "run", lambda *a, **kw: SimpleNamespace(stdout=json.dumps(value).encode()))
    with pytest.raises(AuthorityError):
        _windows_acl(tmp_path / "synthetic.pem")


@pytest.mark.skipif(os.name != "nt", reason="Actual Windows DACL verification")
def test_native_windows_file_and_parent_acl_with_world_read_rejection(tmp_path):
    directory = tmp_path / "isolated-custody"
    directory.mkdir()
    protect_fixture_directory(directory)
    path = directory / "synthetic-placeholder.pem"
    path.write_bytes(b"NONSECRET SYNTHETIC PLACEHOLDER")
    assert protected_file(path, tmp_path / "checkout") == path
    subprocess.run(  # noqa: S603 - only the pytest-owned synthetic file is modified
        [shutil.which("icacls.exe"), str(path), "/grant", "*S-1-1-0:R"],
        capture_output=True, timeout=15, check=True)
    with pytest.raises(AuthorityError):
        protected_file(path, tmp_path / "checkout")


def test_files_inside_another_git_checkout_are_refused(tmp_path):
    directory = tmp_path / "other-checkout"
    directory.mkdir()
    (directory / ".git").mkdir()
    path = directory / "synthetic.pem"
    path.write_bytes(b"SYNTHETIC")
    with pytest.raises(AuthorityError, match="every Git checkout"):
        protected_file(path, tmp_path / "checkout")


def test_known_synchronization_directories_are_refused(tmp_path, monkeypatch):
    directory = tmp_path / "synced"
    directory.mkdir()
    path = directory / "synthetic.pem"
    path.write_bytes(b"SYNTHETIC")
    monkeypatch.setenv("OneDrive", str(directory))
    with pytest.raises(AuthorityError, match="synchronized"):
        protected_file(path, tmp_path / "checkout")


def test_cli_template_schema_refusal_and_private_error(tmp_path, capsys):
    assert main(["reviewer", "--template", "native-bn"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["existing_role_guidance"]["language_scope"] == ["bn"]
    assert main(["schema", "reviewer"]) == 0
    assert "Grant" in json.loads(capsys.readouterr().out)["$defs"]
    data = proposal()
    synthetic_marker = "ghp_" + "a" * 36
    data["intended_identity"] = synthetic_marker
    path = tmp_path / "packet.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert main(["reviewer", "--proposal", str(path), "--ledger-id", "owner-selected-ledger"]) == 1
    output = capsys.readouterr().out
    assert synthetic_marker not in output and json.loads(output)["status"] == "REFUSED"
    path.write_text("invalid SYNTHETIC PRIVATE INPUT", encoding="utf-8")
    assert main(["reviewer", "--proposal", str(path)]) == 1
    assert "SYNTHETIC PRIVATE INPUT" not in capsys.readouterr().out


def test_interactive_guide_requires_actual_answers_and_never_provisions(tmp_path, monkeypatch, capsys):
    prompts = []

    def answer(prompt):
        prompts.append(prompt)
        return "NO"

    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", answer)
    assert main(["--root", str(tmp_path), "owner", "--environment-id", "production", "--ledger-id",
                 "selected-ledger", "--interactive"]) == 2
    result = json.loads(capsys.readouterr().out)
    assert len(prompts) == len(CONFIRMATIONS)
    assert set(result["missing_confirmations"]) == set(CONFIRMATIONS)
    assert not result["production_credentials_created"] and not list(tmp_path.iterdir())
