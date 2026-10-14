# GitHub Gate A release

Release verification began on 2026-10-14 and continues on 2026-10-15 (BDT). The owner authorized public GitHub publication to **NafisAfzal/techline-today**, reviewed corrective commits and safe hosted CI. Cloudflare publication, recurring ingestion, paid inference and backup uploads remain unauthorized.

## Independent recovery

**PASS.** The owner uploaded the recovery ZIP and checksum file to private Google Drive, downloaded them, and supplied the downloaded copy. Storage provenance is the owner's statement; the agent did not access the cloud account.

The downloaded ZIP matches SHA-256 `e173f06533216615cf5d1ce896d070f2e4ed011b2d509bfcb1794a69662e8bc1`. ZIP integrity, outer manifest and all **275 source files / six live-data files** passed. Direct extraction into fresh isolated directories, restored-source data verification, empty-directory data restoration, snapshot validation and content-rights checks passed. Redacted Gitleaks found no credentials. Source and data are sufficient for the documented recovery procedure; clean-machine toolchain installation, account recovery and hosted disaster recovery remain untested. Private paths, logs and backups remain excluded from Git.

## Publication controls

MIT covers original software, copyright 2026 Nafis Afzal. [NOTICE](../NOTICE.md) and [software notices](../apps/web/public/third-party-notices.txt) preserve third-party exclusions and upstream terms. The exact working name is owner-authorized; no trademark clearance is claimed.

Live content permits arXiv descriptive metadata under [its CC0 API terms](https://info.arxiv.org/help/api/tou.html) and attributed documentation under [Cloudflare's CC BY 4.0 license](https://github.com/cloudflare/cloudflare-docs/blob/production/LICENSE). The six approved screenshots show that restricted-source edition without publisher imagery. Generated news, private state, prior captures, browser traces, secrets, caches and backups are excluded from public Git. Authored fixtures remain labelled synthetic and isolated from live mode.

The Gate A guard now requires content review and independent restoration. The inventory checker reviews paths before populating its temporary index. CI explicitly disables AI, indexing and telemetry. Deployment workflows remain manual, default-branch/flag/environment/revision gated; no schedule exists. Git identity uses the confirmed owner's privacy-safe noreply address and leaves global identity unchanged.

## Verification status

The initial local gates passed and the reviewed source was published at [NafisAfzal/techline-today](https://github.com/NafisAfzal/techline-today), public, default branch `main`. Initial release commit: `79314797679e52769cbe4e209d904bd611f2ad84`. The first push occurred with Actions disabled. GitHub recognizes MIT; anonymous browser checks confirmed README text, both inline screenshots, table, code blocks and the rendered Mermaid SVG. The six gallery images retain their reviewed hashes and attribution.

[Initial hosted CI](https://github.com/NafisAfzal/techline-today/actions/runs/38611351828) passed every check, including 144 Python tests, 97 Vitest tests, 130 fixture browser tests, lint/types/build/docs/security/dependency scans, Lighthouse and Wrangler dry-run. [Initial CodeQL](https://github.com/NafisAfzal/techline-today/actions/runs/38611357825) completed for both languages but raised three high-severity pattern warnings. A green analysis job alone did not close the publication audit.

## CodeQL corrective review

| Finding | Review and correction |
|---|---|
| `js/bad-tag-filter`, postbuild | The regex extracted CSP hashes from generated HTML rather than sanitizing input. Replace it with standards-based HTML parsing that handles case, quoted attributes and normalized line endings. |
| `js/incomplete-multi-character-sanitization`, search | React already rendered excerpts as escaped text. Replace regex stripping with inert-template text extraction for Pagefind highlights; retain plain descriptions literally. Never mount the parsed fragment. |
| `js/incomplete-sanitization`, local preview | A one-shot replacement could retain duplicate upgrade directives. Parse directives and remove every actual upgrade directive while preserving other policy terms. |

Six new unit regressions and two browser cases passed locally. The browser cases verify escaped output, no script/style insertion or execution, no resource fetching from the inert fragment, and preservation of literal metadata. Lint and Astro's 58-file typecheck passed; Vitest now has **103 passing tests**. The full fixture suite passed **132 tests**, and the restored live edition passed all **18 mobile tests**, rights/site/security checks and another Wrangler dry-run. The corrected live build contains 307 assets, 5,190,192 bytes, initial JS 96,574 bytes gzip and unchanged CSS 39,107 bytes / 8,911 bytes gzip. All existing budgets remain intact.

The pinned parser stays in development/local-preview tooling, with no new browser dependency. Visual markup, styles and approved screenshots are preserved. The corrected prospective source tree contains **280 files**; private recovery/data artifacts remain excluded. Hosted corrective CI and CodeQL rescanning are pending, so Gate A is not yet complete. No alert was dismissed and no security check was disabled to obtain a passing result.

## Initial local verification

| Local gate | Result |
|---|---|
| Python lint and tests | Ruff passed; 144 tests passed |
| TypeScript lint / Astro check | Passed; 57 files, zero errors, warnings or hints |
| Vitest / localization contracts | 97 tests passed in eight files |
| Fixture browser suite | 130 passed, unchanged assertions and 30-second per-test timeout |
| Live mobile browser suite | 18 passed across Android-size Chromium, iPhone-size WebKit and Firefox touch; English/Bangla, portrait/landscape and both themes |
| Live responsive/accessibility smoke | Six viewport widths; zero console errors |
| Live collection and rights | 37 permitted, prose-backed stories; no synthetic live records, AI calls or Bangla translations; all 37 original URLs returned HTTP 200 |
| Site / security / notices | Passed; attribution and static security headers retained |
| Dependency audits | Python: no known vulnerabilities; Node registry: zero advisories, with the explicit locked cache-policy mitigation still required |
| Build budgets | 307 assets; 5,189,993 bytes; initial JS 96,537 bytes gzip; CSS 39,107 bytes / 8,911 bytes gzip |
| Lighthouse, three runs | All enforced budgets passed; performance median 95, accessibility/best-practices 100; LCP median 1,722 ms; CLS zero; local lab evidence |
| Cloudflare configuration | Both Wrangler dry-runs passed with no bindings and no upload/deployment |

The initial fixture run had 128 passes and two WebKit cases that exceeded the existing 30-second timeout. Trace review showed timing delays rather than a failed UI assertion. Both cases passed unchanged on targeted recheck, then all 130 tests passed on a full rerun without concurrent Lighthouse work. No test, timeout or budget was weakened. Browser checks use emulated viewports, not physical phones. The final local build uses live data and remains noindex.

The final prospective tree contains 276 files, including only the six reviewed JPEG screenshots. Private backups, recovery paths, generated news, logs, caches and dependency binaries are excluded. Gitleaks and targeted credential checks passed; manual review found only a noreply address, synthetic unsafe-URL test credentials, package-version strings and placeholder setup paths. No public history existed before the reviewed initial commit.

## Gate B: Cloudflare preview

Gate B remains unauthorized. It needs green hosted Gate A checks, a confirmed Cloudflare Free account and workers.dev subdomain, zero-spend controls, a separately approved preview Worker/origin/revision and a narrowly scoped token supplied securely. Review fresh live content, build it noindex and run rights/security/site/budget and dry-run checks before explicit preview authorization. Keep production, AI, initial-seed permission and scheduling disabled. No website URL is invented.
