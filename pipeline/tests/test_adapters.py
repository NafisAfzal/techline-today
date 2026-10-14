import json

import httpx
import pytest

from pipeline.adapters import ADAPTERS
from pipeline.security import SafeFetcher


async def fetch_with(handler, source):
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        fetcher = SafeFetcher(client, {}, "TestBot")
        return await ADAPTERS[source.adapter].fetch(source, fetcher)


async def test_rss_fixture(source):
    xml = b'<rss version="2.0"><channel><title>Test</title><item><title>Official model release</title><link>https://example.com/model</link><description>Open weights available.</description><pubDate>Sat, 03 Oct 2026 10:00:00 GMT</pubDate></item></channel></rss>'
    result = await fetch_with(lambda request:httpx.Response(200,content=xml,headers={"Content-Type":"application/rss+xml"}), source)
    assert result[0]["title"] == "Official model release"


async def test_atom_fixture(source):
    xml = b'<feed xmlns="http://www.w3.org/2005/Atom"><title>Updates</title><entry><id>1</id><title>Official update</title><link href="https://example.com/update"/><updated>2026-10-03T10:00:00Z</updated><summary>Known source evidence.</summary></entry></feed>'
    result = await fetch_with(lambda request:httpx.Response(200,content=xml,headers={"Content-Type":"application/atom+xml"}), source)
    assert result[0]["external_id"] == "1"


async def test_generic_json_mapping(source):
    source = source.model_copy(update={"adapter":"json_api", "item_path":"data.updates", "field_map":{"title":"name"}})
    result = await fetch_with(lambda request:httpx.Response(200,json={"data":{"updates":[{"url":"https://example.com/a","name":"A useful release","summary":"Known"}]}}),source)
    assert result[0]["title"] == "A useful release"


async def test_hn_is_discussion_not_primary_article(source):
    source = source.model_copy(update={"adapter":"hacker_news", "endpoint":"https://example.com/v0/"})
    def handler(request):
        return httpx.Response(200,json=[123] if "topstories" in str(request.url) else {"id":123,"type":"story","title":"An AI announcement","url":"https://unfetched.com/article","score":99,"time":1791021600})
    result = await fetch_with(handler,source)
    assert result[0]["url"] == "https://news.ycombinator.com/item?id=123"


async def test_github_ignores_prerelease(source):
    source = source.model_copy(update={"adapter":"github_releases", "endpoint":"https://example.com", "repositories":["owner/repo"]})
    result = await fetch_with(lambda request:httpx.Response(200,json=[{"id":1,"tag_name":"v1","name":"Stable","html_url":"https://example.com/release","published_at":"2026-10-03","body":"Known changes"},{"id":2,"prerelease":True}]),source)
    assert len(result) == 1 and result[0]["external_id"] == "owner/repo:1"


async def test_redirect_ssrf_denied(source):
    calls=[]
    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(302,headers={"location":"https://169.254.169.254/metadata"})
    with pytest.raises(ValueError):
        await fetch_with(handler,source)
    assert len(calls) == 1


async def test_size_and_content_type_limits(source):
    source = source.model_copy(update={"fetch_policy":source.fetch_policy.model_copy(update={"max_response_bytes":100})})
    with pytest.raises(ValueError,match="size"):
        await fetch_with(lambda request:httpx.Response(200,content=b'x'*101,headers={"Content-Type":"application/xml"}),source)
    with pytest.raises(ValueError,match="content type"):
        await fetch_with(lambda request:httpx.Response(200,content=b'bad',headers={"Content-Type":"text/html"}),source)


async def test_conditional_requests(source):
    seen=[]
    def handler(request):
        seen.append(request.headers)
        return httpx.Response(304 if len(seen)>1 else 200,content=b'feed',headers={"Content-Type":"application/xml","ETag":"stable"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        fetcher=SafeFetcher(client,{},"TestBot")
        assert await fetcher.get(source.endpoint,source,accept=("application/xml",)) == b'feed'
        assert await fetcher.get(source.endpoint,source,accept=("application/xml",)) is None
    assert seen[1]["if-none-match"] == "stable"


async def test_robots_disallows_html(source):
    source=source.model_copy(update={"adapter":"html","html_permission":True})
    calls=[]
    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200,text="User-agent: *\nDisallow: /",headers={"Content-Type":"text/plain"})
    with pytest.raises(ValueError,match="Robots"):
        await fetch_with(handler,source)
    assert len(calls) == 1


async def test_html_extraction_is_limited(source):
    source=source.model_copy(update={"adapter":"html","html_permission":True})
    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(200,text="User-agent: *\nAllow: /",headers={"Content-Type":"text/plain"})
        return httpx.Response(200,text='<h1>Official offer</h1><main><script>Bad</script><p>Short evidence</p></main>',headers={"Content-Type":"text/html"})
    result = await fetch_with(handler,source)
    assert result[0]["text"] == "Short evidence"


async def test_html_excessive_crawl_delay_is_not_shortened(source):
    source = source.model_copy(update={"adapter": "html", "html_permission": True})
    calls = []
    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, text="User-agent: *\nAllow: /\nCrawl-delay: 120", headers={"Content-Type": "text/plain"})
    with pytest.raises(ValueError, match="crawl delay"):
        await fetch_with(handler, source)
    assert len(calls) == 1


async def test_html_redirect_requires_policy_review(source):
    source = source.model_copy(update={"adapter": "html", "html_permission": True})
    calls = []
    def handler(request):
        calls.append(str(request.url))
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text="User-agent: *\nAllow: /", headers={"Content-Type": "text/plain"})
        return httpx.Response(302, headers={"location": "https://example.com/unreviewed"})
    with pytest.raises(ValueError, match="HTML redirects"):
        await fetch_with(handler, source)
    assert len(calls) == 2


async def test_bad_json_response(source):
    source=source.model_copy(update={"adapter":"json_api"})
    with pytest.raises(json.JSONDecodeError):
        await fetch_with(lambda request:httpx.Response(200,text='malformed',headers={"Content-Type":"application/json"}),source)


async def test_transient_network_failure_retried(source):
    calls=[]
    def handler(request):
        calls.append(request)
        if len(calls)==1:
            raise httpx.ReadTimeout("Transient", request=request)
        return httpx.Response(200,content=b'<rss><channel><title>Recovered</title></channel></rss>',headers={"Content-Type":"application/xml"})
    assert await fetch_with(handler,source)==[]
    assert len(calls)==2
