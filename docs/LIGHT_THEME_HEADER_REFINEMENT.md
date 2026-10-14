# Light-theme art direction and header refinement — 14 October 2026

The owner's approved architecture remains. This pass makes the light appearance more expressive through coordinated blue/mint/navy surfaces and strengthens masthead search. No application rebuild, new dependency, font, image asset, commit, push, public deployment or external production credential use occurs.

## Header and search

- Removed the visible **Appearance** caption. The localized `role="group"` accessible name, visible Light/Dark labels, selected styling, `aria-pressed`, keyboard access, metadata and persistence remain.
- Added a real desktop search form in the existing React island. The localized field shares the existing query state. Enter or the magnifier opens the native dialog with that query; Escape returns focus to the originating input or button. Header typing alone does not download a search index.
- Search area width is `clamp(280px,24vw,340px)` above 1000px: measured **307.19px at 1280**, **327.83px at 1366**, **340px at 1440**. At 1000px and below the same button becomes a compact search action; mobile keeps its Search label above 380px.
- One 3px blue outline surrounds the search form, avoiding competing nested rings. Existing dialog focus containment, 120ms debounce, stale-result protection, fallback search, shortcuts and focus restoration remain.
- Narrow navigation keeps one row and 44px targets. English moves Chips into More at ≤380px. Bangla moves Chips at ≤720px and Security at ≤380px. Every destination has one visible link; the full desktop shortcut row remains. No label is crushed or made tiny to fit.

The masthead keeps its 44/36/30/27px type scale. Its width and first-row balance were inspected with actual screenshots and bounding boxes, including intermediate widths around both responsive breakpoints.

## Light-theme composition

The former light system used similar gray-blue fields. The refined appearance uses broader, coordinated color regions with clear purposes; warm ivory and readable ink remain the reading foundation.

| Role | Previous light | Final light | Purpose |
|---|---|---|---|
| Header | `#fcfbf7` | `#e9f1f7` | Soft editorial blue establishes the publication/navigation field |
| Reading paper | `#fcfbf7` | `#fffdf8` | Brighter warm paper, including the search input |
| Summary / ticker | `#e9f0f4` | `#e1edf7` | Clearer blue gives the edition strip and summary a recognizable field |
| Directory | `#eaf0f2` | `#e0eee8` | Mint distinguishes topic navigation |
| Grouped / selected surface | `#e7ecee` | `#e3eee9` | Quiet sage supports secondary states |
| Interaction | `#235aa0` | `#1e5da8` | Cobalt identifies actions and focus |
| Brand / icon teal | `#216a6b` | `#167467` | Richer teal coordinates wordmark and topic symbols |
| Directory heading | `#1d6064` | `#145f56` | Deep teal anchors the mint field |
| Editorial heading / rule | `#183e68` | `#184b7e` | Rich blue marks further reporting |
| Tools band | `#142b49` | `#17344b` | Rich navy separates reference utilities |
| Utility credit gold | `#e6cc98` | `#e8cd97` | Restrained warm credit cue |
| Credit outside utilities | `#785820` | `#855a27` | Bronze supports the light appearance |
| Strong / supporting rules | `#c0c9cf` / `#d8dfe2` | `#afc3c6` / `#d0ddd8` | Coordinated structural separators |

The ivory page `#f4f2eb`, primary ink, evidence green, caution amber and expiry rose remain. The dark palette retains every established value; `--header-bg` resolves to its existing `--surface`. [Complete 28-role palette](VISUAL_IDENTITY.md), [canonical design system](../DESIGN.md).

The nine category links, editorial story columns, navy utilities, 30/28/26px major headings, icons, reading typography, source content, rankings, translations/fallback, page widths and section spacing remain. Ticker timing and motion code are unchanged. Color supports section purpose and active states; there are no rainbow cards, extra glows or moving backgrounds.

## Accessibility and measured contrast

Computed styles, resolved theme tokens and rendered browser checks cover both themes. The form's focus outline, placeholder, icon and text have dedicated regressions; existing tests retain touch targets, theme switching, readable type, localization, no-JS reading and reduced motion.

| Pair | Light | Dark |
|---|---|---|
| Search placeholder / paper | **5.95:1** | **7.71:1** |
| Search focus / header | **5.77:1** | **7.30:1** |
| Search icon / paper | **6.48:1** | **7.30:1** |
| Header supporting text | 5.30:1 | 7.71:1 |
| Directory heading | 6.27:1 | 9.19:1 |
| Directory icon | 4.71:1 | 8.42:1 |
| Editorial heading | 7.99:1 | 10.97:1 |
| Tools heading | 10.03:1 | 12.06:1 |
| Utility supporting text | 8.32:1 | 10.25:1 |
| Utility divider | 3.06:1 | 3.28:1 |

Affected normal text exceeds 4.5:1; meaningful icons and focus exceed 3:1. *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*. Live smoke reports zero browser console errors and passes axe in light/dark.

## Architecture and performance

The search field stays in the existing lightweight island, reuses query state and opens the existing dialog. Pagefind remains dynamically imported on an actual search; source-backed publication remains static. No external production credential is used.

Initial referenced JavaScript is **96,439 bytes gzip**, versus **96,312** before: **127 bytes added**. Application CSS is **39,127 bytes raw / 8,913 gzip**, versus **39,945 / 9,125** before. All original budgets remain. An unused Tailwind `filter` utility and its generated property helpers were excluded after confirming no UI uses that class; [official source-exclusion documentation](https://tailwindcss.com/docs/detecting-classes-in-source-files#explicitly-excluding-classes). Other source detection, used utilities and preflight remain intact.

Final compressed live-production-preview Lighthouse runs:

| Metric | Three runs | Median |
|---|---|---|
| Performance | 99 / 99 / 98 | **99** |
| Accessibility | 100 / 100 / 100 | **100** |
| Best practices | 100 / 100 / 100 | **100** |
| LCP | 1.960 / 1.799 / 1.661 seconds | **1.799 seconds** |
| CLS | 0 / 0 / 0 | **0** |

SEO is 66 because the local/default-example-origin build deliberately remains noindex. These are local lab measurements. Full reports are preserved under `%TEMP%/techline-precision/header-lighthouse-final/`.

## Owner review and limitations

| Engineering gate | Final result |
|---|---|
| Ruff / pytest | Clean; **120 passed**, 8.96s |
| ESLint | Clean, zero warnings |
| Astro check | **56 files**, zero errors/warnings/hints |
| Vitest | **52 passed**, five files, 883ms |
| Full browser E2E | **112 passed**, 3.0m; desktop/mobile Chromium, including six new header/search cases |
| Header stress | Sixteen widths from 320 to 1440px in both locales; no collisions, overflow, masthead wrapping or navigation-row wrapping |
| Final responsive matrices | **96 live + 96 fixture states**, both locales/themes, six target widths; zero overflow |
| Fixture/localization validation | 12 stories, 14 digests, five authored Bangla examples; resource parity and truthful fallback passed |
| Live site verification | **352 routes**, 18,604 internal links, 1,732 external references, 50 RSS items, 211 sitemap routes |
| Fixture site verification | **94 routes**, 4,556 internal links, 494 external references, 12 RSS items, 81 sitemap routes |
| Live smoke / axe | Passed, light/dark; **zero console errors** |
| Source/build security | Passed |
| JS dependency audit | Zero registry advisories; existing locked build-only cache mitigation verified |
| Python dependency audit | Frozen requirements, pip-audit 2.10.1; no known vulnerabilities |
| Lighthouse / asset budgets | All existing gates passed; *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |
| Cloudflare dry-run | Passed with API credentials removed from the child environment and telemetry disabled; no bindings, upload or deployment |
| Repository verification | Passed: **377 prospective files**; actual Git index unchanged; whitespace, credentials, machine paths, artifacts and file-size gates intact |

All existing tests and thresholds remain intact. Browser artifacts are directed to `%TEMP%/techline-precision/header-e2e-results/` to avoid the project-drive trace-space issue encountered in the previous pass. *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* records the 96-state baseline and both final matrices. The three recorded matrices contain 288 conditions, all without horizontal overflow.

[Comparison gallery](assets/light-header/README.md): before/after light and dark desktop/phone, header closeups at all six target widths in English/Bangla, light reporting/tool surfaces, story detail and search. Before/after use the same 135-story edition. Synthetic Bangla examples are labelled separately.

No blocking visual issue remains after the bounded review. Physical-device system fonts and native Bangla editorial/assistive-technology review remain outside Chromium evidence. Live reporting retains its explicit English fallback. Existing naming clearance and the temporary build-only cache-dependency mitigation remain separate operator concerns. The live edition is restored after fixture tests; no publication occurs.

**Ready for final owner visual approval.** The light palette, simplified appearance control and wider search are complete and reviewable. All three major heading sizes, topic directory, reporting columns, utility structure and ticker behavior remain protected.
