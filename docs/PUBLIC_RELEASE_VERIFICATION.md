# Public release verification — 2026-10-14

> Historical release evidence. The [owner launch plan](OWNER_GITHUB_LAUNCH_PLAN.md) and [current verification](OWNER_LAUNCH_VERIFICATION.md) supersede identity, licensing, source coverage, backup and workflow status below. Older counts and pending ownership statements are not current proof.

This document records the current preparation pass separately from [earlier validation](RELEASE_VALIDATION.md). **All applicable local engineering gates passed; publication remains NO-GO for the owner dependencies.** External publication is blocked; no hosted URL is assumed.

Local evidence logs and timed command records are in ignored `.cache/release-preparation/`. `py -3.12 -m uv` is the installed uv 0.12.22 launcher; its project interpreter is Python 3.13.16. Node is 24.14.1 and pnpm 10.33.1.

## Current gate evidence

Times below are measured wall time for the complete command wrapper, not invented hosted timings. *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* retain exact arguments with local temporary paths redacted.

| Command / check | Result | Duration |
|---|---|---:|
| `pnpm.cmd install --frozen-lockfile` | Passed; lock unchanged | 2.22s |
| `py -3.12 -m uv sync --frozen` | Passed; 31 packages checked | 0.12s |
| `py -3.12 -m uv run ruff check pipeline scripts/production_state.py` | Passed | 0.30s |
| `py -3.12 -m uv run pytest` | **139 passed**; 20.69s pytest runtime | 23.94s |
| Workflow policy recheck after Action pin correction | **3 passed** | 1.42s |
| `pnpm.cmd lint` | Passed; no warnings | 7.55s |
| `pnpm.cmd typecheck` | 56 Astro files; 0 errors/warnings/hints | 31.02s |
| `pnpm.cmd test` | **81 passed**, 6 files, including localization/release/indexing tests | 1.78s |
| Fixture ingestion / validation | 12 stories, 14 digests; 5 authored Bangla translations | 1.59s / 1.00s |
| Final fixture build | Passed, including software notice check | 8.36s |
| Full fixture Playwright suite, temporary output on system drive | **130 passed**, no retries locally | 205.97s |
| Fixture site verification | 94 HTML routes, 4,556 internal links, 494 external references, 81 sitemap routes | 6.84s |
| Live ingestion / validation | **155 stories, 23 digests**, 6 successful source responses + 1 unchanged; 0 validation failures/AI calls/translations | 15.53s / 1.33s |
| Production metadata build / verification | Passed locally against a test canonical origin; not a deployed/owned origin | 11.52s / 0.58s |
| Production editorial gate | 68 prose-backed, 66 headline-only, one duplicate normalized title; 0 errors | 0.08s |
| Explicit staging build / production rejection | Build passed; production verifier correctly exited **1** for noindex | 12.66s / 0.44s |
| Configurable hosted smoke exercised on loopback | Staging and production metadata modes each passed **16 route/resource checks**, search/navigation/themes/mobile; 0 console errors | 3.09s / 2.94s |
| Final local build | **Live + noindex**, 310 indexed EN/BN story pages | 11.91s |
| Final build/provenance/budgets | **943 files**, 13,348,214 bytes; initial JS gzip **96,537/100,000** bytes; CSS **39,107/40,000**, gzip 8,911 bytes | 0.47s |
| Final live site verification | **394 HTML routes**, 20,826 internal links, 1,878 external references, 50 RSS items, 233 sitemap routes | 6.36s |
| Live smoke/accessibility/responsive | Passed at **320/390/834/1280/1366/1440px**, both themes; actual evidence/original links/search/saved state; 0 console errors | 20.67s |
| Live Chromium/WebKit/Firefox touch suite | **18 passed**, EN/BN, both themes, phone portrait/landscape, search, native fields, bookmarks/navigation | 70.19s |
| Node full-tree dependency audit | **0 registry advisories**, none suppressed; locked cache-policy mitigation probes passed | 1.97s |
| Python pip-audit 2.10.1, frozen requirements | **31 requirements**, no known vulnerabilities | 67.80s |
| Final source/build security | Passed; credential names/values excluded from reader assets | 7.11s |
| Redacted Gitleaks 8.30.1 | No detected secrets; prospective text scan, values never printed | Exact final counts in machine-readable evidence |
| GitHub Action pins | Six unique repositories' pins verified as actual commits through official GitHub API | Read-only; no hosted runs |
| Lighthouse, 3 local mobile runs | Performance/accessibility/best practices **100/100/100 each run**; median LCP **1685.28ms**, CLS **0**; existing error budgets passed | 32.44s |
| Cloudflare packaging | Wrangler 4.147.0 **dry-run passed**, 1,359 reported inputs, 0.36 KiB wrapper / 0.25 KiB gzip, no bindings | 7.64s |
| Corrected data backup | **6 files** exported, verified, restored into empty isolated directory; all restored SHA-256 values equal manifest | 0.84s / 0.59s / 0.66s |
| Publication preflight | Expected **exit 1**, `RELEASE_APPROVAL_REQUIRED`, publicationPerformed=false | 0.42s |
| `pnpm.cmd verify:docs` | **75 Markdown files / 416 valid relative links**; external link availability not exhaustively tested | 0.92s |
| `pnpm.cmd verify:repository` | **432 prospective files**, approximately 34.9 MB; real index unchanged | 1.31s |

A private source ZIP generation contains the prospective public tree and a SHA-256/byte-count manifest. It is verified by ZIP integrity checks and isolated extraction/hash comparison on the system temporary volume; its local summary stays in ignored evidence. No `.git`, live data, `.env`, dependency tree or private backup is included. This is still the same laptop, not a durable off-machine backup.

No real index contents, remotes or author configuration were changed. No commit, repository creation, push, preview upload, deploy, DNS change, paid service or external schedule activation occurred.

## Failures and limitations retained honestly

The initial E2E attempt had **118 passes / 12 infrastructure failures**, all `ENOSPC` while traces were written on the nearly full workspace volume. Its logs were retained. Rerunning identical tests with output on the system temporary volume passed all 130; no tests, retries or budgets were weakened. The workspace has roughly 60 MiB free at inspection, so storage cleanup/relocation needs operator attention before extended local work; no user data or existing backup was removed.

During implementation, ESLint flagged two missing global qualifiers and Ruff flagged import ordering; these were corrected. An intermediate provenance check correctly rejected a build made before source edits. An interim documentation check found links to the not-yet-created handoff; final link verification supersedes it. Initial local Python-audit invocation used unavailable `uvx` as a module; the successful supported form was `py -3.12 -m uv tool run pip-audit==2.10.1 -r .cache/release-preparation/requirements.txt`. An output-print encoding error after the successful frozen pnpm install affected only the temporary reporting wrapper, which was corrected to UTF-8. These attempts are retained in ignored command logs.

The earlier 1,176-state matrix and physical-device limitations are preserved in historical reports; this pass reran representative live six-width smoke and the 18-case touch suite plus the full fixture suite. It does not claim to rerun the historical matrix or prove physical iPhone/Android behavior. Pagefind has no Bangla stemming. Lighthouse collected SEO as well, but SEO is not an enforced Lighthouse threshold; canonical/robots/sitemap checks are enforced separately.

The temporary production-metadata test origin was the provider's real `https://www.cloudflare.com`, used only in local generated metadata and loopback smoke. It was never fetched by the smoke script as the site, claimed as owned, selected for launch or published. The final local origin is again the noindex example default. The future actual public URL remains unset.

The source gate still requires an approved clean Git commit. There is no commit in this preparation pass because all original project files were untracked and source ownership/license/public author identity remain unresolved. Preparing an alternate prospective index did not stage user files. There are loose Git objects from prospective scans, but no refs/history to push; ordinary future push transmits reachable history, not an archive of `.git`.

## Reproduction

Run frozen pnpm/uv installs, Ruff, pytest, ESLint, Astro check, Vitest and dependency audits. Export a verified live backup before switching to fixtures. Generate fixtures, validate, build, run E2E and site verification; then recollect/restore live content and rebuild. Use `pnpm.cmd smoke:live` for the actual local edition. Existing mobile tests cover Chromium/WebKit/Firefox with English/Bangla, both themes, touch, portrait/landscape, navigation, search and saved state. The existing broader matrix is preserved.

If the workspace volume cannot hold Playwright traces, keep the same tests and direct output to a separate temporary destination:

```powershell
$browserOutput = Join-Path ([IO.Path]::GetTempPath()) 'techline-release-preparation/fixture-e2e'
pnpm.cmd exec playwright test --output $browserOutput
```

Production smoke requires explicit configuration. Without `SMOKE_BASE_URL` it fails before network access. Future authorized hosted use:

```powershell
$env:SMOKE_BASE_URL = 'https://APPROVED-WORKER.APPROVED-SUBDOMAIN.workers.dev'
$env:SMOKE_EXPECT_INDEXING = 'true' # false for a noindex preview
pnpm.cmd smoke:production
```

The local proof uses `--local`, a loopback origin and an explicit expected canonical origin. It exercises the script without making a hosted claim or contacting an invented public destination. Production-origin/staging tests run only against locally served builds; final local content is live and noindex.

## Limitations

No physical phone, public edge, Cloudflare token/account permissions, actual hosted deployment/version rollback, GitHub-hosted CI, off-machine backup or field performance is proven. Automated content validation does not establish semantic truth or publisher rights. Current results and remaining findings are cross-referenced in [the release gate](PUBLIC_RELEASE_PREPARATION.md).
