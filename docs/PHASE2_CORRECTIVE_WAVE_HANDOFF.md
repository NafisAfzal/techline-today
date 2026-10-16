# Phase 2 corrective wave handoff

2026-10-16. Local implementation complete; independent verification requested.
No commit, push, PR, deployment, source activation, item approval or reuse-permission change.
This supersedes the rights-screening and KEV timestamp claims in the original pilot handoff, which is preserved as historical evidence.

## Baseline and preserved work

- Branch `main`; HEAD `837cef894c4cb203c4b001095c993c28f01d7a3c`, matching the audit.
- Initial tracked modifications: `config/source-rights.json`, `config/sources.yaml`, `pipeline/adapters.py`, `pipeline/models.py`, `pipeline/normalize.py`, `pipeline/security.py`; **+87/-3**, no staged changes.
- Initial untracked files: `docs/GITHUB_WAVE1_RELEASE.md`, `docs/PHASE2_SOURCE_PILOT_HANDOFF.md`, `pipeline/tests/test_pilot_sources.py`.
- Enabled sources remain exactly `cloudflare_ai_terms` and `arxiv`. Both pilots remain disabled, rights-excluded and AI-submission-disabled. Every source's publication permission and enablement value was compared with the starting files and is unchanged.
- All seven required verification reports were present and read under `%USERPROFILE%\Documents\TechlineToday-Audits\Phase2-Pilot-Verification`; relevant original source research and the pilot handoff were inspected. The code confirmed F1/F4/F5/F6; blueprint suggestions were adjusted where insufficient.
- Initial suite: **168 passed, 1 failed**. The pre-existing 20,000-entry RSS test repeatedly exceeded its unchanged five-second subprocess deadline. Expensive parsing is now bounded before feedparser; the original assertion passes. No assertions or deadlines were relaxed.
- Before-edit copies and the initial pilot patch are retained privately at `%TEMP%\techline-phase2-corrective-20261016-013216`. Originally clean changed files were subsequently backed up from the verified baseline commit.
- Wave 1 release document SHA-256 remains `ea52f40ad8d262461983e812450456a1e118600b0cf8d95dc73ba87fc9173305`. The original pilot handoff remains byte-identical (`5023bdb94aa3c378e61cf0ed4178cc6f205ec04e9263b3eedd19da4ad1e6cc66`). Unrelated local files were preserved.

## Findings and behavior

**F1 — addressed.** Normalization and publication eligibility are separate. Every Kubernetes item gets `REVIEW_REQUIRED`, including first-party-looking posts, named authors and items asserting a license. Explicit reservation/permission markers yield a retained `REJECTED` observation. Missing author/license/origin evidence, origin-trigger phrases, license exceptions, external canonicals and invalid canonicals receive distinct reasons. Signals inspect full transient evidence before the 600-character excerpt truncation. Benign trigger phrases also require review; lexical matches do not establish a rights violation or grant.

RSS preserves explicit canonical and license links and item rights fields when supplied. Canonical evidence comes from feed metadata or explicit adapter fields; article pages are not fetched. `kubernetes.io` and its `www` variant are treated as the same site for review classification. Valid external canonicals are retained as review evidence. Malformed, insecure and malicious canonicals remain held with SHA-256 fingerprints instead of unsafe URL strings. A malformed item URL itself fails parsing. On-site URLs and absent suspicious phrases never establish permission. IDs continue to derive from source ID plus normalized item URL; reordering is stable and duplicate feed GUIDs cannot erase distinct review observations.

The deterministic manifest is `.cache/rights-review.json`, written atomically only when collection actually encounters held items. It retains item URLs/IDs, evidence/content hashes, states, reason codes and bounded trigger labels; no titles, bylines, excerpts or publisher bodies. Entries merge by observation hash in sorted order. Corrupt or forged approval records fail closed. The manifest is ignored by Git and is never imported by public code. This session created only synthetic manifests in test temporary directories. There is **no approval state, approval loader or manual decision mechanism**. A future approval implementation must separately require an evidence URL, permitted-use scope, reviewer decision/identity and decision timestamp, bound to the reviewed item/evidence. No individual post was approved.

**F4 — addressed.** KEV is explicitly `security-advisory` intelligence with `category: security`. `catalog_added_on` and optional `remediation_due_on` are validated calendar dates serialized as `YYYY-MM-DD`. `published_at` is `null`, with `missing_publication_time: true`; no midnight/timezone placeholder is fabricated. Invalid dates and attempts to add a publication timestamp are rejected. Optional missing action/deadline fields do not erase the description or create `None` prose. A tested presentation contract supplies “Added to the CISA KEV catalog on …” and “CISA remediation due date: …”. These represent catalog addition and the applicable CISA remediation deadline, never disclosure, exploitation, vendor-advisory or breaking-news publication dates. No directive version is inferred. No current UI renders these local advisory records, so the approved UI is unchanged.

**F5 — addressed.** CVE validation uses full-string, case-sensitive ASCII syntax: `CVE-[0-9]{4}-(?:[0-9]{4}|[1-9][0-9]{4,})`. Four-digit sequences retain leading zeroes; longer sequences begin with a nonzero digit, with no artificial maximum sequence length. The basis is the [CVE Program syntax specification](https://www.cve.org/Resources/Media/Archives/OldWebsite/cve/identifiers/syntaxchange.html) and its [numbering examples](https://www.cve.org/Resources/Media/Archives/OldWebsite/data/board/archives/2013-06/msg00000.html). This checks syntax, not whether an identifier was assigned. Missing/malformed IDs fail before URL synthesis and again at normalization; they cannot fall back to canonical-based eligibility. Valid identifiers are preserved exactly.

**F6 — addressed.** Generic URL templates require a source-configured `template_url_origin`, whose host must also be in that source's fetch allowlist. The URL template's literal HTTPS origin must match exactly before interpolation; the constructed result is checked again. Only simple scalar replacement fields are accepted; attributes, conversions and format specifications are rejected. Values are percent-encoded as single components; standalone dot segments are rejected. Untrusted values cannot add query parameters, fragments, credentials or an origin. Missing constraints, malformed URLs, unsafe schemes, wrong hosts and ports fail closed. Direct-URL adapters retain their existing validation. SSRF allowlists, per-hop redirect checks, response ceilings and connect-time DNS pinning remain in place; only the transform version changes from pilot `8` to `9` to invalidate old conditional interpretations.

## File inventory

| File | Corrective change |
|---|---|
| `config/sources.yaml` | Kubernetes default review; KEV advisory/date/identifier mapping and explicit URL origin. Disabled flags unchanged. |
| `config/source-rights.json` | Corrected explanatory rights scope/evidence; both exclusions and all permission values unchanged. |
| `pipeline/models.py` | Review states, date-only advisory/presentation contracts, local eligibility, origin requirements and snapshot rejection of local evidence. |
| `pipeline/rights.py` (new) | Conservative assessment, metadata-only observation records and deterministic local manifest. |
| `pipeline/adapters.py` | Canonical/rights metadata preservation; CVE and URL synthesis hardening; bounded RSS/Atom processing fixing the baseline timeout. |
| `pipeline/normalize.py` | Separate review assessment; strict CVEs; date-only local advisories; clean optional action text. |
| `pipeline/dedupe.py` | Local advisory deduplication uses the catalog date without inventing a timestamp. |
| `pipeline/runner.py` | Holds review/advisory evidence before publication processing; rejects legacy cached pilot evidence; persists local review observations only. |
| `pipeline/security.py` | Transform version `9`; fetch/security mechanisms unchanged. |
| `schemas/source-registry.schema.json`, `schemas/snapshot.schema.json` | Regenerated to match model contracts; canonical content unchanged. |
| `scripts/content-rights.mjs` | Rejects local review/advisory objects even under a hypothetical source-level allow policy, including build JSON. |
| `pipeline/tests/test_pilot_sources.py` (existing untracked) | Updated existing 15 tests to assert stronger rights/CVE/date contracts. |
| `pipeline/tests/test_corrective_wave.py` (new) | 100 corrective fixture cases, including all requested Kubernetes scenarios and security/date/cache/queue boundaries. |
| `tests/unit/pilot-isolation.test.ts` (new) | 7 rights/editorial isolation tests against unchanged coverage semantics. |
| `docs/PHASE2_CORRECTIVE_WAVE_HANDOFF.md` (new) | This handoff. |

GitHub workflows/schedules, Cloudflare/AI configuration, branding/layout, `coverage.mjs`, the production editorial gate implementation and the published snapshot are unchanged. Original untracked release/pilot handoffs remain present.

Final diff against HEAD: **11 tracked files, +279/-17** (includes the original pilot diff); no staged changes. Four corrective files are new, alongside the three original untracked files. The existing pilot test file was updated; both original handoff documents were preserved byte-for-byte.

## Final verification

Commands use the existing `.venv` directly because `uv` is not on this shell's PATH. No dependencies were added.

| Check | Result |
|---|---|
| `.venv/Scripts/python.exe -m pytest -q` | **269 passed**: 169 existing pilot/baseline cases + 100 new corrective cases. |
| Targeted corrective file | **100 passed**; fixtures only. |
| `node node_modules/vitest/vitest.mjs run` | **130 passed**, 13 files: 123 existing + 7 new. |
| Total | **399 passing tests; 107 new**. |
| `.venv/Scripts/ruff.exe check pipeline` | Passed, including enabled security rules. |
| ESLint on changed JS/TS files | Passed, zero warnings. |
| `.venv/Scripts/python.exe -m pipeline --validate` | Passed: canonical 37 stories / 9 digests. |
| Generated schema/model comparison | Both changed schema files match their models. |
| `node scripts/content-rights.mjs --snapshot-only` | Passed: 37 stories / 37 sources. |
| `node scripts/security.mjs` | Source/build credential and header checks passed. |
| `node scripts/editorial-quality.mjs` | Passed with existing freshness/translation warnings. |
| `node scripts/editorial-quality.mjs --production` | **Expected exit 1**: stale collection and no prose-backed current news within 72 hours; same refusal observed before editing. |
| `git diff --check` | Passed. |
| `node scripts/verify-repository.mjs` | Prospective public-file inventory passed; real Git index unchanged. |
| `node scripts/verify-docs.mjs` | Passed: 87 Markdown files / 264 local links; external availability not checked. |

All new regression scenarios use synthetic data and mock transports. No Kubernetes/CISA live requests or arbitrary synthesized-item URL fetches were performed. Only official CVE documentation was browsed to verify identifier syntax. Historical live observations in the audit/original handoff were not repeated or re-claimed.

Canonical `content/generated/snapshot.json` SHA-256 before **and** after:

`d146d528ed8b00bc4e3a1e379ceffa300f46ce5a17ee9d34e8291410e9973eb5`

## Adversarial review and remaining blockers

Fixture and code review challenge results: guests/mirrors and external canonicals cannot auto-approve; feed fields and local forged approval records cannot authorize publication; malformed CVEs cannot build URLs; templates cannot change origins; HTML is stripped and unsafe item URLs rejected; local dates cannot gain publication timestamps; KEV cannot satisfy the current-news gate; legacy cached pilot evidence is filtered; snapshot and content-rights validators reject local pilot evidence. The disabled pilot config is not fetched in normal collection. The snapshot checksum and all enablement/permission values remain unchanged.

Remaining decisions: Kubernetes blog-versus-documentation license scope (F3), guest/mirror/third-party rights, post-specific exceptions and creator attribution (F2). Site-level/footer evidence is insufficient for item approval. KEV linked third-party content is not ingested; subtle embedded third-party wording still needs rights review before any future publication. No automatic affirmative license detector or approval workflow is provided.

Remaining enablement/publication blockers: independent verification; owner rights decisions; any future separately reviewed approval implementation; controlled staging and attribution checks; live response-size/conditional-request measurements against the existing 3 MB ceiling; and the unchanged production freshness/current-news gate. Advisories deliberately remain outside the news publication pipeline. This wave does not authorize staging, public content or GitHub publication.

## Rollback and next action

To undo only this corrective wave, first compare current work against this inventory. Restore the 11 changed tracked files plus the pre-existing untracked `pipeline/tests/test_pilot_sources.py` from the private pre-corrective backup above. Remove only the four corrective additions: `pipeline/rights.py`, `pipeline/tests/test_corrective_wave.py`, `tests/unit/pilot-isolation.test.ts`, and this handoff. Preserve the original pilot diff, both original handoffs, snapshot and unrelated local files. Do not use blanket reset/clean/checkout operations. Temporary fixture review queues require no migration; no production queue was created. Rolling back the transform version may cause a safe refetch.

**Ready for independent OpenCode verification: YES.** Disabled implementation is prepared for eventual GitHub publication after independent review and the existing owner/publication approvals. It is not approved for source activation or public pilot content. Stop locally with all work uncommitted.
