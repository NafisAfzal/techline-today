# Product Specification

## Product outcome

Build a fast, visually polished technology intelligence product that helps a reader answer five questions quickly:

1. What happened?
2. Why does it matter?
3. What are the important numbers or limitations?
4. How confident should I be in this update and what kind of sources support it?
5. Where can I read the original material?

The product is not a content farm and not a chat wrapper. Its value is curation, compression, evidence, organization and change tracking.

## Primary personas

### Fast reader
Has 30 to 60 seconds. Wants the five most important stories without scrolling through long prose.

### Student/developer
Wants new models, APIs, free credits, open-source releases, claim instructions, pricing changes and useful developer opportunities.

### Research/AI reader
Wants model releases, benchmark context, paper highlights and clear separation between vendor claims and independent results.

### Device enthusiast
Wants meaningful phone, laptop, GPU, CPU and chip news with key specifications rather than long launch articles.

## Information architecture

Top-level navigation:
- For You
- AI
- Research
- Dev & APIs
- Freebies
- Jobs & Skills
- Chips
- Devices
- Security
- Open Source
- Digests

Secondary time controls:
- Latest
- Today
- This Week
- This Month
- This Year

## Story card contract

Every visible card should fit in a compact viewport and contain only high-value content.

Required:
- category label;
- headline rewritten only for clarity, never clickbait;
- three concise key points;
- one-line `Why it matters`;
- up to three important fact chips;
- published age and last-checked time;
- evidence label;
- source count;
- `Details` action;
- `Original` action.

Optional:
- `New since yesterday` delta;
- free/paid/limited availability badge;
- benchmark claim attribution;
- expiry badge for offers.

## Details view

Sections, in this order:
1. 30-second summary
2. Key facts
3. Why it matters
4. What changed / timeline
5. Broader context
6. What different sources say
7. Limitations or uncertainty
8. Sources

Do not bury the source links at the bottom only. Important facts should have source indicators.

## Evidence labels

Avoid displaying a fake numeric “truth score.” Use understandable evidence states:
- Primary confirmed
- Multiple independent sources
- Single credible source
- Community report
- Needs verification

For benchmark/performance claims, always identify the claimant, for example `Vendor-reported` or `Independent benchmark`.

## Special product modules

### AI Release Tracker
Structured fields:
- provider/model
- release date
- modality
- context window when known
- pricing/free availability
- API availability
- open/closed weights
- benchmark claims
- independent benchmark references
- key change from previous model

### Free API & Credit Tracker
Structured fields:
- provider
- offer name
- amount/limit
- eligibility
- geography if relevant
- credit card requirement
- expiration date
- last verified
- claim steps
- official source
- integration notes

Expired offers are automatically archived rather than silently removed.

### Jobs & Skills Pulse
Do not become a generic job board in V1. Aggregate signals such as:
- rising role titles;
- frequently requested AI/ML skills;
- notable layoffs/hiring announcements from reliable sources;
- selected legitimate free internships/programs.

Individual job listings can be added later with explicit source and expiry handling.

### Device & Chip Snapshot
For launches, show a small comparison grid containing only decision-relevant changes: performance, efficiency, process node, memory, price, battery, display, availability and meaningful generation-over-generation differences.

## Personalization

V1, no account:
- category preference stored locally;
- bookmarks stored locally;
- hidden/read items stored locally;
- compact/comfortable density preference;
- theme preference.

V2 account sync:
- favorites and saved searches;
- email/web-push alerts;
- cross-device read state;
- custom keyword watchlists.

## Language

Architect for locale files from day one. Recommended launch:
- English full site
- optional Bangla summary for the daily top stories

Do not automatically translate source quotations. Preserve the original source language and mark translated AI summaries as summaries.

## Non-goals for V1

- no unrestricted chatbot over the open web;
- no full article mirroring;
- no user-generated public comments;
- no complex social network;
- no real-time trading/news terminal promise;
- no paywall bypassing;
- no arbitrary URL scraper endpoint.
