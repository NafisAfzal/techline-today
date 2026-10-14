# Operations Runbook

## Daily automatic checks

Each ingestion run emits a machine-readable report:
- sources attempted/succeeded/failed;
- raw items;
- new items;
- duplicates;
- clusters created/updated;
- stories summarized by provider;
- provider errors/rate limits;
- extractive fallbacks;
- validation failures;
- deployment status;
- start/end time.

## Failure behavior

### Source failure
Continue other sources. Mark adapter unhealthy. Do not delete existing story data.

### AI provider 429/outage
Backoff, route to the next provider, then extractive fallback.

### Bad model output
Retry once with a repair prompt only if budget allows. Otherwise use extractive fallback.

### Build failure
Do not deploy. Keep existing production version.

### Cloudflare deploy failure
Keep production unchanged. Upload/log build artifact only if the workflow storage policy permits.

## Monthly manual checklist

- confirm scheduled workflow is enabled;
- review provider free-tier/rate-limit changes;
- review top failing source adapters;
- remove dead/disallowed sources;
- rotate credentials according to provider policy;
- dependency updates;
- verify Lighthouse/CWV;
- review source correction requests;
- confirm content archive compaction;
- review Cloudflare/GitHub usage dashboards.

## Adding a source

1. confirm official feed/API/robots/terms;
2. assign source type and independence group;
3. add registry entry disabled by default;
4. run adapter fixture test;
5. run one dry ingestion;
6. inspect extraction and attribution;
7. enable source.

## Removing a source

Disable it in registry. Existing summaries keep their citation metadata unless removal is legally/ethically required. Never silently rewrite history.

## Corrections

If a source corrects material facts:
- mark affected claim updated/retracted;
- regenerate summary;
- add short change-log entry;
- update `last_verified_at`;
- do not remove the correction trail from public detail pages when material.
