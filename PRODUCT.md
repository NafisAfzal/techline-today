# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Readers who want to understand important technology developments, scan a short edition, and reach the underlying evidence. English and Bangla interface routes support the same reading and source-checking workflows.

## Product Purpose

Turn collected technology updates into a useful edition: what changed, why it matters, the available facts, and where those facts came from. Readers can scan the ranked lead and briefing, browse a topic, read a source-backed detail page, or return through a digest.

## Positioning

Selection and evidence are the product's mechanism. An allowlisted ingestion pipeline normalizes, deduplicates, clusters, ranks, and validates reports before a static publication is built. Primary announcements, independent coverage, community reports, and insufficient evidence remain distinguishable. Reading does not require an account or trigger an AI call.

## Operating Context

The existing implementation uses Astro static delivery, small React reader islands, Pagefind with a JSON search fallback, and a Python publication pipeline. Collection is periodic; dates and calendar digests use Asia/Dhaka. Provider outages are isolated from normal reading, and an invalid candidate does not replace the last validated edition.

The local fixture edition contains clearly labelled synthetic examples. Live ingestion uses actual permitted sources. These modes remain separate; a local live render does not establish deployment or production availability.

## Capabilities and Constraints

- Today presents a deterministic editorial lead and short briefing. In focus rotates the same ranked headlines with visible position, playback state, Previous/Pause/Next controls, and a timed progress accent; it pauses while reading, focusing, opening search, or leaving the viewport. Categories navigate to topic feeds through an icon-led topic directory; further stories remain distinct editorial previews. Tools & trackers always provides links and field guidance for offers and model releases, including when its destination has no records. All stories supports reader ordering without replacing editorial ranking.
- Story previews show meaningfully labelled numeric facts and omit generic `Source-reported` extractions. Story pages retain original-source links, evidence classes, attributed claims, all original numbers, limitations, verification timestamps, and correction history. Headline-only records disclose their limited evidence.
- Free credit is an offer tracker at `/freebies/`; Freebie stories is the editorial category at `/category/freebies/`. Model releases and offers use source-reported terms; unavailable fields remain unknown.
- Daily, weekly, monthly, and yearly digests provide calendar context. Compacted archive bundles preserve historical records and evidence.
- Search runs against static indexes. Bookmarks, read state, language, theme, category preferences, and density remain on the reader's device; storage failure has visible feedback.
- AI summaries and translations are optional, bounded publication-time operations. Extractive summarization and explicit English fallback keep the product usable without credentials.
- English is canonical. UI localization does not imply story translation. A missing Bangla translation is labelled; source evidence and tracker terms retain verified wording. Production translation needs a capable provider and native editorial review.
- Public deployment, defensible brand/domain/handle clearance, durable operator backups, and source-code licensing remain owner decisions. The configured publication workflow is not proof of a deployed service.

## Brand Commitments

**Techline Today** is the provisional UI-facing working name, with the descriptor **Technology News & Insights**. It is not legally cleared; the full-name and near-name collision review remains recorded in [docs/BRAND_NAMING_REVIEW.md](docs/BRAND_NAMING_REVIEW.md). Preserve the full English wordmark and its language/translation protection. Internal Apertide identifiers, repository/package names, source IDs, routes, and storage keys remain stable unless separately authorized. Earlier Techline Journal and Apertide presentation names remain historical context.

The product voice is plain, informative, and source-aware. Controls name their action; uncertainty and limited evidence remain explicit. Do not invent real-time news claims, benchmark certification, customer proof, or production translation coverage.

## Evidence on Hand

The code and validated publication contracts are the implementation truth. [Engineering overview](docs/ENGINEERING_OVERVIEW.md), [localization contract](docs/LOCALIZATION.md), and [brand review](docs/BRAND_NAMING_REVIEW.md) provide supporting context. [Current screenshot gallery](docs/assets/light-header/README.md) records the light-theme art direction and header/search refinement. The [precision gallery](docs/assets/precision/README.md) preserves the prior typography/theme comparison. The [owner portal gallery](docs/assets/owner-portal/README.md) preserves the approved section architecture. The [earlier motion gallery](docs/assets/deep-motion/README.md) distinguishes local live renders from authored synthetic Bangla examples; it and the [earlier correction gallery](docs/assets/owner-correction/README.md) remain historical evidence.

[DESIGN.md](DESIGN.md) records the implemented visual system. The [homepage surface brief](.impeccable/surfaces/homepage.md) records the owner-directed correction. Historical brand language or earlier validation totals in other documents do not override the current artifact.

## Product Principles

- Keep source evidence and uncertainty within reach.
- Preserve editorial selection while making reader preferences transparent.
- Keep normal reading independent of AI availability and reader accounts.
- Separate synthetic examples, live reporting, translation availability, and deployed behavior.
- Preserve useful unknowns instead of manufacturing complete records.

## Accessibility & Inclusion

Support keyboard operation, visible focus, usable touch targets, light and dark appearance, reduced motion, and readable layouts at narrow widths. Appearance offers explicit Light/Dark choices at every width, a visible selected state, a localized accessible group name and local persistence. Its visible Appearance caption is removed. Desktop search accepts a query in the masthead before opening the existing dialog; compact layouts retain an accessible search action. Narrow navigation moves overflowing shortcuts into More while keeping one visible link per destination. In focus retains manual headline navigation under reduced motion, omits playback controls for one headline, and leaves a static first headline without JavaScript; automatic changes do not repeatedly announce themselves. Standard reading and source navigation use static HTML; search, local saved state, and preferences progressively add interaction. English/Bangla language tags, explicit fallback notices, and script-appropriate system font stacks remain part of the reading contract. Native-language semantic review and physical-device font checks are distinct from browser rendering checks.
