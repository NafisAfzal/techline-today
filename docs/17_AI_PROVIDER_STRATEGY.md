# AI Provider Strategy

## Principle

AI capacity is a replaceable resource. Product logic must not depend on a single model/provider.

## Recommended routing tiers

### Tier A - routine compression

Use the cheapest/free small model that reliably produces schema-valid summaries.

Tasks:
- category classification
- 3-bullet summary
- entity/tag extraction
- claim formatting

### Tier B - complex synthesis

Use only for clusters with multiple conflicting/complex sources.

Tasks:
- reconcile source differences without choosing unsupported facts
- create `what changed`
- summarize multiple perspectives

The router may choose a stronger model when available, but must stay inside configured quota.

## Current free-first candidates

### Cloudflare Workers AI

Good default because it is close to the hosting stack and currently includes a daily free allocation. Model availability changes, so select the model through config rather than code.

### Gemini Developer API

Selected models currently have a free tier. Good fallback for structured summarization. Free-tier data-use terms should be reviewed before sending content.

### Groq

Useful free-plan throughput for supported open models. Rate limits are model-specific; parse 429/retry headers.

### OpenRouter

Useful as an additional fallback and for testing free models, but the current free-plan daily request count is relatively small. Do not make it the only provider.

### Generic OpenAI-compatible provider

Required. Owner can later supply any compatible endpoint/key/model without changing the pipeline.

Examples could include a private router or another service the owner already has access to. The platform should validate base URL configuration and never trust a provider response without schema/content checks.

## Quota controller

Track per provider:
- calls today
- input/output tokens when reported
- 429 count
- consecutive errors
- average latency
- valid JSON rate
- last success
- disabled-until timestamp

Routing decisions should consider both configured priority and current health.

## Cache key

Do not regenerate a summary when nothing material changed.

Suggested key:

```text
sha256(
  prompt_version +
  schema_version +
  sorted(source_content_hashes) +
  selected_model_family +
  requested_language
)
```

A model-specific key is optional if summaries may be reused across equivalent providers.

## Extractive fallback

When all AI calls fail:
- choose the most informative sentences from primary/independent evidence;
- compress duplicates;
- build a 3-point summary;
- label internally as `generation_mode=extractive`;
- avoid `why it matters` speculation; use a conservative template from known category rules.

This fallback makes AI outages non-fatal.
