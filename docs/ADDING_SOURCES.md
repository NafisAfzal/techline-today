# Adding sources

`config/sources.yaml` is active; the original example remains unchanged. Entries must pass `SourceConfig` and `schemas/source-registry.schema.json`.

1. Verify the exact feed/API URL, publisher terms and redirect hosts. Add disabled first.
2. Supply ID, name, adapter, source class, categories, independence group, endpoint, exact allowed hosts, terms URL and fetch policy.
3. Test against an offline adapter fixture, then run `uv run python -m pipeline --mode live --output .cache/source-review.json` and inspect evidence/attribution.
4. Set a verification date and enable after successful parsing.

| Adapter | Configuration | Policy |
|---|---|---|
| rss | HTTPS endpoint | RSS/Atom metadata and limited excerpts |
| hacker_news | Official API base | Discussion citation; linked articles remain unfetched |
| github_releases | API base, repositories | Stable releases; newest across repositories |
| arxiv | API/feed endpoint, query_groups | Preprint publication, not peer-review confirmation |
| json_api | item_path, field_map | Explicit list path and mappings |
| github_document | Contents API URL, document_url, excerpt_patterns | Explicitly configured openly licensed official docs; bounded excerpts |
| html | html_permission, html_selector | Explicit permission, robots approval, exact host allowlist |

All fetching enforces HTTPS, public DNS answers pinned at connection, bounded redirects, MIME/size/time limits and domain intervals. HTML is disabled by default and robots failures fail closed. HTML redirects require reviewing and updating the endpoint rather than following a destination with an unchecked robots policy. Crawl delays above the 60-second fetch budget refuse extraction instead of being shortened. Do not turn this pipeline into an arbitrary URL scraper.

Verified on 2026-10-03:

- `https://huggingface.co/blog/feed.xml`
- `https://research.google/blog/rss/`
- `https://blogs.nvidia.com/feed/`
- `https://export.arxiv.org/api/query`
- `https://hacker-news.firebaseio.com/v0/`
- `https://api.github.com/repos/{repository}/releases` for ruff, Astro and Transformers
- `https://api.github.com/repos/cloudflare/cloudflare-docs/contents/src/content/docs/workers-ai/platform/pricing.mdx`

Generic JSON/HTML `example.com` entries are disabled. No uncertain original planning feed is enabled.

`config/trackers.yaml` holds curated offers/model releases/announced events and narrow auto-offer rules. Use source-item IDs from a live snapshot. Offer amounts must occur in official evidence; model releases reference an existing story and primary sources. Dates use timezone-aware ISO 8601. Unknown card/geography/expiry remains empty/null.

Auto-offers match an allowance from approved evidence. Workers AI is rechecked each ingestion, including successful conditional revalidation. Outages do not refresh last verification; offers become unverified after seven days. Changed/unmatched allowance text becomes unverified instead of silently claiming unchanged terms.

Announced events require `at`, exact `evidence_date_text`, and a fact with text/source_ids/attribution/status. Text/date must be present in evidence. Only relevant future events enter `watch_next`; there is no prediction generator.

Disable removed sources rather than silently erase citation history. Excerpts are bounded to 600 characters; full articles are never stored.

Broad discovery sources can set `discovery_keywords` to literal words/phrases matched at word boundaries in the title and excerpt. Hacker News uses this to exclude unrelated general news; the rule also applies to retained community items. It is a conservative editorial filter, so review missed technical stories and adjust the list as coverage grows. Primary publisher feeds have no keyword restriction.
