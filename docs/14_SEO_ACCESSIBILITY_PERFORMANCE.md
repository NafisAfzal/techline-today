# SEO, Accessibility and Performance

## SEO

- descriptive title/meta per page;
- canonical URL for platform summary page;
- visible original-source links;
- OpenGraph/Twitter metadata for the platform page, not copied publisher marketing text;
- sitemap for active story/digest routes;
- platform RSS/Atom feed for generated summaries;
- structured data only where accurate;
- do not impersonate the original publisher.

## Content freshness

Expose:
- `Published`
- `First seen`
- `Last verified`
- `Updated`

This makes automated curation transparent.

## Performance budget

Recommended targets:
- initial JS on feed route: as small as practical, aim well below 100 KB compressed application JS;
- avoid JS for static text cards;
- no client-side framework hydration for the entire page;
- inline only critical small CSS when appropriate;
- no large autoplay video;
- image dimensions fixed;
- route-level code splitting.

## Search engine archive strategy

Individual old story pages can be compacted after 12-18 months to control static file count. Keep high-value monthly/yearly digest archives indexable.

## Accessibility

Treat accessibility as release criteria, not polish:
- headings are hierarchical;
- buttons are real buttons;
- links are real links;
- no clickable divs;
- skip link;
- keyboard command palette;
- ARIA only where native semantics are insufficient;
- accessible names for source/evidence badges;
- reduced-motion mode.
