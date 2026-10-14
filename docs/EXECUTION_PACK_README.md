# AI Tech Intelligence Platform - Execution Pack

Working project label: **Tech Intelligence Platform**. Rename the product only after a basic domain/trademark check.

This pack defines a production-minded, free-first architecture for a concise AI and technology news platform. It is designed to start as a GitHub portfolio project, remain useful in real life, and evolve later into a monetizable product without a rewrite.

## Core product idea

Users should understand the important technology news in roughly 30 to 60 seconds, then expand only the stories they care about.

Each story should expose:
- a 3-bullet concise summary;
- why it matters;
- important numbers, prices, limits or benchmarks;
- source quality/context;
- a broader explanation on demand;
- direct links to original sources;
- timestamps for publication and last verification.

Core categories:
- AI models and releases
- AI benchmarks and performance claims
- AI tools and developer platforms
- Free APIs, credits, student/developer offers and claim guides
- AI/tech jobs and skills pulse
- Research and papers
- Chips, GPUs and semiconductors
- Laptops, phones and devices
- Cybersecurity and platform changes
- Developer ecosystem and open source

Time views:
- Live/latest
- Daily
- Weekly
- Monthly
- Yearly

## Recommended architecture

### V1: static-first, free-first

1. **Astro + React islands + Tailwind CSS** frontend.
2. **GitHub Actions** runs the ingestion pipeline four times per day.
3. Python pipeline uses RSS/Atom first, official APIs second, HTML extraction only where permitted.
4. Items are normalized, deduplicated, clustered, ranked, verified and summarized.
5. Structured JSON/Markdown is generated into the repository build workspace.
6. Astro builds static pages and JSON payloads.
7. Deploy to **Cloudflare Workers Static Assets**.
8. Guest bookmarks/preferences use localStorage/IndexedDB.
9. Cloudflare Web Analytics can provide privacy-first analytics.
10. No server call is required for ordinary readers, making traffic very cheap and fast.

### V2: dynamic growth layer

Add only when needed:
- Cloudflare Worker API (Hono)
- D1 for users/preferences/alerts
- KV/cache for hot payloads
- R2 for owned assets or exports
- OAuth accounts
- email/push alerts
- paid plans, API access, affiliate/sponsor modules

The V1 code must use service interfaces so V2 can be added without replacing the UI.

## Why this architecture

The content is processed once, not once per reader. AI costs are therefore tied to the number of new stories rather than the number of visitors. Most site traffic is served as static files at the edge.

## Collection cadence

Default production cadence in `Asia/Dhaka`:
- 01:17
- 07:17
- 13:17
- 19:17

Implementation may use UTC cron equivalents. Avoid minute 00 because scheduled GitHub jobs can be delayed during periods of high Actions load.

Each run uses a lookback overlap so a missed run does not create a content gap.

Digest policy:
- Daily digest: generated from the final local-day run.
- Weekly: Sunday evening, Asia/Dhaka.
- Monthly: generated when a new month begins from the previous month.
- Yearly: generated after the year closes.

## AI policy

AI never invents facts. It receives only extracted source material and emits schema-validated structured output. Every key claim must be traceable to one or more source records.

Provider order is configurable. Recommended free-first order:
1. Cloudflare Workers AI
2. Gemini free tier
3. Groq free tier
4. OpenRouter free models
5. generic OpenAI-compatible provider adapter for user-supplied providers
6. extractive/non-LLM fallback

Do not hard-code provider names into product logic.

## Source policy

Use this order:
1. official primary source / newsroom / changelog / model card;
2. RSS or Atom feed;
3. official/public API;
4. trusted independent publication feed;
5. community signal such as Hacker News only as a discovery/sentiment signal;
6. HTML extraction only when permitted by robots.txt and the site's terms.

Never republish full articles. Store metadata, concise derived summaries and limited source excerpts needed for verification.

## Start here

Read in this order:
1. `docs/01_PRODUCT_SPEC.md`
2. `docs/02_SYSTEM_ARCHITECTURE.md`
3. `docs/03_INGESTION_AND_AI_PIPELINE.md`
4. `docs/04_DATA_MODEL.md`
5. `docs/05_UI_UX_SPEC.md`
6. `docs/06_SECURITY_PRIVACY.md`
7. `docs/07_DEPLOYMENT_FREE_TIER.md`
8. `docs/08_MONETIZATION_ROADMAP.md`
9. `docs/09_TESTING_ACCEPTANCE.md`
10. `docs/10_OPERATIONS_RUNBOOK.md`
11. `docs/16_SOURCE_CANDIDATES.md`
12. `docs/17_AI_PROVIDER_STRATEGY.md`
13. `docs/18_CONTENT_SCHEDULE.md`
14. `CODEX_MASTER_PROMPT.md`

## Local folder recommendation

On Windows, do not place this in XAMPP unless you intentionally need PHP. Use a normal development directory, for example:

```text
C:\Users\<YOUR_WINDOWS_USERNAME>\Documents\Projects\ai-tech-intelligence
```

or, if you keep code on another drive:

```text
D:\Projects\ai-tech-intelligence
```

Unzip this pack into that project directory, open a terminal there, initialize Git, then start your coding agent.

## Important cost note

No external provider can promise that a free tier will remain unchanged forever. The architecture therefore treats every third-party service as replaceable and includes quota/failure fallbacks.
