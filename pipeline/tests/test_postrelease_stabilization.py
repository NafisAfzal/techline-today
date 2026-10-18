"""Regressions for lexical path safety and controlled recovery refusals."""

import json
import subprocess
import sys

import pytest

from pipeline import generation
from pipeline.filesystem import confined_file, regular_path
from pipeline.tests.test_release_completion import interrupted


@pytest.mark.parametrize("name", [
    "content/trailing.", "content/trailing ", "content/parent./child.json",
    "content/parent /child.json", "trailing.", "trailing ",
    "content/CON", "content/aux.txt", "content/PRN.json", "content/NUL",
    "content/com1.json", "content/LPT9.log", "content/COM¹.txt", "content/LPT²",
])
def test_unsafe_lexical_names_refuse_before_os_normalization(tmp_path, name):
    with pytest.raises(ValueError, match="^Unsafe or reserved filesystem name$"):
        confined_file(tmp_path, name)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("name", ["trailing.", "trailing ", "CON", "aux.txt"])
def test_regular_path_rejects_relative_first_component(name):
    with pytest.raises(ValueError, match="^Unsafe or reserved filesystem name$"):
        regular_path(name)


def test_unsafe_root_is_not_silently_normalized(tmp_path):
    with pytest.raises(ValueError, match="Unsafe or reserved"):
        confined_file(tmp_path / "root. ", "content/snapshot.json")
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("name", ["content/console.json", "content/auxiliary.txt", "content/COM10.txt"])
def test_ordinary_cross_platform_names_remain_valid(tmp_path, name):
    assert confined_file(tmp_path, name) == tmp_path / name


@pytest.mark.parametrize("action", ["finish", "rollback"])
def test_repeated_recovery_is_a_typed_refusal_without_writes(tmp_path, monkeypatch, action):
    snapshot, state = interrupted(tmp_path, monkeypatch)
    with generation.writer(tmp_path):
        generation.recover(tmp_path, action)
    before = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    with generation.writer(tmp_path), pytest.raises(generation.NoPendingGeneration, match="No pending generation"):
        generation.recover(tmp_path, action)
    after = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert before == after
    assert snapshot.read_bytes() in {b"old snapshot", b"new snapshot"}
    assert state.read_bytes() in {b"old state", b"new state"}


@pytest.mark.parametrize("action", ["finish", "rollback"])
def test_cli_reports_no_pending_generation_without_traceback(tmp_path, action):
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pipeline.generation", action, "--root", str(tmp_path)],
        capture_output=True, text=True, check=False, timeout=20,
    )
    assert result.returncode == 1
    assert json.loads(result.stdout) == {"status": "NO_PENDING_GENERATION", "action": action,
                                       "recovery_performed": False, "publication_performed": False}
    assert not result.stderr
    assert not (tmp_path / generation.LOCK).exists()
    assert not (tmp_path / "content").exists()


def test_corrupt_journal_is_not_misreported_as_no_pending_work(tmp_path):
    journal = tmp_path / generation.JOURNAL
    journal.parent.mkdir()
    journal.write_bytes(b"{corrupt")
    with generation.writer(tmp_path), pytest.raises(ValueError) as error:
        generation.recover(tmp_path, "finish")
    assert not isinstance(error.value, generation.NoPendingGeneration)
    assert journal.read_bytes() == b"{corrupt"
