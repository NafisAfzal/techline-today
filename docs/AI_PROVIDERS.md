# AI providers

Summary cache keys include source content hashes, publisher/URL/publication time, attribution/independence/category/language, missing-date flags, actual prompt contents, generated Summary schema, configured prompt/schema/locale versions and `SUMMARY_POLICY_VERSION`. Editing the prompt or schema invalidates automatically; bump the policy constant after semantic validator changes. Adding a provider affects new or changed clusters; bump the configured prompt version to deliberately regenerate retained extractive summaries. The fetch transform version in `pipeline/security.py` invalidates conditional extraction state after parser changes.

Every provider is optional. Live and fixture modes work with extractive summaries if no keys are set. Reading never triggers inference.

Priority, daily call limits, retries, timeout, circuit breaker and output budget live in `config/ai.yaml`. Model IDs come from operator settings because availability/free tiers can change.

| Provider | Secret | Model variable | Other configuration |
|---|---|---|---|
| Workers AI | CLOUDFLARE_AI_API_TOKEN | CLOUDFLARE_AI_MODEL | CLOUDFLARE_ACCOUNT_ID |
| Gemini | GEMINI_API_KEY | GEMINI_MODEL | Direct Developer API |
| Groq | GROQ_API_KEY | GROQ_MODEL | Compatible chat endpoint |
| OpenRouter | OPENROUTER_API_KEY | OPENROUTER_MODEL | Choose a currently eligible free model |
| Generic | OPENAI_COMPAT_API_KEY | OPENAI_COMPAT_MODEL | HTTPS OPENAI_COMPAT_BASE_URL |

The generic adapter appends `/chat/completions`; configure the API root (including `/v1` if required). Private/local endpoints are rejected. Credentials are sent in headers; Gemini uses `x-goog-api-key` rather than a key-bearing URL.

Prompts include bounded untrusted source evidence and output schema. Models have no tools, secrets or write access. Bullets require claim mappings; key facts and numbers require source IDs. Numeric tokens must occur in their cited evidence. Unknown sources, markup, duplicates, unsupported certainty and undisclosed conflicts reject output.

Timeout/429/invalid output, empty response arrays and unexpected adapter exceptions route through bounded retries with jitter, then the next provider and extractive fallback. Invalid optional endpoint configuration is skipped without logging its URL or key. Provider redirects are disabled even if the HTTP client permits them. Failed calls count toward daily ceilings. Reservations are atomically persisted before each call in `.cache/provider-usage-live.json`, independently of snapshot publication, without exception strings or secrets. The production workflow restores this ledger separately and saves it even if publication fails. Cache eviction or abrupt job termination can still lose runner-local state; provider-side hard spending limits remain the authoritative ceiling. Unchanged evidence/prompt/schema/language hashes reuse summaries across equivalent providers.

`PIPELINE_MAX_LLM_STORIES_PER_RUN` caps new/changed selected clusters. Provider call counts are guardrails, not currency spending caps: use an eligible free account/model or provider-side spending controls. Review current data-use terms before enabling.

Credentialed provider integration remains untested locally because no keys were supplied. Transport mocks exercise all response formats and failure paths; run an operator-only smoke check when adding credentials.
