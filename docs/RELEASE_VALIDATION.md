# Final release verification ? 2026-10-14

> Historical release evidence. The [owner launch plan](OWNER_GITHUB_LAUNCH_PLAN.md) and [current verification](OWNER_LAUNCH_VERIFICATION.md) supersede identity, licensing, source coverage, backup and workflow status below. Older counts and pending ownership statements are not current proof.

> Historical evidence from the earlier pass. [Current verification](PUBLIC_RELEASE_VERIFICATION.md), [independent re-review](PUBLIC_RELEASE_REVIEW.md) and the [A–T owner handoff](PUBLIC_RELEASE_PREPARATION.md) supersede earlier counts/readiness claims. Public GitHub and Cloudflare Free are confirmed preferences; actual publication remains unauthorized.

**All applicable local engineering gates passed. External publication is intentionally blocked at the release approval gate.** The approved design is preserved. No commit, push, repository creation, deployment, paid service, domain purchase, production credential use or external recurring job occurred.

## Baseline and changes

Before changes: Ruff/ESLint clean; pytest 120, Vitest 52 and existing Chromium E2E 112 passed; Astro 56 files had no diagnostics. The broader baseline simulated 1,152 fixture states: no overflow, small checked targets, overlaps, clipped labels or nav wrapping, but 271 states contained undersized native fields and 60 WebKit searches failed invoking-focus restoration. An intermediate confirmation left 72 wide-tablet search-field cases; the final 16px field rule resolves them.

Changes: Safari explicitly retains the invoking search control; all native search/sort/preference fields use 16px; edition metadata receives a named landmark; extractive advice is labelled Before you act; title-first classification avoids incidental research misclassification; insufficient prose receives a deterministic ranking penalty and homepage prominence prefers primary/independent prose. Invalid candidates consume their allowance before processing. No new library, font, palette or animation was added.

Release safety: exact repository/visibility/account/Worker/origin/approved revision, rights/license/backup and clean-checkout checks; production inference rejected until cost enforcement is verified; build provenance binds source/snapshot/archive inputs/assets; unexpected published-state cache loss fails closed. Ingestion/CodeQL cron and Dependabot activation remain disabled. Backup manifests validate monthly/yearly evidence contracts before empty-directory restoration.

## Exact final evidence

| Gate | Result |
|---|---|
| Python lint/tests | Ruff clean; **136 passed**, 0 failed, 16.39s |
| Frontend lint/types | ESLint clean; Astro **56 files**, 0 errors/warnings/hints |
| Vitest | **78 passed**, 0 failed, 6 files; final 821ms |
| Fixture browser regressions | **130 passed**, 0 failed, 4.7m; original 112 retained, 18 cross-engine cases added |
| Actual live touch checks | **18 passed**, 0 failed, 1.6m; actual Playwright tap input in Chromium/WebKit/Firefox, both locales, portrait/landscape, search/menu/theme/save/back-forward |
| Final live responsive matrix | **1,176 states**, 0 failing states/page errors; 15 widths, EN/BN, both themes, 3 engines, 4 device profiles with orientation/DPR |
| Live smoke | Passed actual 152-story edition at 6 widths, warm/dark axe, original links, search, save and fallback; 0 console errors |
| Fixture site verification | 94 HTML routes, 4,556 internal links, 494 external references, 12 RSS items, 81 sitemap routes |
| Final live/local site verification | **388 HTML routes**, **20,514 internal links**, **1,858 external references**, **50 RSS items**, **230 sitemap routes**; metadata/heading order/IDs/links/anchors/XML/robots/404 passed |
| Contracts/editorial gate | **152 live stories / 23 digests**, no demo flags; production editorial gate 0 errors |
| Node dependency policy | Full registry **0 advisories**, none suppressed; visible cache patch retained and verified |
| Python dependency audit | **31 frozen requirements**, no known vulnerabilities; pip-audit 2.10.1 |
| Source/build security | Passed secret/header/CSP scans; no browser provider/deploy credentials |
| Upstream mitigation reassessment | Official 4.3.0 tarball SHA-512 verified; all **5 unpatched restricted-cache probes** still permit unsafe reuse. Locked local patch and existing 14 cache tests retained. Review by **2026-11-03**. |
| Build budgets/provenance | **927 asset files**; **96,537 bytes initial JS gzip** / 100,000 limit; **39,107 CSS bytes** / 40,000 limit; **8,911 CSS gzip bytes**. Current source/data/archive/asset provenance verified. |
| Cloudflare dry-run | Wrangler 4.147.0, 1,337 reported input entries, 0.36 KiB wrapper / 0.25 KiB gzip, no bindings; dry-run exits without publishing |
| Backup recovery | Live **7-file pack** exported/verified/restored in an isolated empty directory; checksum equality verified. Local recovery only, no durable off-machine storage. |
| Repository/docs | 420 prospective files; 68 Markdown files / 372 local links passed; real Git index unchanged. Exact final counts are in *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*. |
| Publication authorization | Expected **RELEASE_APPROVAL_REQUIRED**, publish preflight exits 1; no Wrangler publication invoked |

Existing tests/thresholds were not weakened. The added touch suite uses the served edition's real headline rather than assuming fixture content; the original fixture assertions remain unchanged. The final local bundle was rebuilt with blank SITE_URL and remains **live data + noindex**. Temporary public-origin metadata validation used `https://release-validation.techline-today.dev` locally only; this is not an owned/selected production domain or deployment.

## Mobile, accessibility and contrast

Widths: 320, 360, 375, 390, 393, 412, 430, 480, 600, 768, 834, 1024, 1280, 1366, 1440. Chromium 153.0.8010.12, Firefox 155.0 and WebKit 26.6 on Windows. Simulated iPhone SE/iPhone 13/Pixel 7/iPad Pro 11 cover portrait/landscape and profile DPRs; Firefox uses supported viewport/touch simulation. Keyboard-reduced viewport checks verify close-button access, focus return and scroll unlocking. They do not operate a real mobile keyboard, physical notch or screen reader.

Final measured contrast ratios:

| Role/surface | Light | Dark |
|---|---|---|
| Category heading/directory | 6.27:1 | 9.19:1 |
| More stories heading/page | 7.99:1 | 10.97:1 |
| Tools heading/utility surface | 10.03:1 | 12.06:1 |
| Body text/page | 12.79:1 | 15.21:1 |
| Search text/field | 14.10:1 | 12.91:1 |

Existing computed hover/focus/icon/selected-state checks pass; axe passes both themes/locales. All above exceed the applicable WCAG text thresholds. System/Bangla font availability on physical Android/iOS, screen-reader announcements and assistive technology remain unverified.

## Performance

Unchanged Lighthouse median gates passed twice. First triplet: **70/100/100**, LCP **1705.31/1664.58/1664.53ms**, CLS 0; its first run recorded **4177.35ms TBT**, including a long module-start task. That outlier is retained and not hidden. A fresh confirmation triplet scored **98/100/99**, median **99**, median LCP **1729.41ms**, median TBT **97.62ms**, CLS **0**. Accessibility, best practices and temporary-production-origin SEO were **100 in all six runs**. *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*.

The long first-run task did not recur in the confirmation. Lab variability remains a limit, not a guaranteed production score. Field INP and actual edge/mobile-network performance require authorized deployment and real usage. Bangla Pagefind lacks stemming; exact-term search works with the fallback index.

## Live editorial scope and remaining limits

Five sources succeeded; Cloudflare's document and GitHub Releases returned HTTPStatusError and prior evidence was retained. The edition has **68 primary/independent prose-backed stories**, **64 headline-only records**, **0 Bangla story translations**, and one normalized-title mirror across an arXiv/community report more than the 72-hour clustering window apart. Source dates/links remain explicit; headline-only/community records are deprioritized. No full article was fabricated. Structural, numeric and evidence-length gates do not certify semantic truth or perfect classification.

Production AI/translation is blocked pending model-specific monetary enforcement and durable quota accounting. A safe launch uses extractive English reporting and a Bangla interface with disclosed English fallback. Full native reporting needs configured providers and native review.

[Independent audit](INDEPENDENT_RELEASE_AUDIT.md) found no open confirmed implementation defect in its audited scope. P1 launch dependencies remain: exact publication/account/origin/budget/revision approval; source-code/content/brand rights; durable off-machine backup and independent restoration. Physical devices, hosted CI/CodeQL, edge security/routing/rollback and field performance are unverified. [Owner handoff](RELEASE_HANDOFF.md) ? [Approval gate/actions](RELEASE_APPROVAL_GATE.md) ? [21 screenshots](assets/release/README.md).
