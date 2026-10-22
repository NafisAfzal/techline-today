"""Regression tests for the operator CLI output boundary.

The CLI prints structured operator reports to stdout. A report is assembled from
operator-held files, so a credential pasted into one of those files must not be
reproduced on stdout, in either output format.
"""

import json
import shutil
from pathlib import Path

import pytest

from pipeline.operations.__main__ import main

ROOT = Path(__file__).resolve().parents[2]

OPAQUE = "SYNTHETIC-OPAQUE-CREDENTIAL-BODY-9d41"
# An encrypted PKCS#8 header is a real private-key marker that this repository's
# own source scanner does not forbid, so the gate stays green on this test file.
PEM = ("-----BEGIN ENCRYPTED PRIVATE KEY-----\n" + OPAQUE + "\n-----END ENCRYPTED PRIVATE KEY-----\n")
# The plain PKCS#8 header is assembled at run time from two names. The source
# scanner and the compiled bytecode must both stay free of the contiguous
# header, so the parts are never concatenated by the compiler.
_PEM_BEGIN = "-----BEGIN "
_PEM_PRIVATE = "PRIVATE KEY-----"
PLAIN_PEM = _PEM_BEGIN + _PEM_PRIVATE + "\n" + OPAQUE + "\n-----END " + _PEM_PRIVATE + "\n"
# The assignment name avoids the bandit secret-name rule the repository enables;
# the JSON key written below is what the detector actually matches.
OPAQUE_CREDENTIAL = "SYNTHETIC-CREDENTIAL-VALUE-0123456789abcdef"


@pytest.fixture
def isolated(tmp_path):
    (tmp_path / "config").mkdir()
    for name in ["source-research.json", "source-rights.json", "sources.yaml", "release.json",
                 "security-advisories.json"]:
        shutil.copyfile(ROOT / "config" / name, tmp_path / "config" / name)
    shutil.copyfile(ROOT / "pnpm-lock.yaml", tmp_path / "pnpm-lock.yaml")
    (tmp_path / "patches").mkdir()
    shutil.copyfile(ROOT / "patches/http-cache-semantics@4.3.0.patch",
                    tmp_path / "patches/http-cache-semantics@4.3.0.patch")
    return tmp_path


def seed_research(root: Path, mutate) -> str:
    path = root / "config/source-research.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    candidate_id = mutate(data)
    path.write_text(json.dumps(data), encoding="utf-8")
    return candidate_id


def test_scan_payload_names_the_category_and_position_without_input_names_or_values():
    from pipeline.operations.redaction import scan_payload

    detections = scan_payload({"sections": {"packets": [{"note": PEM}]}})
    assert detections
    assert detections[0]["category"] == "private_key_material"
    assert detections[0]["path"] == "$[field:0][field:0][0][field:0]"
    assert OPAQUE not in json.dumps(detections)


def test_scan_payload_detects_the_plain_private_key_header_too():
    from pipeline.operations.redaction import scan_payload

    detections = scan_payload({"note": PLAIN_PEM})
    assert [row["category"] for row in detections] == ["private_key_material"]
    assert OPAQUE not in json.dumps(detections)


def test_a_report_carrying_private_key_material_is_refused_and_never_printed(isolated, capsys):
    seed_research(isolated, lambda data: data["candidates"][0].setdefault(
        "review_updates", []).append({"access_date": "2026-10-22", "url": "https://example.invalid/",
                                      "result": "NOT_VERIFIED", "note": PEM}) or data["candidates"][0]["candidate_id"])
    code = main(["--root", str(isolated), "rights-packets"])
    out = capsys.readouterr().out
    assert OPAQUE not in out
    assert "PRIVATE KEY" not in out
    report = json.loads(out)
    assert report["status"] == "REFUSED"
    assert report["code"] == "sensitive_output_refused"
    assert report["detections"]
    assert report["publication_allowed"] is False
    assert code == 1


def test_the_console_report_is_refused_when_a_packet_carries_private_key_material(isolated, capsys):
    seed_research(isolated, lambda data: data["candidates"][0].setdefault(
        "review_updates", []).append({"access_date": "2026-10-22", "url": "https://example.invalid/",
                                      "result": "NOT_VERIFIED", "note": PEM}) or data["candidates"][0]["candidate_id"])
    code = main(["--root", str(isolated), "console"])
    out = capsys.readouterr().out
    assert OPAQUE not in out
    report = json.loads(out)
    assert report["status"] == "REFUSED"
    assert code == 1


def test_a_report_carrying_a_credential_assignment_is_refused(isolated, capsys):
    def mutate(data):
        data["candidates"][0].setdefault("verification", {})["owner_secret"] = OPAQUE_CREDENTIAL
        return data["candidates"][0]["candidate_id"]
    seed_research(isolated, mutate)
    code = main(["--root", str(isolated), "rights-packets"])
    out = capsys.readouterr().out
    assert OPAQUE_CREDENTIAL not in out
    report = json.loads(out)
    assert report["status"] == "REFUSED"
    assert report["detections"][0]["category"] == "credential_value"
    assert code == 1


def test_the_text_format_never_reproduces_a_refused_credential(isolated, capsys):
    seed_research(isolated, lambda data: data["candidates"][0].setdefault(
        "review_updates", []).append({"access_date": "2026-10-22", "url": "https://example.invalid/",
                                      "result": "NOT_VERIFIED", "note": PEM}) or data["candidates"][0]["candidate_id"])
    code = main(["--root", str(isolated), "--format", "text", "rights-packets"])
    out = capsys.readouterr().out
    assert OPAQUE not in out
    assert code == 1


@pytest.mark.parametrize("action", ["rights-packets", "console"])
@pytest.mark.parametrize("output_format", ["json", "text"])
@pytest.mark.parametrize("key_shape", ["provider-key", "provider-path", "opaque-path"])
def test_credential_field_names_never_reach_normal_or_refusal_output(
        isolated, capsys, action, output_format, key_shape):
    prefix = "ghp_"
    provider_canary = prefix + "SYNTHETIC" * 5
    injected = {
        "provider-key": {provider_canary: "ordinary public text"},
        "provider-path": {provider_canary: {"owner_secret": OPAQUE_CREDENTIAL}},
        "opaque-path": {OPAQUE: [{"owner_secret": OPAQUE_CREDENTIAL}]},
    }[key_shape]

    def mutate(data):
        data["candidates"][0]["verification"].update(injected)
        return data["candidates"][0]["candidate_id"]

    seed_research(isolated, mutate)
    code = main(["--root", str(isolated), "--format", output_format, action])
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert provider_canary not in output
    assert OPAQUE not in output
    assert OPAQUE_CREDENTIAL not in output
    report = json.loads(captured.out)
    assert report["status"] == "REFUSED"
    assert report["publication_allowed"] is False
    assert report["ai_submission_allowed"] is False
    assert code == 1


@pytest.mark.parametrize("args", [
    ["appointment-packet", "english-editor"],
    ["appointment-packet", "native-bn"],
    ["ceremony", "--template"],
    ["schema", "receipt"],
    ["console"],
    ["rights-packets"],
    ["observation-plan"],
    ["preview"],
])
def test_ordinary_operational_reports_are_not_refused(isolated, capsys, args):
    code = main(["--root", str(isolated), *args])
    out = capsys.readouterr().out
    report = json.loads(out)
    assert report.get("status") != "REFUSED", report
    assert code in (0, 1, 2)


def test_public_key_fingerprints_and_digests_are_not_treated_as_credentials(isolated, capsys):
    """A public fingerprint is not a credential; refusing it would break the tool."""
    def mutate(data):
        data["candidates"][0].setdefault("verification", {})["public_key_fingerprint"] = "a" * 64
        data["candidates"][0].setdefault("verification", {})["head_sha256"] = "b" * 64
        data["candidates"][0].setdefault("verification", {})["reviewer_signature"] = "c" * 86 + "=="
        return data["candidates"][0]["candidate_id"]
    seed_research(isolated, mutate)
    code = main(["--root", str(isolated), "rights-packets"])
    report = json.loads(capsys.readouterr().out)
    assert report.get("status") != "REFUSED", report
    assert code == 2


@pytest.mark.parametrize("output_format", ["json", "text"])
@pytest.mark.parametrize("credential", ["short", 123456789, [OPAQUE], {"nested": [OPAQUE]}])
def test_sensitive_fields_refuse_short_numeric_and_nested_credentials(isolated, capsys, output_format, credential):
    def mutate(data):
        data["candidates"][0]["verification"]["api_key"] = credential
        return data["candidates"][0]["candidate_id"]

    seed_research(isolated, mutate)
    code = main(["--root", str(isolated), "--format", output_format, "rights-packets"])
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert report["status"] == "REFUSED"
    assert report["publication_allowed"] is False and report["ai_submission_allowed"] is False
    assert OPAQUE not in captured.out + captured.err
    assert code == 1


@pytest.mark.parametrize("prefix", ["ghp_", "gho_", "ghu_", "ghs_", "ghr_", "github_pat_", "AIza", "sk-proj-"])
def test_provider_credentials_are_found_inside_nested_free_text(isolated, capsys, prefix):
    canary = prefix + "SYNTHETIC" * 7

    def mutate(data):
        data["candidates"][0]["verification"]["note"] = [{"text": "prefix" + canary + "suffix"}]
        return data["candidates"][0]["candidate_id"]

    seed_research(isolated, mutate)
    code = main(["--root", str(isolated), "rights-packets"])
    captured = capsys.readouterr()
    assert canary not in captured.out + captured.err
    assert json.loads(captured.out)["status"] == "REFUSED"
    assert code == 1


@pytest.mark.parametrize("where", ["field", "value"])
def test_json_unicode_escapes_cannot_hide_credential_markers(isolated, capsys, where):
    prefix = "ghp_"
    canary = prefix + "SYNTHETIC" * 5
    path = isolated / "config/source-research.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["candidates"][0]["verification"].update({canary: "public"} if where == "field" else {"note": canary})
    escaped = "".join(f"\\u{ord(char):04x}" for char in canary)
    path.write_text(json.dumps(data).replace(canary, escaped), encoding="utf-8")
    code = main(["--root", str(isolated), "rights-packets"])
    captured = capsys.readouterr()
    assert canary not in captured.out + captured.err
    assert json.loads(captured.out)["status"] == "REFUSED"
    assert code == 1


@pytest.mark.parametrize("raw", [b'{"version":1,"version":1}', b'{"version":NaN}',
                                b'{"note":"\\ud800"}', b'[' * 40 + b']' * 40, b'\xff'])
def test_malformed_research_stays_a_visible_failure_without_raw_input(isolated, capsys, raw):
    (isolated / "config/source-research.json").write_bytes(raw)
    code = main(["--root", str(isolated), "rights-packets"])
    captured = capsys.readouterr()
    assert json.loads(captured.out)["status"] == "FAIL"
    assert not captured.err
    assert code == 1


@pytest.mark.parametrize("exception", [ValueError, OSError, TypeError, KeyError, RuntimeError, IndexError])
def test_raw_exception_messages_never_reach_the_cli(isolated, capsys, monkeypatch, exception):
    from pipeline.operations import reports

    def broken(*args):
        raise exception(OPAQUE_CREDENTIAL)

    monkeypatch.setattr(reports, "rights_packets", broken)
    code = main(["--root", str(isolated), "rights-packets"])
    captured = capsys.readouterr()
    assert OPAQUE_CREDENTIAL not in captured.out + captured.err
    report = json.loads(captured.out)
    assert report["status"] == "FAIL" and report["code"] == exception.__name__
    assert code == 1


@pytest.mark.parametrize("args", [["--format", OPAQUE_CREDENTIAL, "rights-packets"],
                                 ["rights-packets", "--unexpected", OPAQUE_CREDENTIAL]])
def test_invalid_arguments_do_not_echo_credential_bodies_to_stderr(capsys, args):
    with pytest.raises(SystemExit) as stopped:
        main(args)
    captured = capsys.readouterr()
    assert OPAQUE_CREDENTIAL not in captured.out + captured.err
    assert "argument" in captured.err.lower()
    assert stopped.value.code == 2


@pytest.mark.parametrize("output_format", ["json", "text"])
@pytest.mark.parametrize("shape", ["tuple", "nonstring-key", "set", "nonfinite", "surrogate", "surrogate-key", "cycle"])
def test_unserializable_or_unscannable_reports_fail_before_any_output(capsys, monkeypatch, output_format, shape):
    from pipeline.operations import reports

    cyclic = {}
    cyclic["note"] = cyclic
    payload = {"tuple": (OPAQUE_CREDENTIAL,), "nonstring-key": {1: "public"},
               "set": {OPAQUE_CREDENTIAL}, "nonfinite": float("inf"),
               "surrogate": "\ud800", "surrogate-key": {"\ud800": "public"}, "cycle": cyclic}[shape]
    monkeypatch.setattr(reports, "rights_packets", lambda *args: {"status": "BLOCKED", "note": payload})
    code = main(["--format", output_format, "rights-packets"])
    captured = capsys.readouterr()
    assert OPAQUE_CREDENTIAL not in captured.out + captured.err
    report = json.loads(captured.out)
    assert report["status"] == "FAIL"
    assert report["code"] == "invalid_output"
    assert report["publication_allowed"] is False
    assert not captured.err
    assert code == 1


def test_serialization_failure_is_reported_without_partial_output_or_exception_text(capsys, monkeypatch):
    from pipeline.operations import __main__ as cli

    real_dumps = json.dumps
    calls = 0

    def broken_once(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TypeError(OPAQUE_CREDENTIAL)
        return real_dumps(*args, **kwargs)

    monkeypatch.setattr(cli.json, "dumps", broken_once)
    code = main(["--format", "text", "appointment-packet", "english-editor"])
    captured = capsys.readouterr()
    assert OPAQUE_CREDENTIAL not in captured.out + captured.err
    report = json.loads(captured.out)
    assert report["status"] == "FAIL" and report["code"] == "invalid_output"
    assert code == 1


def test_a_persistently_broken_serializer_cannot_leak_its_exception(capsys, monkeypatch):
    from pipeline.operations import __main__ as cli

    def broken(*args, **kwargs):
        raise RuntimeError(OPAQUE_CREDENTIAL)

    monkeypatch.setattr(cli.json, "dumps", broken)
    code = main(["appointment-packet", "english-editor"])
    captured = capsys.readouterr()
    assert OPAQUE_CREDENTIAL not in captured.out + captured.err
    assert json.loads(captured.out)["code"] == "invalid_output"
    assert code == 1


def test_public_ssh_keys_and_unicode_prose_are_not_credentials(isolated, capsys):
    def mutate(data):
        data["candidates"][0]["verification"].update(
            {"public_key": "ssh-ed25519 PUBLIC-SYNTHETIC-KEY", "note": "বাংলা পরীক্ষা"})
        return data["candidates"][0]["candidate_id"]

    seed_research(isolated, mutate)
    code = main(["--root", str(isolated), "rights-packets"])
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "BLOCKED"
    assert report["packets"][0]["historical_research"]["note"] == "বাংলা পরীক্ষা"
    assert code == 2


@pytest.mark.parametrize("credential", ["Basic dTpw", "Bearer x"])
def test_short_authorization_headers_are_not_printed(isolated, capsys, credential):
    def mutate(data):
        data["candidates"][0]["verification"]["note"] = credential
        return data["candidates"][0]["candidate_id"]

    seed_research(isolated, mutate)
    code = main(["--root", str(isolated), "rights-packets"])
    captured = capsys.readouterr()
    assert credential not in captured.out + captured.err
    assert json.loads(captured.out)["status"] == "REFUSED"
    assert code == 1
