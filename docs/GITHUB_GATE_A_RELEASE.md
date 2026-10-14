# GitHub Gate A release

Release verification in progress on 2026-10-14. The owner authorized public GitHub publication to **NafisAfzal/techline-today**, reviewed corrective commits and safe hosted CI. Cloudflare publication, recurring ingestion, paid inference and backup uploads remain unauthorized.

## Independent recovery

**PASS.** The owner uploaded the recovery ZIP and checksum file to private Google Drive, downloaded them, and supplied the downloaded copy. Storage provenance is the owner's statement; the agent did not access the cloud account.

The downloaded ZIP matches SHA-256 `e173f06533216615cf5d1ce896d070f2e4ed011b2d509bfcb1794a69662e8bc1`. ZIP integrity, outer manifest and all **275 source files / six live-data files** passed. Direct extraction into fresh isolated directories, restored-source data verification, empty-directory data restoration, snapshot validation and content-rights checks passed. Redacted Gitleaks found no credentials. Source and data are sufficient for the documented recovery procedure; clean-machine toolchain installation, account recovery and hosted disaster recovery remain untested. Private paths, logs and backups remain excluded from Git.

## Publication controls

MIT covers original software, copyright 2026 Nafis Afzal. [NOTICE](../NOTICE.md) and [software notices](../apps/web/public/third-party-notices.txt) preserve third-party exclusions and upstream terms. The exact working name is owner-authorized; no trademark clearance is claimed.

Live content permits arXiv descriptive metadata under [its CC0 API terms](https://info.arxiv.org/help/api/tou.html) and attributed documentation under [Cloudflare's CC BY 4.0 license](https://github.com/cloudflare/cloudflare-docs/blob/production/LICENSE). The six approved screenshots show that restricted-source edition without publisher imagery. Generated news, private state, prior captures, browser traces, secrets, caches and backups are excluded from public Git. Authored fixtures remain labelled synthetic and isolated from live mode.

The Gate A guard now requires content review and independent restoration. The inventory checker reviews paths before populating its temporary index. CI explicitly disables AI, indexing and telemetry. Deployment workflows remain manual, default-branch/flag/environment/revision gated; no schedule exists. Git identity uses the confirmed owner's privacy-safe noreply address and leaves global identity unchanged.

## Verification status

All local engineering gates passed. Public repository creation, published revision, hosted CI and GitHub rendering are still pending.

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
