# Deployment and Free-Tier Strategy

## Current recommended platform

Use **Cloudflare Workers Static Assets** for new deployment rather than starting a new Cloudflare Pages project. Cloudflare currently recommends Workers for new projects and focuses newer platform features there.

V1 runtime profile:
- almost every reader request is a static asset request;
- no database required for normal reading;
- no AI inference at page view;
- ingestion occurs in GitHub Actions;
- deploy only after a successful pipeline/build.

## Current free-tier facts to verify before launch

As of the preparation date of this pack (2026-10-03), official documentation reports approximately:
- Workers Free: 100,000 Worker requests/day; static asset requests are not billed like Worker invocations.
- Workers Static Assets: 20,000 files per Worker version, 25 MiB individual asset limit.
- D1 Free: 5 million rows read/day, 100,000 rows written/day, 5 GB total included storage, with additional free-plan database limits.
- KV Free: 100,000 reads/day, 1,000 writes/day, 1 GB stored data.
- Workers AI: 10,000 Neurons/day free allocation, with model availability varying.
- Turnstile Free: unlimited challenge/verification traffic within the documented product limits.
- Cloudflare Web Analytics: free privacy-first analytics.
- standard GitHub-hosted runners for public repositories: free/unlimited usage under GitHub's public-repository policy.

Never encode these numbers as permanent assumptions. Check official docs during deployment and at least quarterly.

## GitHub Actions schedule

Recommended cron concept: four runs/day at a non-zero minute.

GitHub notes that scheduled jobs can be delayed or dropped under high load, especially near the start of an hour. The pipeline therefore:
- runs at an offset minute such as 17;
- uses a 12-hour overlap window;
- deduplicates by IDs/hashes;
- never assumes one run happened merely because it was scheduled.

GitHub also documents automatic disabling of scheduled workflows in public repositories after 60 days of no repository activity. Because this project normally publishes generated changes, activity should occur, but the operations checklist must still verify the workflow monthly. A manual `workflow_dispatch` trigger is mandatory.

## Deployment workflow

1. Checkout default branch.
2. Install pinned Node/Python tooling.
3. Fetch content.
4. Run normalization/verification tests.
5. Summarize selected clusters.
6. Validate JSON schemas.
7. Build Astro.
8. Run unit + smoke + accessibility checks.
9. Deploy `dist` with Wrangler.
10. Save a compact run report.

Do not commit secrets or raw scraped article bodies.

## Domain

`workers.dev` can be used without buying a custom domain. A custom domain is optional and may be the first unavoidable monetary cost if the project becomes a branded product.

## AI providers

Use provider quotas as opportunistic capacity, never as a single point of failure.

Current examples:
- Workers AI free daily allocation;
- Gemini developer API free tier for selected models;
- Groq free-plan model-specific quotas;
- OpenRouter free models with a low daily request allowance;
- generic OpenAI-compatible adapter for any user-provided provider.

Free tiers can change. Maintain a provider health/quota table in the run report.

## Cost guardrails

Defaults:
- maximum LLM stories/run;
- maximum output tokens/story;
- maximum retries/provider;
- daily provider request budget;
- do not process unchanged clusters;
- reuse previous summary if evidence set is unchanged;
- AI call hash cache keyed by evidence + prompt version + model family.

If all LLM quotas are exhausted, publish extractive summaries rather than failing deployment.
