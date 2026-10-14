# Light-theme art direction and header — owner gallery

Actual Chromium captures from local production builds on 14 October 2026 (Asia/Dhaka). Before and after use the identical live edition generated at **2026-10-13T18:27:07.525175Z**, containing 135 stories. Bangla live UI labels English story fallback honestly. These images are local review evidence, not a deployment.

Capture uses reduced motion for stationary comparisons. Interactive query submission, keyboard focus/restoration, ticker behavior, appearance persistence and responsive menus are verified by browser tests. [Measured report](../../LIGHT_THEME_HEADER_REFINEMENT.md) · *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* · *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*.

## Before and after

| Condition | Before | After |
|---|---|---|
| Light desktop, 1366px | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |
| Light phone, 390px | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |
| Dark desktop, 1366px | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |
| Dark phone, 390px | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |

## Header detail at every requested width

| Width | English light | Bangla light |
|---|---|---|
| 320px | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |
| 390px | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |
| 834px | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |
| 1280px | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |
| 1366px | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |
| 1440px | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |

Dark header checks: *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*, *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*, *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*, *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*.

## Light-theme reading surfaces

| Surface | Desktop | Phone |
|---|---|---|
| Category, reporting and tools sections | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |
| Story detail | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |
| Search | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |

*Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*. The gallery includes 31 live JPEGs. Authored fixture examples added below are explicitly synthetic.

## Reproduction

Build the intended edition, then run `node scripts/precision-review.mjs <label>`. It checks edition/build agreement and captures 96 states per edition: homepage, category, story and populated search × six widths × two themes × two languages. Every homepage condition includes a header closeup and computed search dimensions. Full matrices remain under `%TEMP%/techline-precision/<label>/`; selected JPEGs are copied here. Historical galleries remain intact.

## Authored Bangla fixture examples

These two real browser renders use synthetic, authored test content generated on 2026-10-13T20:05:32.160634Z. They are not live reporting, provider output or evidence of production Bangla coverage. The visible demonstration notice remains.

- *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*: 1280 × 960, warm theme.
- *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*: 390px, full page, dark theme.

Reproduce with fixture generation/build and `node scripts/capture-localized-fixture.mjs docs/assets/light-header`.
