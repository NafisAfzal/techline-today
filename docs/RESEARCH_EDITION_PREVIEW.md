# Research preview preparation and release runbook

Status: local synthetic rehearsal only. No Cloudflare account has been selected, modified or queried. No login, upload, deployment, push, PR or merge is authorized. The [research policy](RESEARCH_EDITION_POLICY.md) reports zero real eligible records and requires a separate reviewed approval implementation before a public research edition.

## Static hosting profile

[Research Wrangler configuration](../wrangler.research-preview.jsonc) targets the existing isolated preview Worker name `ai-tech-intelligence-preview`, distinct from production `ai-tech-intelligence`, using only `apps/web/dist-research`. It has no Worker entrypoint, SSR adapter, AI, database, KV, D1, R2, Queues, cron, service binding or paid observability. `run_worker_first=false`; version preview URLs are disabled. The account and actual workers.dev subdomain remain unset. No custom domain or automatic Git deployment is configured by this work.

[Cloudflare's Static Assets billing](https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/) documents free unlimited static asset requests and no extra asset storage cost. Worker execution is a separate metered path; this profile supplies no application Worker. The project enforces conservative budgets of 18,000 assets, 25 MiB per asset and 25 MiB total for rollback storage, below the documented Free asset count/size limits. Recheck [platform limits](https://developers.cloudflare.com/workers/platform/limits/) and actual account billing before any future authorization. No account-level zero-spend guarantee is inferred from a config file.

HTML noindex, robots disallow, `X-Robots-Tag`, `Cache-Control: no-store`, no-referrer, CSP, HSTS, permissions policy and download attribution are prepared. [Static Assets headers](https://developers.cloudflare.com/workers/static-assets/headers/) support this static response mechanism. Public workers.dev is not private; noindex does not restrict access or guarantee removal from search. Revocation/removal cannot recall material already downloaded. Edge headers, canonical redirects, caching and remote rollback remain untested until a separately authorized deployment.

## Reproduce locally without deployment

Run only in a new isolated worktree with no live snapshot. Node 24, pinned pnpm and frozen uv dependencies are required. The Python commands below use `uv`; Windows may invoke the installed launcher as `py -3.12 -m uv`.

```powershell
pnpm install --frozen-lockfile
uv sync --frozen
uv run python -m pipeline --mode fixture
uv run python -m pipeline --validate
pnpm build:research
pnpm verify:research
pnpm test:research
pnpm preview:research
```

The last command binds loopback only. Stop it with Ctrl+C. Do not run fixture generation in the original canonical-data workspace. The separate research browser suite covers all generated HTML routes, static assets, noindex/headers, missing routes, synthetic-only selection, search, both themes, accessibility and Bangla fallback. The ordinary browser suite continues to run against the full fixture edition in `apps/web/dist`.

## Minimal owner setup for a future authorized session

1. Create or select the intended Cloudflare account; enable 2FA and retain recovery codes offline.
2. Verify the actual Workers Free plan, billing and zero-spend settings. Do not enable paid Workers, AI, storage, databases, queues, addons or paid products.
3. Select the account's workers.dev subdomain. Confirm the exact origin `https://ai-tech-intelligence-preview.<confirmed-subdomain>.workers.dev` and account ID; this document does not invent either value.
4. Verify Workers Builds/Git integrations and deploy hooks are absent/disabled. Keep `PREVIEW_ENABLED` and `PRODUCTION_ENABLED` unset/false and all recurring schedules disabled. Do not use the existing news preview workflow for this research rehearsal.
5. Resolve item rights/editorial/checkpoint requirements and approve the separately reviewed research adapter and eligible content manifest. No reviewer signatures or consent may be fabricated. Confirm brand and content scope, backup/restore and local rollback evidence.
6. Review the exact future code SHA, content/input digest, asset digest, account, public preview origin and rollback version. Issue separate exact-SHA authorization for the specific external action. Use a least-privilege token scoped to the selected account only; never store it in Git or static assets.

These are instructions, not account actions executed by this preparation.

## Exact preflight and deployment sequence, future session only

This template uses values supplied by that session's owner authorization. It is intentionally blocked on the current implementation. A new reviewed implementation/SHA is required to add a public research build and replace the deny-only research publication preflight. Never remove the refusing check to force this rehearsal through. The current news `deploy:preview` script is not a research deployment shortcut.

```powershell
$ErrorActionPreference = 'Stop'
function Require-Success { if ($LASTEXITCODE -ne 0) { throw 'Preflight stopped; no deployment permitted' } }
$reviewedSha = '<exact-40-character-owner-approved-future-SHA>'
$expectedAccount = '<confirmed-32-character-account-id>'
$expectedSubdomain = '<confirmed-workers-dev-subdomain>'
$env:RELEASE_APPROVED_SHA = $reviewedSha
$env:CLOUDFLARE_ACCOUNT_ID = $expectedAccount
$env:SITE_URL = "https://ai-tech-intelligence-preview.$expectedSubdomain.workers.dev"
$env:SITE_NOINDEX = 'true'
$env:PIPELINE_AI_ENABLED = 'false'
$env:WRANGLER_SEND_METRICS = 'false'
$env:ASTRO_TELEMETRY_DISABLED = '1'
if ($reviewedSha -notmatch '^[a-f0-9]{40}$' -or (git rev-parse HEAD).Trim() -ne $reviewedSha) { throw 'SHA mismatch' }
if (git status --porcelain) { throw 'Dirty checkout' }
node scripts/release-gate.mjs --publish --preview
Require-Success
# The separately reviewed future build must already bind eligible real content,
# exact SITE_URL and the approved public research profile. Current rehearsal denies.
node scripts/verify-research.mjs --publish
Require-Success
pnpm exec wrangler whoami
Require-Success
# Review whoami against expectedAccount; do not continue on an account mismatch.
pnpm exec wrangler deployments list --config wrangler.research-preview.jsonc
Require-Success
# Record the known-good prior VERSION ID, not just the deployment ID, privately.
pnpm exec wrangler deploy --config wrangler.research-preview.jsonc --dry-run
Require-Success
# Only after all preflights pass and exact artifact/account authorization is current:
pnpm exec wrangler deploy --config wrangler.research-preview.jsonc
Require-Success
curl.exe --fail --head "$env:SITE_URL/"
Require-Success
curl.exe --fail "$env:SITE_URL/robots.txt"
Require-Success
```

The current `--publish` check must fail before `whoami` or any upload. Token injection uses the future session's approved secret channel. Never paste tokens into these commands, logs or reports. The release plan remains unmodified here, so its account/origin/preview authorization checks also refuse today. A future approved change must retain those controls while binding the research-specific artifact and policy.

## Exact rollback and first-deployment removal, future session only

Review/authorize the exact account, Worker and known-good version before executing. Preserve an independently verified source/content/asset pack outside Git. Native rollback is applicable only when a valid prior version exists; after a first deployment there may be none.

```powershell
$ErrorActionPreference = 'Stop'
$env:WRANGLER_SEND_METRICS = 'false'
# Verify CLOUDFLARE_ACCOUNT_ID against the separately authorized account first.
pnpm exec wrangler deployments list --config wrangler.research-preview.jsonc
if ($LASTEXITCODE -ne 0) { throw 'Cannot verify current deployment' }
$knownGoodVersion = '<verified-known-good-worker-version-uuid>'
if ($knownGoodVersion -notmatch '^[a-f0-9-]{36}$') { throw 'Missing rollback version' }
pnpm exec wrangler rollback $knownGoodVersion --config wrangler.research-preview.jsonc --message 'Restore reviewed research preview' --yes
if ($LASTEXITCODE -ne 0) { throw 'Rollback failed; use authorized removal procedure' }
curl.exe --fail --head "$env:SITE_URL/"
if ($LASTEXITCODE -ne 0) { throw 'Rollback smoke failed' }
```

For the first-ever preview or a rights/privacy withdrawal requiring removal, separately authorize deletion of this preview Worker and then use the exact command below. It deletes the preview service and its history; never target production. Independently verify the public origin stops serving and retain incident evidence. There is no remote rollback proof in this local preparation.

```powershell
pnpm exec wrangler delete --config wrangler.research-preview.jsonc --name ai-tech-intelligence-preview
if ($LASTEXITCODE -ne 0) { throw 'Preview removal failed' }
```

No command in the deployment or rollback sections was executed here. Local Wrangler `--dry-run` packaging and CLI help are the only Wrangler operations permitted during preparation; they do not prove account readiness or hosted behavior.
