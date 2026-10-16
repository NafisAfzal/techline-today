# Phase 3 corrective execution handoff

Local implementation of independent findings F1-F5 is complete. This is a disabled-code engineering candidate for independent GitHub-only review, not public production readiness or permission to reuse publisher content. No commit, push, PR, deployment, source activation, real approval or AI request was made.

## Starting state and preservation

Starting/current HEAD: `ebe7f071512efd0cee19dc2849ba6650f86b0839`.
Branch: `feat/phase3-activation-readiness-local`.
The initial index and tracked diff were empty, with 299 tracked files and the same 15 untracked files recorded by the independent audit. All 314 visible starting files were copied byte-for-byte outside the repository before editing. Original Phase 3 cache/ledger files were hashed and were not used as experiment state. The pending `docs/GITHUB_WAVE1_RELEASE.md` remains untouched and outside the proposed Phase 3 release.

Canonical snapshot SHA-256 before and after:

`d146d528ed8b00bc4e3a1e379ceffa300f46ce5a17ee9d34e8291410e9973eb5`

Both pilots remain disabled, publication-excluded and AI-denied. Registry/rights/AI/release configuration, workflows, schedules, deployment files, dependency locks, public snapshot schema and canonical content are unchanged. Only arXiv and Cloudflare terms remain enabled under the existing source policy. Their presence is not new activation authorization.

## Findings mapped to changes

| Finding and original audit location | Correction | Main regression evidence |
|---|---|---|
| P2-1 / F1, `pilot_staging.py:228-232,253-329` | Explicit source attempts, error categories, scenario expectations, aggregate outcomes and CLI exits; last-successful report retained separately | Nominal two/one/zero adapter failures, legitimate empty feeds versus unexpectedly empty nominal output, parser errors, bounded timeout retries, missing configuration, changed rights, stale cache, actual CLI exit 1 and recovery |
| P2-2 / F2, `review_governance.py:78-100,132,252-287`; `pilot_attribution.py:19` | Binding provenance survives serialization, draft/CLI and attribution; contradictory flags reject; public rights boundary rejects all local provenance/internal records | Synthetic round-trip/default CLI, malformed/missing origin, feed override, cross-source identity checks, live snapshot compatibility, five new JS gate cases |
| P2-3 / F3, `pilot_attribution.py:13-54` | Latest ledger event supplies review and claims together; scope/evidence/obligations retained; stale/revoked claims quarantined; pending standalone input explicitly a proposal; references explicitly unresolved | Scope round-trip, expired/revoked/rejected/policy-changed/modified records, stale cached decision, altered URL/identity, guest mirror/license spoof, absent reviewer authority and unsupported approval |
| P2-4 / F4, `pilot_staging.py:56-108,233-241`; `adapters.py:72-92,143` | Timestamp selection before response-level retention cap, deterministic payload tie-breaks, complete dedupe tie-break, malformed XML refusal, transform cache version 10; distinct forgery/reordered fixtures | Original/reverse/eight seeded permutations per adapter, six fresh identities after the old cap in every permutation, complete normalized-output hashes, duplicate identifiers, timestamp ties/missing/malformed values, truncation boundary |
| P3 / F5, `review_governance.py:27-28,126-128,173` | Nonblank bounded labels/notes, unsafe Unicode controls rejected, strict integer version 1 and explicit stored format required | Whitespace/control/length boundaries, multilingual reviewer, boolean/float/string/future/missing disk versions, malicious CLI arguments |

## Staging outcome contract

`status=passed` means selected fixture expectations matched. `outcome` separately describes collection: `success`, `empty`, `partial_degradation` or `total_failure`. An intentional attack may pass its refusal assertions while explicitly reporting degraded/failed collection. For a run containing `normal`, that required control determines aggregate collection health; every scenario must still meet its own expectations. A selected attack-only run does not establish nominal source health or real publisher availability.

Nominal partial results are diagnostics only: any failed required source makes verification fail and CLI exit 1. Legitimate empty feeds are distinct from failed feeds, and an unexpectedly empty normal fixture fails its count/routing expectation. Configuration refusals exit 1; invalid CLI arguments exit 2. Reports retain error type/category and source identity without source bodies. `report.json` is the latest verdict; `last-successful-report.json` is historical evidence and is never current collection input. Writes remain individually atomic, without a multi-file transaction or power-loss durability claim.

All 25 scenarios pass their explicit expectations. Normal/retry/conditional/volume/reordered/HTML/forgery/rights-rejection cases process records; empty feeds report empty; partial-outage and single-source parser/security/validation cases report partial degradation; total-outage/timeout/oversize/redirect cases report total failure with expected refusal. Source-by-source outcomes are in the external `staging-outcomes.json`. Rights-denied CISA input is explicitly counted as `rights-rejected`, not invalid data or collection failure; Kubernetes holds the negative review observation. The typed normalization refusal remains a `ValueError` subtype, preserving existing caller compatibility.

Two complete runs produced identical deterministic SHA-256:

`558509eec1e43e9c8d09ab44004fc45d6e822a5803d56a8076f10f597ef7b3bf`

Measured evaluation: 25.752770 / 26.422796 seconds; traced Python peak: 10,336,001 / 10,338,489 bytes; report: 295,435 / 295,432 bytes. Timings/memory are excluded from the digest. Protected input bytes, fixed clock and deterministic observations/contracts/outcomes are included. These are fixture measurements, not live-source or full-process capacity claims.

The exact audit false-success scenario was repeated in an isolated subprocess: both normal adapters raise `ValueError`, actual CLI exits **1**, report says `failed/total_failure`, observations are empty and last-successful bytes are preserved. A subsequent normal CLI run exits **0**. Tests also prove stable repeated failed outcomes with old cached data present.

## Provenance and attribution contracts

The trusted simulation harness stamps its normalized fixture inputs as synthetic. `bind_item` derives `binding.provenance` from the normalized fixture marker; feed-supplied origin/approval fields cannot establish a verified origin. Local bindings support `synthetic` and `unknown`, with missing origin conservatively unknown. There is no trusted-real classification or fabricated collection attestation. `draft` derives its legacy `synthetic` flag from the binding; CLI flags cannot override it. Attribution checks item/binding/decision agreement and carries the classification independently from licensing and editorial labels.

Local provenance/internal attribution records are rejected by the JavaScript publication gate, even with an allowed source identity. This is a contract for the inactive Phase 3 workflow. The established legacy public `SourceItem` format is unchanged; continued compatibility of the existing edition does not certify missing legacy provenance as verified publisher origin. No local ledger or simulator output is connected to production ingestion/publication.

Attribution contract version 2 derives current claims and review metadata from the latest item/source ledger event, including exact content/evidence/URL/provenance binding, policy, review/expiry times and event/head hashes. Creator and publisher remain separate. Proposed license identity, permitted fields/transformations, scoped evidence links, attribution obligations and exceptions survive serialization; absent scope stays empty. Every use remains denied. Standalone supplied decisions appear explicitly as `proposed_review`, never authoritative approval. Stale/revoked/rejected/future/policy-changed/mismatched claims are quarantined and their active creator/license/scope fields unresolved. Cached pending metadata cannot override revocation. Unknown rights, pending review and denial are distinct; there is no approved state. A normalization notice does not claim an unobserved specific shortening operation.

CISA reference identities were never collected by this mapping, so vendor identity/URLs remain explicitly unresolved. No linked vendor text is fetched or reused. Evidence URLs and reviewer strings are operator metadata, not authenticated authority, legal permission or independently verified facts.

## Bounded ordering and remaining limitations

RSS/JSON scan the entire byte-bounded fetched response, then retain at most the configured newest 20/30 entries. Missing/malformed timestamps sort last; URL and payload SHA-256 break timestamp ties. Dedupe resolves complete payload ties deterministically. Timestamp interpretation does not bypass downstream freshness, rights or advisory rules. Tests compare whole normalized outputs, not just ID sets, across ten input orders per adapter. Normal and reversed complete staging responses also yield identical observations/contracts.

Completeness stops at fetched response entries and the retained newest subset. No claim covers unseen pages, upstream truncation, every historical entry or all eligible records beyond the item budget. Malformed/unsafe/newer records and duplicate observations can consume that budget before downstream eligibility validation. Future supplied timestamps still fail the established downstream freshness rules. The 3 MB response cap, entry cap for expensive RSS parsing, HTTPS/allowlist/DNS/redirect defenses and bounded retries remain. Malformed XML now fails closed; permissive partial XML recovery is intentionally removed. Transform version 10 invalidates conditional cache bindings made under the old first-N selection.

The ledger remains inactive. Hash chains detect corruption, not malicious rewrite or whole-history rollback; reviewers are not authenticated. Optional evidence capture hashes do not detect every publisher-page/license change or omitted upstream field. Windows ACLs and local path-race resistance are not an OS sandbox. Those existing limits remain activation blockers and are not solved by these corrections. Existing real ledgers were not migrated; older synthetic decisions missing binding provenance refuse and require isolated fixture regeneration.

## Combined integrity review

| Case | Disposition |
|---|---|
| A: all sources fail with old data | Stable failure report/CLI exit; old data never read as new evidence |
| B: synthetic stale approval | Affirmative enum rejects; expiry quarantines; provenance remains synthetic; publication false |
| C: content modified after review | Changed normalized/evidence binding invalidates claims; external unmapped publisher changes remain an explicit inactive-workflow limitation |
| D: shared IDs across source identities | Source-scoped binding checks and external-ID dedupe; review evidence cannot migrate between sources; canonical-URL display dedupe remains intentional |
| E: guest mirror with license label | Origin review remains required; feed license/byline cannot become operator approval |
| F: fresh record after old cap | Six fresh identities recovered in all ten tested orders for both adapters |
| G: revoked cached review | Latest ledger wins; active license/creator/scope cleared |
| H: malicious CLI output attempt | Fixed write paths, argparse/schema refusal and existing junction/traversal tests preserve unrelated sentinel files |
| I: malformed ledger version | Explicit stored version and strict integer validation refuse without downgrade |
| J: failed run looks successful | Explicit failed status, collection outcome, source diagnostics and actual nonzero CLI exit; historical success is separate |

## Verification and reproducibility

Initial full Python baseline: **346 passed**. First 54 new Python cases before correction: **34 failed, 20 passed**; final corrective module has **82 cases**. Five additional JavaScript cases failed before the gate fix. Total tests added: **87**. Earlier intermediate failures were the expected local-schema regeneration/scenario-count updates; final results retain all assertions and add stricter verdict checks.

Final full Python: **428 passed**. Full JavaScript: **135 passed**, 13 files. Ruff, ESLint, typecheck (63 files), pipeline/local-review schema validation, security, snapshot/built content rights, nonproduction editorial, dependency policy, canonical and fixture builds/site/build verification pass. Production editorial and release gate both refuse with expected exit 1. No browser assertions or timeouts were changed.

Final browser fixture result: **184 passed (5.8 minutes)** across all five projects, including iOS WebKit. The earlier complete run also passed 184 tests in 6.1 minutes. After the final CISA rights-classification refinement, the full matrix and complete browser suite were repeated against the refreshed final build. No browser test or timeout was changed, and no targeted retry was used. The tested runtime hashes match the final source tree.

Use an isolated copy for fixture generation/builds. From the private execution directory, the supplied `run_checks.py` reproduces `python`, `javascript`, `build`, `fixture` and `repository` batches using the existing locked environments; `run_staging_checks.py staging` creates a separate staging copy and reproduces the repeated CLI/failure/recovery evidence. `run_checks.py build` precedes `fixture`. Do not copy a real ledger or regenerate fixtures in the canonical workspace. Logs and `.result.json` files record exact command, cwd, exit, duration and log checksum. Browser results apply to the isolated fixture build; they do not constitute hosted CI or approval of these uncommitted files.

## Exact corrective inventory and review scope

Changed from the captured starting tree (17 files):

- `pipeline/adapters.py`
- `pipeline/dedupe.py`
- `pipeline/normalize.py`
- `pipeline/security.py`
- `pipeline/pilot_staging.py`
- `pipeline/pilot_attribution.py`
- `pipeline/review_governance.py`
- `pipeline/tests/test_phase3_corrective.py` (new)
- `pipeline/tests/test_phase3_staging.py`
- `schemas/local-rights-review.schema.json`
- `scripts/content-rights.mjs`
- `tests/unit/content-rights.test.ts`
- `docs/PILOT_STAGING.md`
- `docs/PILOT_ATTRIBUTION_SPEC.md`
- `docs/RIGHTS_REVIEW_CONTRACT.md`
- `docs/PHASE3_ENGINEERING_HANDOFF.md`
- `docs/PHASE3_CORRECTIVE_HANDOFF.md` (new)

The other original Phase 3 additions remain present. The private `corrective-wave.patch` compares this wave against the preserved starting files; `phase3-candidate.patch` compares the complete proposed Phase 3 tree against published main, excluding the separate Wave 1 document. Neither patch changes the real Git index.

Full private report and evidence root:

`%USERPROFILE%/Documents/TechlineToday-Audits/Phase3-Corrective-Execution/`

Read `EXECUTION_REPORT.md`, `before-state.json`, `after-state.json`, `final-inventory.json`, `verification-results.json`, `staging-outcomes.json`, `SELF_REVIEW.md` and the command logs. Initial source copies under `starting-files/` support byte-exact rollback. Private reports, fixture builds, caches, ledgers and dependency links are excluded from release scope.

Recommended independent OpenCode scope: inspect the complete candidate patch against the stated main SHA and the separate corrective patch; reproduce the source-failure subprocess and ledger/provenance/attribution tests; challenge newest-item selection/ties/duplicates and publishing rejection; verify all protected hashes and source states; verify browser results and required production refusals. No remaining P0/P1/P2 issue is known in this disabled local correction scope; an independent verdict is still required. Actual source rights, authenticated approval/checkpoint design, live operational measurements, lawful fresh news and separately authorized deployment remain blocked.

Rollback: preserve current diffs and the two new files first. Restore only the 15 modified pre-existing files from their exact `starting-files/` copies after confirming no later edits; remove only this wave's two additions if desired. Never reset/clean the repository or delete existing owner caches, ledgers, documents, canonical content or audit directories. No commit exists to revert, and published main is unchanged.
