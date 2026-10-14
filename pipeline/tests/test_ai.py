from pathlib import Path

import httpx
import pytest

from pipeline.ai import AIRouter, RemoteProvider, evidence_hash, extractive
from pipeline.runner import config


class FakeProvider:
    id="fake"
    model="test-model"
    daily_call_limit=2

    def __init__(self,result=None,error=None):
        self.result,self.error,self.calls=result,error,0

    async def generate_structured(self,request):
        self.calls+=1
        assert "untrusted" in request["messages"][0]["content"]
        assert "EVIDENCE_DATA" in request["messages"][1]["content"]
        if self.error:
            raise self.error
        return {"summary":self.result,"tokens":30}


def router(providers,state=None):
    settings={**config('ai'),"max_retries":0}
    return AIRouter(providers,settings,state if state is not None else {},Path('prompts/story_summary.md'))


async def test_no_keys_extractive(items):
    summary,metadata=await router([]).summarize(items[:1])
    assert metadata.generation_mode == 'extractive' and summary.key_facts


def test_english_locale_does_not_report_untranslated_source(items):
    source = items[0].model_copy(update={"language": "en-US"})
    assert not any("no automatic translation" in text for text in extractive([source]).limitations)
    translated = source.model_copy(update={"language": "bn"})
    assert any("no automatic translation" in text for text in extractive([translated]).limitations)


async def test_malformed_then_next_provider(items):
    bad=FakeProvider(result={"headline":"Invalid"})
    good=FakeProvider(result=extractive(items[:1]).model_dump(mode='json'))
    good.id='good'
    summary,metadata=await router([bad,good]).summarize(items[:1])
    assert metadata.provider == 'good' and len(summary.summary_bullets)==3


@pytest.mark.parametrize('error',[httpx.ReadTimeout('timeout'),ValueError('malformed JSON'),KeyError('missing')])
async def test_provider_errors_fallback(items,error):
    provider=FakeProvider(error=error)
    _,metadata=await router([provider]).summarize(items[:1])
    assert metadata.generation_mode == 'extractive'


async def test_429_quota_and_health(items):
    request=httpx.Request('POST','https://example.com/ai')
    response=httpx.Response(429,request=request,headers={'retry-after':'1'})
    provider=FakeProvider(error=httpx.HTTPStatusError('quota',request=request,response=response))
    state={}
    routing=router([provider],state)
    for _ in range(3):
        await routing.summarize(items[:1])
    assert provider.calls == 2 and state['fake']['rate_limits']==2
    assert state['fake']['calls']==2


async def test_circuit_breaker_after_three_errors(items):
    provider=FakeProvider(error=ValueError('bad'))
    provider.daily_call_limit=10
    state={}
    routing=router([provider],state)
    for _ in range(4):
        await routing.summarize(items[:1])
    assert provider.calls == 3 and state['fake']['disabled_until']>0


def test_cache_changes_with_evidence(items):
    settings=config('ai')
    old=evidence_hash(items[:1],settings)
    new=evidence_hash([items[0].model_copy(update={'content_hash':'changed'})],settings)
    assert old != new and old == evidence_hash(items[:1],settings)


async def test_generic_provider_http_contract(items):
    result=extractive(items[:1]).model_dump(mode='json')
    def handler(request):
        assert request.headers['authorization']=='Bearer test-placeholder'
        return httpx.Response(200,json={'choices':[{'message':{'content':__import__('json').dumps(result)}}],'usage':{'total_tokens':30}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider=RemoteProvider('custom','test-model','test-placeholder','https://example.com/v1/chat/completions',client,10)
        output=await provider.generate_structured({'messages':[], 'max_tokens':1000})
    assert output['summary']['headline']==result['headline'] and output['tokens']==30


@pytest.mark.parametrize("kind", ["gemini", "cloudflare"])
async def test_native_provider_formats(items, kind):
    result = extractive(items[:1]).model_dump(mode="json")
    encoded = __import__("json").dumps(result)
    def handler(request):
        if kind == "gemini":
            assert request.headers["x-goog-api-key"] == "test-placeholder"
            return httpx.Response(200, json={"candidates":[{"content":{"parts":[{"text":encoded}]}}], "usageMetadata":{"totalTokenCount":50}})
        assert request.headers["authorization"] == "Bearer test-placeholder"
        return httpx.Response(200, json={"result":{"response":encoded, "usage":{"total_tokens":50}}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = RemoteProvider(kind, "synthetic-model", "test-placeholder", "https://example.com/ai", client, 10, kind)
        output = await provider.generate_structured({"messages":[{"role":"system","content":"Schema"},{"role":"user","content":"Evidence"}], "max_tokens":1000})
    assert output["summary"]["headline"] == result["headline"] and output["tokens"] == 50
