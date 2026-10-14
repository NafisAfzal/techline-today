# Cloudflare deployment readiness

**No deployment is authorized or performed.** The [release approval gate](RELEASE_APPROVAL_GATE.md) governs repository/account/origin/cost/rights/backup decisions and the exact approved revision.

Public GitHub and Cloudflare Free are confirmed preferences. [Current preparation and owner decisions](OWNER_GITHUB_LAUNCH_PLAN.md) supersede earlier counts. Official [Astro deployment guidance](https://docs.astro.build/en/guides/deploy/cloudflare/) confirms that static output uses an assets-only Wrangler configuration without the on-demand Cloudflare adapter. The [limits](https://developers.cloudflare.com/workers/platform/limits/) and [static billing](https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/) were rechecked on 2026-10-14: 20,000 Free assets/version, 25 MiB/file, free unlimited static requests. Worker runtime limits do not authorize running Python here.

## Actual target

`wrangler.jsonc` configures Worker `ai-tech-intelligence`, compatibility date `2026-10-03`, assets directory `apps/web/dist`, and `not_found_handling: 404-page`. There is no Worker main script, runtime asset binding, Python service, database or paid storage binding. Astro uses static output. Wrangler's asset-only wrapper is packaging, not a Python scheduler. The proposal uses **Workers Static Assets**, not Pages plus an assumed Python cron.

Build: `pnpm build`; delivery output: `apps/web/dist`. Postbuild emits `_headers` with exact-hash CSP and copies referenced archives; Astro generates localized static data, RSS/sitemap and metadata. No custom `_redirects` file is configured. Workers' HTML routing and `404-page` handling supply normal static route behavior. Hashed assets cache immutably; Pagefind/current data revalidate or expire according to headers, while Cloudflare supplies default HTML cache behavior. Actual edge redirects/cache headers require hosted checks. No visitor inference endpoint exists.

The bundle is limited to 18,000 files (margin under the free 20,000 limit) and 25 MiB per asset. [Official static asset limits and billing](https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/).

## Configuration after approval

- Exact account ID and Worker name must agree with `config/release.json`; actual account eligibility is not verified locally.
- Set `SITE_URL` to the exact credential-free public HTTPS origin, without path/query/fragment/port. Use the approved workers.dev URL initially; purchasing a domain is optional and unauthorized.
- Blank/local/example origins and fixture output are noindex. Production validation rejects them. A successful local test with a temporary canonical origin does not establish ownership or deployment.
- Export `SITE_NOINDEX=true` for a staging build with a real origin. Both HTML robots metadata and robots.txt block indexing; `verify-build --production` rejects it. Clear the flag and rebuild only after publication is approved. No public preview is created by preparation.
- Keep deploy credentials in a protected production environment. Use a selected-account Workers Scripts edit token. No global API key, DNS edit, database or AI permission is required.
- Set `RELEASE_APPROVED_SHA` to the reviewed commit, `PIPELINE_AI_ENABLED=false`, and leave analytics/model credentials unset. Production job permission is read-only for GitHub contents; the deploy token appears only in the deploy step.

## Workflow

Manual-only `ingest.yml` checks owner approval before collection or provider access. It performs frozen installs, Python/frontend/fixture/browser checks, restores successful live state, collects real evidence, validates and builds, scans/crawls/smoke-tests, checks production metadata/editorial freshness, dry-runs Wrangler and retains a two-day asset bundle within the 25 MiB total artifact budget. A publication receipt is recorded only after successful deployment; verified no-change collector checkpoints can also be cached; call reservations are retained independently on failure. CI caches/artifacts are not durable backups.

Proposed schedules run the Python pipeline in GitHub-hosted Linux, not Cloudflare. No schedule trigger is present until owner approval. Single production concurrency and a 30-minute job timeout avoid overlap. Scheduling limitations/manual recovery are in [operations](OPERATIONS.md).

## Commands after owner approval only

```sh
# Configure secrets securely and the approved origin/revision in the environment.
uv run python -m pipeline --mode live
uv run python -m pipeline --validate
pnpm build
pnpm security
pnpm verify:site
pnpm smoke:live
node scripts/verify-build.mjs --production
node scripts/editorial-quality.mjs --production
pnpm deploy:check
pnpm deploy
```

`pnpm deploy` checks authorization before Wrangler. `pnpm deploy:check` packages a dry-run and does not publish. Local verification clears Cloudflare credential variables and disables Wrangler telemetry. Neither proves edge configuration, DNS ownership, account limits or token scope.

After the first approved deployment, verify HTTPS routes/404, external citations, CSP/security/cache headers, compression, search assets, both themes/locales, canonical/OG/robots/sitemap and RSS. Save the successful version identifier. Rollback uses `pnpm exec wrangler rollback APPROVED_GOOD_VERSION_ID` only with owner-authorized credentials/destination. [Cloudflare versions and deployments](https://developers.cloudflare.com/workers/versions-and-deployments/), [Wrangler rollback command](https://developers.cloudflare.com/workers/wrangler/commands/workers/).

## Final audit safeguards

Every build now records the actual code revision and SHA-256 identities for relevant source inputs, the snapshot, monthly/yearly archives and the complete asset tree. Verification rejects a stale or modified bundle. Publication refuses a dirty checkout or a mismatch between checked-out HEAD and the claimed workflow revision. Local visibility requires actual GitHub metadata after owner approval; no credentials are used for the current unapproved gate.

A missing successful-production cache no longer silently seeds a seven-day edition. It blocks collection unless an explicitly approved initial seed is requested through the manual `allow_initial_seed` dispatch input (default false), and `config/release.json` authorizes that seed. After first successful publication, revoke `initial_seed_authorized`, remove the initial-seed option from operational use and approve the resulting revision before recurring publication. A later cache miss requires restoration from the durable generation; do not use reseeding as recovery.

Production AI/translation remains blocked until model-specific monetary enforcement and durable quota accounting are implemented and independently reviewed. Merely entering a positive cost ceiling does not enable inference. The current release proposal uses deterministic extraction only.

## Separate initial destinations

Production remains `ai-tech-intelligence`; preview is `ai-tech-intelligence-preview` from `wrangler.preview.jsonc`. The gate requires different Worker names/origins and the confirmed account subdomain: `https://WORKER.ACCOUNT_SUBDOMAIN.workers.dev`. Neither account/subdomain nor URL is known yet. This is a URL pattern, not an existing service. No workers.dev hostname is reserved.

Preview is a separate public noindex Worker, not an assumed private access-controlled preview. Gate B requires completed GitHub/hosted CI and explicit publication authorization. Gate C additionally requires hosted preview and durable restore proof. Local dry-runs clear credential variables and do not prove account eligibility, edge Link/header behavior, actual rollback or hosted search/navigation. See the current launch plan for commands and exact remaining approvals.
