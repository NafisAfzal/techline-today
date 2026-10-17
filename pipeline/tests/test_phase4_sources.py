import json
import random

import httpx
import pytest

from pipeline.adapters import ADAPTERS
from pipeline.models import SourceConfig
from pipeline.normalize import parse_date
from pipeline.security import SafeFetcher
from pipeline.strict_json import strict_json


@pytest.mark.parametrize("payload", [b'{"x":1,"x":2}', b'{"x":{"a":1,"a":2}}',
    b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}', b'{"x":1e999}',
    b'[' * 33 + b'0' + b']' * 33, b'[] trailing', b'{"x":'])
def test_ambiguous_json_refuses(payload):
    with pytest.raises(ValueError):
        strict_json(payload)


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16", "utf-32"])
def test_nesting_guard_handles_encoding_and_escaped_strings(encoding):
    payload = {"braces": '[\\\"{\\\"}]', "nested": [[1]]}
    assert strict_json(json.dumps(payload).encode(encoding)) == payload
    with pytest.raises(ValueError, match="nesting"):
        strict_json(("[" * 10000 + "0" + "]" * 10000).encode(encoding))


def test_json_byte_budget():
    with pytest.raises(ValueError, match="byte"):
        strict_json(b'"' + b'x' * 101 + b'"', max_bytes=100)


def release_source():
    return SourceConfig(id="synthetic_release", name="Synthetic project", adapter="github_releases",
        source_class="primary", endpoint="https://api.github.com", allowed_hosts=["api.github.com"],
        repositories=["owner/project"], categories=["open-source"], independence_group="synthetic",
        terms_url="https://github.com/owner/project/blob/main/LICENSE")


def release(index=1, **changes):
    return {"id": index, "tag_name": f"v{index}", "html_url": f"https://github.com/owner/project/releases/tag/v{index}",
            "published_at": "2026-10-17T10:00:00Z", "body": "Synthetic release prose", **changes}


async def fetch(source, payload):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(
            200, content=payload, headers={"content-type": "application/json"}))) as client:
        return await ADAPTERS[source.adapter].fetch(source, SafeFetcher(client, {}, "SyntheticTest"))


@pytest.mark.parametrize("payload", [{"message": "error"}, [None], [release(id=True)],
    [release(prerelease="false")], [release(body={"text": "unsafe shape"})],
    [release(html_url="https://github.com/other/project/releases/tag/v1")],
    [release(html_url="https://attacker.example/forged")], [release(html_url="https://127.0.0.1/private")],
    [release(html_url="https://github.com/owner/project/releases/tag/../../../other", tag_name="../../../other")],
    [release(html_url="https://github.com/owner/project/releases/tag/%2e%2e/other", tag_name="../other")],
    [release(html_url="https://github.com/owner/project/releases/tag/wrong-tag")]])
async def test_release_shape_identity_and_origin_refuse(payload):
    with pytest.raises(ValueError):
        await fetch(release_source(), json.dumps(payload).encode())


async def test_seeded_release_order_and_bounded_first_page():
    source = release_source()
    source = source.model_copy(update={"fetch_policy": source.fetch_policy.model_copy(update={"max_items": 3})})
    records = [release(index) for index in range(1, 20)] + [release(50, prerelease=True), release(51, draft=True)]
    baseline = await fetch(source, json.dumps(records).encode())
    for seed in range(10):
        random.Random(seed).shuffle(records)  # noqa: S311 - reproducible adversarial order, not secrets
        assert await fetch(source, json.dumps(records).encode()) == baseline
    assert len(baseline) == 3


async def test_release_does_not_follow_untrusted_pagination_or_assets():
    calls = []
    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, json=[release(assets=[{"url": "https://127.0.0.1/private"}])],
                              headers={"link": '<https://127.0.0.1/private>; rel="next"'})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await ADAPTERS["github_releases"].fetch(release_source(), SafeFetcher(client, {}, "SyntheticTest"))
    assert len(calls) == len(result) == 1
    assert "per_page=30" in calls[0]


@pytest.mark.parametrize("adapter", ["json_api", "github_releases", "github_document", "hacker_news"])
async def test_all_json_adapters_refuse_ambiguous_keys(source, adapter):
    source = source.model_copy(update={"adapter": adapter, "repositories": ["owner/project"]})
    with pytest.raises(ValueError, match="Duplicate JSON"):
        await fetch(source, b'{"items":[],"items":[]}')


@pytest.mark.parametrize("value", ["2026-10-02T12:00:00", "Fri, 02 Oct 2026 12:00:00"])
def test_timezone_missing_never_establishes_publication_time(now, value):
    assert parse_date(value, now) == (now, True)
