from datetime import timedelta

import pytest
from pydantic import ValidationError

from pipeline.ai import evidence_hash, extractive
from pipeline.dedupe import cluster, deduplicate, simhash
from pipeline.digests import build_digests, period_bounds
from pipeline.models import AIMetadata, Change, Offer, Story, safe_url
from pipeline.normalize import canonicalize, classify, clean_text, discovery_relevant, normalize, parse_date
from pipeline.ranking import novelty, rank
from pipeline.runner import config, is_model_announcement
from pipeline.security import public_addresses
from pipeline.storage import compact
from pipeline.verification import conflicts, evidence_state, offer_status, validate_summary


@pytest.mark.parametrize("url", ["http://example.com", "https://localhost", "https://127.0.0.1/", "https://10.0.0.1/", "https://[::1]/", "https://169.254.169.254/", "https://user:pass@example.com", "file:///etc/passwd", "https://example.com:8080", "https://private.local/", "https://224.0.0.1/", "https://[ff02::1]/", "https://[fec0::1]/"])
def test_unsafe_urls(url):
    with pytest.raises(ValueError):
        safe_url(url)


def test_canonicalization_preserves_semantic_query():
    assert canonicalize("https://EXAMPLE.com/path?utm_source=x&id=42&fbclid=y&mode=full#ref") == "https://example.com/path?id=42&mode=full"
    assert canonicalize("https://example.com?id=42") != canonicalize("https://example.com?id=43")


def test_private_dns_and_mixed_answers_rejected():
    for values in (["10.0.0.1"], ["8.8.8.8", "127.0.0.1"], [], ["::ffff:127.0.0.1"], ["224.0.0.1"], ["ff02::1"], ["8.8.8.8", "fec0::1"]):
        with pytest.raises(ValueError):
            public_addresses(values)
    assert public_addresses(["8.8.8.8"]) == ["8.8.8.8"]
    assert public_addresses(["2001:4860:4860::8888"]) == ["2001:4860:4860::8888"]


def test_plain_content_removes_scripts():
    assert clean_text('<p>Hello</p><script>steal()</script><style>secret</style>') == "Hello"


def test_community_discovery_relevance_uses_literal_boundaries():
    keywords = ["ai", "linux", "show hn", "open source"]
    assert discovery_relevant("Linux on a new processor", "", keywords)
    assert discovery_relevant("Show HN: A new tool", "", keywords)
    assert discovery_relevant("A release announcement", "Open source weights", keywords)
    assert not discovery_relevant("The escalation of war in Ethiopia", "", keywords)
    assert not discovery_relevant("A painting exhibition", "", keywords)
    assert discovery_relevant("A publisher announcement", "", [])


def test_missing_and_future_publication_time(source, now):
    assert parse_date(None, now) == (now, True)
    assert parse_date("2030-01-01", now) == (now, True)
    item = normalize({"url":"https://example.com/new","title":"A real announcement","text":"Known facts"}, source, now)
    assert item.missing_publication_time and item.published_at == now


def test_dedupe_latest_update_wins(items, now):
    changed = items[0].model_copy(update={"fetched_at":now + timedelta(hours=1),"excerpt":"Updated content"})
    unique, count = deduplicate([items[0], changed])
    assert count == 1 and unique[0].excerpt == "Updated content"


def test_independent_copies_remain_evidence(items):
    independent = items[0].model_copy(update={"id":"other", "source_independence_group":"other", "source_registry_id":"other","source_class":"independent", "canonical_url":"https://reporter.example.com/story"})
    assert len(deduplicate([items[0], independent])[0]) == 2
    assert len(cluster([items[0], independent])) == 1


def test_same_canonical_url_is_one_article_even_across_registries(items):
    duplicate = items[0].model_copy(update={"id":"copy", "source_registry_id":"other", "source_independence_group":"other", "source_class":"independent"})
    unique, count = deduplicate([duplicate,items[0]])
    assert count==1 and unique[0].source_class=="primary"


def test_cluster_new_versions_and_old_events_separate(items):
    a = items[0].model_copy(update={"title":"Acme model version 1 released"})
    b = a.model_copy(update={"id":"b","title":"Acme model version 2 released","canonical_url":"https://example.com/2"})
    old = a.model_copy(update={"id":"old","published_at":a.published_at - timedelta(days=7)})
    assert len(cluster([a,b,old])) == 3
    assert simhash("A model for local inference") == simhash("A model for local inference")


def test_evidence_groups(items):
    base = items[0]
    assert evidence_state([base]) == "primary-confirmed"
    a = base.model_copy(update={"source_class":"independent", "source_independence_group":"wire"})
    b = a.model_copy(update={"id":"b"})
    assert evidence_state([a,b]) == "single-source"
    assert evidence_state([a,b.model_copy(update={"source_independence_group":"reporter"})]) == "multi-source"
    assert evidence_state([base.model_copy(update={"source_class":"community"})]) == "community-report"
    assert evidence_state([base.model_copy(update={"source_class":"aggregator"})]) == "needs-verification"


def test_rank_bounded_and_popularity_cannot_override_primary(items, now):
    ranking, categories = config("ranking"), config("categories")["categories"]
    official = rank([items[0]], ranking, categories, now)
    community = items[0].model_copy(update={"source_class":"community", "community_score":10000000})
    assert 0 <= rank([community], ranking, categories, now) < official <= 1


def test_rank_novelty_and_unknown_publication_are_conservative(items, now):
    ranking, categories = config("ranking"), config("categories")["categories"]
    item = items[0]
    assert novelty([item], {}) == 1
    assert novelty([item], {item.id: item}) == 0
    assert novelty([item.model_copy(update={'content_hash': 'corrected'})], {item.id: item}) == .65
    assert rank([item], ranking, categories, now, 0) < rank([item], ranking, categories, now, 1)
    unknown_date = item.model_copy(update={'missing_publication_time': True})
    assert rank([unknown_date], ranking, categories, now) < rank([item], ranking, categories, now)


def test_explicit_open_model_announcements_exclude_library_releases():
    assert is_model_announcement('Open-sourcing AstaBrief, the fast report-generation model in Asta')
    assert is_model_announcement('Provider releases a new inference model')
    assert not is_model_announcement('huggingface/transformers Release 5.18.0')
    assert not is_model_announcement('A paper evaluates model performance')


def test_evidence_cache_tracks_attribution_category_and_locale(items):
    item = items[0]
    policy = config('ai')
    original = evidence_hash([item], policy)
    for update in ({'source_class': 'independent'}, {'source_independence_group': 'another publisher'}, {'category': 'research'}, {'language': 'bn'}):
        assert evidence_hash([item.model_copy(update=update)], policy) != original
    assert evidence_hash([item.model_copy(update={'fetched_at': item.fetched_at + timedelta(hours=6)})], policy) == original
    assert classify('NVIDIA DGX Spark 64GB', '64GB of unified memory', ['ai']) == 'chips'


def test_fallback_claims_are_numeric_and_source_mapped(items):
    result = extractive(items[:1])
    validate_summary(result, items[:1])
    assert len(result.summary_bullets) == 3
    altered = result.model_copy(update={"summary_bullets":["The context window is 999K", *result.summary_bullets[1:]]})
    with pytest.raises(ValueError, match="numeric"):
        validate_summary(altered, items[:1])
    bad_fact = result.key_facts[0].model_copy(update={"source_ids":["invented"]})
    with pytest.raises(ValueError, match="source"):
        validate_summary(result.model_copy(update={"key_facts":[bad_fact]}), items[:1])


def test_conflicting_benchmarks_disclosed(items):
    a = items[0].model_copy(update={"excerpt":"The benchmark throughput is 50 tokens per second."})
    b = a.model_copy(update={"id":"other", "publisher":"Independent lab", "source_class":"independent", "excerpt":"The benchmark throughput is 30 tokens per second."})
    result = extractive([a,b])
    assert conflicts([a,b]) and any("different throughput" in limitation for limitation in result.limitations)


def test_non_english_and_community_disclaimers(items):
    item = items[0].model_copy(update={"language":"bn", "source_class":"community"})
    result = extractive([item])
    assert any("original language" in text for text in result.limitations)
    assert any("Discovery signal" in text for text in result.limitations)


def test_markup_rejected(items):
    data = items[0].model_dump()
    data["title"] = "<script>malicious</script>"
    with pytest.raises(ValidationError):
        type(items[0]).model_validate(data)


def test_offer_lifecycle(now):
    offer = Offer(id="test",provider="Official",title="Trial",offer_type="trial",value_text="Limited",eligibility=[],regions=[],card_required=None,claim_steps=[],last_verified_at=now,status="active",official_source_url="https://example.com/offer",source_ids=["s"],integration_notes="Check terms")
    assert offer_status(offer,now) == "active"
    assert offer_status(offer.model_copy(update={"expires_at":now + timedelta(days=3)}),now) == "expiring"
    assert offer_status(offer.model_copy(update={"expires_at":now - timedelta(seconds=1)}),now) == "expired"
    assert offer_status(offer.model_copy(update={"last_verified_at":now - timedelta(days=8)}),now) == "unverified"
    assert offer_status(offer.model_copy(update={"starts_at":now + timedelta(days=1)}),now) == "unverified"


def make_story(item, now):
    summary = extractive([item])
    return Story(**summary.model_dump(),id="story_"+item.id,slug="demo-"+item.id.replace('_','-'),canonical_topic="demo",source_ids=[item.id],primary_source_id=item.id,evidence_state="primary-confirmed",published_at=item.published_at,first_seen_at=now,updated_at=now,last_verified_at=now,importance_score_internal=.8,change_log=[Change(at=now,text="First seen",source_ids=[item.id])],ai_metadata=AIMetadata(evidence_hash="abc"),is_demo=True)


def test_calendar_periods_and_digests(items, now):
    assert period_bounds(now,"daily")[0] == "2026-10-03"
    assert period_bounds(now,"weekly")[0] == "2026-W40"
    _, start, end = period_bounds(now,"monthly")
    assert start.day == 1 and end.month == 11 and start.utcoffset() == timedelta(hours=6)
    assert period_bounds(now,"yearly")[2].year == 2027
    stories = [make_story(item,now) for item in items]
    digests = build_digests(stories,now)
    assert {d.period_type for d in digests} == {"daily","weekly","monthly","yearly"}
    assert all(not digest.watch_next for digest in digests)
    assert any(d.status == "finalized" for d in digests)
    current = next(d for d in digests if d.id == "2026-10-03")
    assert current.status == "in-progress"


def test_archive_compaction_idempotent(tmp_path, items, now):
    stories = [make_story(item,now) for item in items]
    sources = {item.id:item for item in items}
    active, index = compact(stories,sources,tmp_path,now,{"retain_individual_days":548},[])
    assert len(active) == len(stories)-1 and len(index) == 1
    _, again = compact(stories,sources,tmp_path,now,{"retain_individual_days":548},index)
    assert again == index
