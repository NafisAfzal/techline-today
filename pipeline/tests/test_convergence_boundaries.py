"""Independent integration regressions using only authored, isolated fixtures."""

import json
import shutil
from pathlib import Path

import pytest

from pipeline.models import StoryTranslation, TranslationContent
from pipeline.newsroom_readiness import newsroom_readiness
from pipeline.operations.observation import review_observations
from pipeline.operations.reports import console, observation_plan
from pipeline.recovery.fixtures import SYNTHETIC_NOW
from pipeline.tests.test_operations_observations import receipts
from pipeline.tests.test_translation import example
from pipeline.translation import DIRECTION_CONTROLS, canonical_hash
from pipeline.translation_fixtures import translated_fixture
from pipeline.translation_governance import integrity_findings


@pytest.mark.parametrize("control", sorted(DIRECTION_CONTROLS))
@pytest.mark.parametrize("field", ["headline", "number_labels", "number_contexts"])
def test_stored_translation_cannot_bypass_direction_validation(now, control, field):
    content = translated_fixture(example(now)).model_dump(mode="json")
    content[field] = content[field] + control if field == "headline" else ["synthetic" + control]
    with pytest.raises(ValueError, match="direction"):
        TranslationContent.model_validate(content)


@pytest.mark.parametrize("field", ["number_labels", "number_contexts"])
def test_review_checks_direction_controls_in_numeric_translation_fields(now, field):
    story = example(now)
    content = translated_fixture(story).model_copy(update={field: ["synthetic\u202e"]})
    translation = StoryTranslation(language="bn", content=content, canonical_hash=canonical_hash(story),
                                   cache_key="a" * 64, provider="synthetic", model="test", generated_at=now)
    assert any(f["check"] == "directional_controls" and f["severity"] == "fail"
               for f in integrity_findings(story, translation))


def test_console_propagates_actual_readiness_failure(tmp_path):
    source = Path(__file__).resolve().parents[2]
    (tmp_path / "config").mkdir()
    for name in ["source-research.json", "source-rights.json", "sources.yaml", "release.json",
                 "security-advisories.json"]:
        shutil.copyfile(source / "config" / name, tmp_path / "config" / name)
    path = tmp_path / "config/release.json"
    release = json.loads(path.read_text(encoding="utf-8"))
    release["schedule_enabled"] = True
    path.write_text(json.dumps(release), encoding="utf-8")
    result = console(tmp_path, now=SYNTHETIC_NOW)
    assert any(row["item"] == "security_configuration" and row["result"] == "FAIL"
               for row in result["sections"]["readiness"]["items"])
    assert not result["unreadable_sections"]
    assert result["status"] == "FAIL"
    assert "readiness" in result["failed_sections"]
    assert not result["publication_allowed"]


def test_receipt_directory_enumeration_is_not_a_clock_regression(tmp_path, monkeypatch):
    receipts(tmp_path)
    original = Path.glob

    def reversed_directory(self, pattern):
        found = list(original(self, pattern))
        return iter(sorted(found, reverse=True))

    # Directory enumeration has no ordering guarantee, including after restore.
    monkeypatch.setattr(Path, "glob", reversed_directory)
    result = review_observations(tmp_path, environment_id="synthetic-test", ledger_id="synthetic-ledger",
                                 now=SYNTHETIC_NOW)
    assert result["window"]["elapsed_window_satisfied"]
    assert not result["window"]["anomalies"]
    assert result["status"] == "BLOCKED" and result["genuinely_authenticated_days"] == 0


def test_observation_plan_reports_duplicate_evidence_as_failure(tmp_path):
    receipts(tmp_path, mutate=lambda row, index: row.update(run_id="copied-run"))
    report = observation_plan(tmp_path, now=SYNTHETIC_NOW)
    assert report["existing_window"]["anomalies"]
    assert report["status"] == "FAIL"
    assert report["genuinely_authenticated_days"] == 0 and not report["publication_allowed"]


def test_readiness_preserves_corrupt_observation_failure(tmp_path):
    directory = tmp_path / ".cache/phase4/observations"
    directory.mkdir(parents=True)
    (directory / "2026-10-19.json").write_bytes(b'{"corrupt":')
    report = newsroom_readiness(tmp_path, SYNTHETIC_NOW)
    coverage = next(row for row in report["items"] if row["item"] == "operational_observation_coverage")
    assert coverage["result"] == "FAIL"
    assert coverage["evidence"]["anomalies"] == [{"kind": "unreadable_observation_evidence"}]
