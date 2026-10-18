# Local generation and operational checks

This local engineering continuation awaits independent review. It grants no rights,
source activation, AI access, publishing, scheduling or deployment authority.
Use an isolated checkout for fixtures and recovery drills; preserve any owner edition.

## Generation boundary

The pipeline and supported `pnpm build` share `.cache/pipeline-writer.lock`.
Schemas, referenced archive updates, snapshot, translation cache, last snapshot,
fetch state, successful run report and briefing are staged under a unique
`.cache/pipeline-generations/<id>/` directory. The manifest binds before/after
bytes and hashes. All staged artifacts and destinations are checked before
promotion. `.cache/pipeline-transaction.json` remains until promotion completes.

This is a recoverable promotion with a publication barrier. Single-file replaces
do not form an atomic directory transaction. Snapshot readers, the supported
build, rights checks, backup export and release provenance refuse an active writer
or unresolved journal. Build children may read only under their own lock token.
An old complete static deployment remains available during a failed local run.

Provider call reservations and the rights review queue remain separate operational
records. Failed attempts are in `.cache/pipeline-attempt.json`; a failure never
overwrites the last successful generation's report. The Actions summary reads
attempt status without changing generation artifacts.

For an interrupted run, preserve the lock, journal and generation directory.
Inspect the recorded PID, process start time and command; PID reuse is possible.
Do not remove a lock based on age. After establishing that its writer is dead,
an operator can remove only that inspected lock, then choose in the isolated
workspace:

```powershell
uv run python -m pipeline.generation finish
# Or restore the staged before-images:
uv run python -m pipeline.generation rollback
uv run python -m pipeline --validate
pnpm build
node scripts/verify-build.mjs
```

Recovery validates every before/after payload and path before replacing anything.
Recovery requires an outstanding journal. Repeating a completed recovery returns
the controlled `NO_PENDING_GENERATION` refusal (exit 1, no traceback or artifact
writes); it does not claim to finish or roll back a generation. Python callers
receive `NoPendingGeneration`, a `ValueError` subclass. Corrupt journals and
missing staged payloads continue to refuse as recovery failures.
Corrupt files, unrelated post-crash edits, links, junctions, reparse points,
reserved names and directory collisions block recovery. Retain the evidence for
review; never repair a journal by guessing hashes. A failure during recovery
leaves the barrier for another explicit attempt. New files absent before a run
are removed only during an explicit rollback of that generation.

Limits: 1,000 artifacts, 50 MB per artifact, 250 MB staged before/after bytes,
16 retained generations. Archive older verified generations to owner-controlled
storage before reaching capacity. No automatic deletion is performed. Local
generation copies are subject to the same content permissions as their inputs.
Do not put them in Git, public artifacts or an unreviewed shared cache.
Power-loss durability depends on the OS/filesystem; Windows directory fsync is
not available here. Same-user hostile path replacement is not an OS sandbox.
Off-machine backup and restoration remain separate requirements.

## Manual source observations

```powershell
uv run python -m pipeline.observations            # synthetic, no network
uv run python -m pipeline.observations --summary  # retained metadata only
# For a separately scoped manual research observation:
uv run python -m pipeline.observations --live
```

The live flag uses the disabled, mandatory-review research registry through pinned
public HTTPS. It never activates those sources or constructs an AI router. Store
one receipt per UTC day; repeat runs cannot overwrite that day's live receipt.
Receipts retain state, counts, durations, freshness, retry recovery and report
digests. They omit titles, excerpts, canonical item URLs and publisher bodies.
New receipts also retain HTTP status counts (including 429), the terminal
exception category, terminal-timeout status and measured diagnostic run duration.
Timeout evidence is terminal-only: retries that later succeed do not establish
how many earlier transport failures were timeouts. Never infer that from missing
HTTP responses. Existing dated receipts remain intact and readable; do not
rewrite historical evidence to add fields that were not measured.
The authoritative receipts are under `.cache/phase4/observations/`; index.json is
a regenerable summary. Maximum retention is 31 daily receipts; archive minimized
metadata privately before continuing. Preserve failed observations too.

An eight-observation daily series spanning at least seven elapsed days is needed
for the local threshold: stable source set, gaps no greater than 36 hours, at least
95% successful/empty source observations, healthy latest sample and latest sample
within 36 hours. Empty transport success does not prove useful news coverage.
Rights/editorial holds remain separate. Synthetic loops never count. These local
receipts are corruption-detecting operator records, not signed remote attestations
or evidence of hosted uptime, alerts, permissions or production readiness.

Local intake proposes NEWS, OFFICIAL_RELEASE, RESEARCH, SECURITY_ADVISORY or
EVERGREEN for review. Its 0–8 utility rubric exposes each deterministic signal;
origin, originality, claim accuracy and cross-source duplicates remain unknown.
Configured primary-source status is not authenticated authorship. The rubric is
private triage, never public popularity, approval or a public schema migration.

## Incident actions

| Trigger | First action | Evidence needed before resuming |
|---|---|---|
| Source failure / 429 / corrupt input | Inspect diagnostic collection state and retries; retain last valid edition. | Bounded successful observation and identified root cause; no unbounded retries. |
| Rights revocation | Deny source in authoritative policy; generate only in isolation. | No denied citations in active stories/history/archives/build; rights check passes. Existing archived evidence may require a reviewed removal migration. |
| Incorrect article / withdrawal | Hold publication, preserve evidence and prepare a correction/removal. | Editorial approval and exclusion from search/RSS/sitemap/digests as applicable. No authenticated public withdrawal workflow exists yet. |
| Broken build / CI | Reproduce with frozen locks and the correct fixture edition. | Supported build, provenance and relevant regression checks pass. Never bypass a gate. |
| Interrupted promotion / disk full | Stop writers and builds; preserve recovery data; inspect free space. | Valid finish/rollback, snapshot validation and clean build. |
| Dependency incident | Hold release; run `pnpm audit:dependencies` and Python audit. | Compatible fix passes unchanged exploit tests and full build. Cache patch reassessment remains 2026-11-03. |
| Secret exposure | Stop release; revoke/rotate with the account owner; preserve a sanitized incident record. | Credential revocation confirmed, affected artifact inventory and clean scans. Do not print tokens. |
| Rollback | Verify an authorized backup with `python -m pipeline.backup verify <directory>`; restore to a new empty workspace. | Hash/schema/rights checks and source-bound build; hosted rollback needs separate authority. |
| Stale news | Keep honest coverage/empty labels; inspect actual publisher dates. | Useful permitted current items and editorial acceptance, not a new observation timestamp. |
| Unexpected cost | Keep AI and schedules disabled; inspect account usage with the owner. | Verified quotas/free plan and explicit approval. |
| Preview misconfiguration | Hold release; inspect noindex, origin, headers and build provenance locally. | Exact revision/origin/account authorization and separately authorized hosted checks. |

## Editorial and Bangla closure

Generated numeric claims, citations, caveats and source dates retain existing
validation. Automated validation cannot establish semantic truth or human review.
The public five-type/richer-date schema migration and authenticated withdrawal
and rights-approval authority remain pending; local candidates do not implement them.

A real Bangla review must bind the canonical story/evidence hash and translation
hash to a named authorized native reviewer, decision time, expiry and revocation.
Review names, quantities/units, dates, negation, uncertainty, research/peer-review
claims, security-impact terms and attribution. Changed evidence invalidates the
review. This is an acceptance contract; no production human-review state is enabled.
Current English fallback and machine/synthetic labels remain truthful.

Standalone snapshot reads use the shared generation reader: an exclusive lock
protects each synchronous read, while build children inherit their build token.
Site, editorial and build verifiers use that same pathway. A pending journal,
active/unknown writer or invalid snapshot refuses; no last-good data is silently
replaced. The lock covers the read, not an entire later asynchronous browser
review. Full builds continue to hold the writer lock for the complete build.

Independent review should reproduce `pipeline/tests/test_release_completion.py`,
the retained-rights cases in `test_owner_launch.py`, and
`tests/unit/generation-state.test.ts`, then run the full fixture browser suite.
