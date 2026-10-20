# Phase 10 — newsroom operations and launch readiness

Status: **production launch is not authorised**. Every command below is
read-only or reduces exposure. None of them enables a schedule, a publisher, a
paid model, a preview or a deployment.

## The one report

```sh
uv run python -m pipeline.newsroom_readiness --root . --format markdown
uv run python -m pipeline.newsroom_readiness --root .
```

Every item resolves to `PASS`, `FAIL`, `BLOCKED` or `INCONCLUSIVE` with the
evidence that produced it and the specific missing thing. `BLOCKED` means an
owner-controlled decision is the only thing missing. `INCONCLUSIVE` means the
evidence does not exist. Neither is a pass. There are no invented progress
percentages.

| Item | What it means today |
|---|---|
| `authority_provisioning` | An independently pinned owner trust root verifies the signed history |
| `trusted_checkpoint` | An independently held, unexpired checkpoint agrees with the local journal head |
| `source_rights_coverage` | Every enabled source has a recorded rights approval |
| `rights_evidence_completeness` | Every approved source records licence, licence URL and scope |
| `source_candidate_backlog` | No candidate is awaiting a rights decision |
| `current_news_coverage` | The edition contains verified current-news coverage |
| `editorial_backlog` | Every stored story carries an authenticated editorial approval |
| `english_editorial_approval` | An appointed English editor has approved the stories |
| `native_bangla_review` | An appointed native Bangla reviewer has reviewed the translations |
| `translation_staleness` | The newest Bangla translation is inside the freshness limit |
| `operational_observation_coverage` | Seven elapsed days of independently attested live observation |
| `publication_eligibility` | Every story satisfies every publication dimension |
| `security_advisory` | Every recorded advisory has its mitigation in place and is inside its reassessment window |
| `preview_readiness` | The preview prerequisites are recorded |
| `security_configuration` | No unauthorised AI, scheduling or seed is enabled |
| `production_launch_readiness` | The derived overall verdict and the blocking item list |

The report is built from the existing gates — the authority status, the
composite publication gate, the candidate ledger, the Phase 6 editorial and
translation ledgers, the observation receipts and the release configuration —
so it cannot drift away from the systems it describes.

## Daily editorial operations

```sh
uv run python -m pipeline.authority status          # identity and history
uv run python -m pipeline.authority queue           # what still needs a decision
uv run python -m pipeline.authority reviewers        # current grants and scopes
uv run python -m pipeline.authority history          # the verified decision history
uv run python -m pipeline.source_onboarding report   # the candidate lifecycle
uv run python -m pipeline.newsroom_readiness         # the whole picture
```

`queue` lists local story IDs with the denied dimensions for each. It never
approves anything.

## Rights-evidence review

```sh
uv run python -m pipeline.source_onboarding evidence --root .
```

Work one candidate at a time. The report names the missing evidence, the
required decision and the required role. Record the decision in the candidate
dossier; the authority-gated transitions remain refused until a real reviewer
authority exists. Do not work around the refusal.

## Checking content freshness

```sh
uv run python -m pipeline.newsroom_readiness --root . --format markdown
```

Read `current_news_coverage`, `translation_staleness` and
`operational_observation_coverage`. A collection is not freshness: only
validated publication dates inside the window count, and a retained paper is
still a retained paper.

## Handling source failures

1. Check `ingestion_failure_rate` in the observation report and the per-source
   diagnostics.
2. A failed source does not remove its previously published stories. Retract
   or correct them through the signed editorial lifecycle if the evidence
   behind them changed.
3. A source that loses its rights becomes `exclude` in
   `config/source-rights.json`. The composite gate then refuses every story
   that cites it.
4. Never widen the fetch policy to "fix" a failure. The bounds exist to keep
   a hostile or broken publisher from becoming a denial of service.

## Corrections and retractions

1. `prepare` a `CORRECTED` decision that names the exact prior decision in
   `--supersedes`. A correction without a named prior record is refused.
2. Sign, verify and record it. The correction supersedes that exact evidence
   version; a changed version starts a fresh lifecycle.
3. A retraction or withdrawal blocks the story across versions. It does not
   remove static files already delivered to a website, a cache or a reader —
   coordinate the takedown through a separately authorised publication action.

## Revoking a compromised reviewer

See the [Phase 10 recovery runbook](PHASE10_RECOVERY_RUNBOOK.md) for the full
sequence. In short: preserve the evidence, `revoke_key` and `revoke_grant`,
`revoke_reviewer`, inspect the affected scope, then reappoint and re-review
only after real human authorisation. If credentials or history are broken,
create the emergency stop first — it needs neither.

## Responding to suspected ledger rollback

1. `python -m pipeline.authority checkpoint-status`. A rollback shows up as
   `journal_revision_regression`, `journal_hash_mismatch` or
   `incomplete_history` against the independently held checkpoint.
2. Create the emergency stop if publication might continue on the rolled-back
   state.
3. Restore the complete history from a verified copy into an isolated
   directory and verify it: `python -m pipeline.recovery verify PACK --checkpoint CUSTODY.json --expected-checkpoint-sha256 DIGEST`.
4. Compare against the custodian's checkpoint before promoting anything.
5. If the trusted checkpoint itself is ambiguous, two custodians hold
   conflicting checkpoints, the owner resolves the conflict and retires one.
6. A denial that was never included in the trusted checkpoint cannot be
   detected from that checkpoint. Capture a fresh anchor after every
   publication.

## Reviewing Bangla translation status

`native_bangla_review` and `translation_staleness` in the readiness report.
The required role is a native Bangla reviewer; the tooling never invents one.
Machine translation and a `fixture-reviewed` label are not native review and
the publication gate refuses both for current-news kinds. Any English or
source-evidence change invalidates the translation binding and requires a
fresh native review.

## Preparing a lawful article publication

1. The source must be rights-approved in `config/source-rights.json` with a
   licence, a licence URL and a scope.
2. The source must be enabled in `config/sources.yaml` with the correct
   adapter, and the adapter must not be an HTML scraper without an explicit
   permission.
3. The story must have a real publication date from the publisher, not the
   build time, and the source must not be relabelled to pass the news
   freshness window.
4. An English editor, a rights reviewer, a fact checker and a publisher must
   each sign their own scoped step. No single role signs all steps.
5. Publication additionally requires a current, independently held checkpoint
   and its out-of-band digest.

## Preparing for a future approved Cloudflare preview

`preview_readiness` lists the missing prerequisites. `preview_approved`,
`free_plan_verified` and `zero_spend_verified` are owner decisions recorded in
`config/release.json` and are currently absent. Nothing in Phase 10 sets them,
and `pnpm deploy:preview` remains gated by the release gate. The canonical
edition is the unchanged rights-reviewed snapshot; it is not current news and
its byte-hash build exception does not make it approved.

## Safety notes

- Administrative tooling is private and local by default. It is not part of the
  public bundle and adds no page weight.
- No command in this document contacts a network, provisions a credential,
  appoints a reviewer, grants a permission, enables a schedule, enables paid
  AI, deploys, or pushes anything.
- Every readiness report ends with "This report authorises nothing."

Related: [external checkpoints](PHASE10_EXTERNAL_CHECKPOINTS.md) ·
[recovery runbook](PHASE10_RECOVERY_RUNBOOK.md) ·
[source intelligence](PHASE10_SOURCE_INTELLIGENCE.md) ·
[operations](OPERATIONS.md) ·
[owner launch plan](OWNER_GITHUB_LAUNCH_PLAN.md)
