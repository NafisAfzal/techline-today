# Operations, backups and recovery

This is a prepared runbook, not proof of operational services. No external schedule, monitor, durable backup destination or deployment is enabled. The owner/operator is responsible for review, publication, recovery and account limits.

## One-time setup after authorization

1. Complete [the owner release gate](OWNER_GITHUB_LAUNCH_PLAN.md): ownership/license, source/brand rights, exact destinations, off-machine restoration and zero-spend account controls. Use [Windows setup](LOCAL_SETUP_WINDOWS.md) for Node 24, pnpm 10.33.1, uv 0.12.22 and Python 3.13. Frozen lock installs are required.
2. After expressly authorized public repository creation, keep Actions disabled for the initial push. Review staged files/history and public author identity; repository-local author email is now the verified account ID/login noreply address; global identity is unchanged. Enable validation later with the owner's approval.
3. In the approved Cloudflare Free account, confirm a workers.dev subdomain and the existing Wrangler name. Do not connect Workers Builds/Pages auto-deploy, paid bindings or a domain purchase. No Cloudflare runtime secrets or Python service are needed for this asset-only site. Verify current plan and account consumption.
4. Prepare the GitHub `production` environment: restrict it to main, restrict environment branches and use reviewers only where useful and supported; this single-owner project has no co-owner approval requirement, and require passing validation. A solo owner's unavailable reviewer feature is not silently treated as protection; record the alternative approval process. Keep default token contents permission read-only and checkout credentials disabled. Configure branch protection and secret scanning/push protection where supported; exact check names are established by the first hosted CI run.
5. Supply only the selected-account Workers Scripts edit token as environment secret `CLOUDFLARE_API_TOKEN`. Add the approved account ID as `CLOUDFLARE_ACCOUNT_ID` variable for preflight and matching secret for deployment. Set variables `SITE_URL`, `RELEASE_APPROVED_SHA`, `PIPELINE_AI_ENABLED=false`; leave analytics/provider/model keys unset. `PRODUCTION_ENABLED` remains false until the exact first-deployment approval. Enter tokens through the secure GitHub UI/secret prompt; never put them in a command, transcript, artifact or `.env.example`.
6. Update the release plan with supported owner decisions and selected LICENSE. Bind the reviewed executable commit to `RELEASE_APPROVED_SHA`. Approve initial seeding only for a truly first publication; do not use it after cache loss. Dispatch the manual workflow, find its exact run ID, and use `gh run watch APPROVED_RUN_ID --repo APPROVED_OWNER/techline-today --exit-status` before asserting success.
7. Verify the actual hosted URL with `smoke:production`, record its Cloudflare version and private matching data generation, test hosted rollback, and revoke initial-seed authority. Keep schedules disabled until durable cache-import recovery and owner schedule approval are complete.

| Configuration | Location and purpose |
|---|---|
| `SITE_URL` | Shell build environment / GitHub production variable; exact approved HTTPS origin, no path/credentials |
| `SITE_NOINDEX=true` | Explicit staging build isolation; clear only for approved production and rebuild |
| `SMOKE_BASE_URL`, `SMOKE_EXPECT_INDEXING` | Read-only hosted smoke; actual origin plus true production/false staging |
| `SMOKE_CANONICAL_ORIGIN` | Optional local or preview proof when canonical and inspected origin intentionally differ |
| `PIPELINE_AI_ENABLED=false` | Python environment and release workflow; no inference or paid provider needed |
| `PIPELINE_USER_AGENT` | Optional respectful publisher identification; no confidential contact details |
| `PRODUCTION_ENABLED`, `RELEASE_APPROVED_SHA` | Repository/environment publication switch and exact reviewed revision |
| Deploy token/account ID | Protected environment secret and matching account variable; absent during local dry-runs |
| Optional provider keys | Unset; production inference remains prohibited pending separate cost/durability review |

Root `.env` is loaded by Python; Astro's public origin/staging settings must be exported in the shell or workflow environment. Do not expect editing `.env` alone to change canonical metadata.

## Preview and manual refresh

Before authorization, preview only on loopback with `pnpm.cmd build` and `pnpm.cmd preview`. For a future approved external preview, export its approved `SITE_URL` and `SITE_NOINDEX=true`, build and inspect robots/canonical output, then obtain explicit preview publication authorization. A Workers version URL can still be publicly accessible; noindex is not access control. No preview upload command is run in preparation. [Cloudflare version URLs](https://developers.cloudflare.com/workers/versions-and-deployments/version-urls/).

After launch, manual refresh dispatches the approved `ingest.yml` revision. Wait for the exact run and inspect its summary. For local diagnosis use `py -3.12 -m uv run python -m pipeline --mode live`, validate and rebuild; it does not itself deploy. Never refresh with fixtures. A semantic fingerprint includes code revision, content/corrections/order, digest period status and normalized archives, excluding collection-only times and internal score changes. An unchanged run skips the live build/deployment and saves a verified collector checkpoint with its previous publication receipt. Failed collection keeps prior served assets. There is no timestamp-only heartbeat deployment.

## Signals and proposed cadence

Read `content/generated/run-report.json`: source outcomes, filtered/raw items, duplicate count, validation failures, summary modes, provider reservations and translation coverage. Review every failed production workflow, collection age over 24 hours, no prose-backed story within 72 hours, a duplicate-rate change above 50% of the prior successful run, provider quota exhaustion and missing archive state. GitHub's normal failure notifications are the proposed initial alert mechanism; no third-party alert integration is configured.

Manual publication first. Proposed UTC cron `17 1,7,13,19 * * *` corresponds to Asia/Dhaka 07:17, 13:17, 19:17 and next-day 01:17. Twelve-hour overlap and last-success tracking help recover missed collection, subject to feed/API retention. Jobs have a 30-minute timeout and serialized production concurrency. Schedules can be delayed/dropped; public schedules can be disabled after 60 days' repository inactivity. Check daily freshness and monthly schedule status; manually rerun `ingest.yml` on the approved revision. [GitHub schedule behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

## Failure procedures

| Incident | Response and recovery |
|---|---|
| Total ingestion failure / stale edition | Keep deployed assets; inspect source statuses without logging credentials. Retry manually after recovery. Never publish a fixture or refresh timestamps to conceal stale evidence. |
| Malformed RSS / individual source outage | Quarantine invalid entries; healthy sources proceed. Confirm parser/terms and compare original URLs. Retain last verified evidence; disable a source if unsafe. |
| Duplicate surge / weak extraction / wrong category | Inspect representative originals and transformation version; fix deterministic logic and regressions. Recollect/validate and review prominent stories. Preserve IDs, canonical titles and correction history. |
| Provider outage / exhausted quota | Keep inference disabled or fall back to extraction. Respect reserved-call ledger and retry limits. Do not rotate providers to evade an approved budget. |
| Build/security/editorial failure | Deployment is not invoked. Fix the failing gate, repeat affected tests and build a fresh live candidate. |
| Deployment failure | Keep the prior successful Cloudflare version. Candidate data/build artifact can be inspected; only successful deployment state becomes the published cache. Verify actual edge version before reporting success. |
| Bad released content | Disable production, preserve evidence, publish a corrected validated edition or roll back to the recorded good version. Restore matching data state before the next collection. |
| Dependency vulnerability | Disable publication if exposure is material; review lockfiles, patch behavior and full audits. Never suppress an advisory globally. Cache mitigation reassessment is due 2026-11-03. |

## State boundaries

Live conditional fetch state, last snapshot, provider usage and translation cache are separate from fixtures. A 304 verifies only records belonging to the exact response. An old absent story retains its previous verification timestamp. Ingestion stages archive writes and validates before snapshot replacement. Local candidate state is not evidence of deployment; collector checkpoints are saved after successful publish or a proven semantic no-change run; publication receipts change only after deployment, and provider reservations persist separately.

Individual stories normally retain 548 days, subject to a 4,000-story compaction ceiling. Monthly archive bundles preserve facts/sources/history. A compacted old URL can use the archive-aware 404 recovery path.

## Backup and restoration

`python -m pipeline.backup` exports an allowlisted live-data pack with byte lengths/SHA-256 manifests. It includes generated snapshot/run report/briefing, live state/last snapshot/provider ledger/translation cache when present, and only snapshot-referenced month/year archives. It excludes credentials, node_modules, fixture caches, orphan archives and arbitrary files. Verification rejects corruption, non-live snapshots, extra/missing archives, duplicate/injected paths and symlinks. Restoration requires an empty destination and never overwrites an existing working tree. [Manifest, source backup, retention and recovery assumptions](BACKUP_RECOVERY.md).

```powershell
py -3.12 -m uv run python -m pipeline.backup export BACKUP_GENERATION_DIRECTORY
py -3.12 -m uv run python -m pipeline.backup verify BACKUP_GENERATION_DIRECTORY
py -3.12 -m uv run python -m pipeline.backup restore BACKUP_GENERATION_DIRECTORY --destination EMPTY_RESTORE_DIRECTORY
```

Use new generation directories. Local export/isolated restoration are testable here; **durable off-machine storage is not provisioned**. Owner proposal: encrypted access-controlled versioned destination; 14 daily, 8 weekly and 12 monthly successful generations. Include the code commit and Cloudflare version in the operator's generation record. Keep backup data private because excerpts and caches have separate content rights. Perform an independent restore before launch and quarterly thereafter. Cache eviction must not reset a paid provider's budget: paid inference remains blocked pending a durable quota ledger.

Restore procedure: verify manifest, restore into an empty directory, copy only reviewed data paths into an isolated checkout of the matching code revision, run contract/editorial/build/security checks, inspect history and source links, then deploy through the approval gate. Never restore credentials from data packs. Set `PRODUCTION_ENABLED=false` during recovery.

## Rollback

After an authorized launch, record each successful Cloudflare version and retain its Actions static bundle for **two days** under the 25 MiB total bundle budget. Durable operator generations have separate retention. `pnpm.cmd exec wrangler rollback APPROVED_GOOD_VERSION_ID` creates a deployment and requires explicit recovery authorization plus the approved account/token. Verify edge routes and then restore matching ingestion state to avoid republishing the bad candidate. [Cloudflare versioned rollback](https://developers.cloudflare.com/workers/versions-and-deployments/rollbacks/). Local tests do not establish a remote rollback or off-machine restore.

## Regular operation and optional enhancements

Daily: inspect freshness, failed-run notifications/source outcomes and the served edition. Per release: preserve matching code/data/version records. Monthly: review schedule health, account storage/zero-spend controls, source terms, dependency updates and backup capacity. Quarterly: independently restore off-machine generations and exercise authorized rollback. Patch dependencies in an isolated branch, regenerate notices if needed, repeat frozen audits and affected tests, then bind a new approved revision. The cache-policy mitigation review deadline is 2026-11-03.

Scheduling at roughly six hours is proposed, not enabled; GitHub delays mean it is not a clock guarantee. Initial monitoring uses the owner's verified Actions email notifications and manual hosted smoke/freshness checks. No external uptime monitor is provisioned. Optional enhancements—external alerts, AI/native-reviewed Bangla, analytics, a custom domain, automated durable backup/import—require their own owner authorization, quota/rights/privacy review and tests. No paid enhancement is part of the current plan.

## Final audit safeguards

Every build now records the actual code revision and SHA-256 identities for relevant source inputs, the snapshot, monthly/yearly archives and the complete asset tree. Verification rejects a stale or modified bundle. Publication refuses a dirty checkout or a mismatch between checked-out HEAD and the claimed workflow revision. Local visibility requires actual GitHub metadata after owner approval; no credentials are used for the current unapproved gate.

A missing successful-production cache no longer silently seeds a seven-day edition. It blocks collection unless an explicitly approved initial seed is requested through the manual `allow_initial_seed` dispatch input (default false), and `config/release.json` authorizes that seed. After first successful publication, revoke `initial_seed_authorized`, remove the initial-seed option from operational use and approve the resulting revision before recurring publication. A later cache miss requires restoration from the durable generation; do not use reseeding as recovery.

Production AI/translation remains blocked until model-specific monetary enforcement and durable quota accounting are implemented and independently reviewed. Merely entering a positive cost ceiling does not enable inference. The current release proposal uses deterministic extraction only.

## Current preview and monitoring contract

`preview.yml` is manual-only, gated by `PREVIEW_ENABLED=true`, the preview environment and Gate B. It uses `wrangler.preview.jsonc`, a separate Worker/origin and `SITE_NOINDEX=true`. `ingest.yml` is manual-only, gated by production environment and Gate C; no schedule is active. Hosted CI/free-plan evidence is required before either deploy. Account and workers.dev subdomain remain unconfirmed. No automatic Workers Builds connection is proposed.

State cache generation is `production-data-v3`: six allowlisted files today, plus an optional seventh publication receipt after deployment. Never import a legacy/contaminated generation blindly. Cache miss blocks unless a separately approved genuine first seed is requested. Later recovery requires the off-machine generation and a tested cache-import procedure; recurring execution remains blocked until that procedure/destination is selected.

Production smoke rejects served edition age above 24 hours. This is an edition-age signal, not proof that ingestion stopped: a healthy unchanged weekend may retain an older edition. Inspect the last successful collector run and no-change checkpoint separately. Postdeploy smoke runs only after changed releases, so it does not monitor silent collector failure. Initially the owner must check Actions failure notifications and collector freshness daily; no external monitor exists. Four daily attempts are a proposal. At the measured local runtimes, a 30-minute workflow ceiling leaves margin, but Ubuntu/network/queue duration and account storage must be verified in hosted runs.

Tokens belong only in environment secrets, account/origins in environment variables. Preview uses `PREVIEW_SITE_URL`; production uses `SITE_URL`; each has `RELEASE_APPROVED_SHA`. The first hosted CI run establishes exact required check names. Personal ownership does not imply a paid environment protection feature or a second reviewer; maintain explicit owner/revision approval even if a plan lacks reviewer controls.

At the initial four-attempt cadence, a 25 MiB maximum rollback artifact retained two days implies at most about 200 MiB of release artifacts in steady state, plus other account artifacts/Packages. [Current GitHub billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions) lists 500 MB shared artifact allowance for Free and separate 10 GB included cache per repository; do not raise paid cache capacity or use larger runners. Keep cache limit within allowance and verify owner account budgets/other repositories before enabling automation. No billing settings were changed here.
