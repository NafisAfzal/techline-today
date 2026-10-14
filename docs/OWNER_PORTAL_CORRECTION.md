# Owner-directed portal correction — 14 October 2026

Follow-up: [precision visual refinement](PRECISION_VISUAL_REFINEMENT.md) preserves this approved architecture while strengthening the three major headings, theme-specific accents and optical alignment. Its [before/after gallery](assets/precision/README.md) is the current owner-review artifact. The original correction evidence below remains historical.

The existing Astro publication has been corrected for final owner visual review. This report covers the implementation and local production-preview evidence. Internal repository/package/infrastructure identifiers remain intact. No commit, push or deployment occurred.

## A. What was visually wrong

The actual preview at localhost:4321 was inspected before source edits at 1366px and 390px. The two sections immediately below **Explore by category** were **More stories** and **Tools & trackers**. Categories and reporting shared similar outlined rectangular treatments. The tracker band contained offer/model excerpts that also resembled story previews. This flattened navigation, reporting and reference tools into similar blocks. A short lead left excessive empty space beside the four-story briefing.

The current preview already contained Techline Today, neutral navy/teal tokens, labelled Light/Dark choices and a rotating In focus strip from prior work. Those rendered facts were acknowledged instead of claiming the preview was still pink or Apertide. This pass materially corrected the composition and strengthened the existing owner-directed identity.

## B. Category-area correction

- **Categories:** a cool neutral topic directory with consistent SVG symbols, short descriptions, actual story counts and Browse links. Nine links navigate to category routes without embedded news excerpts. Three columns become two on phones and one at 320px.
- **More stories:** reporting on the warm canvas, separated by a strong heading rule and editorial column dividers. Three desktop columns become a single mobile list. Headlines, short summaries, evidence links, publication ages, source names, original links and Save retain distinct roles.
- **Numeric previews:** only meaningfully labelled measurements appear as chips. Generic Source-reported extractions are omitted from previews; all original values and detailed source evidence remain unchanged.
- **Tools & trackers:** a navy reference band, with separate credit and model links, descriptive reference fields, high-contrast gold/teal headings and clear calls to action. Duplicated offer/model preview excerpts were removed. The navigation remains available when a tracker has no records; its destination explains that state.

The additional digest invitation remains a compact link row rather than another competing content section. *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* · *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*.

## C. Color system

| Role | Light appearance | Dark appearance / reference band |
|---|---|---|
| Canvas / reading surface | `#f4f2eb` / `#fcfbf7` | `#101c2d` / `#192a3f` |
| Masthead ink / interaction blue | `#142b49` / `#235aa0` | `#eef2f4` / `#91baf5` |
| Identity teal | `#216a6b` | `#88d0ca` |
| Category directory | `#eaf0f2` | `#16293c` |
| Utility band | `#142b49` | `#0c192a` |
| Utility text / secondary text | `#f3f6f8` / `#c0cedb` | Same contrast-safe roles |
| Utility links / credit gold / model teal | `#a8d1ff` / `#ead29e` / `#96d8cf` | Same contrast-safe roles |

Blue identifies interaction; teal is the secondary brand voice; gold identifies credit; status green/amber/rose retain evidence/expiry meanings. Ivory supports prolonged reading. Dark appearance has layered navy surfaces. Pink is absent from the primary identity. Only the small focus progress line transitions through blue, teal and muted indigo; no page canvas or headline changes hue.

## D. Naming decision

The five conditional candidates are **Techline Today**, **Techfield News**, **Techlane News**, **Techspan Today** and **Techrange Today**. The [naming review](BRAND_NAMING_REVIEW.md) records the seven requested scores, English/Bangla pronunciations, exact/near-name searches, primary source links and unresolved domain/handle availability.

**Techline Today** remains the leading local working name because it is easy to pronounce, immediately suggests technology reporting and supports expansion beyond AI. Techfield News is the backup. The Techline root is crowded, including a technical journal; retaining it is a design decision, not legal clearance. No exact domain or handle availability has been verified.

## E. Wordmark

A more prominent 44px system-sans masthead uses midnight Techline and restrained teal Today, with a lightweight two-page folio SVG and Technology News & Insights descriptor. The favicon uses matching geometry. The full English wordmark remains translation-protected on Bangla routes. Phone sizes are 30px/27px; the footer is consistently 26px. No heavy font or brain/circuit/robot illustration was added.

## F. Editorial motion

In focus rotates four actual deterministically ranked edition headlines every eight seconds. It makes no breaking-news or real-time claim; collection dates and periodic-collection language remain visible. Every rotating headline has a stationary lead/briefing alternative and a clickable story destination. Automatic changes use a restrained 220ms opacity entrance; manual changes are instant. A small linear progress line changes blue → teal → indigo and stays synchronized with the remaining interval.

Hovering the reading content or label pauses playback. Pointer playback controls stay usable so Resume works while the pointer remains there. Keyboard focus, reduced motion, open search, hidden tabs and offscreen placement pause rotation. Visible Previous/Pause/Next controls, position and playback state expose the behavior. Reduced motion disables automatic playback and decorative motion while retaining manual navigation. A single headline has no fake playback controls; no JavaScript leaves a static linked headline. No animation dependency was added.

## G. Theme usability

Desktop explicitly says Appearance beside the Light/Dark segments. Both visible labels persist on mobile; useful sun/moon symbols accompany them where space permits. Current choice is visibly filled and represented with `aria-pressed`. The control supports keyboard activation and local persistence, remains geometrically stable while switching, and updates browser theme metadata. There are exactly two header choices.

## H. Spacing and alignment

Shared 4–40px spacing tokens establish group and section rhythm. The lead/brief split is 1.4:1, with a tighter four-story briefing. When the lead has an excerpt, two additional existing summary points improve context and balance without adding facts. Directory rows remove repetitive card padding. Reporting columns align source/action rows. Tracker columns share a separator and align their links; mobile modules stack with a clear horizontal division. Header controls, footer lettering and narrow-screen gutters were checked optically.

Superseded homepage CSS was consolidated and unused selectors removed. Tailwind source detection is scoped to the web source directory. The existing CSS/JavaScript performance limits were retained.

## I. Accessibility and reduced motion

The browser checks cover English/Bangla UI, both themes, the six required widths, readable text, contrast, labelled controls, focus visibility, hit areas, keyboard navigation, search focus containment/restoration, saved-state feedback and static reading without JavaScript. Axe checks reported no violations on the covered fixture/live routes. Automatic changes do not repeatedly announce headlines; requested manual changes use a polite status message. Reduced motion has zero active page animations. Preview evidence remains explicit, including headline-only reports and untranslated English fallback.

## J. Verification results

| Check | Result |
|---|---|
| Ruff / pytest | Clean; 120 Python tests passed |
| ESLint | Clean, zero warnings |
| Astro typecheck | 56 files; zero errors, warnings or hints |
| Vitest | 52 tests passed across five files |
| Fixture E2E | 100 tests passed across desktop/mobile; latest complete run 2.4 minutes |
| Final preview correction | Live English/Bangla home and All stories contain no generic chips; canonical lead headline and all detail numeric values/labels unchanged |
| Responsive capture | 264 fixture and 264 final live measured states; six widths, two themes and two languages; zero overflow |
| Real-clock motion | English 1366px desktop and Bangla 390px touch: advance, pause, parked-pointer resume; stable strip/lead geometry; zero errors/overflow |
| Live ingestion / validation | 135 stories, 22 digests, seven successful/unchanged sources, zero validation failures; 121 cached extractive summaries; no AI generation |
| Live smoke / axe | Passed; six widths and major routes, both themes; working search/saved interactions, zero console errors, zero covered axe violations |
| Build / size budgets | 352 static HTML routes; CSS 39,844 bytes (9,025 gzip), initial referenced JS 96,312 gzip bytes; unchanged 40 KB/100 KB limits passed |
| Site verification | 352 HTML routes, 17,900 internal links, RSS/metadata/anchors/sitemap/404 passed |
| Security | Source/build secret scan and strict header checks passed |
| Node dependencies | Full policy audit and production audit: zero registry advisories; documented cache mitigation verified |
| Python dependencies | Frozen requirements audit: no known vulnerabilities |
| Lighthouse, final live build | Performance 100/99/100, median **100**; accessibility **100**, best practices **100** in all runs; median LCP **1.666 seconds**, CLS **0** |
| Cloudflare dry-run | Passed; no asset publication, bindings or deployment |
| Repository verification | Passed; real Git index unchanged; no commit/push |

Lighthouse SEO is 66 because this local/default-example-origin build deliberately remains noindex. These are compressed local production-preview measurements, not deployed field results. Reports are under `.lighthouseci/reports/` with preserved final copies in `%TEMP%/techline-deep-review/owner-lighthouse-live-final/`. The earlier fixture measurement had median performance 99, accessibility/best-practices 100, median LCP 1.730 seconds and CLS 0.

The fixture browser suite ran against its own hardened preview and fixture data. The final numeric-preview correction was subsequently validated against live rendering and exact canonical/detail preservation; it does not modify fixture source data. The live snapshot/build now serves localhost:4321. Before running fixture-specific release assertions again, select fixture mode and rebuild as described in [TESTING.md](TESTING.md).

The CSS budget initially failed at 42,083 bytes. Removing superseded rules and restricting source detection resolved it without relaxing the limit. The final visual-review fix was frontend-only. Temporary evidence resides under `%TEMP%/techline-deep-review/`, including the `owner-approval-fixture`, `owner-approval-live`, `owner-runtime` and preview-preservation records.

## K. Screenshots

The [gallery](assets/owner-portal/README.md) contains thirteen live production-preview images, two complete complaint-area images and two explicitly synthetic Bangla article examples. Desktop, phone, tablet, both themes, Bangla fallback, article detail, credit tracker and search are represented. The complete six-width/theme/language matrices and wall-clock runtime evidence remain in the local temporary review directory, separate from repository content.

## L. Remaining issues

- Name/domain/handle and relevant trademark clearance remain unresolved.
- Live Bangla reporting has no provider-generated translations; English fallback is clearly labelled. Authored Bangla fixtures demonstrate layout, not production translation quality or native editorial approval.
- Generic extracted numeric labels and category assignments require editorial review, including the research classification of an NVIDIA investment announcement. Preview cleanup preserves the underlying records and detail evidence.
- The existing `http-cache-semantics` mitigation remains explicit and is due for review by 3 November 2026; a clean registry audit does not certify an upstream fix.
- Local preview/default-example-origin builds deliberately remain noindex. Physical devices, assistive technologies and deployed field performance are outside the local browser evidence.

## M. Approval readiness

**Ready for final owner visual approval.** The independent bounded review confirmed that the category directory, reporting previews and tracker utilities clearly communicate their purpose. Its single frontend blocker—the anonymous numeric chips—was corrected and scored **resolved** in the updated-capture verdict pass. No rebuild or further recapture was requested. The scoped disposition was **Ship to owner visual review**.

Public release, legal clearance and production translation readiness are separate decisions. The owner can inspect the resulting source-backed local edition at localhost:4321; no deployment authorization is implied. No commit, push or deployment occurred.
