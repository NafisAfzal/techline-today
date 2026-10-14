"""Cached publication-time translations. English evidence remains authoritative."""
import hashlib
import json
import re
import unicodedata
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from pipeline.models import StoryTranslation, TranslationContent

POLICY_VERSION = "1"
DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
NUMBERS = re.compile(r"[$€£]?[-+]?\d+(?:[,.]\d+)*(?:\s?(?:GB|MB|TB|GHz|MHz|nm|Wh|mAh)|[KkMmBb%])?")
TERMS = re.compile(r"\b(?:CUDA|GPU|CPU|API|H100|GPT(?:-\w+)*|Gemini|Claude|Llama|NVIDIA|Cloudflare|"
                   r"[A-Za-z]+[-/]?\d[\w./-]*|[A-Z][a-z]+[A-Z]\w*)\b")
UNCERTAINTY = (
    (r"\b(may|could|might)\b", r"হতে পারে|পারতে পারে|সম্ভব|সম্ভাব|পারেন|পারে"),
    (r"\bclaim(?:s|ed)?\b", r"দাবি"),
    (r"\breport(?:s|ed)?\b", r"জানিয়|জানিয়ে|প্রতিবেদন|বলেছে|অনুযায়ী"),
    (r"\bpreliminary\b", r"প্রাথমিক"),
    (r"\bnot\b|\bunknown\b|\bunavailable\b", r"না|নেই|অজানা|পাওয়া যায়নি|করেননি|হয়নি"),
)


def canonical_content(story):
    return {"headline": story.headline, "summary_bullets": story.summary_bullets,
            "why_it_matters": story.why_it_matters, "broader_summary": story.broader_summary,
            "key_fact_texts": [fact.text for fact in story.key_facts],
            "number_labels": [number.label for number in story.key_numbers],
            "number_contexts": [number.context for number in story.key_numbers], "limitations": story.limitations}


def canonical_hash(story):
    value = {"content": canonical_content(story), "evidence_hash": story.ai_metadata.evidence_hash,
             "source_ids": story.source_ids, "facts": [(fact.source_ids, fact.status) for fact in story.key_facts]}
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def cache_key(story, prompt, language="bn"):
    value = {"canonical": canonical_hash(story), "prompt": prompt, "language": language,
             "schema": TranslationContent.model_json_schema(), "policy": POLICY_VERSION}
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def validate_content(content, story):
    canonical = canonical_content(story)
    translated = content.model_dump()
    if not re.search(r"[\u0980-\u09ff]", content.headline):
        raise ValueError("Headline must contain Bangla")
    # Keep known proper names, plus the named subject of a fixture/announcement.
    names = set(story.entities) | set(TERMS.findall(" ".join([story.headline, *story.summary_bullets])))
    subject = story.headline.split()[0]
    if subject[:1].isupper() and subject not in {"A", "An", "The", "New", "How", "What", "Why", "Toward", "From", "Only", "Archive"}:
        names.add(subject)
    for key, original in canonical.items():
        values = translated[key]
        originals = original if isinstance(original, list) else [original]
        values = values if isinstance(values, list) else [values]
        if len(originals) != len(values):
            raise ValueError(f"Translation changed array length: {key}")
        for source, target in zip(originals, values, strict=True):
            if not target.strip() or len(target) > max(180, len(source) * 3) or len(target) > 2700:
                raise ValueError("Empty or excessive translation")
            if target.strip() == source.strip() and re.search(r"[A-Za-z]{3}", source):
                raise ValueError("Accidental identical translation")
            if (re.search(r"[<>\ufffd\ud800-\udfff]", target)
                    or any(unicodedata.category(char) == "Cc" for char in target)
                    or any(marker in target for marker in ("Ã", "Â", "à¦", "à§", "â€"))):
                raise ValueError("Unsafe Unicode or unexpected HTML")
            def numbers(text):
                return Counter(token.replace(",", "").replace(" ", "")
                               for token in NUMBERS.findall(text.translate(DIGITS)))
            if numbers(source) != numbers(target):
                raise ValueError("Translation changed numbers or units")
            for name in names:
                if name in source and name not in target:
                    raise ValueError("Translation removed a product/model name")
            for english, bangla in UNCERTAINTY:
                if re.search(english, source, re.I) and not re.search(bangla, target):
                    raise ValueError("Translation removed detectable uncertainty")
    if len(set(content.summary_bullets)) != 3:
        raise ValueError("Translation duplicated summary bullets")
    return content


def validate_translation(translation, story):
    if translation.canonical_hash != canonical_hash(story):
        raise ValueError("Translation is stale for this evidence")
    return validate_content(translation.content, story)


async def translate_stories(stories, router, settings, cache, prompt: Path, now, fixture=False, eligible_story_ids=None):
    policy = settings.get("translation", {})
    prompt_text = prompt.read_text(encoding="utf-8")
    report = {"available": 0, "cached": 0, "generated": 0, "failed": 0, "unavailable": 0}
    attempts = 0
    retained_cache = {}
    for story in stories:
        # Never retain a translation after canonical content or evidence changes.
        story.translations = {}
        key = cache_key(story, prompt_text)
        record = cache.get(key)
        if not isinstance(record, dict):
            record = None
        if record and "translation" in record:
            try:
                translation = StoryTranslation.model_validate(record["translation"])
                validate_translation(translation, story)
                if translation.cache_key != key or (not fixture and translation.review_status == "fixture-reviewed"):
                    raise ValueError("Invalid translation cache entry")
                story.translations["bn"] = translation
                retained_cache[key] = record
                report["cached"] += 1
                report["available"] += 1
                continue
            except (ValueError, TypeError, KeyError):
                pass
        if fixture:
            from pipeline.translation_fixtures import translated_fixture
            content = translated_fixture(story)
            if content:
                validate_content(content, story)
                translation = StoryTranslation(language="bn", content=content, canonical_hash=canonical_hash(story),
                                               cache_key=key, provider="fixture", model="reviewed-examples",
                                               generated_at=now, review_status="fixture-reviewed")
                story.translations["bn"] = translation
                retained_cache[key] = {"translation": translation.model_dump(mode="json")}
                report["available"] += 1
            else:
                report["unavailable"] += 1
            continue
        retry_wait = False
        if record and "failed_at" in record:
            try:
                failed_at = datetime.fromisoformat(record["failed_at"])
                retry_wait = 0 <= (now - failed_at).total_seconds() < policy.get("retry_after_seconds", 21600)
            except (ValueError, TypeError):
                pass
        if retry_wait:
            retained_cache[key] = record
        providers = set(policy.get("provider_ids", []))
        capable = any(provider.id in providers for provider in router.providers)
        if ((eligible_story_ids is not None and story.id not in eligible_story_ids)
                or not policy.get("enabled") or "bn" not in policy.get("target_languages", []) or not capable
                or retry_wait or attempts >= policy.get("max_stories_per_run", 20)):
            report["unavailable"] += 1
            continue
        attempts += 1
        request = {"messages": [{"role": "system", "content": prompt_text + "\nSCHEMA\n" +
                                 json.dumps(TranslationContent.model_json_schema())},
                                {"role": "user", "content": "CANONICAL_STORY\n" +
                                 json.dumps(canonical_content(story), ensure_ascii=False)}],
                   "max_tokens": policy.get("max_output_tokens", 3000)}
        try:
            result = await router.generate_validated(request, lambda payload, canonical=story: validate_content(
                TranslationContent.model_validate(payload), canonical), provider_ids=providers)
            if result:
                content, provider = result
                translation = StoryTranslation(language="bn", content=content, canonical_hash=canonical_hash(story),
                                               cache_key=key, provider=provider.id, model=provider.model,
                                               generated_at=now)
                story.translations["bn"] = translation
                retained_cache[key] = {"translation": translation.model_dump(mode="json")}
                report["generated"] += 1
                report["available"] += 1
                continue
        except Exception:
            # Isolate this story; never log provider exception strings or publish invalid output.
            result = None
        retained_cache[key] = {"failed_at": now.astimezone(UTC).isoformat()}
        report["failed"] += 1
        report["unavailable"] += 1
    return report, retained_cache
