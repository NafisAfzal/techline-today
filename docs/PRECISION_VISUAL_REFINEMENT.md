# Precision visual refinement — 14 October 2026

This pass refines the owner's approved homepage architecture. The ranked lead/brief, category navigation, three editorial previews, navy utilities, authored icons and controlled ticker retain their purpose and behavior. Frontend implementation changes are confined to CSS; supporting changes add regressions, reproducible inspection and documentation. No commit, push or deployment is authorized or performed.

## A. Before and after typography

Fresh production-preview measurements confirmed all three titles were 25px at every target width, weight 650 and English line height 1.3. The existing gallery was checked against those renders before editing.

| Title | Before | Desktop after | Tablet after | Phone after |
|---|---|---|---|---|
| Explore by category | 25px / 650 | 30px / 700 | 28px / 700 | 26px / 700 |
| More stories | 25px / 650 | 30px / 700 | 28px / 700 | 26px / 700 |
| Tools & trackers | 25px / 650 | 30px / 700 | 28px / 700 | 26px / 700 |

Breakpoints: tablet ≤1100px, phone ≤720px. English leading is 1.2; tracking is -0.02em, previously -0.015em. Bangla keeps 1.5 leading and normal tracking. Targeted rules apply only to `.home-section>.section-top h2`. The shared 25px heading scale, 23px briefing title, 44px desktop masthead, 36px desktop lead, 16px summaries and 18px prose retain their established sizes. All three major titles remain one line at 320/390/834/1280/1366/1440px in both locales/themes.

## B. Theme-aware composition

| Semantic role | Warm/light | Dark | Purpose |
|---|---|---|---|
| Page / paper | `#f4f2eb` / `#fcfbf7` | `#101c2d` / `#192a3f` | Existing comfortable reading foundation |
| Directory heading | `#1d6064` | `#96d8cf` | Topic navigation uses deep / soft teal |
| Editorial heading / rule | `#183e68` | `#b7d1f5` | Recognizable reporting section |
| Utility heading | `#d4e5f6` | `#bed8f5` | Azure hierarchy within the navy band |
| Utility background | `#142b49` | `#0c192a` | Existing stronger reference surface |
| Utility reading / supporting ink | `#f3f1e9` / `#c6d1dc` | `#eeefe9` / `#b8c7d6` | Warm off-white and cool supporting text |
| Utility link / focus | `#b7d5f7` | `#9fc6f5` | Clear source-directed navigation |
| Model / credit labels | `#a5d7cc` / `#e6cc98` | `#92d2c7` / `#ddc18b` | Teal models, restrained gold credit |
| Utility divider | `#667e96` | `#536d85` | Readable structure in each theme |

The complete 27-role palette is in [VISUAL_IDENTITY.md](VISUAL_IDENTITY.md) and [DESIGN.md](../DESIGN.md). Existing blue actions, teal wordmark, evidence green, caution bronze/amber and occasional expiry rose remain semantic. No random headline colors, additional category colors, gradients or glow effects are added.

## C–D. Section, icon and spacing refinements

- **Directory:** stronger teal title, familiar cool field, existing nine pure navigation rows. Removing the 4px row inset aligns icon edges, descriptions and shared rules with the title. SVGs retain 24px desktop / 20px phone sizing and 1.5px rounded strokes.
- **More stories:** stronger editorial-blue title with a coordinated 2px upper rule. The existing three serif columns, summaries, evidence, source links and Save actions remain. See all stories now aligns with the title row instead of the combined title/description block.
- **Tools & trackers:** stronger azure title; separately tuned utility ink, links, gold, teal and dividers in both themes. Desktop descriptions reserve two lines to align fields/actions; phone descriptions remain natural. The two modules and their shared divider remain unboxed.

The 1240px content width, 16px narrow-phone gutters, 20px title/content gaps, 40px desktop / 32px phone section separation, lead padding and footer rhythm remain. Existing reader prose and Bangla mixed-script handling remain comfortable. Icons stay decorative for assistive technology; action names remain explicit.

## E. Interaction and motion

Utility hover changes to its own warm off-white ink and thickens the underline to 2px, preventing the global link hover color from taking over that surface. Utility focus uses its existing 3px outline with a theme-specific link shade. Directory hover keeps its 160ms background response; an unused border-color transition is removed.

Ticker rotation, actual ranked links, timing, position, Previous/Pause/Next, keyboard handling, remaining-time preservation, hover/focus/modal/offscreen/hidden pauses and reduced-motion manual navigation are preserved. Captures use reduced motion for deterministic comparisons; browser regressions exercise actual interaction behavior separately. There is no new motion, island, font or dependency.

## F. Accessibility and contrast

Ratios use the final theme tokens read from computed browser styles. Text, icons and utility interaction states also have rendered regression checks; live smoke and existing browser gates run axe.

| Pair | Warm | Dark |
|---|---|---|
| Category heading / directory | 6.27:1 | 9.19:1 |
| Editorial heading / page | 9.72:1 | 10.97:1 |
| Tools heading / utility | 11.10:1 | 12.06:1 |
| Utility supporting text | 9.21:1 | 10.25:1 |
| Utility link / focus | 9.43:1 | 9.99:1 |
| Model label / icon | 8.96:1 | 10.32:1 |
| Credit label / icon | 9.14:1 | 10.16:1 |
| Utility hover text | 12.62:1 | 15.28:1 |
| Utility divider | 3.39:1 | 3.28:1 |
| Directory icon | 5.46:1 | 8.42:1 |
| Directory supporting text | 5.26:1 | 7.86:1 |
| Selected appearance text | 6.16:1 | 8.60:1 |

Affected text exceeds WCAG AA: 4.5:1 normal text, 3:1 large text; meaningful icons and focus exceed 3:1. Structural directory rules retain their quieter existing tokens. Keyboard, touch targets, selected appearance state, dark/light switching, no-JS reading, fallback disclosure and reduced motion remain under the existing suite. *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*.

## G. Performance and engineering evidence

Three compressed local-production Lighthouse runs, against the preserved live edition:

| Measurement | Runs | Median |
|---|---|---|
| Performance | 99 / 100 / 99 | **99** |
| Accessibility | 100 / 100 / 100 | **100** |
| Best practices | 100 / 100 / 100 | **100** |
| LCP | 1.971 / 1.764 / 1.660 seconds | **1.764 seconds** |
| CLS | 0 / 0 / 0 | **0** |
| FCP | 1.442 / 1.347 / 1.367 seconds | **1.367 seconds** |
| Total blocking time | 7 / 59.486 / 113ms | **59.486ms** |

SEO is 66 in all runs because this default-example-origin local build intentionally stays noindex. These are local lab measurements, not deployed field results. Reports are preserved under `%TEMP%/techline-precision/lighthouse-live/`.

Initial referenced JavaScript remains **96,312 bytes gzip**, identical to baseline. CSS is **39,945 bytes raw / 9,125 bytes gzip**, versus baseline **39,844 / 9,025**. Consolidating superseded declarations keeps the existing 40,000-byte gate intact; its first failure was fixed without changing thresholds. No dependency, font, runtime, ranking, route, content contract or publication pipeline changed.

| Engineering gate | Final result |
|---|---|
| Ruff | Passed |
| pytest | **120 passed**, 13.26s |
| ESLint | Passed, zero warnings |
| Astro typecheck | **56 files**, zero errors/warnings/hints |
| Vitest | **52 passed**, five files, 773ms |
| Complete browser E2E | **106 passed**, 2.5m; desktop/mobile Chromium, including six new precision cases |
| Fixture validation / localization | 12 stories, 14 digests, five authored Bangla translations; resource parity and fallback gates passed |
| Preserved live validation | 135 stories, 22 digests |
| Site verification, live | **352 routes**, 17,900 internal links, 1,732 external references, 50 RSS entries, 211 sitemap routes |
| Site verification, fixture | **94 routes**, 4,368 internal links, 494 external references, 12 RSS entries, 81 sitemap routes |
| Live smoke | Passed at six widths; axe in warm/dark, **zero console errors** |
| Source/build security | Passed against live and fixture builds |
| JavaScript dependency audit | Zero registry advisories; existing locked build-only `http-cache-semantics` mitigation verified, review due 3 November 2026 |
| Python dependency audit | Frozen requirements scanned with pip-audit 2.10.1; no known vulnerabilities |
| Performance / build budgets | All existing thresholds passed |
| Cloudflare deployment dry-run | Passed; no bindings, upload or deployment |
| Repository verification | Passed: 337 prospective files; real Git index unchanged; whitespace, secrets, machine paths, artifacts and file-size checks passed |

The first full browser run had 102 passes and four trace-write failures from insufficient space on the project drive. Traces were preserved on the temporary drive, and the unchanged full suite passed with `--output` redirected there. No assertions, thresholds, retries or trace settings were weakened. Fixture tests ran against a separate hardened preview; the live snapshot is restored after testing. Reproduction and output paths are documented in [TESTING.md](TESTING.md).

## H. Screenshot comparison

The [owner gallery](assets/precision/README.md) includes before/after warm desktop, dark desktop, warm phone, dark phone and the complete three-section area, plus all requested widths, category feeds, search and story paths in both locales/themes. **52 live images and two explicitly synthetic Bangla article images** are included. Before and after use the identical 135-story live edition generated at 2026-10-13T18:27:07.525175Z. The original owner-portal gallery remains intact.

*Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* records 96 baseline live states, 96 final live states and 96 final fixture states. Each matrix covers six widths × two locales × two themes × four reader states, with **zero horizontal overflow**. Final live/fixture matrices include homepage, category, story and populated search. The source comparison confirms unchanged live lead size and height across all 24 homepage conditions. Authored fixture translations provide five examples; live translation fallback remains truthful.

## I. Remaining limitations

No blocking visual defect was found in the bounded final review. Platform fonts can differ on physical Android/Linux devices; native Bangla editorial and assistive-technology review remain outside Chromium evidence. Existing mixed English technical terms and explicit untranslated reporting remain visible. The CSS gate has only 55 bytes of raw headroom, so future additions should consolidate styles. Existing naming clearance and the documented temporary build-only cache-dependency mitigation remain operator concerns, separate from this visual change.

## J. Owner approval readiness

**Ready for final owner visual approval.** The larger, separately colored section titles strengthen hierarchy while preserving the approved directory, editorial grid, navy tools band and motion. The comparison gallery makes the scope reviewable in both themes on desktop and phone. This local validation does not imply approval for public publication. No commit, push or deployment occurred.
