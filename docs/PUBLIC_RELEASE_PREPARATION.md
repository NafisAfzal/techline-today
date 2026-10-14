# Techline Today public release preparation

> Historical release evidence. The [owner launch plan](OWNER_GITHUB_LAUNCH_PLAN.md) and [current verification](OWNER_LAUNCH_VERIFICATION.md) supersede identity, licensing, source coverage, backup and workflow status below. Older counts and pending ownership statements are not current proof.

**RELEASE AUTHORIZATION GATE — NO-GO for external publication.** Public GitHub visibility and Cloudflare Free hosting are approved preferences. Creating a repository, pushing, deploying, indexing publicly, activating recurring automation and paying for services are not authorized. Preparation does not grant those permissions.

The approved frontend appearance, responsive rules, typography, themes, search and ticker are preserved. This pass strengthens backup isolation, software notices, staging/production indexing checks, workflow state recovery and release controls. [Evidence inventory](READINESS_INVENTORY.md), [exact verification](PUBLIC_RELEASE_VERIFICATION.md), [independent review](PUBLIC_RELEASE_REVIEW.md).

| Question | Evidence-based answer |
|---|---|
| A. Is local Git safe to publish? | Technically prepared for final review, **not approved for publication**. No existing commits/refs/remotes; prospective-file and redacted secret scans are required and recorded in verification. Owner rights and durable-backup blockers remain. |
| B. Proposed repository name? | `techline-today`, public, default branch `main`. Candidate owner from authenticated CLI: `NafisAfzal`; the owner must confirm the intended personal account/organization. |
| C. Name sufficiently cleared? | **No.** Preliminary exact-name search was inconclusive; publication-adjacent TechLine usage exists. No trademark/legal clearance or reliable account reservation. [Naming review](BRAND_NAMING_REVIEW.md). |
| D. Public files/artifacts? | Source, config, locks, tests, synthetic fixtures, workflows, prompts, docs, SVGs, software notices and curated screenshots in Git. Live news stays out of Git but appears in built HTML/JSON/search/RSS/archives, proposed Actions caches and release artifacts. [Exact boundary](CONTENT_RIGHTS_REVIEW.md). |
| E. Recommended license? | MIT after confirming all project ownership; Apache-2.0 is an alternative for an explicit patent grant. No owner LICENSE added. Third-party notices are included separately. |
| F. Content/image rights unresolved? | **Yes.** Confirm each source's excerpt/summary/translation/screenshot rights, Cloudflare CC attribution and NVIDIA restrictions. No publisher image/logo is bundled. Factual metadata and source expression have different rights. |
| G. Off-machine backup complete? | **No.** Corrected local data export/checksum/isolated restoration and source export are evidenced locally. Destination, encryption/key custody, independent machine restore and hosted cache-import recovery remain outstanding. |
| H. Recommended Cloudflare architecture? | Astro 7 static output → Wrangler → **Workers Static Assets**, `apps/web/dist`, Worker `ai-tech-intelligence`, `404-page`; no Python runtime/SSR/database/bindings. |
| I. Verified free-tier fit? | Asset-only requests are free/unlimited; Free limit 20,000 assets/version and 25 MiB/file. Project enforces 18,000 assets, existing JS/CSS budgets and a new 25 MiB total rollback-bundle budget. Actual account plan/storage remains unverified. [Costs](SERVICES_AND_COSTS.md). |
| J. Automatic news updates? | Proposed GitHub-hosted Actions every roughly six hours after manual launch and separate schedule approval; Python ingestion → validation/dedup/classification → extraction → snapshot → Astro → gates → deployment. **No active schedule.** |
| K. Failed updates? | Workflow failure notifications and summaries; stale/content/build checks block deployment; previous hosted edition and successful state pack remain. Missing state requires durable recovery, never silent reseeding. [Operations](OPERATIONS.md), [backup recovery](BACKUP_RECOVERY.md). |
| L. CI/deployment separated? | PR/main validation has no publication secrets; manual deployment is default-branch/environment/repository-switch/approved-revision gated. `approved=false`, schedule=false and no cron. No remote automation was enabled. |
| M. Credible English-first launch? | Technically yes, subject to P1 blockers and editorial review: deterministic English summaries with source citations and explicit evidence limits; no paid AI dependency or invented AI claim. |
| N. Bangla status? | Localized UI/routes work; live stories have zero validated Bangla translations. English fallback is explicit; authored translated fixtures are test-only. Full reporting needs a capable provider, native review and independently verified quota/cost controls. |
| O. Exact blockers? | Publication authorization/identity/origin/revision; ownership/license; brand and source-content/screenshot rights; durable off-machine backup/restore; account free-storage/zero-spend confirmation. Scheduled recovery additionally needs destination-specific import proof. |
| P. Required owner actions/credentials? | Confirm exact GitHub owner/repository and Cloudflare account/Worker/origin; approve source ownership/license, brand and source-by-source rights; complete durable recovery and account quota checks; then explicitly authorize actual publication and CI execution. Only afterward supply a selected-account Workers Scripts edit token through secure secret entry. No AI key is needed. |
| Q. Commands after authorization? | [Post-authorization commands](#commands-prepared-but-not-executed) below. They are proposals; no external mutation was executed. |
| R. Public URL? | Not known. Expected shape: `https://ai-tech-intelligence.<approved-account-subdomain>.workers.dev`. No domain/account subdomain is assumed or registered. |
| S. Tests impossible before hosting? | Real Cloudflare TLS/cache/headers/routing/404/preview isolation/token scope/version rollback; hosted Actions/CodeQL/environment approvals; actual production URL smoke, field performance and physical-device/screen-reader checks. Local browser simulations do not prove real devices. |
| T. Ongoing costs/risks? | Proposed service baseline USD 0/month, no AI/domain/paid binding. Standard public runner minutes are free; artifact/Packages storage is shared and not unlimited. Feed availability, GitHub delays/inactivity, cache eviction and backup storage are operational risks. No cost guarantee before account checks. |

## GO / NO-GO checklist

- **GO:** continue local review, tests, builds, dry-runs and owner decision preparation.
- **NO-GO:** public repository creation/push or Cloudflare publication while any P0/P1 item remains.
- [ ] Owner confirms source ownership and license/copyright holder; chosen text reviewed and added.
- [ ] Owner accepts the brand after appropriate target-market clearance or selects a reviewed replacement; no automatic rename.
- [ ] Every enabled source and retained screenshot/cache/artifact copy has a recorded reuse basis; unresolved material removed through a reviewed migration.
- [ ] Encrypted off-machine source/data recovery generation independently restored; custody and retention assigned.
- [ ] Exact repository/account/Worker/origin and zero-spend account/storage controls confirmed.
- [ ] Final staged tree/history, public author email and exact commit reviewed; latest checks pass on that revision.
- [ ] Owner explicitly authorizes repository publication and hosted CI, then separately the first Cloudflare deployment.
- [ ] Required production environment controls and token scope verified; `RELEASE_APPROVED_SHA` binds the reviewed revision.
- [ ] After launch: actual hosted smoke and rollback verification; only then approve scheduling and test durable cache rehydration.

There is no P0 finding in the completed review. P1 owner-dependent items prohibit publication. Optional AI/full Bangla reporting remain outside the zero-cost English-first launch scope and blocked in the production gate.

## Commands prepared but NOT executed

Use PowerShell from the project root **only after the above decisions and explicit publication authorization**. Replace placeholders with approved values; do not paste tokens into shell history. The current gate will refuse publication. [Full deployment procedure](CLOUDFLARE_DEPLOYMENT.md).

```powershell
# First, record approved decisions in config/release.json and add the chosen LICENSE.
# Choose a public author identity; current configured email is not a GitHub noreply address.
pnpm.cmd verify:repository
pnpm.cmd verify:docs
git add --pathspec-from-file=.cache/owner-launch/public-paths.nul --pathspec-file-nul
git diff --cached --check
git diff --cached --stat
# Privately inspect the complete staged tree and repeat redacted secret scanning.
git commit -m 'Prepare Techline Today release candidate'

$repository = 'APPROVED_OWNER/techline-today'
gh repo create $repository --public --description 'Source-backed technology news with an Astro portal and Python evidence pipeline' --source=. --remote=origin
if ($LASTEXITCODE -ne 0) { throw 'Repository creation failed; stop' }
# Keep hosted automation disabled for the initial reviewed push.
gh api --method PUT "repos/$repository/actions/permissions" -F enabled=false
if ($LASTEXITCODE -ne 0) { throw 'Could not disable Actions; stop before push' }
git push -u origin main
if ($LASTEXITCODE -ne 0) { throw 'Initial push failed; stop' }
```

The repository creation and push make information public and need express authorization. Recheck repository existence before running; never replace an existing remote or repository automatically. No local commit was necessary during this preparation pass. Re-run the complete gates before the actual release commit if code/configuration changes.

After the separately authorized repository setup, configure read-only default token permissions, main-branch protection where supported, push protection/secret scanning, and the protected `production` environment. Enable hosted validation only with owner approval. Use [the operations guide](OPERATIONS.md) for variables and secure token setup. Do not set `PRODUCTION_ENABLED=true` until all gate decisions are supported.

```powershell
# After explicit first-deployment approval and secure token/environment setup:
$env:SITE_URL = 'https://APPROVED-WORKER.APPROVED-SUBDOMAIN.workers.dev'
$env:SITE_NOINDEX = 'false'
$env:PIPELINE_AI_ENABLED = 'false'
$env:RELEASE_APPROVED_SHA = (git rev-parse HEAD).Trim()
pnpm.cmd release:check
# With the approved SHA recorded in the production environment and initial seed
# explicitly approved only when no previously published state exists:
gh workflow run ingest.yml --repo $repository --ref main -f allow_initial_seed=true
# Find the dispatched run in `gh run list --workflow ingest.yml --repo $repository`.
# Wait for that exact run, rather than treating dispatch success as deployment success:
gh run watch APPROVED_RUN_ID --repo $repository --exit-status
if ($LASTEXITCODE -ne 0) { throw 'Deployment workflow failed; preserve the previous edition' }
# After successful deployment, verify the actual URL supplied by the owner:
$env:SMOKE_BASE_URL = $env:SITE_URL
$env:SMOKE_EXPECT_INDEXING = 'true'
pnpm.cmd smoke:production
```

These placeholders do not establish domain ownership. Do not execute `pnpm deploy`, `wrangler deploy`, `versions upload`, rollback, DNS or account commands during preparation. Keep recurring triggers absent and revoke initial-seed authority after the first approved publication; approve the resulting new revision before further releases.
