from datetime import timedelta

import pytest
from pydantic import ValidationError

from pipeline.digests import build_digests
from pipeline.models import AnnouncedEvent, Fact, ModelRelease, Offer
from pipeline.storage import compact
from pipeline.tests.test_quality import make_story


def test_naive_offer_time_rejected(now):
    with pytest.raises(ValidationError, match="Timezone-aware"):
        Offer(id="test", provider="Test", title="Offer", offer_type="trial", value_text="Limited", eligibility=[], regions=[], card_required=None,
              claim_steps=[], last_verified_at=now.replace(tzinfo=None), status="active", official_source_url="https://example.com/terms", source_ids=["s"], integration_notes="Unknown")


def test_unknown_model_terms_are_null_in_public_contract(now):
    import jsonschema

    release = ModelRelease(id="model", story_id="story", provider="Publisher", model="Announcement",
                           release_date=now, modality=[], key_change="Announcement", source_ids=["source"])
    payload = release.model_dump(mode="json")
    assert payload["pricing"] is None and payload["context_window"] is None and payload["api_available"] is None
    jsonschema.validate(payload, ModelRelease.model_json_schema())


def test_watch_next_only_future_related_events(items, now):
    story = make_story(items[0], now)
    fact = Fact(text="Announced developer briefing", source_ids=story.source_ids, attribution="primary")
    future = AnnouncedEvent(at=now+timedelta(days=1), evidence_date_text="Tomorrow", fact=fact)
    past = future.model_copy(update={"at":now-timedelta(days=1)})
    unrelated = future.model_copy(update={"fact":fact.model_copy(update={"source_ids":["unrelated"]})})
    digest = build_digests([story], now, announced_events=[future,past,unrelated])[0]
    assert digest.watch_next == [fact]


def test_budget_compaction_and_year_index(tmp_path, items, now):
    stories = [make_story(item,now) for item in items[:3]]
    active, index = compact(stories,{item.id:item for item in items},tmp_path,now,{"retain_individual_days":548,"max_individual_stories":2},[])
    assert len(active)==2 and index[0]['count']==1
    assert (tmp_path/'content/archives/2026.json').exists()
