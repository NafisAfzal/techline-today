# Testing and Acceptance Criteria

## Unit tests

Pipeline:
- URL canonicalization;
- source allowlist;
- private-IP/SSRF rejection;
- title normalization;
- duplicate detection;
- story clustering edge cases;
- ranking score bounds;
- evidence-state assignment;
- provider fallback;
- JSON schema validation;
- offer expiry transitions.

Frontend:
- filters;
- bookmark local storage;
- time-period switch;
- search result rendering;
- source-link rendering;
- no unsafe HTML rendering.

## Contract tests

Every generated story must pass JSON Schema/Pydantic validation before build.

Golden fixtures should cover:
- single official release;
- official + two independent reports;
- conflicting benchmark numbers;
- rumor/community-only item;
- expired free offer;
- corrected story;
- missing publication time;
- non-English source.

## Integration tests

Test source adapters against saved fixtures, not live websites, during normal CI. Live adapter health checks run separately and should not block PR tests.

## E2E

Use Playwright for:
- homepage loads;
- category navigation;
- mobile viewport;
- Details route;
- Original source link has safe attributes;
- bookmark survives reload;
- keyboard search;
- theme persists;
- 404 and empty-state behavior.

## Accessibility

Automate axe checks on core routes. Manually test keyboard focus order and screen-reader labels before release.

## Performance

Production acceptance:
- avoid shipping unnecessary JS;
- no layout shift from late card dimensions;
- compressed assets;
- no third-party marketing scripts in V1;
- Lighthouse CI thresholds defined, but tests should tolerate reasonable CI variance.

## Security

- secret scan;
- dependency audit;
- code scanning if available;
- test CSP locally/preview;
- verify PR workflows cannot access production secrets;
- fuzz/negative tests for URL fetch validation.

## Content quality acceptance

A story fails publication if:
- original source URL is absent;
- key numeric fact cannot be mapped to evidence;
- generated summary contradicts source;
- evidence state is inconsistent;
- text is duplicated from a source beyond a small permitted excerpt;
- free offer lacks `last_verified_at`;
- an expired offer is marked active.

## Definition of done for V1

- responsive desktop/tablet/mobile;
- four scheduled ingestion runs/day plus manual trigger;
- at least five categories operating;
- daily/weekly/monthly digest code paths;
- source-grounded short and broader summaries;
- direct original source access;
- local bookmark/preference system;
- search;
- freebie tracker;
- one model-release structured view;
- security headers;
- automated tests;
- Cloudflare deployment documentation;
- zero required paid service for normal operation.
