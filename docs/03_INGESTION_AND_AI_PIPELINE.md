# Ingestion and AI Pipeline

## Pipeline stages

### 1. Fetch

Use conditional requests where possible:
- `ETag`
- `If-Modified-Since`
- reasonable timeouts
- retry only idempotent requests
- per-domain rate limiting

Every source lives in an allowlisted registry. Do not accept arbitrary URL input from public users.

### 2. Normalize

Normalize into `SourceItem`:
- canonical URL
- source/domain
- source type
- title
- author if available
- published time
- fetched time
- language
- clean text or feed excerpt
- content hash
- external IDs
- tags from source metadata

Canonicalization removes tracking parameters and known referral fragments while preserving URLs where query parameters are semantically required.

### 3. Deduplicate

Run cheap rules before embeddings:
1. exact canonical URL;
2. same external ID;
3. normalized-title hash;
4. SimHash/MinHash over title + excerpt;
5. TF-IDF cosine within a recent time window;
6. optional embedding similarity only for ambiguous cases.

This reduces AI calls.

### 4. Story clustering

Group reports about the same event. One story cluster can contain:
- one primary source;
- multiple independent sources;
- community discussion;
- subsequent updates.

A new article should update an existing cluster when the core event/entity remains the same and the time window is reasonable. Meaningfully new facts become a delta in the cluster timeline.

### 5. Relevance and importance ranking

Use deterministic scoring before AI.

Suggested internal formula:

```text
importance =
  0.25 * recency +
  0.20 * source_strength +
  0.15 * cross_source_support +
  0.15 * novelty +
  0.15 * category_relevance +
  0.10 * community_signal
```

Weights live in config, not code.

Important safeguards:
- popularity cannot override a weak/unverified source;
- a primary announcement can rank highly with one source because it is the authoritative source for its own release;
- community discussion is a signal, not proof;
- duplicated syndication does not count as independent corroboration.

### 6. Source extraction

Preferred input to summarization:
- official RSS/API content;
- official changelog/model card;
- limited extracted page content only when permitted;
- trusted independent excerpts.

Raw third-party article text should be ephemeral. Do not commit entire articles to Git.

### 7. Claim extraction

Before prose generation, build factual records:

```json
{
  "claim": "Provider X launched model Y",
  "type": "release",
  "value": null,
  "source_ids": ["src_123"],
  "attribution": "primary",
  "confidence": "supported"
}
```

Numbers receive special validation. If two sources disagree, preserve the disagreement instead of choosing silently.

### 8. AI selection budget

Do not summarize everything with an LLM.

Default per run:
- collect up to several hundred raw items;
- dedupe/cluster locally;
- run full LLM processing only for the top 30 to 60 new/updated clusters depending on quota;
- lower-ranked items can remain headline-only or use extractive summaries;
- always prioritize urgent official releases and expiring opportunities.

### 9. AI router

Provider interface:

```text
generate_structured(
  task,
  source_bundle,
  output_schema,
  max_output_tokens,
  quality_tier
) -> validated object
```

Provider behavior:
- central timeout;
- 429-aware exponential backoff with jitter;
- quota accounting;
- circuit breaker after repeated provider failures;
- next-provider fallback;
- deterministic extractive fallback if all providers fail;
- model/provider metadata stored with generated content for debugging.

Recommended configurable priority:
1. Workers AI
2. Gemini free
3. Groq free
4. OpenRouter free
5. user-supplied OpenAI-compatible endpoint
6. local extractive fallback

Never send secrets or unrelated private data to AI providers.

### 10. Structured summary generation

Schema should include:
- concise headline
- exactly 3 short bullets for fast view
- why it matters
- key facts
- key numbers
- broader summary
- limitations/uncertainty
- category/subcategory
- entities/tags
- claim-to-source mapping

Reject output that:
- contains a number not present in evidence;
- lacks source mapping for key facts;
- adds unsupported superlatives;
- calls something “best” without a source-defined metric;
- transforms rumor into fact.

### 11. Validation

Use Pydantic/JSON Schema. Then run deterministic checks:
- URL/domain validation;
- numeric token cross-check against evidence;
- maximum lengths;
- duplicate bullet detection;
- profanity/unsafe markup sanitation;
- publication timestamp sanity;
- expiry date sanity for offers;
- source count and evidence-state consistency.

### 12. Digest generation

Daily/weekly/monthly/yearly summaries are generated from already validated story objects, not by refetching the web.

A digest contains:
- top 5 overall;
- top items per selected category;
- biggest model/tool release;
- biggest free developer opportunity;
- one `what changed` section;
- one `watch next` section derived only from announced future dates, not unsupported prediction.

## Resilience

- retain the previous successful data snapshot;
- deploy new snapshot only after validation passes;
- if ingestion fails, site serves last successful snapshot;
- show `Last updated` honestly;
- never deploy an empty feed due to upstream failure.
