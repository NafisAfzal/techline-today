from pathlib import Path

import pytest
from pydantic import ValidationError

from pipeline.ai import AIMetadata, AIRouter, evidence_hash, extractive
from pipeline.fixtures import fixture_data
from pipeline.models import Story, StoryTranslation, TranslationContent
from pipeline.runner import config
from pipeline.translation import (
    cache_key,
    canonical_hash,
    translate_stories,
    validate_content,
    validate_translation,
)
from pipeline.translation_fixtures import translated_fixture


def example(now, category="ai"):
    item = next(item for item in fixture_data(now) if item.category == category)
    summary = extractive([item])
    return Story(**summary.model_dump(), id="story_example", slug="example-story", canonical_topic="example",
                 source_ids=[item.id], primary_source_id=item.id, evidence_state="primary-confirmed",
                 published_at=now, first_seen_at=now, updated_at=now, last_verified_at=now,
                 importance_score_internal=0.5, change_log=[], is_demo=True,
                 ai_metadata=AIMetadata(evidence_hash=evidence_hash([item], config("ai"))))


@pytest.mark.parametrize("category", ["ai", "research", "chips", "security", "freebies"])
def test_authored_examples_preserve_evidence(now, category):
    story = example(now, category)
    content = translated_fixture(story)
    assert content and validate_content(content, story)
    assert content.headline != story.headline
    assert len(content.key_fact_texts) == len(story.key_facts)


@pytest.mark.parametrize("field,value", [
    ("headline", ""), ("headline", "Meridian model release"), ("headline", "<script>খবর</script>"),
    ("headline", "খবর \ufffd ত্রুটি"), ("headline", "খবর \ud800 ত্রুটি"),
    ("headline", "খবর \x00 ত্রুটি"), ("headline", "Meridian " + "অ" * 300),
    ("headline", "নতুন model প্রকাশ করেছে একটি প্রতিষ্ঠান"),
    ("summary_bullets", ["খবর প্রকাশ হয়েছে।"]),
])
def test_invalid_translation_rejected(now, field, value):
    story = example(now)
    payload = translated_fixture(story).model_dump()
    payload[field] = value
    with pytest.raises((ValueError, ValidationError)):
        validate_content(TranslationContent.model_validate(payload), story)


def test_removed_or_added_numbers_and_units_rejected(now):
    story = example(now)
    original = translated_fixture(story)
    for replacement in ["", "256K", "128", "128K 42"]:
        bad = original.model_copy(update={"summary_bullets": [text.replace("128K", replacement)
                                                             for text in original.summary_bullets]})
        with pytest.raises(ValueError, match="numbers"):
            validate_content(bad, story)


def test_uncertainty_and_accidental_identical_output_rejected(now):
    story = example(now, "research")
    original = translated_fixture(story)
    bad = original.model_copy(update={"summary_bullets": [*original.summary_bullets[:2],
                                                          "অন্য গবেষকেরা স্বাধীনভাবে ফলাফল পুনরায় পরীক্ষা করেছেন।"]})
    with pytest.raises(ValueError, match="uncertainty"):
        validate_content(bad, story)
    bad = original.model_copy(update={"headline": story.headline})
    with pytest.raises(ValueError):
        validate_content(bad, story)


def test_translation_cache_invalidates_content_evidence_prompt_and_language(now):
    story = example(now)
    key = cache_key(story, "prompt")
    assert key != cache_key(story, "new prompt")
    assert key != cache_key(story, "prompt", "future-locale")
    assert key != cache_key(story.model_copy(update={"headline": "A changed verified headline"}), "prompt")
    changed = story.model_copy(update={"ai_metadata": story.ai_metadata.model_copy(update={"evidence_hash": "different"})})
    assert key != cache_key(changed, "prompt")


class TranslationProvider:
    id = "fake"
    model = "test"
    daily_call_limit = 3

    def __init__(self, payload=None):
        self.payload, self.calls = payload, 0

    async def generate_structured(self, request):
        self.calls += 1
        assert "untrusted" in request["messages"][0]["content"]
        assert "CANONICAL_STORY" in request["messages"][1]["content"]
        assert "tools" not in request
        if self.payload is None:
            raise ValueError("Provider unavailable")
        return {"summary": self.payload, "tokens": 10}


def router(providers):
    settings = {**config("ai"), "max_retries": 0}
    settings["translation"] = {**settings["translation"], "provider_ids": ["fake"]}
    return AIRouter(providers, settings, {}, Path("prompts/story_summary.md")), settings


async def test_no_provider_english_fallback_and_fixture_isolation(now):
    story = example(now)
    routing, settings = router([])
    report, cache = await translate_stories([story], routing, settings, {}, Path("prompts/story_translation.md"), now)
    assert not story.translations and report["unavailable"] == 1 and not cache
    report, cache = await translate_stories([story], routing, settings, {}, Path("prompts/story_translation.md"), now, fixture=True)
    assert story.translations["bn"].review_status == "fixture-reviewed" and report["available"] == 1
    # A fixture cache must never become a live publication's translation.
    report, _ = await translate_stories([story], routing, settings, cache, Path("prompts/story_translation.md"), now)
    assert not story.translations and report["unavailable"] == 1


async def test_denied_submission_never_calls_capable_translation_provider(now):
    story = example(now)
    provider = TranslationProvider(translated_fixture(story).model_dump())
    routing, settings = router([provider])
    assert settings["translation"]["enabled"]
    report, cache = await translate_stories([story], routing, settings, {},
        Path("prompts/story_translation.md"), now, eligible_story_ids=set())
    assert provider.calls == 0 and not story.translations and not cache
    assert report["unavailable"] == 1


async def test_valid_provider_translation_is_cached_without_further_calls(now):
    story = example(now)
    provider = TranslationProvider(translated_fixture(story).model_dump())
    routing, settings = router([provider])
    report, cache = await translate_stories([story], routing, settings, {}, Path("prompts/story_translation.md"), now)
    assert report["generated"] == 1 and provider.calls == 1
    translation = story.translations["bn"]
    assert translation.canonical_hash == canonical_hash(story)
    assert validate_translation(translation, story)
    report, _ = await translate_stories([story], routing, settings, cache, Path("prompts/story_translation.md"), now)
    assert report["cached"] == 1 and provider.calls == 1


async def test_failure_is_per_story_and_retry_is_bounded(now):
    stories = [example(now), example(now, "security")]
    provider = TranslationProvider(translated_fixture(stories[1]).model_dump())
    routing, settings = router([provider])
    report, cache = await translate_stories(stories, routing, settings, {}, Path("prompts/story_translation.md"), now)
    assert report["failed"] == 1 and report["generated"] == 1
    assert not stories[0].translations and stories[1].translations
    calls = provider.calls
    report, _ = await translate_stories(stories, routing, settings, cache, Path("prompts/story_translation.md"), now)
    assert provider.calls == calls and report["cached"] == 1
    assert routing.state["fake"]["calls"] == calls


async def test_invalid_cache_and_budget_do_not_publish_translation(now):
    story = example(now)
    provider = TranslationProvider(translated_fixture(story).model_dump())
    routing, settings = router([provider])
    settings["translation"]["max_stories_per_run"] = 0
    key = cache_key(story, Path("prompts/story_translation.md").read_text(encoding="utf-8"))
    report, _ = await translate_stories([story], routing, settings, {key: {"translation": {}}},
                                        Path("prompts/story_translation.md"), now)
    assert report["unavailable"] == 1 and not story.translations and provider.calls == 0


def test_stale_translation_rejected(now):
    story = example(now)
    translation = StoryTranslation(language="bn", content=translated_fixture(story), canonical_hash="0" * 64,
                                   cache_key="0" * 64, provider="fake", model="test", generated_at=now)
    with pytest.raises(ValueError, match="stale"):
        validate_translation(translation, story)
