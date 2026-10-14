# Apertide pre-release refinement — October 12, 2026

> Historical report. The owner rejected parts of this visual direction. The October 13 correction changes the working masthead, palette, homepage architecture and motion. Use [OWNER_DESIGN_CORRECTION.md](OWNER_DESIGN_CORRECTION.md) and [current validation](IMPLEMENTATION_VALIDATION.md) for the latest state. Measurements below remain the original October 12 evidence.

The existing product has been refined and visually inspected. Static Astro delivery, small React islands, deterministic ranking, source validation, strict security headers and zero AI calls per visitor remain intact. No commit, push, deployment, account change or license selection occurred. The working dataset and build are restored to synthetic fixture/example-origin/noindex mode.

## A–B. Design decisions and visual hierarchy

The design uses ivory, cream and midnight navy with controlled indigo, plum, burgundy and gold roles. A more confident 42px masthead and burgundy introductory phrase distinguish the publication. The desktop lead increases from 33px to 36px, phones use 29px (27px at 320), while 18px article prose, 16px summaries and a 66ch reading measure remain. Lead padding becomes 28×32px on desktop and 20px on phones. One soft plum-to-surface blend adds depth; cards use rules and spacing rather than decorative effects. [Palette, typography and rationale](VISUAL_IDENTITY.md).

Current rendered editorial research included The Guardian technology section, Rest of World and The Verge. The transferable principles were masthead recognition, a distinct lead and quieter supporting stories. Their identities and layouts were not copied. Both themes and mixed English/Bangla text were inspected in actual Windows Chromium.

## C–D. Motion, overlays and interaction

The brand statement is static. Its decorative rule makes one 240ms scale/opacity entrance; reduced motion shows it immediately. Navigation underlines and pointer/touch press feedback use 160ms transitions; keyboard interactions stay immediate. A brief theme-icon rotation conveys selection, while colors switch instantly to preserve contrast. News, facts and numbers never rotate or animate. There is no continuous movement, timer, typewriter, ticker or animation dependency.

Search keeps its native modal semantics and focus protection, Tab containment, Escape, focus restoration and mobile scrolling. Clicking padding no longer dismisses it; backdrop clicks do. Its existing 120ms debounce remains. Closed/stale requests are ignored, fallback indexing is reused, no-results text is localized, and clean story metadata replaces previews polluted with button labels. Original/fallback language tags remain visible to assistive technology.

More remains native navigation disclosure, now with Escape/outside dismissal. Evidence uses consistent localized explanation links instead of an unnecessary popup. Save feedback occupies a reserved adjacent live region, with explicit storage errors. Saved-item downloads were already parallel in batches of eight; the improvement reuses successful downloads, bounds concurrency and prevents stale refreshes overwriting current state.

## E–F. Homepage, article and editorial improvements

The homepage preserves its top-ranked lead and four-item brief. A 1.6:1 split emphasizes the lead on desktop; tablet and phone layouts stack naturally. Category teasers choose the next ranked story outside those five featured records, retaining truthful sparse-category states. Credit and model signals link to existing source-backed trackers. Original links are obvious on every feed card, and evidence/uncertainty remain accessible.

Articles add contents links to summary, facts, sources and uncertainty. Displayed summaries omit duplicated headlines and attribution filler while canonical three-bullet records and claim maps remain complete. Source excerpts and correction history retain their original evidence.

Release processing removes generic document headings, repeated model headings and changeset thank-you prefixes while preserving actual fixes, preview/breaking/known-issue context, names and numbers. A same-line changeset regression prevents accidentally removing the fix after a thank-you. Source-transform and summary-policy revisions invalidate processed caches correctly. No benefits, benchmarks, prices, dates or translations were invented. Digest ranking and announced-event constraints are unchanged; the optional digest prompt already requires plain international English and is not a production AI-generated digest service.

The final live collection contains **112 stories and 21 digests**, with **47 headline-only records (41.96%)**. All seven sources succeeded; validation failures: **0**. All summaries are extractive. The limited-evidence rate remains a content limitation, not a target met by weakening checks. Some vendor/research prose remains dense; automated extraction is not equivalent to a human-edited newsroom. [Editorial contract](EDITORIAL_STYLE.md).

## G–H. Bangla and brand status

English/Bangla UI dictionaries, static routes, language persistence, cached translation validation, fallback SEO and five authored translated fixtures remain operational. The live edition has **0 Bangla translations / 112 English fallbacks**, explicitly labelled. No visitor triggers translation. Configure a capable provider key, model and endpoint through [AI_PROVIDERS.md](AI_PROVIDERS.md) and `config/ai.yaml`, set bounded shared summary/translation budgets, process at publication time, then obtain native Bangla editorial review. Do not market a fully translated edition yet. Physical Android/Linux font coverage and Bangla stemming remain incomplete. [Localization](LOCALIZATION.md).

The provisional wordmark is protected from automatic translation. An exact-name product, [Apertide Star Profiles](https://apps.apple.com/us/app/apertide-star-profiles/id6818600227), and several similar Apitide services supersede the earlier low-collision assessment. Public-web evidence does not settle trademark clearance. The next owner decision is a clearance review across target markets, domains and social handles; approve a cleared replacement if necessary. Internal identifiers remain stable. [Naming review](BRAND_NAMING_REVIEW.md).

## I–J. Engineering, security, performance and tests

| Gate | Exact final result |
|---|---|
| Python / Ruff | **120 passed**, Ruff clean |
| TypeScript / ESLint | **52 passed in 5 files**, zero lint warnings |
| Astro typecheck | **53 files**, 0 errors, warnings or hints |
| Browser suite | **72 passed** in 1.8 minutes, desktop/mobile Chromium |
| Responsive rendering | **264 live + 264 fixture states**, 0 horizontal overflows; 320/390/834/1280/1366/1440px, both locales/themes |
| Fixture generation / schemas | **12 stories, 14 digests, 5 authored translated examples**, validation passed |
| Fixture route crawler | **94 HTML routes, 4,340 internal links, 488 external references, 12 RSS items, 81 sitemap routes** |
| Live collection / validation | **112 stories, 21 digests, 7 successful sources, 0 validation failures** |
| Live route crawler | **304 HTML routes, 15,504 internal links, 1,554 external references, 50 RSS items, 186 sitemap routes** |
| Accessibility / interaction | Axe A/AA, computed text/brand contrast, 44px designated controls, keyboard/focus, no-JS reading, reduced motion passed |
| Security / dependency review | Source/build scans passed; full/prod Node audit **0 advisories**; frozen Python export **31 requirements**, no known vulnerabilities |
| Explicit cache mitigation | **14 regression tests passed**; unpatched 4.3.0 still accepts all 5 restricted max-stale probes |
| Build budgets | **91,763 bytes initial referenced JS gzip; 35,440 bytes CSS / 8,105 gzip**; 197 fixture / 717 live assets |
| Cloudflare package | Wrangler **4.147.0 dry-run passed**, 316 asset files read, 0.36 KiB worker / 0.25 KiB gzip, no bindings, no publication |
| Repository / documentation | **211 prospective files**, real index unchanged; local links passed in **46 Markdown files** |


The new Sharp advisory was fixed by moving the exact Miniflare dependency path from 0.35.4 to 0.35.5. Registry audits are clean without global suppression. The conservative http-cache-semantics patch remains visible: integrity-verified unpatched upstream 4.3.0 still accepted all five max-stale probes, whereas the patched installation rejects them and passes 14 regression tests. Reassess by **2026-11-03**. Static exposure remains unchanged. [Security review](SECURITY.md).

Three-run local Lighthouse values and exact build budgets appear in [IMPLEMENTATION_VALIDATION.md](IMPLEMENTATION_VALIDATION.md). These are compressed local production-preview measurements, not deployed field results. Fixture SEO intentionally reflects noindex. CodeQL is configured for CI; no remote CI/account execution is claimed.

## K. Screenshots and review

Eleven repository-owned live screenshots and two clearly labelled authored Bangla fixture screenshots show live desktop, tablet, phone, both themes, full homepage, article, credit and search. [Gallery and provenance](assets/README.md). Start with *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*, *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*, *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.* and *Historical capture/evidence retained privately; excluded from public distribution pending source rights review.*. The English/Bangla matrices in `.cache/visual/premium-live-release/` and `.cache/visual/premium-fixture-release/` each measure 264 states with zero overflow.

Use `pnpm.cmd preview` and open `http://127.0.0.1:4321` to inspect the restored fixture build; the synthetic notice is intentional. For real sources, run `py -3.12 -m uv run python -m pipeline --mode live`, validate, rebuild, then preview. Use the theme/language controls, Tab/Shift+Tab/Escape in search, Save/Saved, More and article source anchors. Check reduced motion in browser emulation. Restore fixture mode and rebuild before deterministic E2E. Screenshots are point-in-time local editions, not a deployed publication.

## L–N. Release blockers, verdict and owner actions

**English is technically ready for launch preparation. Public release remains operationally blocked. A production Bangla edition is not ready.**

1. Resolve the exact/similar name collisions and clear the intended name, domain and handles before final public branding.
2. Choose the actual HTTPS origin, configure hosting credentials and repository protections, and authorize publication separately. The local readiness-check origin is a test value. Post-deployment headers, nested 404s, indexing, freshness and field performance still need edge verification.
3. Establish owner-controlled versioned off-machine backups of snapshots, archives, source state, provider reservations and translation caches; verify restoration. Actions cache remains evictable. [Operations](OPERATIONS.md).
4. If a Bangla launch is intended, configure a translation provider and arrange native review before claiming content coverage.
5. Review dependency/source/free-tier changes periodically and reassess the cache patch by November 3. Decide separately whether to grant source-code reuse under a license; none was selected.

The implementation requires no additional aesthetic micro-decisions. The owner can review the concrete screenshots and proceed with these operational decisions. [Release setup checklist](GITHUB_RELEASE_CHECKLIST.md).
