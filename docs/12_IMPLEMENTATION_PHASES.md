# Implementation Phases

## Phase 0 - foundation

Deliver:
- monorepo/tooling;
- Astro shell;
- design tokens;
- data contracts;
- source registry;
- test fixtures;
- CI checks.

Exit: local site renders fixture stories on mobile and desktop.

## Phase 1 - ingestion MVP

Deliver:
- RSS/Atom adapter;
- Hacker News discovery adapter;
- GitHub release adapter;
- generic official API adapter;
- allowed HTML extractor;
- canonicalization;
- dedupe;
- local ranking;
- JSON output.

Exit: one command produces validated `latest.json` from live configured sources.

## Phase 2 - evidence + AI

Deliver:
- claim extraction;
- AI provider interface;
- Workers AI provider;
- Gemini/Groq/OpenRouter adapters;
- generic OpenAI-compatible provider;
- extractive fallback;
- schema validation;
- prompt-injection resistant prompts.

Exit: provider failure does not stop output generation.

## Phase 3 - product UI

Deliver:
- 60-second briefing;
- category pages;
- story details;
- source panel;
- search;
- bookmarks;
- theme;
- responsive navigation;
- skeleton/empty/error states.

Exit: Lighthouse/accessibility targets and E2E pass.

## Phase 4 - special trackers

Deliver:
- AI release tracker;
- free API/credit tracker;
- expiry automation;
- jobs/skills pulse;
- device/chip structured cards.

## Phase 5 - digests and automation

Deliver:
- daily/weekly/monthly/yearly builders;
- scheduled GitHub workflow;
- manual dispatch;
- run report;
- fail-safe previous snapshot;
- Cloudflare deploy.

## Phase 6 - hardening

Deliver:
- CSP/security headers;
- secret scanning;
- dependency pinning/updates;
- source adapter health checks;
- archive compaction;
- analytics;
- documentation.

## Phase 7 - optional growth

Only after real usage:
- Worker API;
- D1 accounts/preferences;
- notification service;
- email digest;
- custom alerts;
- monetization modules.
