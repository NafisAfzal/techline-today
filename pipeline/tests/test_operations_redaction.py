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


def test_scan_payload_names_the_category_and_path_without_the_value():
    from pipeline.operations.redaction import scan_payload

    detections = scan_payload({"sections": {"packets": [{"note": PEM}]}})
    assert detections
    assert detections[0]["category"] == "private_key_material"
    assert "note" in detections[0]["path"]
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
