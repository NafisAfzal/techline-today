# Testing

Current launch counts, source scope and limitations are in [owner verification](OWNER_LAUNCH_VERIFICATION.md). Historical screenshots named below are private/excluded; only the six current [launch captures](assets/launch/README.md) are public candidates. Restore live content and a noindex build after tests.

Current authoritative results are in [final release verification](RELEASE_VALIDATION.md). New release/editorial/provenance/backup regressions, three-engine touch cases and the 15-width matrix supplement the original tests. `pnpm verify:docs` checks local documentation links; `pnpm verify:repository` checks a temporary Git index without staging actual files.

The current [light-theme/header report](LIGHT_THEME_HEADER_REFINEMENT.md) records the latest validation and screenshot provenance. `tests/e2e/header-search.spec.ts` adds three cases per browser project: header separation and single-row navigation across sixteen widths/two languages, desktop query submission and focus restoration, and measured input/placeholder/icon/focus contrast in both themes. `tests/e2e/precision-theme.spec.ts` retains major-heading hierarchy and one-line wrapping in both scripts at six widths, measured text/icon/hover/focus contrast, and tracker-field/action alignment. Existing tests and thresholds are retained.

`node scripts/precision-review.mjs <label>` captures 96 states per edition: homepage, category, story and populated search × six widths × two themes × two locales. It rejects stale build/snapshot combinations and writes screenshots/computed measurements to `%TEMP%/techline-precision/<label>/`. On a constrained workspace drive, use `pnpm exec playwright test --output <temporary-review-directory>` to retain the full suite and traces on a drive with space.

Two datasets serve different purposes. **Live mode is for inspecting the real product and source health. Fixture mode is for repeatable CI and browser assertions.** The fixtures deliberately include corrections, conflicts, expired offers and old archive records. They are synthetic, visibly labelled and blocked from production publication.

Python tests run before repository fixture generation in CI and must pass in a clean checkout without `content/generated/snapshot.json`. Readiness unit tests use a fresh in-memory synthetic edition, a fixed clock and the isolated pytest `root` fixture. They do not read the owner's canonical edition or provision authority. Generate fixture mode only for the later schema, build and browser stages, in an isolated checkout when preserving an existing live edition.

Offline operator and mock-custodian regressions live in `pipeline/tests/test_phase12_operations.py`, `pipeline/tests/test_operations_reports.py` and `pipeline/tests/test_operations_observations.py`. Run `uv run pytest pipeline/tests/test_phase12_operations.py pipeline/tests/test_operations_reports.py pipeline/tests/test_operations_observations.py` before the full suite. These tests require only committed policy files and temporary synthetic journals. The source fault matrix uses `httpx.MockTransport`; it must never contact publishers. See the [operator commands and trust limits](OFFLINE_NEWSROOM_OPERATIONS.md).

Do not run fixture-specific Meridian/Harbor browser assertions against a live build. Regenerate fixture mode and rebuild first. E2E starts its own hardened production preview at port 4327 and refuses server reuse; a development server on 4321 cannot replace that target. Two browser workers prevent resource contention without changing assertion thresholds or the test timeout.

## Local validation

From the project root in PowerShell:

```powershell
py -3.12 -m uv run ruff check pipeline
py -3.12 -m uv run pytest
pnpm.cmd lint
pnpm.cmd typecheck
pnpm.cmd test
pnpm.cmd audit:dependencies
py -3.12 -m uv run python -m pipeline --mode fixture
py -3.12 -m uv run python -m pipeline --validate
pnpm.cmd build
pnpm.cmd security
node scripts/verify-build.mjs
pnpm.cmd verify:site
pnpm.cmd test:e2e
pnpm.cmd performance
pnpm.cmd deploy:check
pnpm.cmd verify:repository
```

Install Chromium once with `pnpm.cmd exec playwright install chromium`. The CI workflow installs its Linux system dependencies too. Bash uses `uv` and `pnpm`; the Windows Python bootstrap prefix can be replaced with `uv` when it is on PATH.

If the workspace drive lacks room for browser traces, redirect only the output directory to a drive with space. The final correction used the following command, with the same workers, assertions, retries and thresholds:

```powershell
$taskBrowserOutput = Join-Path ([System.IO.Path]::GetTempPath()) 'techline-owner-correction-e2e'
pnpm.cmd exec playwright test --output $taskBrowserOutput
```

Python supply-chain checks use the frozen dependency set:

```powershell
py -3.12 -m uv export --frozen --no-hashes --format requirements-txt --output-file .cache/python-requirements.txt
py -3.12 -m uv tool run pip-audit==2.10.1 -r .cache/python-requirements.txt
```

Raw `pnpm.cmd audit` is useful, but it does not replace `audit:dependencies`. The latter visibly verifies a documented local patch even when the advisory database reports zero findings.

## Requirement-to-test matrix

| Area | Behavior / risk | Test level | Location | What failure detects |
|---|---|---|---|---|
| Source adapters | RSS, APIs, releases, permitted HTML and official document parsing | Python unit/integration | `pipeline/tests/test_adapters.py`, `test_documents.py` | Parser drift, malformed payloads, lost billing constraints |
| Fetch security | SSRF, DNS pinning, private/multicast/site-local addresses, redirect/MIME/size/rate limits | Python negative tests | `pipeline/tests/test_quality.py`, `test_audit.py`, `test_adapters.py` | A hostile or misconfigured source reaching an unsafe destination |
| Data normalization | Canonicalization, missing timestamps, hostile HTML | Python unit | `pipeline/tests/test_quality.py`, `test_audit.py` | Unstable IDs, unsafe text or falsely fresh records |
| Deduplication | Exact/near duplicates and distinct release versions | Python unit | `pipeline/tests/test_quality.py`, `test_audit.py` | Noisy repeats or unrelated versions merged |
| Evidence / ranking | Attribution, source independence, numbers, conflicts, novelty | Python unit | `pipeline/tests/test_quality.py`, `test_audit.py` | Unsupported numbers, false corroboration or inappropriate boosts |
| Provider routing | Response formats, failures, 429, quota, redirects and extractive operation | Python unit with mocked HTTP | `pipeline/tests/test_ai.py`, `test_audit.py` | Provider outage stopping an edition or leaking credentials on redirects |
| Cache policy | Prompt/schema/evidence/attribution changes, separate quota reservations | Python unit/integration | `pipeline/tests/test_ai.py`, `test_audit.py`, `test_integration.py` | Stale summaries or lost usage accounting after failed publication |
| Reliability | Partial/total failures, validated fallback, corrections and reuse | Python integration | `pipeline/tests/test_integration.py`, `test_audit.py` | Empty replacement snapshots or falsely reverified old evidence |
| Trackers / archives | Null terms, offer expiry, calendar boundaries, staged compaction and safe paths | Python contracts | `pipeline/tests/test_contract_extensions.py`, `test_quality.py`, `test_audit.py` | Invented terms, expired offers remaining active or unsafe archive publication |
| Schemas | Snapshot/record JSON Schema and Pydantic contracts | Python integration + CLI | `pipeline/storage.py`, `test_integration.py`, `python -m pipeline --validate` | Invalid generated data reaching Astro |
| Reader state | Local bookmarks, preferences and period filtering | Vitest | `tests/unit/local.test.ts` | Persistence/filter/sort regressions |
| Editorial selection | Pipeline importance, stable ties, truthful preview lines, category exclusions and visible-summary deduplication | Vitest | `tests/unit/editorial.test.ts` | Hard-coded lead selection, repeated featured headlines or attribution filler replacing news |
| Release prose | Preview/breaking context, same-line changeset fixes, substantive bullets and processed-cache invalidation | Python | `pipeline/tests/test_editorial_refinement.py` | Dropped fixes, changed measurements or stale release extraction |
| Premium interactions | Theme metadata, protected brand, evidence links, search debounce/races/previews, modal dismissal, stable save geometry, reduced motion, More and saved concurrency/cache | Playwright | `tests/e2e/premium.spec.ts` | State regressions, inaccessible overlays, duplicate headlines or wasted downloads |
| Canonical configuration | Public HTTPS origin and production preconditions | Vitest + build gate | `tests/unit/site-url.test.ts`, `scripts/verify-build.mjs` | Unsafe origins, fixture publication or mismatched canonical URLs |
| Dependency mitigation | Private/cookie/stale cache reuse and legitimate public behavior | Vitest + dependency gate | `tests/unit/cache-policy.test.ts`, `scripts/audit-dependencies.mjs` | Missing/ineffective patch or unreviewed dependency upgrade |
| Reader flows | Details/source links, search, saved/read/preferences, theme, periods, trackers, archives, 404, no-JS reading | Playwright | `tests/e2e/platform.spec.ts` | Broken end-to-end product behavior |
| Accessibility | WCAG A/AA axe checks in both themes | Playwright | `tests/e2e/platform.spec.ts` | Detectable semantic, naming or color failures |
| Responsive constraints | 12px floor, page overflow and designated 44px controls at 320/390/834/1280/1366/1440 | Playwright | `tests/e2e/ux.spec.ts` | Tiny text, clipped mobile pages or inadequate non-prose hit areas |
| Translation contract | Five offline examples, cache invalidation, missing/invalid provider, per-story isolation, names/numbers/uncertainty/Unicode | Python | `pipeline/tests/test_translation.py` | Fabricated fallback, stale translation, lost claims or unsafe output |
| UI localization | Resource parity, Unicode, safe URLs and evidence-preserving presentation | Vitest | `tests/unit/i18n.test.ts` | Missing keys, broken strings or translated evidence IDs/values |
| Bangla reader flows | Language/theme persistence, five translated examples, fallback canonical/hreflang/404, search/save/preferences, no-JS reading | Playwright | `tests/e2e/localization.spec.ts` | Broken localization, indexing duplication or unreadable mixed content |
| Larger typography / Bangla layouts | Actual rendered sizes, wrapping at all six widths, both themes and axe | Playwright | `tests/e2e/localization.spec.ts` | Font scale regression, Bangla overflow or contrast/semantics failure |
| Brand / state contrast | Computed foreground/background contrast in both themes | Playwright | `tests/e2e/ux.spec.ts` | Contrast failures including visible branding missed by axe |
| Card / navigation semantics | One lead, four briefing items, feed differences, labelled facts, More and distinct credit routes | Playwright | `tests/e2e/ux.spec.ts` | Equal-card homepage regressions, bare numbers or route ambiguity |
| Search / feedback | Initial readiness, Tab containment, Escape/restored focus, adjacent storage failure | Playwright | `tests/e2e/ux.spec.ts` | Dead hydration controls, escaping modal focus or distant failure feedback |
| Mobile detail | Sticky actions and citation scroll clearance | Playwright | `tests/e2e/detail-actions.spec.ts` | Unreachable reader actions or evidence hidden under controls |
| Rendered site / SEO | Every route, heading order, IDs, links/anchors, XML RSS/sitemap, robots and canonical origin | Browser-backed crawl | `scripts/verify-site.mjs` | Broken generated pages, skipped headings, invalid XML or missing public sitemap routes |
| Live product | Actual source URLs, page interactions, responsive routes, empty archives, both themes | Live smoke | `scripts/live-smoke.mjs`, `inspect-ui.mjs` | A real dataset exposing regressions fixtures cannot show |
| Secrets / release hygiene | Source/build key checks and prospective tracked files | Static checks | `scripts/security.mjs`, `verify-repository.mjs` | Credentials, private keys, machine paths or build artifacts in public files |
| Workflow isolation | SHA pins, read-only PR permissions, production branch/switch, token scope and separate usage persistence | Python configuration tests | `pipeline/tests/test_workflows.py` | Unsafe Actions permissions, untrusted PR secrets or ungated publication |
| Performance | Three Lighthouse runs, fixed median thresholds, LCP/CLS and JS/CSS/file budgets | Production preview | `scripts/performance.mjs`, `verify-build.mjs` | Slower page loads, layout shifts or oversized assets |
| Deployment packaging | Wrangler asset configuration without publication | Dry run | `pnpm deploy:check` | Invalid deployment package; does not prove account authorization |

Touch tests target semantic controls, navigation, citations and checkbox labels. Inline links within prose intentionally remain inline. Native closed `details` content is excluded from visible-text/hit-area measurements. Disabled controls are excluded from hit-area/contrast assertions. Visible branding is included in computed contrast even when decorative for assistive technology.

## Live inspection and screenshots

```powershell
py -3.12 -m uv run python -m pipeline --mode live
py -3.12 -m uv run python -m pipeline --validate
pnpm.cmd build
pnpm.cmd smoke:live
node scripts/inspect-ui.mjs review
node scripts/refinement-review.mjs live-review
node scripts/capture-product.mjs
```

Read `content/generated/run-report.json` before trusting counts. Successful and unchanged sources count toward coverage; failed sources do not. Network results are time-sensitive and run separately from PR CI. Inspect captured images and computed layout, including sparse trackers and a real detail page. Screenshots record a point in time; they are not pixel-diff gates. Browser artifacts stay under ignored `.cache/` and `test-results/`; historical selected live/fixture captures remain local under ignored `docs/assets/` paths. Generate the latter with `node scripts/capture-localized-fixture.mjs` after restoring fixtures and rebuilding. [Gallery/provenance](assets/README.md). `refinement-review.mjs` covers both locales/themes and all six requested widths; fixture mode supplies the five authored Bangla story examples, while live mode honestly shows provider-unavailable fallback.

The owner-correction suite adds browser regressions in `tests/e2e/owner-correction.spec.ts` for distinct category/story/tool architecture, explicit appearance state and stable control size, ranked headline links, fixed ticker geometry, pointer/keyboard pause and resume, hover/focus suspension, hidden/offscreen behavior, reduced motion, no-JS reading and inline text boundaries. Final exact counts and results appear in [IMPLEMENTATION_VALIDATION.md](IMPLEMENTATION_VALIDATION.md).

The headline's visible keyboard outline is asserted on its clipping wrapper, keeping the ring visible around ellipsized text. Actual desktop and phone focus captures in both themes complement that computed-style check.

The six-width matrices each cover 264 measured states with zero horizontal overflow in live and fixture modes. Use `node scripts/refinement-review.mjs owner-correction-final-fixture` or `owner-correction-final-live` after the appropriate build; the script rejects a build/snapshot mode or generation mismatch. Captures wait for finite entrances, excluding the controlled infinite ornament from that wait. Category closeups use document-coordinate clips of complete sections. Authored Bangla samples are synthetic and are not evidence that a production provider produces equally good language. Automated translation checks cannot certify complete semantic equivalence. Actual-browser inspection checks mixed scripts, line height, punctuation, technical terms and wrapping; physical Android/Linux testing remains operator work.

Preserve previous gallery provenance when capturing a new correction: use `node scripts/capture-product.mjs docs/assets/owner-correction` after a live build, then `node scripts/capture-localized-fixture.mjs docs/assets/owner-correction` after restoring and building fixtures. The current [gallery](assets/owner-correction/README.md) labels both datasets.

For fixture E2E use fixture mode; before handoff restore live mode and rebuild with local noindex. Lighthouse fixture/default-example builds intentionally disallow indexing, so their SEO score includes that deliberate limitation. A separate live build with a valid test canonical origin checks production SEO locally; it does not prove domain ownership or deployment. Timing scores depend on the local machine and are recorded as measurements rather than field performance guarantees.

The prospective repository check uses a temporary Git index and leaves the user's actual index unchanged. Wrangler dry-run uploads nothing. Credentialed providers, GitHub environment protections, Cloudflare routing and public-domain headers require operator checks after authorized setup. See [IMPLEMENTATION_VALIDATION.md](IMPLEMENTATION_VALIDATION.md) for the latest measured results.

## Final motion pass

`tests/e2e/deep-motion.spec.ts` adds five cases in each browser project: real playback state and parked-pointer Resume, one-item honesty, reduced-motion manual navigation, remaining-time preservation, and changing-headline geometry across six widths/both locales. Modal suspension/resumption and manual-pause preservation are included in those cases. Appearance regressions now assert two visible choices, mutually exclusive pressed state and idempotent selection. Full exact counts are in [the final report](FINAL_MOTION_BRAND_PASS.md).

The dedicated current [gallery](assets/deep-motion/README.md) preserves older captures as history. On a full workspace drive, `refinement-review.mjs` accepts a third argument inside `%TEMP%/techline-deep-review/` or `.cache/visual/`; mode/generation assertions still apply. Capture waits exclude the continuing `focus-progress` animation, while settling finite entrance effects.

Wall-clock evidence in `.cache/deep-motion/real-runtime.json` uses no mocked clock and covers actual localhost:4321 plus a live production preview with mouse/touch. Pause measurements wait two rendering frames before strictly comparing frozen compositor transforms. The WebM path is recorded in that JSON. Browser tests use controlled clocks separately for deterministic timer assertions. All artifacts and videos remain local; no deployment occurs.
