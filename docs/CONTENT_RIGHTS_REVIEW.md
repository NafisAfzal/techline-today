# Content rights: current publication policy

Reviewed 2026-10-14. Original code ownership is confirmed by sole creator Nafis Afzal; [MIT](../LICENSE) applies to original software, authored documentation and fixtures. It does not grant rights over publisher material. [NOTICE](../NOTICE.md) records exclusions. This is a technical reuse assessment, not trademark or legal clearance.

## Allow and exclude

| Registry | Public candidate | Basis and limits |
|---|---|---|
| arxiv | Allow descriptive metadata only | [API terms](https://info.arxiv.org/help/api/tou.html) offer titles, abstracts, authors and identifiers under CC0. No e-print/PDF/full text is fetched. Original abstract-page links remain. Requests, including retries, respect at least three seconds and one concurrent connection per host. Other clients using the same operator's account/network must also respect the terms. |
| cloudflare_ai_terms | Allow attributed documentation excerpts/adaptations | [Documentation license](https://github.com/cloudflare/cloudflare-docs/blob/production/LICENSE) is CC BY 4.0. Preserve source/publisher links, license link and indication of normalization/extraction/summarization; no endorsement. |
| nvidia | Exclude | [NVIDIA legal terms](https://www.nvidia.com/en-us/about-nvidia/legal-info.html) do not establish the required broad republication basis for these blog extracts. No assumption that vendor material is freely reusable. |
| huggingface, google_research | Exclude | Specific blog/feed excerpt and adaptation rights unresolved. |
| github_releases | Exclude | Release-note licensing must be established per repository and included material. |
| hacker_news | Exclude | API access does not establish a blanket license over user post text or linked articles. |

`config/source-rights.json` is the executable allow/exclude policy. Only the two permitted sources are enabled in `config/sources.yaml`. The runner removes disabled source records and stories whose evidence or correction history contains removed sources before reusing cached summaries. Disabling a feed alone would have been insufficient. Referenced archives are checked, not silently relicensed or rewritten: any excluded source blocks publication. The historical orphan archive and old backup remain private incident/recovery evidence.

The current candidate has 37 live stories and zero production Bangla translations. It is a narrow research/documentation briefing, not a broad vendor-news service. Original summaries are predominantly source-derived extracts, not independent original reporting. No full publisher article bodies, external thumbnails, publisher logos or downloaded news images are included in the public candidate.

## Where material goes

| Surface | Public exposure and controls |
|---|---|
| GitHub | Original source/configuration, authored fixtures/tests/docs, software notices, six current licensed-source JPEG captures and their manifest. Generated snapshot, raw cache, prior screenshots, historical capture JSON and backups are ignored. A fresh alternate-index scan verifies this inventory. |
| CI | PR/main validation uses synthetic fixtures. Future production cache/short-lived rollback artifacts contain only rights-approved live excerpts/state; cache is not confidential on a public repository. No credentials or complete article bodies belong there. |
| Cloudflare build/site | Permitted titles, abstracts/excerpts, source-derived summaries/facts, original links, HTML/JSON/search/RSS and referenced archives. Pagefind also indexes displayed wording. No ignored orphan archive is copied. |
| Attribution | Story details show license/change notices. RSS descriptions carry source URLs and license/change notices. `/content-attribution.json` carries per-source titles, publishers, original URLs, licenses and adaptation disclosure for active and archived sources. A `Link` response header references it for all static formats, including JSON/search/archive downloads. Software notices are separate. Verify the header on real hosting. |
| Private recovery | Historical 155-story edition, old captures and contaminated pack are retained locally, excluded from publication. An ordinary archive is not permission for external upload. |

The six README/gallery captures show the actual filtered edition without third-party imagery; retain their attribution/manifest. They do not prove hosted availability or physical-device compatibility. Historical document links to excluded captures now identify private retained evidence instead of creating broken public links. A pre-edit private source export preserves the originals.

Neither permitted source is approved for AI submission: `ai_submission_allowed=false` is enforced for local live summaries and translations. Production inference is additionally prohibited by release gates. Publication permission and third-party inference processing are distinct decisions.

Before expanding coverage, record exact source/material/license and permitted fields, add required attribution, test removal of cached evidence/history/archives and recapture screenshots. If permission depends on legal interpretation or consent, keep that source excluded pending owner review. No publisher was contacted or permission invented. [Brand assessment](BRAND_NAMING_REVIEW.md) remains a separate owner decision.
