# Techline Today visual identity ? light theme and header, 14 October 2026

The current light-theme/header pass adds a soft-blue masthead, clearer summary blue, mint topic directory and richer utility navy to the established technology news desk. A real desktop search field replaces the small trigger; the visible Appearance caption is removed while its accessible group name remains. [Canonical system](../DESIGN.md) · [current validation](LIGHT_THEME_HEADER_REFINEMENT.md) · [current gallery](assets/light-header/README.md). The [precision report](PRECISION_VISUAL_REFINEMENT.md) and its gallery remain historical evidence.

## Semantic palette

Names match the existing CSS architecture. Warm and dark appearances remap the same roles; utility colors are considered separately on their respective navy backgrounds.

| CSS token | Warm/light | Dark | Role |
|---|---|---|---|
| `--bg` | `#f4f2eb` | `#101c2d` | Ivory / midnight page |
| `--surface` | `#fffdf8` | `#192a3f` | Warm reading paper / raised navy |
| `--secondary` | `#e3eee9` | `#23354a` | Sage grouping and selected surfaces |
| `--featured` | `#e1edf7` | `#20364b` | Clearer summary and ticker blue |
| `--header-bg` | `#e9f1f7` | `#192a3f` | Soft-blue masthead / existing raised navy |
| `--text` | `#182b43` | `#eef2f4` | Primary reading ink |
| `--muted` | `#566474` | `#b2becc` | Secondary text |
| `--navy` | `#142b49` | `#eef2f4` | Masthead and structural ink |
| `--accent` | `#1e5da8` | `#91baf5` | Cobalt actions, selection and focus |
| `--brand-secondary` | `#167467` | `#88d0ca` | Richer wordmark teal and topic icons |
| `--indigo` | `#515da0` | `#b0b7ef` | Existing ticker progress accent |
| `--warm` | `#855a27` | `#dec18c` | Bronze credit outside the utility band |
| `--green` | `#24664d` | `#a0cfb5` | Confirmed evidence |
| `--amber` | `#785820` | `#dec18c` | Caution and approaching expiry |
| `--coral` | `#923b43` | `#edaab0` | Expiry status only |
| `--line` | `#afc3c6` | `#4e6175` | Shared structural rules |
| `--soft-line` | `#d0ddd8` | `#354a60` | Supporting separators |
| `--directory-bg` | `#e0eee8` | `#16293c` | Mint topic directory / existing navy |
| `--section-category` | `#145f56` | `#96d8cf` | Deep directory teal |
| `--section-stories` | `#184b7e` | `#b7d1f5` | Rich editorial blue and upper rule |
| `--section-tools` | `#d4e5f6` | `#bed8f5` | Utility heading azure |
| `--utility-bg` | `#17344b` | `#0c192a` | Rich blue utility band |
| `--utility-text` | `#f3f1e9` | `#eeefe9` | Warm off-white utility ink / hover |
| `--utility-muted` | `#c6d1dc` | `#b8c7d6` | Utility descriptions and fields |
| `--utility-link` | `#b7d5f7` | `#9fc6f5` | Utility actions and focus |
| `--utility-teal` | `#a5d7cc` | `#92d2c7` | Model tracker label and icon |
| `--utility-gold` | `#e8cd97` | `#ddc18b` | Credit tracker label and icon |
| `--utility-line` | `#667e96` | `#536d85` | Utility dividers |

Teal denotes topic navigation, editorial blue denotes further reporting, and azure introduces utilities. Gold identifies credit; rose remains a minor expiry status. Article headlines retain reading ink. The *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* complement computed browser checks for default, hover and keyboard focus. Dark-theme palette values remain intact.

## Typography and optical spacing

The established major homepage section headings remain 700/30px desktop, 28px tablet (≤1100px), and 26px phone (≤720px). English leading stays 1.2 with -0.02em tracking. Bangla keeps 1.5 leading and normal tracking. All three titles fit one line at the six reviewed widths in both languages.

The 44/36/30/27px masthead, 36/29/27px lead, 23px brief title, 24/23px further-story headlines, 21px feed headlines, 16px summaries and 18px prose retain their roles. No font, package or dependency is added.

Directory rows lose their 4px inline inset, aligning icon edges and rules with the heading. More stories aligns its navigation action with the title row. Desktop tracker descriptions reserve two lines to align fields and actions; mobile descriptions flow naturally. The 20px heading/content gap, 40/32px section separation, 1240px container and 16px mobile gutters remain.

Existing SVG icons retain 24px desktop / 20px mobile directory sizing and 1.5px rounded strokes. Utility icons inherit their label color. Decorative aria-hidden semantics and accessible action names remain.

## Interaction and evidence

Utility hover uses warm off-white and a thicker underline, preserving contrast within the navy band. A redundant border-color transition is removed from category hover; the existing 160ms background response remains. Ticker timing, ranked links, Previous/Pause/Next, keyboard handling, pause reasons, reduced motion and stable geometry are unchanged.

Desktop search occupies 280–340px above 1000px; narrow layouts use the same accessible compact action. Typing and Enter carry the query into the existing dialog; Escape restores the originating field/button. Light/Dark labels and selected-state persistence remain. Narrow navigation moves overflowing shortcuts into the existing More menu, retaining one visible link per destination and 44px targets.

The [current gallery](assets/light-header/README.md) records the same live edition before and after refinement. Synthetic Bangla article examples are labelled separately. [Validation](LIGHT_THEME_HEADER_REFINEMENT.md) records exact tests, contrast, performance and limitations. Native Bangla review and physical-device font checks remain distinct from Chromium rendering. The provisional name remains subject to the existing [naming review](BRAND_NAMING_REVIEW.md). No commit, push, deployment or external production credential use occurred.

## Production mobile hardening, 2026-10-14

Approved palette and hierarchy are preserved. Native form fields use 16px for iOS focus behavior; Safari search focus restoration and a named edition-status landmark improve accessibility without a visual redesign. [Measured release checks](RELEASE_VALIDATION.md).
