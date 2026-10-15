# Post-audit Wave 1 remediation

Local review of baseline `68d6a3bda6468d971798f4f8170344ba1cba679b`, 2026-10-15. No commit, push, PR, deployment, live collection, inference or schedule activation was performed.

## Examined evidence and baseline

Read all eleven preserved audit artifacts in `%USERPROFILE%/Documents/TechlineToday-Audits/2026-10-15`: reports 01–10 and `findings.json`. Both preserved and original temporary copies exist. The reports contain 3 P1, 8 P2 and 6 P3 findings; no P0. Rechecked the named source paths and tests, rather than treating the audit's assertions as implementation instructions.

HEAD, `main`, and read-only `git ls-remote origin refs/heads/main` match the baseline. Origin is `https://github.com/NafisAfzal/techline-today.git`. Initial working tree and real index are clean. Installed: Node 24.14.1, pnpm 10.33.1, Python 3.13.16 in `.venv`, uv 0.12.22 through `py -3.12 -m uv`, Playwright 1.63.0. Existing pytest/Ruff, Vitest, ESLint, Astro, Playwright and axe infrastructure is available.

Initial resources: D: 262,242,304 bytes free, C: 6,768,328,704 bytes free, RAM 903,960 KiB free of 7,667,720 KiB. No installation or duplicate dependency tree is planned. Estimated additional disk: under 40 MiB for static build/cache work on D:, under 100 MiB for isolated pytest/browser artifacts on C:, under 5 MiB for screenshots. Checks run sequentially and browser workers are limited locally. This is not a clean-machine install proof.

The canonical snapshot has 37 stories (36 research, one evergreen documentation record), two source identities, zero Bangla translations, and zero new/updated stories in the last run. arXiv failed; Cloudflare documentation was unchanged. The enabled registry contains 2 of 9 entries, capped at 12 papers plus one document per fetch. Publication dates span October 1–13; generation is October 14 at 17:31:56 UTC. Generation/collection does not establish publication freshness. Snapshot SHA-256: `d146d528ed8b00bc4e3a1e379ceffa300f46ce5a17ee9d34e8291410e9973eb5`. A private temporary baseline manifest and copies preserve snapshot/report hashes. Canonical ingestion will not be run for tests.

## Triage and prioritized action plan

| Finding | Revalidation / severity | Evidence and proposed disposition | Risk / regression | Gates |
| --- | --- | --- | --- | --- |
| F-01 | Confirmed P1 | Registry, rights, snapshot and run report confirm narrow research coverage. Implement separate current-news/research/reference classification, timestamp validation, explicit empty/stale states and production freshness checks. Keep technology portal positioning; no feed expansion. | Medium: conservative classification; test absent/stale/research-only/current/invalid timestamps and legacy records. | B: honest noindex preview; C: fresh rights-cleared news still required. |
| F-02 | Confirmed P1 | `ai.py` supplies category boilerplate; `verification.py` prioritizes primary provenance; old preprints lack limitations. Clarify visible labels, preprint review unknowns and claim attribution; omit unassessed significance. | Medium: preserve enum/legacy readers and numeric/attribution validation; adversarial peer-review and corroboration tests. | B: trust copy before preview; C: editorial review remains required. |
| F-03 | Confirmed P1 scope gap | Translation rights disallow both live sources. Existing cards AND details already have a fallback paragraph; audit's claim of no card disclosure is overstated. Add compact consistent English-content indicator, including briefing/saved cards. | Low: mobile/theme/locale regression; do not imply translation readiness. | B: indicator; C: native review before claiming translated corpus. |
| F-04 | Partially confirmed P2 | `cluster()` already sorts `(published_at,id)`, so representative-only grouping is not inherently feed-order dependent. `deduplicate()` ties retain input order; rank and extractive category use first items. Reproduce/fix stable ties and category agreement only. | Medium: permutation, version/event separation, source-update, repeat/hash tests; no graph-clustering redesign. | Before coverage expansion; review first regenerated edition at B/C. |
| F-05 | Confirmed P2 process item | Patch, 14 regression probes, explicit gate expiry and operations reminders already exist. Keep unchanged; upstream reassessment remains due November 3. No new claim of upstream remediation. | No implementation; rerun local probes/security. | Not a B blocker; retain C dependency gate. |
| F-06 | Confirmed P2 test gap | Summary forbidden-call test exists; translation eligibility lacks the analogous negative test. Add direct and runner-path coverage; annotate README diagram. | Low; mock capable provider and forbid transmission under denied rights. | Supports B/C rights boundary. |
| F-07 | Confirmed P2 test gap | Fetcher caps responses, RSS truncates after parser; adversarial/large-feed fixtures absent. Add isolated byte/entity/item/encoding/namespace cases and only any demonstrated parser safeguard. | Low to medium; bounded synthetic local inputs, no third-party traffic. | Supports B/C ingestion robustness. |
| F-08 | Partially confirmed P2 | Historical `.cache/deep-motion/e2e-first.log` and `.cache/premium-validation/e2e.log` contain 30-second failures. Width matrices and network delays are real. Split affected matrices and replace artificial response sleeps with barriers; keep timeouts. No current WebKit-failure claim without rerun. | Test-only risk; run affected scenarios serially. | Test confidence at B/C; hosted browser evidence outstanding. |
| F-09 | Confirmed P2 | `live-smoke.mjs` silently omits pagination for small editions and loops over possibly zero offers. Add explicit applicability outcomes; retain sparse-edition acceptance. | Low; inspect/report both branch states, never require invented offers. | B/C smoke evidence must name unexercised branches. |
| F-10 | Partially confirmed P2 operational inference | Schedule is disabled. Runbook already states concurrency, 30-minute budget, cache limits, quarterly restore and seed discipline. Defer extra operational implementation until authorized hosted preview; no active four-times/day burden today. | No code; owner evidence/drill. | B/C account, recovery and staffing decisions. |
| F-11 | Partially confirmed P2 | Astro config reads snapshot before data library's existing actionable error. Implement shared actionable read preflight and input mode validation. Postbuild already selects archive root by snapshot mode; alleged archive mismatch is not reproduced. Archive payload mode assertions are deferred: legacy archives have no mode field, so that change needs an explicit migration. | Low; missing/malformed input and invalid input-mode tests. | B/C reproducible build safeguard; archive migration is not required for these fixes. |
| F-12 | Confirmed P3 | `digests.py` uses 19:17, consistent with prepared cadence. Defer configuration change. | No correctness blocker shown. | Neither. |
| F-13 | Confirmed P3 defense in depth | Saved-story original anchor uses validated source URL directly. Defer separate URL abstraction; no bypass reproduced. Touch saved trust/language text only as necessary for F-02/F-03 consistency. | Existing safe-url and plain-text controls retained. | Neither. |
| F-14 | Confirmed P3 test depth | TS rights unit uses minimal dictionaries; Python integration already validates full snapshots. Defer extra roundtrip unless a new gap requires it. | Existing full validation retained. | Neither. |
| F-15 | Confirmed P3 test depth | One GitHub document test. Defer separate malformed-document expansion, unrelated to selected P1 fixes. | Fetch byte bounds and validation remain. | Neither. |
| F-16 | Invalid as defect / P3 observation | Disabled adapters are deliberate, policy-tested extension points. Keep them. | Removing them would lose useful controls/tests. | Neither. |
| F-17 | Partially confirmed P3 | README lacks inline per-image dates; `docs/assets/launch/manifest.json` and gallery already preserve provenance. Defer cosmetic captions. | Historical gallery must not be presented as Wave 1 captures. | Neither. |

Order: product truth/trust/language safeguards, focused deterministic and rights/parser regressions, targeted build/smoke/test reliability, sequential verification, complete diff review, independent review context, owner handoff. P2 work is selected because it protects the requested P1 behavior and verification; no P3 implementation is planned.

## Implemented paths and behavior

- F-01: `scripts/coverage.mjs`, `scripts/editorial-quality.mjs`, `packages/contracts/index.ts`, `apps/web/src/components/CoverageStatus.astro`, `apps/web/src/pages/index.astro`, `apps/web/src/pages/news.astro`, `apps/web/src/pages/bn/news.astro`, `apps/web/src/lib/data.ts`, `apps/web/src/components/Feed.astro`, and the shared layout/dictionaries. News/official announcements, research, reference and unclassified records are separate derived classes. Home uses absolute dates and a short absent-news message. `/news/` and `/bn/news/` show an honest empty state; they contain no invented news. Existing source and story identities, rankings and topic links remain.
- F-02: `pipeline/ai.py`, `pipeline/verification.py`, `prompts/story_summary.md`, `pipeline/translation_fixtures.py`, `apps/web/src/lib/trust.ts`, `ContentIndicators.astro`, `StoryCard.astro`, `SavedStories.tsx`, homepage, story and archive templates. Generated preprint summaries expose review uncertainty and unassessed limitations. Legacy records receive equivalent reader caveats. Extractive significance is recorded as unassessed and omitted from presentation; numeric/citation validation remains. The summary policy version increases from 6 to 7 to invalidate cached generation on a future authorized run.
- F-03: the shared content indicator, briefing rows, saved cards and story headers show localized English-content text on untranslated Bangla routes, with an accessible explanation. The full detail fallback, source-language tags, canonical/noindex and sitemap behavior remain. The chip uses existing spacing, color and typography tokens; no new font, icon system or animation is introduced.
- F-04: `pipeline/dedupe.py` and `pipeline/ranking.py` use stable dedupe ties and a shared majority category with a lexical tie-break. `extractive()` uses the same category. Sorted compensated cosine sums avoid floating-point iteration effects. Representative clustering, thresholds, time/version guards and identities remain intact.
- F-06: translation forbidden-call and runner-path assertions plus the README diagram distinguish capability from permission. No source-submission approval changes.
- F-07: `pipeline/adapters.py` rejects DTD/entity declarations before feedparser, including UTF-16/32 ASCII markup. A small baseline probe demonstrated internal entity expansion. Fetcher byte/MIME/DNS/timeout controls are untouched.
- F-08: header and responsive width matrices are split into independently bounded scenarios; controlled network barriers replace two artificial response delays in `premium.spec.ts`. No timeout or retry policy changes. Existing historical logs show obsolete-selector/interaction failures; they do not prove a new current WebKit defect.
- F-09: `scripts/live-smoke.mjs` reports pagination/offer applicability with explicit reasons and checks the zero-offer empty state. The Today assertion now checks visible publication-date results rather than all mounted cards. Optional screenshots can use `TECHLINE_ARTIFACT_DIR`.
- F-11: `scripts/read-snapshot.mjs`, Astro config and data loader provide an actionable missing/corrupt/mode error that explicitly preserves live data. There is no automatic seed or snapshot substitution.

## Editorial policy decisions

The long-term product remains a technology news intelligence portal. This wave does not permanently reposition it as a research-only publication and does not approve additional publishers. Present coverage is disclosed rather than made to look broader.

The stored `primary-confirmed` enum is retained for compatibility, but all affected reader surfaces call it **Primary source**. Presence of a primary publisher establishes provenance. The tooltip and visible article explanation distinguish that from independent reporting; a single primary source does not establish corroboration. Independent reporting is not treated as independent experimental replication.

An arXiv posting is a preprint source. Metadata alone does not establish whether a later journal version was reviewed. The notice therefore says **peer review has not been established from the collected metadata**, rather than asserting that every arXiv paper is necessarily unreviewed. Paper-specific methods/limitations are not inferred from an abstract: **limitations have not been assessed**. Existing conflicts and source-reported uncertainty remain visible. Unsupported affirmative peer-review wording is rejected; negated review language cannot license a positive claim. This remains a conservative lexical check, not a semantic truth oracle.

Extractive facts remain quoted/source-reported research findings or publisher claims, supported by cited text. Future AI significance is labelled editorial interpretation and remains subject to human semantic review. No AI call was enabled or made. Existing attribution, numeric subset, conflict and claim-map checks are preserved. See `docs/EDITORIAL_STYLE.md` and `docs/LOCALIZATION.md`.

## Freshness contract and compatibility

`timestamp()` requires a real, timezone-bearing ISO timestamp, rejects invalid calendar dates and impossible times, and allows only the existing ten-minute future skew. `coverage(snapshot, now)` takes an explicit clock for reproducible tests.

| Type | Classification | Freshness basis |
| --- | --- | --- |
| Current news | Dated primary/independent RSS, release or JSON evidence with explicit `missing_publication_time=false`; research excluded | Story publication and at least one known source publication within 72 hours |
| Research | Research category or arXiv provenance | Known publication within seven days |
| Reference | Official GitHub documentation | Last source collection within 30 days; an undated document is never promoted to news |
| Unclassified | Incomplete or insufficient provenance/date metadata | Never satisfies current-news publication gate |
| Collection | Snapshot's last successful collection | Overdue after 24 hours; success may include unchanged feeds and failures elsewhere |

Invalid/future source timestamps fail editorial checks. Research/reference stale counts and the exact assessment time appear in the expandable coverage region. Publication freshness is a **build-time assessment** with its displayed clock; collection expiry also updates on load, pageshow, visibility change and every minute in JavaScript. Static/no-JavaScript readers retain the dated assessment. A recently fetched document cannot make an old paper newly published. Repeated unchanged but still-fresh evidence is allowed; requiring `new/updated > 0` would create an incentive for fake churn.

No stored schema field, enum or version was removed. New TS source metadata fields are optional so older consumers remain readable; missing provenance stays conservative. Existing live data is not regenerated or migrated. Generated summaries gain caveats only on a future authorized run; old previews/details/archives receive reader safeguards immediately. Generated source, story, correction and translation identities remain intact.

## Regression coverage

- `tests/unit/coverage.test.ts`: valid news, research-only/empty/legacy snapshots, evergreen docs, 72-hour boundary, stale publication vs fresh collection, invalid/naive/calendar/future timestamps, source timestamp checks, timezone equivalence and unchanged fresh editions.
- `tests/unit/trust.test.ts`: legacy enum readability, provenance vs independent reporting, preprint detection and omitted/unassessed significance.
- `tests/unit/i18n.test.ts`: dictionary parity, readable Bangla for new trust/fallback/freshness keys, and rejection of question-mark/replacement corruption.
- `tests/unit/build-input.test.ts`: missing/corrupt snapshot, invalid mode and compatible legacy input.
- `pipeline/tests/test_wave1.py`: dedupe permutations/ties/updates, clustering/category/rank/evidence-hash invariants, separate versions/events and same-event URLs, generated/legacy preprint policies, positive/negative peer-review examples; 5 MB response blocked before parsing; UTF-8/16 DTD rejection; 20,000 bounded items in a child process with a five-second deadline; Windows-1252, Atom namespace and malformed feeds. All inputs are synthetic and network-isolated.
- `pipeline/tests/test_integration.py`: steady-state snapshot serialization remains identical even with reversed input order; novelty intentionally differs between initial seed and later runs.
- `pipeline/tests/test_translation.py` and `test_owner_launch.py`: denied submissions never reach a capable translation provider; live rights-denied output has no translations.
- `tests/e2e/post-audit.spec.ts` and localization assertions: empty news/research distinction, card/briefing/detail/saved fallback, translated fixture omission, evidence explanation and preprint unknowns, mobile wrapping, themes and axe. Existing mobile prominence and security assertions remain unchanged.

Minimal baseline reproducer (in memory, using `git show HEAD:pipeline/dedupe.py`): equal-priority duplicates with IDs `a`/`b` produce survivors `{a,b}` across permutations before the fix and `{a}` after. The baseline `cluster()` already yields one invariant grouping for these permutations, confirming why a broader rewrite was rejected.

## Verification record

Checks use existing locked dependencies. Pytest temporary roots, browser output/logs and screenshots are under `%TEMP%/techline-wave1-932e2fb1` on C:. The isolated source workspace is approximately 2.3 MiB and links existing locked modules; it is not a clean-room installation. Its first build picked an unrelated profile-level CommonJS `cookie` package because of ancestor resolution; a private link to the already installed locked `cookie@2.0.1` corrected the isolation environment. No package installation or dependency/lock change was made.

The first targeted browser pass caught a 759.8px mobile lead position; extended coverage details were moved after main rather than relaxing the existing 650px assertion. Full browser checks caught the longer Bangla Home label wrapping at 320/390px; the compact localized label was corrected. A measured 100,139-byte initial JS payload exceeded the unchanged 100,000-byte budget; obsolete replaced dictionary entries were removed. The independent review caught a shell encoding conversion in newly added Bangla strings and a negated peer-review loophole; both received corrections and regressions.

| Command/check | Actual result |
| --- | --- |
| `.venv/Scripts/ruff.exe check pipeline` | Pass |
| `.venv/Scripts/python.exe -m pytest -q` with isolated C: `--basetemp`/cache | **154 passed**, final run 22.77 seconds |
| `pnpm exec vitest run --maxWorkers=1` | **123 passed**, 12 files; includes localization, trust, freshness, CSP, cache and release guards |
| `pnpm lint` | Pass, zero warnings |
| `pnpm typecheck` | 63 files, zero errors/warnings/hints |
| `python -m pipeline --validate` | Original live edition: 37 stories, 9 digests |
| `pnpm build` | Final clean Astro static build, notices, Pagefind and provenance pass; live data, local noindex |
| `node scripts/verify-build.mjs` | Pass: 309 assets, 5,708,905 bytes, initial JS **99,708 bytes gzip**, CSS **39,458 bytes** / 8,975 gzip |
| `node scripts/security.mjs` | Source/build credential scan and security-header policy pass |
| `node scripts/audit-dependencies.mjs` | Zero registry advisories; locked mitigation passes, with visible November 3 reassessment warning |
| `node scripts/content-rights.mjs` | 37 stories / 37 sources permitted |
| `node scripts/editorial-quality.mjs` | Pass with explicit zero-current-news/zero-Bangla warnings; 36 research, one reference, 12 research records outside seven days |
| `node scripts/editorial-quality.mjs --production` | **Expected block**, exit 1: no eligible current technology news within 72 hours |
| `node scripts/release-gate.mjs` | **Expected informational refusal**, exit 0, `RELEASE_APPROVAL_REQUIRED`, `publicationPerformed=false`; owner/account/origin/revision/preview gates and dirty-tree check remain |
| `node scripts/verify-docs.mjs` | Pass: 84 Markdown files, 264 local links; external link availability is not asserted |
| `node scripts/verify-repository.mjs` | Pass: 293 prospective files, real index unchanged; excludes private/generated artifacts |
| `node scripts/verify-site.mjs` | Pass: 132 HTML routes, 6,944 internal links, 37 RSS items, 89 sitemap routes; canonical, heading, anchor, robots and 404 checks |
| Full fixture `playwright test --workers=1` | **180 passed / 4 failed** in 6.7 minutes; all four failures were 320/390px Bangla Home wrapping in desktop/mobile projects. Android Chromium, iOS WebKit and touch Firefox scenarios passed; no timeout increase |
| Corrected fixture `playwright test header-search.spec.ts post-audit.spec.ts localization.spec.ts ux.spec.ts --project=desktop --project=mobile --workers=1` | **88 passed** in 2.7 minutes, covering every failed case and all affected UI/localization scenarios after the final copy correction |
| Live `playwright test post-audit.spec.ts --project=desktop --project=mobile --workers=1` | **12 passed** in 33.6 seconds; actual arXiv preprint and empty-news branches exercised |
| `node scripts/live-smoke.mjs` with C: artifact output | Pass: 37 stories, one offer, pagination/offers explicitly exercised, widths 320/390/834/1280/1366/1440, both themes, axe, zero console errors |
| Private `capture-wave1.mjs` | Six final captures; 1280px lead top 350.55px and 390px lead top 461.23px in both themes; no overflow/page errors; 25-hour collection-expiry check passes |
| Impeccable mechanical detector | One bounded pass; inherited design advisories retained, new indicator corrected to the existing micro typography/spacing tokens |

The final 184-scenario fixture suite was **not rerun wholesale** after the dictionary-only correction: all 88 affected scenarios were rerun successfully, and the other 96 passed in the full run. Do not relabel that earlier full run as 184/184 green. The sparse/zero-offer branches of live-smoke are now explicit but were not exercised by the retained 37-story/one-offer edition. No new Lighthouse lab run, clean-machine reinstall, physical-device/native Bangla review, hosted preview or deployment was performed; available RAM varied roughly between 0.5 and 1.7 GiB during work, and D: remains constrained. Existing dependency locks were reused, not reinstalled.

The final JS budget has only **292 bytes** of headroom; CSS has **542 bytes**. Future copy/features must recheck those unchanged limits. No budget or test threshold was relaxed.

Final screenshots are private at `%TEMP%/techline-wave1-932e2fb1/captures`: `home-light-1280.jpg`, `home-dark-1280.jpg`, `home-light-390.jpg`, `home-dark-390.jpg`, `bangla-english-preprint-card.jpg`, `preprint-detail.jpg`, plus `manifest.json`. The final mobile homepage, Bangla card and desktop dark capture were visually inspected against the preserved baseline. These are local live-source renders, not deployed or physical-device evidence. Detailed full/corrected/live browser logs, build logs, scanner/gate output and temporary failing-case traces remain beside the captures for owner review.

## Security and UI impact

SSRF allowlists/DNS pinning, exact-hash CSP generation, headers, SHA-pinned read-only Actions, publication approval, atomic snapshots, allowlisted recovery, disabled-source purge, locks and search architecture are retained. No new external origin, remote resource, visitor inference, API credential, schedule, deployment binding or publisher permission is added. The only parser restriction is rejection of unneeded DTD/entity declarations before expansion.

The approved theme, typography system, navigation mechanics, cards, tool directory, responsive structure and animation remain. Changes are editorial copy, dated metadata, compact language/preprint indicators, a news route/empty state, and expandable coverage information after the reading content. New screenshots are local Wave 1 evidence; the existing public gallery remains a historical October 14 baseline. Browser simulation is not physical-device or native-reader certification.

## Deferred findings and release requirements

F-01 is mitigated in product truth; broader rights-cleared current coverage remains an owner decision. F-03 transparency is implemented; a production Bangla corpus, provider entitlement and native review remain a separate milestone. F-04 fixes demonstrated determinism defects, while representative-only false splits and larger clustering algorithm changes are deferred. F-05 retains the existing November 3 cache-policy review. F-08 improves confirmed test structure without claiming every historical tail is reproduced. F-10 hosted operational capacity/recovery proof is deferred. F-11 legacy archive mode migration is deferred. P3 F-12–F-15/F-17 are not launch blockers and remain deferred; F-16 is retained by design.

Gate B remains unauthorized and undeployed. Required: owner review of this local diff, an approved exact revision, explicit preview approval, actual account/subdomain/origin and zero-spend evidence, an authorized fresh collection, unchanged rights/security/budget gates, noindex preview build, hosted headers/routing checks and rollback evidence. The current preview workflow also invokes the production editorial check: research-only coverage will block it. This wave deliberately does not weaken that gate; an owner-reviewed future preview-only editorial exception would need an explicit decision.

Gate C additionally requires a verified hosted preview, fresh prose-backed current news, a rights-compliant coverage plan, production editorial positioning review, actual recovery/rollback evidence and separate production authorization. Production translation claims require native review. Local tests cannot establish account billing, off-machine restore or edge behavior.

Practical coverage expansion: select one or two official announcement/release sources; establish source-specific terms, allowed fields, attribution/modification notices, excerpt and AI-submission permission; record approval in `source-rights.json`; configure allowlisted adapter limits; test disable/purge including cached summaries/history/archives; collect only after authorization; review precision, freshness, repeated editions and screenshots; then repeat release gates. Unresolved publishers stay disabled. Link-out or owner-authored coverage also needs an approved policy; neither is silently enabled here.

## Recommended commit grouping and rollback

Suggested owner-reviewed groups: (1) freshness/coverage and trust UI/generation policy with localization/regressions; (2) deterministic ties/category and parser/rights safeguards with Python regressions; (3) focused preflight, smoke/browser reliability and handoff documentation. No commits were created.

Rollback is a local, reviewed reversal of these exact source changes followed by a static rebuild from the preserved live snapshot. Do not reset the workspace or delete unrelated recovery material. Keep the existing locks, source/rights policy and release configuration. Policy-version changes invalidate generation caches on a later authorized ingestion; do not reuse a newly generated edition with older editorial assumptions without validation. No remote rollback is necessary because nothing was published.

## Independent review

A separate read-only agent context reviewed the full diff and rechecked corrections. It found the Bangla encoding problem, the negation case and stale test labels; final pass confirmed fixes, archive metadata compatibility, fallback coverage and stale-count disclosure, with no remaining verified P1/P2 code or security blocker. It did not run heavy checks or modify source. Acceptance remains subject to the measured final verification below and owner review; this is not a legal, native-language or hosted deployment clearance.

## Final state and exact next action

HEAD remains the baseline on `main`; origin is unchanged. There are 49 local modified/new files and no staged changes or commits. SHA-256 comparison confirms the canonical snapshot, run report, both dependency locks, source registry, source-rights policy and release configuration are unchanged. The original live edition never needed restoration because tests used isolated roots. Private artifacts occupy 31,949,465 bytes excluding shared dependency links. Final measured free space: C: 6,482,030,592 bytes; D: 261,369,856 bytes; free RAM 1,787,040 KiB after browser shutdown.

No known failing corrected local scenario remains. The expected production editorial block and release refusal are intentional. Product coverage and translation readiness remain open, not silently certified by code fixes. Owner next action: review this report and the local diff/screenshots, then decide a per-source rights-cleared current-news expansion plan (or an explicit preview-only editorial policy). Keep both deployment gates, schedules and inference off pending separate approvals and evidence. Do not commit or publish this working tree automatically.

## Actual changed-file inventory

49 local source/documentation/test files; no lock, rights/source approval, release setting, workflow, generated edition or real index change.

```text
README.md
apps/web/astro.config.mjs
apps/web/src/components/ContentIndicators.astro
apps/web/src/components/CoverageStatus.astro
apps/web/src/components/Feed.astro
apps/web/src/components/SavedStories.tsx
apps/web/src/components/StoryCard.astro
apps/web/src/i18n/bn.json
apps/web/src/i18n/en.json
apps/web/src/layouts/Layout.astro
apps/web/src/lib/data.ts
apps/web/src/lib/trust.ts
apps/web/src/pages/about.astro
apps/web/src/pages/archives/[month].astro
apps/web/src/pages/bn/news.astro
apps/web/src/pages/index.astro
apps/web/src/pages/news.astro
apps/web/src/pages/story/[slug].astro
apps/web/src/styles/global.css
docs/EDITORIAL_STYLE.md
docs/LOCALIZATION.md
docs/POST_AUDIT_WAVE1_REMEDIATION.md
packages/contracts/index.ts
pipeline/adapters.py
pipeline/ai.py
pipeline/dedupe.py
pipeline/ranking.py
pipeline/tests/test_integration.py
pipeline/tests/test_owner_launch.py
pipeline/tests/test_translation.py
pipeline/tests/test_wave1.py
pipeline/translation_fixtures.py
pipeline/verification.py
prompts/story_summary.md
scripts/coverage.mjs
scripts/editorial-quality.mjs
scripts/live-smoke.mjs
scripts/read-snapshot.mjs
tests/e2e/header-search.spec.ts
tests/e2e/localization.spec.ts
tests/e2e/platform.spec.ts
tests/e2e/post-audit.spec.ts
tests/e2e/premium.spec.ts
tests/e2e/ux.spec.ts
tests/unit/build-input.test.ts
tests/unit/coverage.test.ts
tests/unit/i18n.test.ts
tests/unit/release.test.ts
tests/unit/trust.test.ts
```
