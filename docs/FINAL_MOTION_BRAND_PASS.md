# Final UI, motion and branding pass — October 13, 2026

**Ready for final owner visual approval. English launch engineering passes; public release still needs operational setup and naming clearance. Production Bangla reporting is not ready.** No commit, push, deployment, external credential use or license decision occurred. Final snapshot/build is restored to the tested fixture/example-origin/noindex edition.

## A. Ticker root cause

The actual owner page at localhost:4321 was observed using real elapsed time. It had four items, a running timer, no JavaScript errors and reduced motion off. It advanced after 13.5 seconds. Clicking Resume while leaving the pointer over the button kept whole-strip hover suspension active, although the button changed to Pause. Moving the pointer away finally restarted rotation. This was an interaction/state defect, compounded by the long 12-second interval and nearly invisible opacity-only entrance, rather than a one-item or hydration failure. The former early return for fewer than two items also left an unexplained disabled Pause control.

Evidence: `.cache/deep-motion/before-runtime.json`; before desktop/mobile renders and original source are retained as review evidence.

## B. Exact motion fix

The strip now steps through up to four ranked edition records every **8 seconds**, using a **220ms** entrance from opacity **0.85** and **6px** below. The original lead/brief, facts and measurements stay stationary. Each headline remains a genuine clickable link, with its complete title retained. A visible position, Playing/Paused/Motion off/One headline state, Previous/Pause/Next and a synchronized progress line make behavior observable.

Hover pauses the headline reading area; parking the pointer over Resume permits playback. Keyboard focus anywhere in the strip, hidden tabs, offscreen placement, reduced motion and an open native modal suspend automatic changes. Pause preserves the remaining interval instead of silently restarting it. Manual previous/next works under reduced motion without animation; only requested changes use a polite announcement. Automatic changes do not interrupt screen readers with live announcements.

One-item mode omits/hides playback/navigation controls and the meter, reports One headline and schedules no timer. Duplicate IDs are handled conservatively. No-JS users get a stable first linked headline with hidden controls. The native search dialog now pauses the background headline and progress; closing it preserves manual pause and resumes only when other pause reasons clear.

Real wall-clock proof covered four cases on the live production preview and actual localhost:4321, using desktop mouse and mobile touch. All advanced automatically, stayed still during a three-second pause and resumed with the pointer/touch at the control. Progress froze during pause; strip height and lead position stayed unchanged, with zero overflow/page errors. Evidence: `.cache/deep-motion/real-runtime.json`; the local WebM and proof PNGs are in `%TEMP%/techline-deep-review/runtime/`.

## C–E. Modern style, section clarity and color

The strong sans masthead and English section headings provide a contemporary portal voice; article/news headlines retain the established serif and comfortable reading scale. Small category background/border transitions give deliberate hover feedback. The only repeating motion belongs to In focus: its two-pixel timed accent passes through blue, teal and indigo while the headline remains readable. It stops with playback. Important text and page backgrounds never cycle colors.

Nine category tiles remain dedicated navigation, followed by separate More stories cards and the distinct neutral Tools & trackers band. Clear descriptions, original-source destinations, aligned action rows and established spacing are retained. Obsolete category-hybrid/Keep reading CSS was removed. No extra section, card wrapper, interruption, glow, gradient, font download or motion dependency was added.

Navy supplies structure, rich blue denotes actions, teal gives the wordmark its second voice, ivory/cream supports reading, gray groups utilities, and muted gold marks credit. Rose remains only an error/expiry support color. Both themes retain their semantic palette and layered navy dark surfaces. [Current design system](../DESIGN.md).

## F. Appearance usability

Light and Dark are separate labelled buttons in an Appearance group. A filled active choice, mutually exclusive `aria-pressed`, desktop sun/moon icons and persistent selection make the result explicit. Mobile retains both readable labels and omits the icons to fit. Choosing the already active option is idempotent; it never toggles to the opposite choice. Keyboard focus, theme-color metadata and existing settings/device preference remain. Stable group geometry is checked at all six widths in both locale routes.

## G–I. Brand and masthead

Ten names were screened: Techline Today, Techfield News, Techlane News, Techspan Today, Techrange Today, TechScope Daily, Circuit Brief, Technology Dispatch, TechFront News and The Tech Outlook. The first five are conditional finalists; the other five have relevant publication collisions. [Scores, primary public sources and preserved historical reviews](BRAND_NAMING_REVIEW.md).

**Techline Today** is the new reversible UI-facing working name. Today reads more directly as news than Journal, and keeps the already readable root. The root remains crowded; no trademark, domain or handle clearance is claimed. Internal package/repository/infrastructure/storage identifiers stay unchanged.

The navy/teal protected English wordmark uses a **750-weight system-sans** treatment at **42px desktop / 36px tablet / 30px phone / 27px narrow phone**. The lightweight geometric news-sheet SVG and Technology News & Insights descriptor remain. No robot, brain or chip icon was added.

## J. Accessibility and localization

Both themes and locale routes were checked at 320, 390, 834, 1280, 1366 and 1440px. Browser checks cover axe A/AA, text/brand contrast, keyboard focus, static/reduced-motion/no-JS reading, source/evidence semantics, search trapping/restoration/Escape, saved-story feedback and stable layout. The headline clipping wrapper retains its visible 3px focus outline/offset. The Bangla counter uses natural translated word order and localized numerals.

Live coverage is **0/122 Bangla translations**. English fallback stays honest; five authored synthetic Bangla fixtures exercise wrapping and source/numeric preservation. All **122** live summaries are extractive, with **116** cached; AI summary/translation generation is zero. **54/122 (44.26%)** have headline-only source evidence and retain notices. No summaries or news were fabricated to reduce that ratio. Provider setup and native editorial review are still required; visitors trigger zero AI/translation calls. Bangla stemming, physical Android/Linux fonts and assistive-device testing remain limitations.

## K. Final tests, security and performance

| Gate | Final measured result |
|---|---|
| Ruff / pytest | Clean; 120 passed in 9.41s |
| ESLint / Astro check | Zero lint warnings; 55 files, 0 errors/warnings/hints |
| Vitest | 52 passed in 5 files, 498ms |
| Complete browser suite | 100 passed in 2.6m; desktop/mobile Chromium |
| Fixture validation | 12 stories, 14 digests, 5 authored Bangla translations |
| Live validation | 122 stories, 22 digests; 7 healthy sources; 0 validation failures; no provider credentials loaded |
| Responsive matrices | 264 fixture + 264 live states; zero overflow; 116 PNGs each |
| Real-time runtime proof | 4 cases: actual localhost:4321 and live preview; desktop mouse/mobile touch; automatic advance, pause, parked-pointer resume, stable strip/lead geometry; zero page errors |
| Dependency/security | Full/prod Node audits: 0 advisories; 31 frozen Python requirements: no known vulnerabilities; source/build secret scans passed |
| Cache-policy mitigation | Integrity-verified latest upstream 4.3.0 still accepts all 5 restricted max-stale probes; locked patch and 14 regression checks retained; deadline 2026-11-03 |
| Build budgets | 96,189 bytes JS gzip; 39,365 bytes CSS / 8,866 gzip; limits unchanged at 100,000 JS gzip / 40,000 CSS |
| Cloudflare dry-run | Wrangler 4.147.0; 1,120 asset files; worker 0.36 KiB / 0.25 KiB gzip; no bindings or publication |
| Fixture site verification | 94 HTML routes, 4,368 internal links, 494 external references, 12 RSS items, 81 sitemap routes |
| Live site verification | 326 HTML routes, 16,610 internal links, 1,642 external references, 50 RSS items, 198 sitemap routes |
| Repository/docs | 253 prospective files; real index unchanged; 52 Markdown files / 184 local links validated |

| Dataset / run | Performance | Accessibility | Best practices | SEO | LCP (ms) | CLS |
|---|---:|---:|---:|---:|---:|---:|
| Fixture 1 | 100 | 100 | 100 | 66 | 1666.2697 | 0 |
| Fixture 2 | 96 | 100 | 100 | 66 | 1660.9913 | 0 |
| Fixture 3 | 99 | 100 | 100 | 66 | 1794.3500 | 0 |
| Live 1 | 95 | 100 | 100 | 100 | 1672.2242 | 0 |
| Live 2 | 100 | 100 | 100 | 100 | 1667.7266 | 0 |
| Live 3 | 99 | 100 | 100 | 100 | 1779.8188 | 0 |


Live performance 95/100/99 (median 99), median LCP 1672.2242ms. Fixture performance 100/96/99 (median 99), median LCP 1666.2697ms. All unchanged Lighthouse/build gates pass. Accessibility and best practices are 100 in each run; CLS is 0 in all six runs. Live SEO is 100; fixture SEO is intentionally 66 because fixtures/example-origin output are noindex.

These are compressed local production-preview measurements, not deployed field results. LCP is shown to four decimals; original reports retain full values under `.cache/deep-motion/lighthouse-live/` and `lighthouse-fixture/`. The live canonical origin is a test value, not evidence of ownership/publication. Dependency audits remain clean, but the visible http-cache-semantics behavior mitigation is still required. [Security rationale](SECURITY.md).

The initial browser run was **98/100**: the new test expected the wrong Bangla Appearance group name. The expectation was corrected to the existing authored **থিম** label while preserving all assertions; the complete final run passes 100/100. An initial capture-script lint run required qualifying the browser CSSAnimation constructor through window; final lint passes. The first real-time harness sampled progress before the pause had reached the compositor's next frame; it now waits two rendering frames before the unchanged strict frozen-transform comparison, and all four cases pass. Browser output and full matrices use a dedicated temporary folder because the workspace drive has limited free space; no cleanup or weakened gate was used.

Independent fresh review opened all 13 required screens plus four composition captures, aligned the owner-directed portal changes and requested one material fix: background motion during search. Its verdict pass scored that correction **resolved**, disposition **ship**, at that exact scope. It did not run tests or grant legal/native-language/deployed approval. [Product/design documentation](../PRODUCT.md) was refreshed separately from actual code.

## L. Screenshots and review procedure

The [current gallery](assets/deep-motion/README.md) contains thirteen actual live JPEGs and two explicitly labelled authored Bangla fixture images. Start with *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*, *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*, *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*, *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*, *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*, *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* and *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*.

Full matrices and the 13-image review packet remain under `%TEMP%/techline-deep-review/`; each dataset matrix contains 116 PNGs/264 states. The runtime folder includes real-time motion proof and WebM. Earlier galleries and naming notes remain historical evidence.

Hard-refresh localhost:4321. Leave the pointer away from the headline for at least eight seconds, then pause and resume while keeping it over the button. Try Previous/Next, keyboard focus, search/Escape and Light/Dark. Hovering the headline deliberately protects reading. The final default dataset is synthetic; live screenshots show the validated public-source edition separately. [Mode-separated commands](TESTING.md).

## M–N. Remaining limits and approval verdict

**Ready for final owner visual approval.** Public release still requires the owner's appearance decision, defensible full-name/domain/handle clearance, actual HTTPS origin and protected publication credentials/environment, durable off-machine backup plus independent restore, and separately authorized deployment/edge checks. Production Bangla reporting needs a capable publication-time provider and native review. Reassess the cache mitigation by November 3. A legal source-code license remains an owner decision.

One remaining editorial issue is visible in the current live capture: the NVIDIA ecosystem lead is classified as Research and inherits a generic study-methods note. Classification and reusable “why it matters” wording need editorial review; structural/evidence validation does not certify those judgments. Source-backed summaries were preserved in this focused UI pass.

Physical-device/font and assistive-technology checks, credentialed provider transport, external CI/CodeQL and deployed field behavior were not certified. No-JS preserves reading and sources; interactive reader enhancements need JavaScript. [Readiness](PRODUCTION_READINESS_AUDIT.md), [validation](IMPLEMENTATION_VALIDATION.md), [operations](OPERATIONS.md).
