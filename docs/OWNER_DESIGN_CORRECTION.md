# Owner-directed design correction — October 13, 2026

> Historical owner-correction evidence. Superseded by the [final UI/motion pass](FINAL_MOTION_BRAND_PASS.md); retain the original measurements and captures.

**Ready for final owner visual approval. English launch engineering passes; public release remains operationally blocked and production Bangla content is not ready.** Techline Journal is the provisional working masthead. No commit, push, deployment, external account change, credential disclosure or license selection occurred. The final local dataset/build is restored to synthetic fixture/example-origin/noindex mode.

## A. What was visually wrong

The actual owner's localhost homepage was inspected at 1280px and 390px before editing, including full-page and category-area screenshots. The reported “two sections” directly beneath Explore were actually two columns of category/headline hybrids: small category labels, source/evidence metadata and article headlines shared the same row treatment. Counts and browse links did not clearly distinguish navigation from editorial previews. The credit/model pair above Explore also used similar rules, weakening its identity as a utility area. The old plum/burgundy identity, poetic introduction and icon-only appearance control reinforced the owner's concerns.

The correction prioritizes recognizable news architecture, neutral reading surfaces, explicit control labels and one controlled editorial movement. It preserves the existing product and its source/evidence/ranking contracts. The October 12 report remains [historical evidence](PRE_RELEASE_REFINEMENT.md), superseded by this direction.

## B. Category architecture

Explore now contains nine navigation tiles, each with a category, plain description, genuine story count and Browse action. It contains no story headline. Three further ranked records live in a separate More stories section, with original-source links and a digest destination. Tools & trackers is a separate cool neutral editorial band, with two named modules, purpose descriptions, current source-backed signals and distinct calls to action. The redundant Keep reading strip is removed.

The lead and four brief headlines retain their deterministic order. Further stories are the next three ranked records, excluding those five. Redundant brief summary paragraphs are removed; explicit headline-only notices, evidence and time remain. In focus deliberately mirrors the stationary ranked stories because an automatic headline needs a stationary alternative; it is not duplicated again in category navigation.

## C. Color palette

Navy supplies masthead and structure; blue marks interaction; restrained teal identifies the second wordmark color. Warm ivory/cream support long reading, cool gray groups tools, and muted gold identifies credit. Dark uses layered navy surfaces. Rose is confined to error/expired states. The page background and actual headline colors never cycle. [Exact semantic tokens, typography and spacing](VISUAL_IDENTITY.md).

Key light values: canvas `#f4f2eb`, reading surface `#fcfbf7`, navy `#142b49`, blue `#235aa0`, teal `#216a6b`, gold `#785820`. Dark values include canvas `#101c2d`, reading surface `#192a3f`, grouped surface `#23354a`, blue `#91baf5` and teal `#88d0ca`. No gradients or glow were added.

## D–E. Working brand and wordmark

The five conditional candidates are **Techline Journal**, Techfield Journal, Techspan Report, Techscope Journal and Techrange Review. [BRAND_NAMING_REVIEW.md](BRAND_NAMING_REVIEW.md) scores clarity, memorability, pronunciation, editorial fit, distinctiveness, collision risk and domain/handle uncertainty, with primary sources and discarded candidates.

Techline Journal leads because it states the topic and reads naturally as a publication, while allowing coverage beyond AI. Its root is crowded, so the full name remains provisional. Sampled exact-name searches are not proof of availability or legal clearance. Domains, handles and trademarks remain unverified; public branding requires an owner clearance decision.

The masthead uses a substantial navy/teal system-serif wordmark, a geometric news-sheet SVG and Technology News & Insights descriptor. The English wordmark retains `translate="no"`, `notranslate` and language semantics. UI branding and page/RSS titles change; internal package names, infrastructure, file paths, routes and storage identifiers stay stable. No heavy font or cliché technology icon was added.

## F. Editorial motion and controlled color

In focus steps through four actual ranked stories every **12 seconds**, with a **160ms** opacity entrance from **0.85 to 1**. Desktop uses visual ellipsis; mobile reserves two lines. The link retains its complete title. Every item is present in the stationary lead/brief. No important fact, number, release date or real headline is overwritten in its original reading position. The label Updated periodically avoids an unsupported real-time or breaking-news claim.

A **48×2px** accent rule transitions through blue, teal and indigo over **36 seconds**. The visible Pause/Resume button controls both rotation and this decorative rule. Motion pauses on hover, keyboard focus, hidden tabs and offscreen placement. Pointer resume remains usable; keyboard focus continues to protect reading. Reduced motion is stable and labelled Paused. No-JS users see the first linked headline without timers. No animation dependency was added.

## G–H. Appearance, spacing and interaction

Desktop shows **Appearance: Light/Dark**, with a sun/moon and the current state. Mobile retains the readable state label. The accessible name states both current appearance and the change action. The fixed-size control persists selection, updates `aria-pressed` and theme-color metadata, and supports keyboard input without moving surrounding controls. The existing device preference remains in settings; no new theme was introduced.

Desktop retains a 1.55:1 lead/brief split, 32px column gap and compact introduction. Typography remains 36px desktop lead, 29px phone/27px at 320, 21px feed headline, 16px summary and 18px/66ch article prose. Cards share padding and aligned action rows. Mobile removes the redundant dispatch date while retaining the Updated timestamp; tighter masthead and intro spacing moves the lead forward.

The first full E2E run exposed the 320px lead at **653.96875px**, failing the existing **<650px** gate in both projects. The layout was corrected without weakening the assertion. Final measured lead top: **597.171875px (English); 620px (Bangla), both themes**.

The next 90-test run reached 87 passes but three tests failed during trace writes with `ENOSPC`; no test assertion failed in those cases. The workspace drive had approximately 141MB free. Redundant-capture removal was rejected by automatic review (“blocked by policy”), so captures were preserved. The complete suite was rerun with only its output directory redirected to `%TEMP%/techline-owner-correction-e2e` on the drive with available space. Workers, retries, assertions and thresholds stayed unchanged. Final counts below refer to that complete rerun. This storage issue is a local development constraint, not a deployed product result.

The independent visual review requested three material fixes: explicit spaces around inline links/date/status copy; an unframed tracker band instead of nested rounded cards; and removal of decorative page-title kickers on All stories, Free credit, Models, Settings and Digests. These are implemented and included in the recaptured review packet. Final review disposition: **ship — the three initial fixes and final keyboard-focus repair are resolved; documentation and complete test results recorded separately** at its stated visual scope.

Search retains its accessible native dialog, keyboard focus protection/restoration, Escape, backdrop handling and mobile scrolling. Existing 120ms debounce and stale-result protection remain. Save feedback stays beside the action. Evidence explanations and original source links remain accessible. No promotional or arrival popup was added.

## I. Accessibility and localization

Both themes and both locale routes were checked at **320, 390, 834, 1280, 1366 and 1440px**. Final matrices cover **264 fixture + 264 live states**, each with **0 horizontal overflows**. Axe A/AA checks, computed text/brand contrast, keyboard controls, no-JS reading, dialog behavior, save feedback, theme persistence, reduced motion and ticker geometry passed. Timer tests exercise hover/focus/manual controls, hidden/offscreen suspension, a fresh interval on resume and actual ranked links.

A final actual keyboard screenshot exposed the headline focus ring being clipped by its ellipsis wrapper. The wrapper now mirrors the visible 3px focus outline with a 3px offset. Desktop and phone captures in both themes confirm the complete outline, stable geometry and no overflow. The existing browser case asserts this wrapper outline; the independent review resolved the finding. Proof is under `.cache/visual/owner-interactions/ticker-focus-after-*` and `.cache/owner-correction/ticker-focus-after.json`. Inherited decorative labels on About and Saved remain outside this correction's scored routes and are not canonized in the design system.

English/Bangla UI dictionaries and static routes remain intact. Five authored translated fixture examples exercise Bangla shaping and mixed-script wrapping. The live edition has **0/116 Bangla story translations** and explicitly labelled English fallback. No live translation or fully translated edition was fabricated. Configure a capable publication-time provider/model/endpoint using [AI_PROVIDERS.md](AI_PROVIDERS.md), bounded shared budgets and `config/ai.yaml`, then obtain native editorial review. Visitors trigger zero AI/translation calls. Physical Android/Linux font coverage, assistive-device testing and Bangla stemming remain limitations.

## J. Engineering, security and performance

| Gate | Exact final result |
|---|---|
| Python / Ruff | 120 passed in 9.51s; Ruff clean |
| TypeScript / ESLint | 52 passed in 5 files; zero lint warnings |
| Astro typecheck | 55 files; 0 errors, warnings or hints |
| Complete E2E | 90 passed in 2.4m; desktop/mobile Chromium |
| Fixture generation / schemas | 12 stories, 14 digests, 5 authored Bangla examples; validated |
| Live collection / schemas | 116 stories, 22 digests; 7 healthy sources; 0 validation failures |
| Final responsive rendering | 264 fixture + 264 live states; 0 horizontal overflows; 116 PNGs per matrix |
| Fixture site crawler | 94 HTML routes, 4,368 internal links, 494 external references, 12 RSS items, 81 sitemap routes |
| Live site crawler | 314 HTML routes, 15,990 internal links, 1,596 external references, 50 RSS items, 192 sitemap routes |
| Accessibility / interactions | Axe A/AA, computed contrast, keyboard, reduced motion, no-JS, search/save/theme/ticker checks passed |
| Security / dependencies | Source/build scans passed; full/prod Node audit 0 advisories; 31 frozen Python requirements, no known vulnerabilities |
| Visible cache mitigation | 14 regression tests; upstream 4.3.0 still accepts all 5 restricted max-stale probes; locked patch retained |
| Build budgets | 94,494 bytes referenced JS gzip; 38,882 CSS / 8,759 gzip; 198 fixture / 742 live assets |
| Cloudflare dry-run | Wrangler 4.147.0 passed; 1,078 asset files read; worker 0.36 KiB / 0.25 KiB gzip; no bindings or publication |
| Repository / docs | 235 prospective files; real index unchanged; 50 Markdown files / 150 local links checked |

The final live ingestion contains **116 stories and 22 digests**, with **49 headline-only records (42.24%)**. Four sources returned new/successful content and three returned unchanged content; none failed. Validation failures: **0**. All **116** summaries are extractive; **110** were reused from cache. The collection created **4** new and updated **2** stories. Insufficient evidence remains visible; no artificial summaries were written to improve a percentage.

| Dataset / run | Performance | Accessibility | Best practices | SEO | LCP (ms) | CLS |
|---|---:|---:|---:|---:|---:|---:|
| Live 1 | 100 | 100 | 100 | 100 | 1770.5116 | 0 |
| Live 2 | 99 | 100 | 100 | 100 | 1765.7740 | 0 |
| Live 3 | 100 | 100 | 100 | 100 | 1512.7689 | 0 |
| Fixture 1 | 100 | 100 | 100 | 66 | 1781.8151 | 0 |
| Fixture 2 | 99 | 100 | 100 | 66 | 1664.7371 | 0 |
| Fixture 3 | 99 | 100 | 100 | 66 | 1748.7925 | 0 |

All unchanged median gates passed. Live performance median **100**, LCP **1765.7740ms**; fixture performance median **99**, LCP **1748.7925ms**. CLS is **0 in all six runs**. Accessibility and best practices are **100 in every run**; live SEO is **100/100/100**, fixture SEO **66/66/66**. LCP is displayed to four decimal places; original JSON/HTML reports retain full values. JS remains below 100,000 bytes gzip and CSS below 40,000 bytes. No font download, visitor AI request or motion library was added. Reports: ignored `.cache/owner-correction/lighthouse-live/` and `lighthouse-fixture/`.

Full/prod Node audits report **0 advisories**; frozen Python audit covers **31 requirements** with no known vulnerabilities. These do not erase the documented cache-policy concern: official registry latest remains **http-cache-semantics 4.3.0**; the integrity-verified unpatched implementation still accepted all **5** restricted max-stale probes. The locked conservative patch passes **14** regression tests and the explicit audit gate; reassess by **2026-11-03**. [Security evidence and upstream disagreement](SECURITY.md). No dependency suppression, new runtime cache, SSR or visitor AI path was introduced.

Lighthouse uses a compressed local production preview, not deployed field data. Fixture SEO is intentionally lower because fixture/example-origin output is noindex. The live origin is a local readiness-check canonical value, not proof of domain ownership or deployment. Cloudflare dry-run packages assets only; no publication occurred.

## K. Screenshot review

Start with the [current screenshot gallery](assets/owner-correction/README.md): *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*, *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*, *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*, *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*, *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*, *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*, *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* and *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*. Thirteen live JPEGs and two explicitly labelled authored Bangla fixture JPEGs retain dataset and capture provenance.

Full-resolution matrices: `.cache/visual/owner-correction-final-live/` and `owner-correction-final-fixture/`, **116 PNGs each**. Initial owner-page captures: `.cache/visual/owner-correction-before/`. Browser traces, reports and generated content stay ignored. The clipped supplementary category captures from the first packet were replaced by complete page captures with document-coordinate clips before final review.

Open the actual local site at `http://127.0.0.1:4321`, hard-refresh once, and review Today, All stories, a detail page, the category area, tools, Appearance, Pause/Resume and search at phone and desktop widths. The restored default edition is visibly synthetic. For real source inspection, follow [TESTING.md](TESTING.md)'s separate live build procedure, then restore fixtures before deterministic E2E.

## L–M. Remaining issues and approval verdict

The implementation is ready for the owner's final visual approval; the recorded deterministic and visual gates pass. A local independent review cannot approve the owner's taste, clear trademarks, certify native-language semantics or establish deployed behavior.

Public release still requires:

1. Owner visual approval and defensible brand/domain/handle clearance; replace the working name if clearance fails.
2. Actual HTTPS origin, Cloudflare/GitHub credentials, protected publication environment and separate deployment authorization.
3. Versioned off-machine backups and an independently verified restore. Evictable Actions caches are not durable backup.
4. Authorized post-deployment checks for headers, routes/404, robots/canonical/sitemap, ingestion schedule and field performance.
5. A capable provider and native Bangla review before claiming translated news coverage; physical-device checks remain owner operations.
6. Cache-mitigation reassessment by November 3 and current dependency/source/free-tier review. A source-code license remains an owner decision.

English launch engineering and owner visual approval are distinct from public-release authorization. [Readiness audit](PRODUCTION_READINESS_AUDIT.md), [testing commands](TESTING.md), [machine-readable design](../DESIGN.md).
