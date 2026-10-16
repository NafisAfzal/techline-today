# Phase 2 GitHub release verification

The disabled source pilots were merged through [PR #2](https://github.com/NafisAfzal/techline-today/pull/2). Released main is `ebe7f071512efd0cee19dc2849ba6650f86b0839`. The merge used normal branch protection, with all mandatory checks green. No protection, workflow activation or deployment setting was changed.

## Scope and correction

The release began at `837cef894c4cb203c4b001095c993c28f01d7a3c`. The worktree exactly matched the independent corrective audit: 11 tracked modifications (+279/-17) and seven untracked files. Seventeen approved implementation/test/handoff files were committed. The separate pending `GITHUB_WAVE1_RELEASE.md` was preserved and excluded. Private audits, generated publisher data, samples, credentials and caches were excluded.

Implementation commit: `56b0739605256e1d988bff67ab9b00083313b0f6`.
Test correction: `6f86c3a41f2272181cf6fbf76a8bc3dce916eb32`.

Hosted CI exposed two tests reading the ignored owner snapshot, absent from a clean checkout. The correction builds a valid temporary synthetic snapshot using the existing pipeline. All rejection assertions and production implementation remain intact. A separate clean checkout with no canonical snapshot passed all 269 Python tests and still had no canonical snapshot afterward. The correction was disclosed in the PR. Final release scope: the same 17 files, +1163/-17.

## Hosted evidence

| Revision | Validation | CodeQL |
|---|---|---|
| PR head `6f86c3a` | [Successful PR CI](https://github.com/NafisAfzal/techline-today/actions/runs/38849189679): 269 Python, 130 JavaScript, 184 browser tests; frozen installation, lint/types, rights/security, site, Lighthouse, offline packaging and Python dependency audit | [Both analyses passed](https://github.com/NafisAfzal/techline-today/actions/runs/38849189666) |
| Main `ebe7f07` | [Successful post-merge CI](https://github.com/NafisAfzal/techline-today/actions/runs/38849807682) | [Both post-merge analyses passed](https://github.com/NafisAfzal/techline-today/actions/runs/38849807607) |

Code scanning had zero open alerts at verification; three historical alerts were fixed. Remote main, local main and PR merge SHA were checked. Main and the approved PR head have identical trees.

Fresh local verification also passed Ruff, full ESLint, typechecking, schema/model comparison, rights/security/dependency policy, editorial/repository/docs checks, live build and site verification. The complete Windows fixture browser run passed 182 cases and timed out on two unchanged WebKit orientation/accessibility matrices; the targeted rerun passed one and timed out on one. These failures are retained as local limitations, not described as green. No browser assertion or timeout was relaxed. Hosted full-suite success supplies the required release evidence.

An initial browser invocation against live data was stopped and excluded from fixture evidence. The isolated fixture build needed dependency links matching the already-locked cookie package; no dependency or lockfile was changed.

## Preserved controls

Canonical snapshot SHA-256 before and after release:

`d146d528ed8b00bc4e3a1e379ceffa300f46ce5a17ee9d34e8291410e9973eb5`

Both pilots remain disabled, rights-excluded and AI-submission-disabled. Only arXiv and Cloudflare documentation remain enabled. Production editorial and release gates refuse as intended. Ingestion, preview and source-health workflows remain manually disabled; schedules remain absent.

No source activation, article approval, rights expansion, publisher-terms acceptance, paid inference, preview or production deployment occurred. The audit's three P2 activation blockers and optional P3 template-literal refinement remain separate from this completed GitHub code release.

Raw execution evidence remains in the owner's private audit directory. Private reports were not attached to the PR. Historical pilot wording is superseded by the [corrective handoff](PHASE2_CORRECTIVE_WAVE_HANDOFF.md).
