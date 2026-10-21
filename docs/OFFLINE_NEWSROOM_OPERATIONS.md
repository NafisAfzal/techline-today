# Offline newsroom preparation

Run these commands from the repository root after `uv sync --frozen`. On Windows,
use `py -3.12 -m uv` if `uv` is not on PATH; the project selects Python 3.13.
JSON is the default output. Put global options before the subcommand:

```sh
uv run python -m pipeline.operations --format text console
uv run python -m pipeline.operations ceremony --template
uv run python -m pipeline.operations appointment-packet source-rights
uv run python -m pipeline.operations rights-packets --candidate cisa_kev
uv run python -m pipeline.operations rehearse
uv run python -m pipeline.operations source-reliability
uv run python -m pipeline.operations recovery
uv run python -m pipeline.operations observation-plan
uv run python -m pipeline.operations observation-review --environment-id intended-environment --ledger-id intended-ledger
uv run python -m pipeline.operations preview
```

Reports go to stdout. Save operator reports, proposed identities, custody details
and evidence **outside Git and the public build**. Reports do not authorize any
action. Exit 0 means a template or local exercise completed; exit 1 means invalid
input or a failed check; exit 2 means BLOCKED or INCONCLUSIVE. Read the status and
limitations even when the process exits 0. There is no readiness percentage.

## Owner and reviewer preparation

`ceremony --template` produces an unsigned proposal, without a key or identity.
After a human reviews device custody, encrypted offline backup, restore rehearsal,
revocation contact, clock, fingerprints, witness arrangements and independent
checkpoint custody, inspect the private proposal:

```sh
uv run python -m pipeline.operations ceremony --proposal /private/ceremony.json --environment-id proposed-production
```

The proposed environment must match the explicit argument. Existing authority,
journal state and emergency holds are preserved. `READY_FOR_HUMAN_CEREMONY` means
the proposal's declarations are complete; physical custody, identity and clock
remain unverified. Hardware-token integration is unimplemented and inconclusive.
Real key creation, custody selection and installation need separate owner control.

Appointment packets use the existing roles: `source-rights`, `fact-checker`,
`english-editor`, `native-bn`, `publisher` and `suspension`. A filled packet is not
an appointment. Verify consent, identity and key possession; compare fingerprints
over another authenticated channel. The owner must sign existing enrollment and
grant records with bounded role, source, story, language, workflow and expiry.
Owner administration is separate. Do not substitute a local text-file flag.

## Exercises and custody limits

`rehearse` creates an ephemeral synthetic authority journal using the existing
published fixture keys. It exercises signed decisions, reviewer revocation,
English/Bangla digest binding, correction, retraction, root rotation, emergency
freeze and composite publication refusal. It never serializes the synthetic
article or writes the canonical edition. A synthetic positive path proves local
software behavior only. It does not certify a real translation, person or right.

`source-reliability` injects sixteen transport/parser/time cases through the
existing fetcher and diagnostic adapters in temporary directories. No live
publisher is polled and all results remain rights-held. `recovery` runs the
existing fifteen isolated disaster drills. Green results are tooling exercises,
not production recovery certification. Project recovery packs exclude private
keys; losing every separately held key copy cannot be repaired from a journal.

`schema challenge`, `schema commitment` and `schema receipt` expose the proposed
mock wire schemas. `checkpoint-inspect PATH` checks exact canonical wire shape;
it does not authenticate signatures or independent custody. The mock verifier
requires an explicit synthetic session, a pinned key, a single-use challenge and
existing owner-checkpoint verification. Replays, conflicts and clock regression
freeze that session. Production integration is deliberately absent. Process-local
state, a caller's clock and a locally controlled signer cannot establish an
independent current head; production remains blocked. See the [design and trust
requirements](PHASE12_OPERATOR_DESIGN.md).

## Daily work and future readiness

`console` combines the existing authority, newsroom readiness, work queues,
source research, observation evaluator and recovery inventory. Corrupt sections
are failures, not healthy empty queues. Legacy editorial/translation queues are
work lists; the signed authority journal decides authorization.

`rights-packets` prepares at most five existing candidates for qualified human
review. It grants no text, image, AI or ingestion permission. The [portfolio
review](PHASE13_PORTFOLIO_REVIEW.md) records current evidence limitations.

`observation-plan` emits eight future UTC dates spanning seven elapsed days and
a blank daily template. It does not create receipts, schedule collection or
count planned/synthetic days. Existing receipt validation detects duplicate runs,
gaps, timestamps and integrity problems. Authenticated environment, provenance
and clock remain prerequisites; genuine authenticated-day coverage stays zero.
`observation-review` also rejects a different declared environment or ledger and
contradictory transport/provenance declarations. Legacy receipts remain readable
and explicitly unbound. `schema observation-context` describes optional context
inside the existing v1 receipt, covered by its integrity digest. Even eight
correctly labelled local receipts cannot authenticate elapsed time or custody.
The existing collector can accept paired `--environment-id` / `--ledger-id`
arguments after separate collection authorization; these declarations are not
independent evidence. This program does not run live collection.

`preview` evaluates local blockers and identifies inaccessible account, billing
and access controls as INCONCLUSIVE. It never deploys or inspects credentials.
Separate owner approval is required for collection, schedules, paid AI, source
activation, rights/reviewer provisioning, checkpoints, GitHub publication and
Cloudflare preview or production. Use the [incident playbooks](OPERATIONS_INCIDENTS.md)
when evidence conflicts; preserve the evidence before any recovery action.
