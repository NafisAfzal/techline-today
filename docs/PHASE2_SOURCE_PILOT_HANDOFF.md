# Phase 2 Source Pilot Handoff — Kubernetes Blog + CISA KEV (local only)

Date: 2026-10-16. Baseline: `main` @ `837cef8`. No commits, no pushes, no deploys, no schedules, no paid AI. Untracked `docs/GITHUB_WAVE1_RELEASE.md` preserved untouched.

## 1. Step 1 — research validation

**Counts reconciled.** The matrix CSV enumerates **28 rows**: GREEN 6 (incl. 1 GREEN-conditional + 2 live baselines) / YELLOW 8 / RED 10 + 1 YELLOW-leaning-RED (`vscode`, = RED 11 as reported) / UNKNOWN 2 (`apache`, `github_releases`) / 1 HN RED/UNKNOWN baseline. That is 6+8+11+2 = 27 classified + HN = 28. Report prose says "24 candidates + 3 baselines" (27): the CSV holds **25 non-baseline rows** (excluding `arxiv`, `cloudflare_docs`), so the prose undercounts candidates by one. Classifications reconcile exactly; only the prose headcount is off by one. No finding changes.

**Rights re-verified from official sources (2026-10-16), not from the reports:**
- Kubernetes website repo LICENSE (`raw.githubusercontent.com/kubernetes/website/main/LICENSE`) is the CC BY 4.0 legal text. The live blog page footer states "© 2026 The Kubernetes Authors | Documentation Distributed under CC BY 4.0" (linking `git.k8s.io/website/LICENSE`) with a separate LF-policies link for terms/trademark. Blog posts are committed to that repo (page shows "Publish Blog: Oct 14 (ba8865dad1)" commit link). Verdict: GREEN-conditional stands — grant covers site Documentation including blog, with attribution + license link + change notice; per-post exceptions possible.
- CISA Terms of Use (`cisa.gov/terms-use`) contains **no copyright restriction on advisory text** (security/accuracy/liability/no-prohibition clauses only) and restricts only system misuse. Public-domain basis: 17 U.S.C. §105 federal works + CISA's stated CC0-abroad waiver. Marks/seals excluded by design (pipeline ships no images). Verdict: GREEN for CISA-authored advisory metadata with per-item third-party screening.
- Feed availability was never treated as permission: OpenAI/GitHub-Changelog/Cloudflare-Blog all serve 200 RSS with zero reuse grant and stay REJECTED.

**Metadata/summary/attribution compliance:** CC BY 4.0 §2(a)(1) expressly permits reproduction, Sharing **and Adapted Material** — headline + ≤600ch excerpt + extractive summary comply subject to §3(a) attribution (creator, copyright, license notice + link, modification note, material link). CISA public-domain text has no such conditions; credit + canonical link given as trust practice. Attribution is data-driven: `scripts/postbuild.mjs`, `apps/web/src/pages/rss.xml.ts`, `SourceLicense.astro` all key off `source-rights.json` `license`/`license_url` per `source_registry_id` — no UI change needed; pilot entries carry both keys.

**Allowlist/security architecture reviewed:** `SafeFetcher` (public-DNS-only, connect-time pinning, 4-redirect cap, per-hop allowlist, MIME allowlist, 3 MB cap, conditional requests) + `safe_url` + Pydantic contracts unchanged. New hosts `kubernetes.io`, `www.cisa.gov` are per-source allowlisted; pilots add no new fetch primitives.

## 2. Implemented (minimal local pilot, both `enabled: false`, both rights `exclude`)

| File | Change |
|---|---|
| `config/sources.yaml` | +`kubernetes` (rss, primary, `kubernetes.io`, cats open-source/dev-apis, max_items 20, interval 1s, verified 2026-10-16, `rights_guard: true`); +`cisa_kev` (json_api, primary, `www.cisa.gov`, cat security, item_path `vulnerabilities`, field_map dateAdded/cveID, `field_templates` for url/title/text, max_items 30, interval 2s, verified 2026-10-16, `rights_guard: true`). Disabled: zero production behavior change. |
| `config/source-rights.json` | Both `publication: exclude` (pilot evidence recorded; owner flips to allow). `ai_submission_allowed: false` both. |
| `pipeline/models.py` | +`SourceConfig.field_templates: dict` (optional), +`rights_guard: bool = False` (optional, opt-in; existing sources unaffected). |
| `pipeline/adapters.py` | `JSONAdapter` applies `field_templates`; unresolvable placeholder → `None` → quarantined by normalize. No RSS path change. |
| `pipeline/normalize.py` | `parse_date`: bare `YYYY-MM-DD` → midnight UTC + `missing_publication_time=True` (no invented clock time; keeps day-granular items out of current-news per `coverage.mjs` contentKind). +`INCOMPATIBLE_RIGHTS_MARKERS` guard (only when `rights_guard`; bare ©/CC notices do not trigger). |
| `pipeline/security.py` | `SOURCE_TRANSFORM_VERSION` 7→8 (normalize semantics changed; invalidates stale conditional cache once). |
| `pipeline/tests/test_pilot_sources.py` | 15 fixture-only tests covering the full adversarial matrix (below). |
| `docs/PHASE2_SOURCE_PILOT_HANDOFF.md` | This report. |

ASVS applied: V1.2 (URL building validated by `safe_url`; templates config-controlled, data fills fields only), V1.5 (JSON via `json.loads`, no pickle; feedparser DTD-reject retained), V2.2 (per-item validation/quarantine), V4.1/V4.2 (allowlist, MIME, size, redirects), V12.3/V13.2 (public transport, timeouts, backoff), V14.2 (minimal fields, truncated pilot samples), V16.2 (quarantine counts, no secrets).

## 3. Isolated PoC results (live fetch, memory-only, outputs to `%TEMP%\techline-pilot-poc\`)

- **Kubernetes:** 20/20 normalized, 0 invalid, reorder-stable IDs, 0 missing times, categories ai/chips/dev-apis/open-source (no research misclassification), 20/20 attribution-ok, 20 distinct 72h groups (no false merges). **1 item fresh ≤72h** (2026-10-14 Kueue/Headlamp; excerpts ≥120ch → prose-backed news-eligible).
- **CISA KEV:** 30/30 normalized, 0 invalid, reorder-stable, all `security`, all day-granular flagged, dates Sep 25–Oct 14 (Oct 13/14 present → curated delta works), 30/30 attribution-ok. Canonical search-URL pattern verified `200` (`?search_api_fulltext=CVE-2026-0322`).
- Quarantine paths proven by unit tests (markers, missing cveID, malicious URL, oversize, 500s). Canonical snapshot SHA-256 unchanged (`d146d528…9973eb5`, matches Wave 1 record).

## 4. Test results (fresh, this session)

- New: `test_pilot_sources.py` **15/15 pass** (watched 14 fail first on missing fields/behavior — genuine RED).
- Full: `pytest` **169/169 pass** (154 pre-existing + 15 new), `ruff` clean.
- Node: `coverage` + `release` units **52/52 pass**; `content-rights --snapshot-only` **passed** (37/37); `editorial-quality --production` **exit 1, still blocks** (no current news in canonical snapshot — expected, honest).

## 5. Rights and security risks

- K8s footer grants "Documentation … CC BY 4.0"; a blog post framed as non-documentation material is a residual reading risk — mitigated by same-repo provenance + attribution + guard, not eliminated.
- Sampled fresh K8s post is a **labeled mirror of a headlamp.dev original**. Feed summaries carry no origin markers (verified: none of the quarantine phrases appear in 50 live items; bare "permission" hits are RBAC prose). Page-level mirror/guest-post origin screening is NOT automated — owner policy needed (exclude labeled mirrors or verify origin license).
- KEV items are factual metadata; vendor-quoted text beyond short factual description is quarantined by marker guard, but subtle third-party prose without markers cannot be detected lexically.
- K8s feed 1.14 MB + KEV 1.79 MB per full fetch; conditional requests unmeasured on these hosts — first production runs should record 304 rates and tighten intervals if needed.
- `field_templates` are config-controlled format strings: a malicious template could exfiltrate item data into URLs, but config is owner-reviewed code, and `safe_url` constrains output to https allowlisted hosts.

## 6. Remaining unresolved conditions (all excluded from auto-publication)

Per-post "otherwise noted" K8s exceptions; mirror/guest-post origin policy; SA-trigger boundary for excerpts (legal question, K8s is BY not SA so unaffected); KEV third-party inserts without markers; day-granular KEV items stay `unclassified` (advisory list, not breaking news) unless owner grants an explicit advisory-freshness exception; Python-Insider commerciality; all other YELLOW/UNKNOWN sources per `02/03` reports.

## 7. Production gates

**Still block, correctly.** Canonical snapshot untouched (37 stories, zero news); `editorial-quality --production` exits 1; `content-rights` passes. Pilots prove the *mechanism*, not readiness. Do not claim production-ready.

## 8. Rollback

Revert the six tracked-file edits (or `git checkout -- config pipeline`) and delete the untracked test + this doc; rebuild fixture to confirm green. No migration, no state, no remote to roll back. Transform version bump only affects conditional-fetch cache freshness (one refetch).

## 9. Independent review recommendation

Request review of: (a) `field_templates` generality vs a dedicated KEV adapter; (b) day-granular `missing=True` + `unclassified` outcome for advisories (vs an explicit advisory exception in `coverage.mjs` — deliberately NOT implemented here); (c) marker-list narrowness; (d) mirror-post policy. Reviewer should re-run `pytest`, both node gates, and the PoC script from `%TEMP%` (kept) or re-fetch fresh.
