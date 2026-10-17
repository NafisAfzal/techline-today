# Phase 4 local engineering handoff

Status: **partial Phase 4; local and uncommitted, pending independent verification**. Based on released main `aa259359a2f225fa1b47c26ac83c3bb7d001ccc3`; working branch `feat/phase4-news-foundation-local`. No publication, rights approval, activation, AI, schedules, commit, push or deployment is authorized by this handoff.

The 2026-10-17 master execution preserved the original 20-file Phase 4 slice and added targeted hardening. The complete review scope is 24 source/documentation paths; the separately owned `docs/GITHUB_WAVE1_RELEASE.md` stays excluded. See the [Phase 5 continuation plan](PHASE5_READINESS_PLAN.md) for dependencies and acceptance gates.

## Implemented slice

- All structured-source JSON adapters reject duplicate keys, nonfinite constants/overflow and invalid Unicode. Preflight limits allocation before decoding: 3,000,000 input bytes, depth 32, 200,000 lexical tokens, 20,000 items per container, 500,000 encoded characters per string and 128 characters per scalar run. These are resource ceilings, not an assurance of constant memory. UTF-8/16/32, valid surrogate pairs and quoted delimiters are covered.
- GitHub release collection validates shapes, boolean flags, IDs and repository/tag URL identity; uses deterministic timestamp/URL/payload selection; retains publisher-reported author metadata without treating it as verified creator identity. One bounded page per repository is intentional: upstream creation ordering and unseen pages prevent a complete newest-release guarantee. Assets and pagination links are never fetched.
- Supplied API release URLs and repository identities must agree with the requested repository and release ID. Contradictory duplicate release IDs fail the page. Repository case is insensitive; tag case is exact. Drafts and prereleases remain excluded without inventing semantic-version rules. Missing optional identity fields do not establish additional provenance.
- `config/phase4-research-sources.yaml` contains four **disabled**, mandatory-review configurations for PyTorch, Node.js, Rust releases and the Rust blog. The production runner never imports this registry; its absence from the authoritative rights policy denies reuse.
- `pipeline.source_diagnostics` measures collection, rights disposition, item counts, duplicate observations, freshness, timestamp precision, attribution completeness, parsing/transport failures, duration and retry recovery. JSON and Markdown remain under ignored `.cache/phase4`. It never constructs an AI router or writes canonical snapshots, caches, reviews or approval records. Real transport overrides are refused; fixture mode defaults to MockTransport. Live mode requires `--live`, uses pinned public HTTPS and no credentials/environment proxies. Observed provenance remains `unknown`; successful transport is not creator or license authentication.
- Diagnostic report version 2 adds `run_id`, `exit_code`, `collection_state`, `rights_status`, `editorial_status`, observation date, parse outcome and provenance quality. Collection success/empty/degraded/failed is independent of rights review/exclusion and editorial pending. Legacy collection/outcome fields remain for existing readers. A repository-local exclusive writer lock prevents concurrent report writers and overlapping local probe budgets. An abrupt stop leaves a lock for operator inspection; there is no automatic lock takeover. JSON and Markdown are individually atomic and digest-bound, not a two-file transaction.
- Timezone-less source times remain unknown. Cards use actual story first-seen history when publication time is unknown. Detail pages explicitly state publication time is unavailable, in English and Bangla, without displaying normalization placeholders as publisher clock times. RSS omits optional pubDate when publication time is unknown. Source evidence and English fallback remain explicit. Approved styling is preserved.
- Atom `updated` never supplies `published`. Local diagnostics separately retain publication, source update and release creation evidence, including date-only precision. Calendar-only dates still sort chronologically. Newly unknown publication evidence stays unknown even when older cached metadata claimed a known publication; a stable internal sort placeholder is not exported as a publication time. The canonical edition is not rewritten by this work.
- Bangla indicators distinguish English fallback, synthetic translations and machine-translated content. Update-history dates use the selected locale. No production translation was generated and no native-reviewed translation state was invented.
- The general runner fails collection when every returned item is invalid, marks partial validation loss as degraded and distinguishes rights exclusion from parse failure. Snapshot destinations are restricted to the canonical target or isolated source-review JSON paths; traversal, code/configuration targets, operational ledgers and linked ancestors/targets are refused before normal processing. The destination option is not a full dry-run mode; use dedicated diagnostics/staging or an isolated checkout.
- Vite 8 bundles the locked `cookie` dependency into Astro prerender output, preventing an unrelated parent-directory package from satisfying a bare transitive import. Clean isolated and canonical builds passed without changing dependency versions.
- Source transform version is 12, invalidating older conditional evidence after the date/parser changes. No public schema, lockfile, production registry, rights decision, CSP or workflow permission was changed. Existing retained historical dates still require editorial review; a cache-version change does not retroactively authenticate them.

## Reproduce safely

From the repository root, using the existing Python environment:

```powershell
.venv/Scripts/python.exe -m pipeline.source_diagnostics
.venv/Scripts/python.exe -m pytest
pnpm.cmd test
pnpm.cmd lint
pnpm.cmd typecheck
```

Default diagnostics are synthetic and deny publication/AI. A successful diagnostic returns exit 0 for `SUCCESS`, `EMPTY` or `RIGHTS_BLOCKED`; unexpected `PARTIAL_DEGRADATION`, `SOURCE_FAILURE` and `VALIDATION_FAILURE` return 1. The v2 normalized collection states are `COLLECTION_SUCCESS`, `COLLECTION_EMPTY`, `COLLECTION_DEGRADED` and `COLLECTION_FAILED`. Report IDs/timings vary by execution; fixed-fixture evidence and bindings are deterministic. No items become publishable through this tool.

The explicitly authorized bounded research probe was:

```powershell
.venv/Scripts/python.exe -m pipeline.source_diagnostics --live
```

Two bounded development probes each made four successful endpoint requests and retained metadata for 20 held observations. The second followed the cache/date self-review fix; the reports record exact collection clocks and each probe has before/after source-digest receipts. These are development samples, not uptime history or publication clearance. Subsequent narrowing of general-runner output destinations does not change the diagnostic execution path. Use synthetic transports for failure testing.

For browser regression, generate fixtures and build in an isolated checkout; the ordinary fixture command writes generated state. Keep the owner's canonical edition intact. Resource-constrained Windows verification may require one Vitest/Playwright worker, `RAYON_NUM_THREADS=1`, and an explicit Node heap budget. Do not weaken assertions or replace lockfiles to resolve machine pressure.

## Rights and remaining gates

The starting Python/JavaScript claims were independently reproduced: **488 Python and 146 JavaScript tests passed**. Final follow-up results: **542 Python, 147 JavaScript and 188 fixture browser cases passed**, plus **four canonical publication-date/RSS browser checks**, with no browser failures or skips. The master execution added 54 Python cases and one JavaScript test, and strengthened the existing browser assertions. Coverage includes parser allocation/Unicode, date semantics/cache retention, contradictory release identities, collection failure, output confinement, actual junction refusal, concurrent/terminated writers and disk-full/atomic-write recovery. Failed development runs and corrected fixture/environment issues remain in the execution evidence; failures are not counted as passes.

Ruff, ESLint, typecheck, frozen installations, dependency scans, schema/rights/security/site checks and both builds passed. The canonical build has 132 HTML routes; site verification checked 6,944 internal links, 37 RSS entries and 89 sitemap routes. Initial referenced JavaScript is 99,789 bytes gzip against 100,000; application CSS is 39,458 bytes against 40,000. Headroom remains narrow. The existing cache-policy mitigation is still visible and requires reassessment by 2026-11-03. Wrangler's nonpublishing dry run passed; production editorial and preview/production release gates still refuse.

Canonical SHA-256 before and after: `d146d528ed8b00bc4e3a1e379ceffa300f46ce5a17ee9d34e8291410e9973eb5`.

The prior 13-source matrix was reviewed and a W3C standards candidate considered. Four research endpoints were operationally measured. **Zero new sources are rights-approved**. Only the existing arXiv descriptive metadata and attributed Cloudflare documentation retain their prior scoped policy allowances. The [arXiv API terms](https://info.arxiv.org/help/api/tou.html) distinguish descriptive metadata from e-print rights. The [Rust blog README](https://github.com/rust-lang/blog.rust-lang.org/blob/main/README.md) explicitly identifies a blog license, but item applicability, exceptions, required notices and authorized decisions remain unresolved. A software repository license alone does not clear release-note prose.

Kubernetes and CISA KEV remain disabled, excluded and AI denied. KEV catalog-addition dates remain date-only and cannot establish vulnerability disclosure dates or current-news coverage. The inactive Phase 3 review ledger is unchanged and accepts no affirmative approval. Do not connect diagnostics, source recommendations or synthetic reviews to publication.

The canonical edition still has 36 research stories, one reference story, zero current news and zero production Bangla translations. Native Bangla semantic review, source/item rights decisions, authenticated approval/revocation architecture, sustained collection/recovery evidence and separately authorized Cloudflare release gates remain open. No automated test result establishes launch readiness.

Detailed execution logs, source-digest receipts, inventory manifests, private reports and the isolated fixture checkout remain outside the public repository. Preserve the pre-existing untracked Wave 1 release document.

Independent OpenCode review should focus on strict JSON preflight/encoding, repository/tag URL binding, deterministic page limits, diagnostic isolation and exit codes, rights/AI denial under hostile fields, symlink/junction boundaries, honest date/language presentation, clean isolated builds and complete regression evidence. Review the exact uncommitted diff before proposing any later release.
