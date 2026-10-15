import itertools
import json
import subprocess
import sys
from datetime import timedelta

import httpx
import pytest

from pipeline.adapters import RSSAdapter
from pipeline.ai import evidence_hash, extractive
from pipeline.dedupe import cluster, cluster_category, deduplicate
from pipeline.ranking import rank
from pipeline.runner import config
from pipeline.security import SafeFetcher
from pipeline.verification import (
    LIMITATIONS_UNKNOWN,
    PREPRINT_NOTICE,
    SIGNIFICANCE_UNKNOWN,
    evidence_state,
    validate_summary,
)


def test_dedupe_equal_priority_tie_is_stable_and_newer_updates_win(items):
    first = items[0].model_copy(update={"id": "a", "category": "ai"})
    second = first.model_copy(update={"id": "b", "category": "security"})
    assert {tuple(item.id for item in deduplicate(list(order))[0])
            for order in itertools.permutations([first, second])} == {("a",)}
    newer = second.model_copy(update={"fetched_at": second.fetched_at + timedelta(seconds=1),
                                      "content_hash": "updated"})
    assert deduplicate([first, newer])[0] == [newer]


def test_cluster_category_rank_and_evidence_hash_are_permutation_invariant(items, now):
    first = items[0].model_copy(update={"id": "a", "category": "ai"})
    second = first.model_copy(update={"id": "b", "category": "security", "canonical_url": "https://example.com/second"})
    third = first.model_copy(update={"id": "c", "category": "security", "canonical_url": "https://example.com/third"})
    values = set()
    for order in itertools.permutations([first, second, third]):
        groups = cluster(list(order))
        assert len(groups) == 1
        values.add((tuple(tuple(item.id for item in group) for group in groups),
                    cluster_category(order), extractive(order).category,
                    rank(order, config("ranking"), config("categories")["categories"], now),
                    evidence_hash(order, config("ai"))))
    assert len(values) == 1
    assert extractive([first, second, third]).category == "security"
    assert cluster_category([first, second]) == cluster_category([second, first]) == "ai"


def test_cluster_preserves_event_and_version_guards(items):
    first = items[0].model_copy(update={"id": "a", "title": "Orion model version 1 published for developers"})
    other = first.model_copy(update={"id": "b", "title": "Orion model version 2 published for developers",
                                     "canonical_url": "https://example.com/v2"})
    assert len(cluster([first, other])) == 2
    unrelated = other.model_copy(update={"title": "Harbor security gateway patches authentication vulnerability"})
    assert len(cluster([first, unrelated])) == 2
    same_event = other.model_copy(update={"title": "Orion developers gain a newly published model", "canonical_url": first.canonical_url})
    assert len(cluster([first, same_event])) == 1
    outside_window = same_event.model_copy(update={"published_at": first.published_at + timedelta(hours=73)})
    assert len(cluster([first, outside_window])) == 2


def test_preprint_caveats_unknown_significance_and_legacy_reading(items):
    item = items[0].model_copy(update={"source_type": "arxiv", "source_registry_id": "arxiv", "category": "research"})
    summary = extractive([item])
    assert {PREPRINT_NOTICE, LIMITATIONS_UNKNOWN} <= set(summary.limitations)
    assert summary.why_it_matters == SIGNIFICANCE_UNKNOWN
    assert evidence_state([item]) == "primary-confirmed"  # Stored enum remains compatible.
    legacy = summary.model_copy(update={"limitations": []})
    validate_summary(legacy, [item])
    with pytest.raises(ValueError, match="Preprint review status"):
        validate_summary(legacy, [item], generated=True)
    invented = summary.model_copy(update={"why_it_matters": "This peer-reviewed paper establishes the result."})
    with pytest.raises(ValueError, match="peer-review"):
        validate_summary(invented, [item])
    negated = item.model_copy(update={"excerpt": "This preprint is not peer-reviewed. Results remain preliminary."})
    with pytest.raises(ValueError, match="peer-review"):
        validate_summary(invented, [negated])
    # Do not strip supported peer-review attribution from an actual source.
    supported = item.model_copy(update={"excerpt": item.excerpt + " This peer-reviewed paper establishes the result."})
    validate_summary(invented, [supported])


async def test_oversized_rss_rejected_before_parser(source, monkeypatch):
    def forbidden_parse(*args):
        raise AssertionError("Oversized response reached XML parser")
    monkeypatch.setattr("pipeline.adapters.feedparser.parse", forbidden_parse)
    payload = b"x" * 5_000_000
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(
            200, content=payload, headers={"Content-Type": "application/rss+xml"}))) as client:
        with pytest.raises(ValueError, match="size"):
            await RSSAdapter().fetch(source, SafeFetcher(client, {}, "TestBot"))


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16"])
async def test_rss_entity_declarations_rejected_before_expansion(source, encoding):
    payload = ('<?xml version="1.0"?><!DOCTYPE rss [<!ENTITY a "synthetic">'
               '<!ENTITY b "&a;&a;&a;&a;">]><rss><channel><item><title>Test title</title>'
               '<link>https://example.com/</link><description>&b;</description></item></channel></rss>').encode(encoding)
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(
            200, content=payload, headers={"Content-Type": "application/rss+xml"}))) as client:
        with pytest.raises(ValueError, match="entity declarations"):
            await RSSAdapter().fetch(source, SafeFetcher(client, {}, "TestBot"))


def test_large_rss_item_count_is_bounded_in_isolated_process(source, tmp_path):
    # 20k short entries stay below the existing response-byte ceiling. The
    # separate process has a hard deadline and never contacts a network.
    payload = b'<rss version="2.0"><channel>' + b''.join(
        f'<item><title>Entry {index}</title><link>https://example.com/{index}</link></item>'.encode()
        for index in range(20_000)) + b'</channel></rss>'
    assert len(payload) < source.fetch_policy.max_response_bytes
    fixture = tmp_path / "large-rss.xml"
    fixture.write_bytes(payload)
    worker = '''
import asyncio, json, sys
from pathlib import Path
from pipeline.adapters import RSSAdapter
from pipeline.models import SourceConfig
class LocalFetcher:
    async def get(self, *args, **kwargs): return Path(sys.argv[1]).read_bytes()
source = SourceConfig.model_validate_json(sys.argv[2])
result = asyncio.run(RSSAdapter().fetch(source, LocalFetcher()))
assert len(result) == source.fetch_policy.max_items
print(json.dumps({"items":len(result)}))
'''
    result = subprocess.run(  # noqa: S603 - only local synthetic fixture paths and fixed code
        [sys.executable, "-c", worker, str(fixture), source.model_dump_json()],
        capture_output=True, text=True, timeout=5, check=True)
    assert json.loads(result.stdout)["items"] == source.fetch_policy.max_items


async def test_rss_legacy_encoding_namespace_and_malformed_inputs(source):
    payloads = [
        (b'<?xml version="1.0" encoding="windows-1252"?><rss><channel><item><title>Caf\xe9 release</title><link>https://example.com/</link></item></channel></rss>', "Café release"),
        (b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Namespace release</title><link href="https://example.com/"/><id>one</id></entry></feed>', "Namespace release"),
    ]
    for payload, title in payloads:
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request, body=payload: httpx.Response(
                200, content=body, headers={"Content-Type": "application/rss+xml"}))) as client:
            result = await RSSAdapter().fetch(source, SafeFetcher(client, {}, "TestBot"))
        assert len(result) == 1 and result[0]["title"] == title
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(
            200, content=b"not an XML feed", headers={"Content-Type": "application/rss+xml"}))) as client:
        with pytest.raises(ValueError, match="Malformed"):
            await RSSAdapter().fetch(source, SafeFetcher(client, {}, "TestBot"))
