# Owner-led launch verification ? 2026-10-14

This is historical local preparation evidence, superseding earlier 139/81/155-story reports. No external publication, recurring execution, paid API, account permission change or backup upload was performed during that preparation. [Current Gate A results](GITHUB_GATE_A_RELEASE.md) supersede authorization, independent-backup and public-repository status. Original approved UI is preserved; required source-license text and conservative feed scope changed.

Toolchain: Node **24.14.1**, pnpm **10.33.1**, uv **0.12.22**, pipeline Python **3.13.16**, Wrangler **4.147.0**. Windows `py -3.12 -m uv` is the uv launcher, not the pipeline interpreter. Frozen locks/dependency versions did not change in this owner pass.

## Engineering gates

Durations below are measured subprocess wall time including command startup; test-runner durations are stated separately when available. Exact private logs/arguments are retained in `.cache/owner-launch/results.jsonl` and named logs. Browser/Lighthouse output is on the system temporary volume.

| Gate / command purpose | Result | Exit | Seconds |
|---|---|---:|---:|
| `lint-complete` ? Ruff: pipeline + production-state helper | Passed | 0 | 0.33 |
| `python-complete` ? Pytest | 144 passed; test runtime 19.24 s | 0 | 21.41 |
| `workflow-final` ? Workflow regression recheck after manual-CI trigger | 5 passed | 0 | 2.70 |
| `lint-last` ? ESLint, zero warnings | Passed | 0 | 8.23 |
| `types-final` ? Astro check | 57 files; 0 errors/warnings/hints | 0 | 13.58 |
| `unit-last` ? Vitest, including localization/authorization/rights/change detection | 93 passed in 8 files; test runtime 0.905 s | 0 | 3.53 |
| `e2e-final` ? Full fixture Playwright | 130 passed; Chromium desktop/mobile + Android-size, WebKit iPhone-size, Firefox touch | 0 | 204.39 |
| `live-touch` ? Live touch Playwright | 18 passed; Android Chromium / iOS WebKit / Firefox; EN/BN/themes/navigation | 0 | 94.75 |
| `live-final` ? Permitted-source live collection | 37 stories; 0 new/updated; 0 AI calls; 0 real Bangla translations | 0 | 2.30 |
| `live-validate` ? Snapshot contract validation | 37 stories, 9 digests | 0 | 2.17 |
| `final-rights` ? Content rights/current and built data | 37 permitted stories/sources | 0 | 1.75 |
| `editorial` ? Production editorial quality | 37 prose-backed; 0 headline-only/duplicate titles; Bangla warning disclosed | 0 | 0.14 |
| `final-local-site` ? Site verification | 130 HTML routes, 6,738 internal links, 726 external references, 37 RSS items, 87 sitemap routes | 0 | 5.72 |
| `live-smoke` ? Live responsive/accessibility smoke | 320/390/834/1280/1366/1440px; warm/dark; 0 console errors | 0 | 20.64 |
| `final-security` ? Source/build secret and security-header checks | Passed | 0 | 3.22 |
| `node-audit` ? Node complete dependency audit/patched behavior | 0 registry advisories; temporary cache mitigation explicitly retained | 0 | 3.36 |
| `python-audit` ? pip-audit 2.10.1, frozen exported dependencies | No known vulnerabilities | 0 | 89.27 |
| `restored-final-build` ? Final restored live/noindex static build | Passed; notices and Pagefind included | 0 | 16.08 |
| `restored-budget` ? Build/provenance/budgets | 307 files, 5,189,004 bytes; JS gzip 96,537 B; CSS 39,107 B / gzip 8,911 B | 0 | 0.55 |
| `production-metadata` ? Indexable production metadata verification | Passed locally with real test canonical; not owned/hosted | 0 | 0.83 |
| `production-local-smoke` ? Parameterized production smoke on loopback | 16 routes; 390px; 0 console errors | 0 | 4.64 |
| `preview-metadata` ? Noindex preview metadata verification | Passed | 0 | 0.75 |
| `preview-local-smoke` ? Parameterized preview smoke on loopback | 16 routes; 390px; 0 console errors | 0 | 4.67 |
| `preview-production-rejection` ? Reject preview output for production | Expected exit 1: indexing mismatch | 1 | 0.67 |
| `lighthouse` ? Three-run Lighthouse | All enforced budgets passed | 0 | 84.03 |
| `dryrun-production` ? Wrangler production-config dry-run | Passed, no bindings/no upload | 0 | 32.66 |
| `dryrun-preview` ? Wrangler separate-preview-config dry-run | Passed, no bindings/no upload | 0 | 5.08 |
| `backup-export` ? Clean live-data export | 6 allowlisted files, SHA-256 manifest | 0 | 2.30 |
| `backup-verify` ? Live-data manifest/schema verification | Passed | 0 | 1.72 |
| `backup-restore` ? Empty-directory live-data restore | Passed | 0 | 1.66 |
| `final-publication-block` ? Production publication guard | Expected exit 1; publicationPerformed=false | 1 | 0.27 |
| `github-publication-block` ? GitHub publication guard | Expected exit 1; publicationPerformed=false | 1 | 0.33 |
| `preview-publication-block` ? Preview publication guard | Expected exit 1; publicationPerformed=false | 1 | 0.26 |

## Public files, documentation and recovery

The final inventory contains **275 files**, including only **six current launch JPEGs**; generated corpus, private state, historic captures, backups and credentials are excluded. Reviewed path/NUL/classification manifests are saved privately for exact future staging. Fresh alternate-index verification passes without changing the actual empty index. There is no reachable commit history, remote or public repository. Local dangling objects are retained privately and are not distributed. Repository-local commit identity uses the confirmed account noreply format.

Documentation validation checks public inventory membership as well as relative-file existence (Markdown links and HTML image sources). **82 Markdown files and 256 relative links** passed on the populated final report (1.88 s). The final repository scan passed for 275 files (2.39 s), and redacted Gitleaks passed for 269 text files (1.77 s scanner / 2.11 s wrapper). External-reference availability is not part of that gate. Redacted Gitleaks stdin scanned all prospective text and found no leaks; final rerun after report changes is retained privately. Historical/current staged trees must be rechecked before a future push.

A clean source ZIP and matching six-file live-data pack are locally exported and restored in isolated empty directories; per-file SHA-256, ZIP CRC and extracted source hashes are verified. The private recovery summary records exact archive size/hash/path. Credentials and `.git` are excluded. Historical contaminated backup/orphan evidence and pre-edit source/screenshots were preserved, not deleted or uploaded. **No off-machine restore exists.** Local source extraction proves file fidelity; a full clean-machine dependency install, account recovery and end-to-end hosted disaster recovery remain unmeasured.

## Lighthouse, environment separation and limits

Three production-metadata loopback runs: performance **99/100/100**, accessibility **100/100/100**, best practices **100/100/100**, SEO **100/100/100**. Median LCP **1,737.29 ms**, CLS **0**. No threshold was relaxed. These are local lab observations, not field performance or remote network measurements.

For metadata-only tests, `SITE_URL=https://www.cloudflare.com` was a known real canonical origin while all smoke/crawl requests used loopback. This does not claim domain ownership or a deployed Techline Today URL. Production output allowed indexing; explicit preview output disallowed it and production verification correctly rejected it. Final local output is live, noindex and robots-disallowed with no public production origin. Both HTML and data contain zero fixture stories; referenced archive index is empty. All 37 live stories have evidence prose; no provider call/native translation was made.

The full fixture browser suite ran before the final RSS/license-download and workflow/provenance corrections; those changes preserve UI behavior and are covered by the later live touch, site/RSS, content, unit and workflow gates. No redundant full browser rerun was needed. No physical Android/iPhone, real assistive technology, hosted CI/CodeQL, edge route/cache/Link headers, remote rollback, provider entitlement or independent-storage restore has been proven.

Wrangler reports 459 read entries while the filesystem has 307 regular files and 152 directories; both reported/read counts are far below the asset limit. Dry-runs clear Cloudflare credential variables and disable telemetry; packaging success proves neither account Free eligibility nor an actual edge deployment. Wrangler advertised a newer version; locked 4.147.0 was tested rather than silently upgrading dependencies.

## Corrected failures and review

Initial Ruff detected unused imports in the new regression file; those were removed/used and lint passed. The source-submission restriction initially made the existing authored-fixture candidate-budget test fail (142 passed/1 failed); fixture eligibility was corrected while fixture mode still configures no real providers. The complete final Python run then passed 144 tests. Preview-as-production and the three unauthorized publication exits are intentional negative tests, not unresolved engineering failures.

The independent review found and resolved preview/prod destination collision, stale public review index, download attribution gaps, source-submission enforcement, volatile archive hashing, premature successful-state promotion and initial CI-dispatch mismatch. [Review evidence](OWNER_INDEPENDENT_REVIEW.md). Node registry zero is not an upstream fix: the locked build-only cache-policy patch remains visible and expires for reassessment on **2026-11-03**.

Initial project volume had about 43 MiB free. Disposable captures/tool/report folders were reversibly moved to the system temporary volume, raising available space to roughly 255?265 MiB. A relocation manifest preserves exact restoration paths; no source, research or backup was deleted. The system volume has more room but is still the same machine.

**All external gates remain NO-GO.** [Owner/account/rights/backup decisions and prepared commands](OWNER_GITHUB_LAUNCH_PLAN.md). No staged files, local commit, Git remote changes, paid resource or external publication were created by this preparation.

## Local reproduction commands

Run browser fixture and live gates in this order; source modes are deliberately separate. On Windows use pnpm.cmd and the uv launcher below. Local metadata/smoke variables are exported in the same shell; never substitute an invented public service.

```powershell
py -3.12 -m uv run ruff check pipeline scripts/production_state.py
py -3.12 -m uv run pytest
pnpm.cmd lint
pnpm.cmd typecheck
pnpm.cmd test
py -3.12 -m uv run python -m pipeline --mode fixture
py -3.12 -m uv run python -m pipeline --validate
pnpm.cmd build
pnpm.cmd exec playwright test
py -3.12 -m uv run python -m pipeline --mode live
py -3.12 -m uv run python -m pipeline --validate
pnpm.cmd build
pnpm.cmd verify:content-rights
node scripts/editorial-quality.mjs --production
pnpm.cmd verify:site
pnpm.cmd security
pnpm.cmd smoke:live
pnpm.cmd exec playwright test tests/e2e/mobile-release.spec.ts --project=android-chromium --project=ios-webkit --project=touch-firefox
pnpm.cmd audit:dependencies
py -3.12 -m uv export --frozen --no-hashes --format requirements-txt --output-file .cache/owner-launch/requirements.txt
py -3.12 -m uv tool run pip-audit==2.10.1 -r .cache/owner-launch/requirements.txt
pnpm.cmd verify:docs
pnpm.cmd verify:repository
node scripts/verify-build.mjs
pnpm.cmd performance
pnpm.cmd exec wrangler deploy --dry-run
pnpm.cmd exec wrangler deploy --config wrangler.preview.jsonc --dry-run
```

Lighthouse above uses the currently built indexing policy; the recorded 100 SEO median used the controlled indexable metadata build, followed by explicit noindex and default-local rebuilds. For parameterized hosted smoke, use an approved real SMOKE_BASE_URL; loopback requires the script's --local flag and the canonical origin of that local metadata build. No existing hosted URL is assumed. Cloudflare dry-runs disable telemetry and remove credential variables; actual deploy commands remain exclusively behind the release gates.
