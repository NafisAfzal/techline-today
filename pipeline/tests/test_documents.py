import base64

import httpx

from pipeline.adapters import ADAPTERS
from pipeline.security import SafeFetcher


async def test_official_document_billing_constraints_preserved(source):
    source = source.model_copy(update={"adapter": "github_document", "excerpt_patterns": [r"Some models[^\n]+", r"Free allocation[^\n]+"], "document_url": "https://example.com/terms"})
    text = "Header\nSome models require a paid billing method.\nFree allocation is **10,000 Neurons per day**.\nUnrelated body"
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"type": "file", "encoding": "base64", "content": base64.b64encode(text.encode()).decode(), "sha": "synthetic", "html_url": "https://example.com/file"}))) as client:
        result = await ADAPTERS["github_document"].fetch(source, SafeFetcher(client, {}, "TestBot"))
    assert result[0]["text"].startswith("Some models require a paid")
    assert "10,000 Neurons per day" in result[0]["text"] and "Unrelated" not in result[0]["text"]
