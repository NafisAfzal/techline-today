# Autonomous execution handoff: released Phase 2 and local Phase 3

This record preserves the original Phase 3 execution evidence. The subsequent independent findings and local corrections are covered by the [corrective handoff](PHASE3_CORRECTIVE_HANDOFF.md), which supersedes the staging, provenance and attribution claims below for the current uncommitted tree.

Phase 2's GitHub-only release is complete. Phase 3 engineering is local, uncommitted and awaiting independent review. Source activation, rights approval, AI, schedules, Cloudflare preview and production remain blocked.

## Released result

[PR #2](https://github.com/NafisAfzal/techline-today/pull/2) merged normally into protected main at:

`ebe7f071512efd0cee19dc2849ba6650f86b0839`

Both the [PR validation run](https://github.com/NafisAfzal/techline-today/actions/runs/38849189679) and [post-merge main run](https://github.com/NafisAfzal/techline-today/actions/runs/38849807682) passed. Both languages passed [PR CodeQL](https://github.com/NafisAfzal/techline-today/actions/runs/38849189666) and [main CodeQL](https://github.com/NafisAfzal/techline-today/actions/runs/38849807607). No open code-scanning alerts were present; the three historical alerts were fixed.

Release evidence: 269 Python, 130 JavaScript and 184 hosted fixture browser tests. The sole hosted failure encountered was two new tests depending on the ignored owner snapshot. A disclosed test-only correction generated isolated synthetic snapshots and passed a clean local checkout and hosted CI. No runtime implementation, rights rule, assertion or browser timeout was weakened.

The full local Windows fixture browser run had 182 passes and two WebKit timeout failures; the targeted rerun had one pass and one timeout. Hosted full-suite success is recorded separately. These local failures remain visible. See the [release record](PHASE2_GITHUB_RELEASE.md) for exact scope, commits and limitations.

## Local workspace and implementation

Branch: `feat/phase3-activation-readiness-local`, based on released main. No Phase 3 commit, push or PR was created. The review patch contains 14 new files; the real Git index remains empty. The separate pre-existing pending Wave 1 release document remains untouched and excluded from the Phase 3 review scope.

| New implementation | Purpose |
|---|---|
| `pipeline/review_governance.py` | Bounded, item-bound, inactive local review ledger and operator CLI; deterministic hash chain, expiry, revocation, writer lock and atomic replacement |
| `schemas/local-rights-review.schema.json` | Separate governance contract, without changing public snapshot schemas |
| `pipeline/pilot_staging.py` | Twenty fixture-only cases using existing fetcher/adapters/normalization/dedupe; actual measurements and protected-file invariants |
| `pipeline/pilot_attribution.py` | Internal publisher/origin/license/advisory presentation contract with explicit unknown/unapproved fields |
| `pipeline/tests/test_phase3_governance.py` | 52 governance/attribution/security cases, including actual Windows junction isolation and rejection by the existing JavaScript publication gate |
| `pipeline/tests/test_phase3_staging.py` | 25 staging, parser, outage, retry, isolation, measurement and interrupted-write cases |

Supporting records: [baseline](PHASE3_BASELINE.md), [rights contract/operator workflow](RIGHTS_REVIEW_CONTRACT.md), [staging command](PILOT_STAGING.md), [attribution specification](PILOT_ATTRIBUTION_SPEC.md), [adversarial review](PHASE3_SECURITY_REVIEW.md), and [production gap analysis](PRODUCTION_READINESS_GAPS.md).

The approval pathway is inactive. No affirmative decision is accepted or populated. Missing, forged, corrupted, expired, future, policy-changed, mismatched and revoked records deny. Feed fields and same-domain matching cannot approve reuse. A reviewer field is not authenticated identity, and a hash chain is not a signature; those limitations are documented as future activation gates.

## Reproducible staging evidence

Command:

```powershell
.venv/Scripts/python.exe -m pipeline.pilot_staging
```

Two complete runs at the fixed synthetic clock `2026-10-16T12:00:00+00:00` produced identical deterministic SHA-256:

`a81da0693c6abedf3d11ea832e3fe5d7b4dd77e8e3c9a32c37a0299bc9ff24dd`

| Measurement | First run | Second run |
|---|---:|---:|
| Evaluation time, including fixture generation and rate/retry waits | 17.401470 s | 17.475723 s |
| Peak traced Python allocation | 10,159,733 bytes | 10,158,811 bytes |
| Exact local report size | 217,756 bytes | 217,754 bytes |
| Live requests / publication items / AI calls | 0 / 0 / 0 | 0 / 0 / 0 |

Measurements exclude imports/config loading/report persistence; allocation is not full process RSS. Variable timings/report size are separate from the deterministic section. The five local staging/review metadata files occupied 221,364 bytes after the synthetic operator exercise, before any private review indexes. No article bodies or linked third-party text were retained.

Volume case: 5,000 synthetic RSS entries (1,331,739 response bytes) and 4,000 synthetic JSON records (1,580,021 bytes) yielded exactly 20 and 30 retained records. Second-run measured parser time was 0.268178 s for RSS and 0.303372 s for JSON; normalization was 0.095149 s and 0.139104 s respectively. Measured ingestion throughput was 54.57 and 67.33 retained items/s. These are fixture microbenchmarks, not live capacity claims.

Normal fixtures retain six distinct rights observations despite duplicate GUID/CVE inputs; display dedupe yields three unique items and removes five duplicates. Fixture conditional requests produced two 200 and two 304 responses. Retry produced two 429 and two successful 200 responses. Live publisher 304 rates, availability, size, quotas, TLS/DNS and freshness were not measured.

Local outputs:

- `.cache/phase3/staging/report.json`: complete outcomes, hashes, internal contracts and variable measurements.
- `.cache/phase3/staging/binding-example.json` and `review-example.json`: explicitly synthetic binding/pending evidence.
- `.cache/phase3/reviews/draft.json` and `ledger.json`: synthetic operator exercise only.

The documented draft → record → inspect → evaluate workflow ran successfully. Evaluation returned `review_required`, publication false, AI false and approval-path-active false. No real item decision or license acceptance occurred.

## Final verification

| Check | Result |
|---|---|
| Full Python suite | **346 passed**; 77 new Phase 3 cases |
| JavaScript | **130 passed**, 13 files |
| Ruff / full ESLint | Passed |
| Typecheck | 63 files; zero errors, warnings or hints |
| Canonical schema validation | 37 stories / 9 digests; passed |
| Local review schema | Model/schema equality covered; synthetic ledger validated |
| Live-data local build / site verification | Passed; 132 routes, 6,944 internal links, 37 RSS items, 89 sitemap routes |
| Security / content rights | Passed; 37/37 canonical sources permitted |
| Dependency policy | Passed; existing visible cache mitigation and 2026-11-03 reassessment retained |
| Nonproduction editorial | Passed with honest freshness/current-news/translation warnings |
| Production editorial / release publication | Expected refusal, exit 1; gates preserved |
| Repository/docs/whitespace and final remote state | Passed: 314 prospective files, 95 Markdown files, 280 local links; private Phase 3 patch checked; remote main remains the verified release SHA |

Phase 3 has no public-interface changes, so the hosted 184-case browser result applies to the released Phase 2 tree; it is not represented as a hosted scan of uncommitted Phase 3 code. Existing provenance must be rebuilt whenever executable local inputs change.

## Preserved invariants and remaining gaps

Canonical snapshot SHA-256 remains:

`d146d528ed8b00bc4e3a1e379ceffa300f46ce5a17ee9d34e8291410e9973eb5`

Source registry remains 11 entries, only arXiv and Cloudflare documentation enabled. Both pilots remain disabled, excluded and AI denied. Source rights, workflow states, schedules, deployment configuration, locks, public UI and production gates are unchanged from released main. No publisher terms were accepted.

The edition still has 36 research stories, one reference story, zero current news, zero multisource stories and zero production Bangla translations. Research freshness and collection freshness are separately measured; synthetic advisories do not close the current-news gap.

Required before activation: independent review of this local code; actual owner/source/item license and origin decisions; authenticated approval/checkpoint design; authorized bounded live operational measurements; real-item attribution and advisory-copy review; lawful useful current news; durable recovery and separately authorized hosted preview/production checks. Full details and ordered gates are in the [readiness gap analysis](PRODUCTION_READINESS_GAPS.md).

No routine implementation question or further authorization is needed to inspect this handoff. This record requests no activation or deployment approval.

## Preservation and rollback

All original owner documents and private reports remain in place. Raw execution logs, original/staged release patches, report receipts, hosted run metadata, failed browser traces, repeated staging reports and a separate Phase 3 review patch are retained in the private `Autonomous-Execution-20261016` audit directory. No private evidence was published.

To discard Phase 3 later, first preserve the exact new-file inventory and patch, then remove only these local additions and their synthetic `.cache/phase3` state after inspection. Preserve the pending Wave 1 document, canonical content, original audit directories and existing worktrees. Do not use blanket reset/clean operations. The merged Phase 2 release remains independently intact; reverting it would require a normal reviewed revert PR, not shared-history rewriting.
