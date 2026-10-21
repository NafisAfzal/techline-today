import pytest

from pipeline.models import StoryTranslation
from pipeline.tests.test_translation import example
from pipeline.translation import canonical_hash, validate_content
from pipeline.translation_fixtures import translated_fixture
from pipeline.translation_governance import integrity_findings


@pytest.mark.parametrize("control", ["\u061c", "\u200e", "\u200f", "\u202a", "\u202b", "\u202c",
                                    "\u202d", "\u202e", "\u2066", "\u2067", "\u2068", "\u2069"])
def test_hidden_direction_controls_rejected_at_ingress_and_review(now, control):
    story = example(now)
    original = translated_fixture(story)
    poisoned = original.model_copy(update={"headline": original.headline + control})
    with pytest.raises(ValueError, match="Unsafe Unicode"):
        validate_content(poisoned, story)
    translation = StoryTranslation(language="bn", content=poisoned, canonical_hash=canonical_hash(story),
                                   cache_key="a" * 64, provider="synthetic", model="test",
                                   generated_at=now, review_status="automated")
    assert any(row["check"] == "directional_controls" and row["severity"] == "fail"
               for row in integrity_findings(story, translation))


@pytest.mark.parametrize("joining", ["\u200c", "\u200d"])
def test_bangla_joining_controls_remain_available(now, joining):
    story = example(now)
    original = translated_fixture(story)
    content = original.model_copy(update={"headline": original.headline + joining})
    assert validate_content(content, story) == content
