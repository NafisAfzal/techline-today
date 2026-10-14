# Release preparation inventory — 2026-10-14

This pass inspected the implementation and reran local checks. The authoritative final decision is [PUBLIC_RELEASE_PREPARATION.md](PUBLIC_RELEASE_PREPARATION.md); prior release reports describe earlier runs.

| Area | Observed state | Release implication |
|---|---|---|
| Instructions | No applicable `AGENTS.md` in the workspace or its parents | Owner's preparation-only boundary applies |
| Git | Unborn `main`, zero tracked files, no commits/refs/reflogs/remotes | No reachable historical revisions to publish; all prospective files still require review |
| Index | Existing index left untouched; hygiene tool uses an alternate ignored index | No unrelated user work staged or overwritten |
| Authentication | GitHub CLI authenticated; identity needs owner selection | Authentication is not repository/publication authorization; credentials were not retrieved |
| Node | Node 24.14.1, pnpm 10.33.1; frozen pnpm lock | Local installation reproduced |
| Python | Shell `python` is 3.11.9; project environment is 3.13.16; uv 0.12.22 via `py -3.12 -m uv` | Use the documented launcher, not bare shell Python |
| Frontend | Astro 7.3.5, static output; React islands; no Cloudflare adapter | Static Workers assets supported; no Python/runtime server assumed |
| Hosting config | Worker `ai-tech-intelligence`, asset directory `apps/web/dist`, custom 404 | Worker name differs intentionally from proposed GitHub name |
| Pipeline | Seven enabled RSS/API sources; HTTPS allowlisting, bounded excerpts, validation, deduplication, classification and extraction | Sources remain subject to rights review; enabled does not mean legally cleared |
| AI/translation | Provider adapters exist; inference off; production gate rejects inference | English extraction works without API fees; Bangla UI has explicit English fallback |
| Storage | JSON snapshots, fetch/dedup state, translation cache and archives; no database | Git excludes live data; separate recovery is required |
| Publication | Manual-only gated workflow; no cron; approved=false | No active automatic updates or deployment |
| Security | SHA-pinned Actions, read-only contents, fixture PR validation; local dependency mitigation | Hosted CI/token/account behavior remains untested |
| Licensing | No owner LICENSE; dependency metadata available locally | MIT recommendation pending ownership; third-party software notices now included in static assets |
| Screenshots | Existing gallery shows the actual earlier live edition and labelled synthetic translations | Appearance evidence is accurate for that capture; screenshots also redistribute publisher wording |
| Backup | Existing live pack tested locally; newly discovered orphan archive excluded by corrected exporter | Durability, independently restored off-machine storage and scheduled recovery remain prerequisites |

## Documentation inconsistencies corrected or qualified

- Earlier documents called the project ready for an owner release decision and recorded all local gates passing. Those results were historical; this independent pass found an orphan fixture archive in live backups and missing distributed software notices. Both receive fixes and new evidence before handoff.
- Public GitHub visibility and free Cloudflare hosting are confirmed preferences, not questions to ask again. Exact repository/account identity and permission to publish remain unresolved.
- `docs/LOCALIZATION.md` contained an older 112-story count and called a manual workflow scheduled. Translation capability is now described independently of a dated edition count.
- Seven-day Actions rollback retention did not account for shared artifact storage. Retention is two days; production now enforces a 25 MiB total bundle budget. The account's remaining storage still must be checked.
- Ignored live files are excluded from Git, but the proposed Actions caches/artifacts expose copies to people who can access them. Public base-branch caches are not private backup storage.
- The prior backup allowlist included every monthly file. It now includes only snapshot-referenced month/year files and rejects extra archive entries. The discovered orphan and old pack were preserved locally; they are not valid live recovery generations.
- Postbuild creates security headers and 404 handling, not custom redirect rules. Workers' HTML routing provides normal extension/trailing-slash behavior; actual edge redirects require hosted verification.
- Local noindex previously depended on fixture/example-origin detection. `SITE_NOINDEX=true` now explicitly isolates staging with a real origin; production validation rejects a noindex bundle.
- The project has no complete off-machine backup or remote rollback proof. A successful local checksum restoration and an Actions cache do not establish either.
- Two purported full commit pins were actually annotated tag object IDs. The setup-uv tag was peeled to its official commit, and CodeQL v4 was pinned to the verified current official commit; six unique Action repositories now resolve through GitHub's commit API. No hosted workflow was executed.

## Scope of public files

Prospective Git files include application/pipeline source, config with blank destinations, synthetic fixtures, frozen locks, patches, tests, workflows, prompts, documentation and curated screenshots. Live snapshots/archives, `.cache`, `.env`, virtual environments, dependencies, dist, traces, private backups and machine caches are excluded. [Content review](CONTENT_RIGHTS_REVIEW.md) describes the wider site/cache/artifact boundary. Final file counts, scans and command durations are in [current verification](PUBLIC_RELEASE_VERIFICATION.md).
