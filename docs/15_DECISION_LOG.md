# Decision Log

## ADR-014: External checkpoint custody is a separate trust level

A signed journal head proves which key signed it, not that the head is current.
Phase 10 therefore separates five trust levels — locally generated, locally
signed, externally stored, independently authenticated and currently trusted —
and only the last may be reported as a current trusted checkpoint. A file
copied out of the authority state directory is custody, not authenticity: it
is upgraded only by a digest obtained through a channel the checkout does not
control. A document that stays inside the state directory cannot act as an
external anchor at all. Missing evidence yields BLOCKED or INCONCLUSIVE, never
PASS. The existing Phase 8 signature protocol, canonical JSON profile and
journal comparison are reused unchanged; the custody envelope adds only
custody metadata. Storage adapters are read-only and the protected-history
adapter never contacts GitHub.

## ADR-013: Editorial ranking signals

Novelty is 1 for new source evidence, 0.65 for changed evidence and 0 for unchanged coverage. Unknown publication dates receive a configurable recency penalty. The primary release boost requires an announcement/release rather than every primary page; source-backed expiring offers receive the configured urgency boost. Explicit open-sourcing model headlines can populate the model tracker while unsupplied specifications stay unknown.

## ADR-012: Community relevance and summary reuse

Filter broad discovery sources with configurable literal keywords before clustering, including retained items. This limits unrelated Hacker News headlines without upgrading their evidence status. Cached summary text stays stable; ranking ages with each run and successful source rechecks advance verification dates. Failed sources do not receive fresh verification timestamps.

## ADR-008: Compatible tooling and fixture isolation

Use pnpm 10.33.1, Astro 7.3.5, React 19.3, Tailwind 4 and Python 3.13 with lockfiles. TypeScript 6.0.3 matches current Astro checker/typescript-eslint peer ranges; TypeScript 7 does not. Synthetic fixtures are labeled, noindexed, isolated from live archives, and blocked by production validation.

## ADR-009: Archive file budget and state persistence

Keep individual stories 548 days when practical, with a 4,000-record ceiling that can compact oldest entries sooner. Monthly evidence bundles and yearly indexes preserve history while an 18,000-asset margin protects deployment. Actions cache persists successful workspace state without write credentials; owner-managed exports are required for durable archival guarantees.

## ADR-010: Temporary cache-policy patch

No verified upstream security fix exists for GHSA-ch52-4w7c-c8xp. October 4 audit upgraded the compatible transitive dependency to 4.3.0 for its other fixes, but tarball comparison and controlled requests show unchanged disputed cache reuse. Keep a locked local early-rejection patch and fourteen regression tests. The full dependency gate visibly verifies mitigation even when the registry reports zero findings; reassessment is required by 2026-11-03. Remove patch/special gate only after the unchanged exploit suite verifies an upstream fix or Astro removes the dependency. The deployed asset-only architecture has no affected shared cache.

## ADR-011: Conservative official tracker extraction

Workers AI allowance comes from Cloudflare's open documentation through the GitHub Contents API, preserving the paid-model caveat. Unknown offer/model fields stay unknown or curated. HTML remains disabled. Watch-next events require exact source text/date provenance.

## ADR-001: Static-first over request-time SSR

Decision: build content ahead of time and serve mostly static assets.

Why:
- lower recurring cost;
- lower latency;
- fewer outages;
- AI usage independent of traffic;
- excellent portfolio deployment story.

Tradeoff: updates are periodic rather than second-by-second.

## ADR-002: Four ingestion runs per day

Decision: 6-hour cadence by default.

Why:
- enough freshness for a concise tech briefing;
- low upstream and AI usage;
- resilient to one missed schedule;
- avoids turning the project into an expensive real-time crawler.

Urgent sources can later receive a separate lightweight path.

## ADR-003: RSS/API first, scraping last

Why:
- stability;
- publisher intent;
- lower legal/technical risk;
- less breakage;
- less compute.

## ADR-004: No numeric truth score

Why:
A single score can imply certainty the pipeline does not have. Use evidence labels and source attribution instead.

## ADR-005: No accounts in initial release

Why:
- privacy;
- lower complexity;
- fewer attack surfaces;
- no database required;
- enough utility through local preferences/bookmarks.

## ADR-006: Provider-agnostic AI layer

Why:
Free quotas and model availability change. A provider must be replaceable through configuration.

## ADR-007: Cloudflare Workers Static Assets

Why:
Current Cloudflare guidance recommends Workers for new full-stack/static projects, while keeping static asset delivery inexpensive and globally cached.


## ADR-008: Restrained publication composition and motion — October 12, 2026

Keep the existing static publication architecture and deterministic lead/brief ranking. Use a stronger masthead, warm and dark editorial surfaces, readable type and category teasers that exclude featured stories. Retain obvious original sources and consistent evidence-explanation links. News and facts stay static; only a decorative introductory rule enters once, with short action feedback and full reduced-motion support. Native search/disclosure semantics remain preferable to new overlay or animation dependencies. [Design and release evidence](PRE_RELEASE_REFINEMENT.md).

## ADR-009: Honest bilingual coverage and provisional identity

UI localization and cached story translation remain separate. Publish explicit English fallback when no validated translation exists, retain noindex/canonical rules, and require configured publication-time processing plus native review before claiming a Bangla edition. Exact-name and similar-brand collisions require owner clearance before final public branding; internal identifiers remain unchanged. Durable off-machine backup, real origin/credentials and authorized edge checks remain release operations.
