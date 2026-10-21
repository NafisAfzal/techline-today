from concurrent.futures import ThreadPoolExecutor

import pytest

from pipeline.recovery import verify
from pipeline.tests.test_phase10_recovery import newsroom, pin_file


def pack(tmp_path):
    room = newsroom(tmp_path)
    path = tmp_path / "pack"
    verify.build_recovery_pack(room.root, path, trust_file=pin_file(tmp_path))
    return path


def tree(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def expected_restore(archive):
    # The manifest authenticates transport; the restore contract installs only
    # its listed payloads, not another recovery-pack manifest in the destination.
    expected = tree(archive)
    expected.pop("manifest.json")
    return expected


def test_restore_interruption_preserves_partial_evidence_and_requires_new_destination(tmp_path, monkeypatch):
    archive = pack(tmp_path)
    target = tmp_path / "interrupted"
    fsync = verify.os.fsync

    def interrupted(fd):
        raise OSError("Synthetic interruption during destination sync")
    monkeypatch.setattr(verify.os, "fsync", interrupted)
    with pytest.raises(OSError, match="Synthetic interruption"):
        verify.restore_recovery_pack(archive, target)
    partial = tree(target)
    assert partial
    monkeypatch.setattr(verify.os, "fsync", fsync)
    with pytest.raises(ValueError, match="new empty destination"):
        verify.restore_recovery_pack(archive, target)
    assert tree(target) == partial
    fresh = tmp_path / "fresh"
    verify.restore_recovery_pack(archive, fresh)
    assert tree(fresh) == expected_restore(archive)
    result = verify.verify_recovery_pack(archive)
    assert result.current is False and result.independently_trusted is False


def test_concurrent_restore_has_one_winner_and_repeat_is_nonmutating(tmp_path):
    archive = pack(tmp_path)
    target = tmp_path / "destination"

    def restore():
        try:
            verify.restore_recovery_pack(archive, target)
            return "restored"
        except (ValueError, FileExistsError):
            return "refused"
    with ThreadPoolExecutor(max_workers=2) as workers:
        outcomes = list(workers.map(lambda _: restore(), range(2)))
    assert sorted(outcomes) == ["refused", "restored"]
    before = tree(target)
    assert before == expected_restore(archive)
    assert restore() == "refused" and tree(target) == before
