# Precision refinement — owner comparison gallery

Actual Chromium screenshots from local production builds, captured on 14 October 2026 (Asia/Dhaka). Before and after show the identical live snapshot generated at **2026-10-13T18:27:07.525175Z**, with 135 stories and no fixture content. Bangla live UI honestly labels English reporting fallback. These images do not represent a deployment.

Capture uses reduced motion to keep the edition stationary for comparison. Ticker behavior is verified separately by the full browser suite. [Typography, palette, contrast and validation](../../PRECISION_VISUAL_REFINEMENT.md) · *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* · *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*.

## Three major sections, before and after

Each image includes Explore by category, More stories and Tools & trackers in their existing order.

| Condition | Before | After |
|---|---|---|
| Warm desktop, 1366px | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |
| Dark desktop, 1366px | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |
| Warm phone, 390px | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |
| Dark phone, 390px | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |

## Complete homepage comparison

| Condition | Before | After |
|---|---|---|
| Warm desktop | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |
| Dark desktop | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |
| Warm phone | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |
| Dark phone | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |

## Other reviewed widths

| Width | Warm | Dark |
|---|---|---|
| 320px | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |
| 834px | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |
| 1280px | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |
| 1440px | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |

## English and Bangla reader paths

| Surface | Warm desktop | Dark desktop | Warm phone | Dark phone |
|---|---|---|---|---|
| English category | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |
| English story | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |
| English search | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |
| Bangla homepage | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |
| Bangla category | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |
| Bangla story fallback | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |
| Bangla search | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* | *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* |

## Reproduction

Run `node scripts/precision-review.mjs <label>` after building the intended edition. It verifies snapshot/build agreement and measures homepage, category, story and populated search in both themes/languages at 320, 390, 834, 1280, 1366 and 1440px: 96 states per dataset. Full matrices and computed styles stay in `%TEMP%/techline-precision/<label>/`. Selected review JPEGs are copied here; historical galleries remain intact.

Authored Bangla fixture examples added below demonstrate script layout, not provider translation quality or live reporting.

## Authored Bangla fixture examples

These two real browser renders use synthetic, authored test content generated on 2026-10-13T19:17:53.974560Z. They are not live reporting, provider output or evidence of production Bangla coverage. The visible demonstration notice remains.

- *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*: 1280 × 960, warm theme.
- *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*: 390px, full page, dark theme.

Reproduce with fixture generation/build and `node scripts/capture-localized-fixture.mjs docs/assets/precision`.
