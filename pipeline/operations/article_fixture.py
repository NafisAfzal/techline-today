"""Authored in-memory article for explicit synthetic authority-mode gates only.

It is never a snapshot, an ingestion result or a production publication record.
"""

import asyncio
from datetime import timedelta

import httpx

from pipeline.adapters import RSSAdapter
from pipeline.models import (
    AIMetadata,
    Change,
    Fact,
    SourceConfig,
    Story,
    StoryTranslation,
    TranslationContent,
)
from pipeline.normalize import normalize
from pipeline.recovery.fixtures import SYNTHETIC_NOW
from pipeline.security import SafeFetcher
from pipeline.translation import canonical_hash


async def ingest_metadata():
    """Authored RSS bytes through existing transport/parser/normalization only."""
    source = SourceConfig(id="news-wire", name="Synthetic rehearsal publisher", adapter="rss",
                          source_class="primary", endpoint="https://example.com/synthetic-feed",
                          allowed_hosts=["example.com"], categories=["ai"], independence_group="synthetic",
                          terms_url="https://example.com/synthetic-permission", enabled=False)
    xml = (b'<rss version="2.0"><channel><title>Synthetic offline feed</title><item>'
           b'<title>Synthetic offline newsroom exercise</title><link>https://example.com/synthetic</link>'
           b'<description>Authored synthetic evidence for an isolated rehearsal.</description>'
           b'<pubDate>Mon, 19 Oct 2026 23:00:00 GMT</pubDate></item></channel></rss>')
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(
            200, content=xml, headers={"content-type": "application/rss+xml"}))) as client:
        raw = await RSSAdapter().fetch(source, SafeFetcher(client, {}, "TechlineSyntheticRehearsal"))
    return normalize(raw[0], source, SYNTHETIC_NOW)


def article():
    at = SYNTHETIC_NOW - timedelta(hours=1)
    source = asyncio.run(ingest_metadata())
    sid = source.id
    bullets = ["First authored synthetic observation for the rehearsal.",
               "Second authored synthetic observation for the rehearsal.",
               "Third authored synthetic observation for the rehearsal."]
    facts = [Fact(text=b, source_ids=[sid], attribution="primary") for b in bullets]
    story = Story(id="story-one", slug="synthetic-rehearsal-story", canonical_topic="synthetic",
                  source_ids=[sid], primary_source_id=sid, evidence_state="primary-confirmed",
                  published_at=at, first_seen_at=at, updated_at=at, last_verified_at=at,
                  importance_score_internal=0.5, change_log=[Change(at=at, text="Synthetic initial evidence.",
                                                                               source_ids=[sid])],
                  ai_metadata=AIMetadata(evidence_hash="c" * 64), headline="Synthetic offline newsroom exercise",
                  summary_bullets=bullets, why_it_matters="Exercises the existing composite gate offline.",
                  broader_summary="Authored test prose; never a real current-news article.",
                  key_facts=facts, claim_map=facts, category="ai")
    rights = {"news-wire": {"publication": "allow", "license": "SYNTHETIC-ONLY",
                            "license_url": "https://example.com/synthetic-permission",
                            "scope": "Isolated authored test prose; not a publisher grant"}}
    return story, {sid: source}, rights


def bangla_fixture(story):
    """Authored test text only; no native quality claim or provider call."""
    content = TranslationContent(
        headline="সিন্থেটিক সংবাদকক্ষের পরীক্ষামূলক অনুশীলন",
        summary_bullets=["প্রথম পরীক্ষামূলক তথ্য।", "দ্বিতীয় পরীক্ষামূলক তথ্য।", "তৃতীয় পরীক্ষামূলক তথ্য।"],
        why_it_matters="এটি শুধু সফটওয়্যার পরীক্ষার অনুশীলন।",
        broader_summary="এটি বাস্তব সংবাদ বা অনুমোদিত অনুবাদ নয়।",
        key_fact_texts=["প্রথম পরীক্ষামূলক তথ্য।", "দ্বিতীয় পরীক্ষামূলক তথ্য।", "তৃতীয় পরীক্ষামূলক তথ্য।"])
    translation = StoryTranslation(language="bn", content=content, canonical_hash=canonical_hash(story),
                                   cache_key="a" * 64, provider="synthetic-offline", model="authored-test-fixture",
                                   generated_at=SYNTHETIC_NOW, review_status="automated")
    return story.model_copy(update={"translations": {"bn": translation}})
