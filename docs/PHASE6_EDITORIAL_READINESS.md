# Phase 6 — Editorial readiness infrastructure

The [Phase 8 authority extension](PHASE8_EDITORIAL_AUTHORITY.md) now provides an
offline signed path using these same lifecycles. The legacy draft ledgers below
still cannot grant approvals, and the default real environment remains
UNPROVISIONED. Real appointments, rights and independent history trust are not
supplied by implementing the cryptographic mechanism.

This document describes the infrastructure added for lawful source onboarding,
editorial review, bilingual governance and operational readiness. It grants
nothing. Every approval path in it is deliberately blocked until an owner
appoints accountable people.

Phase 6 builds on the frozen Phase 5 stabilisation commit. **It cannot be merged
or released until Phase 5 is owner-approved.** Nothing here activates a source,
approves rights, enables scheduling or AI, or publishes.

## Architecture

Five new local-first modules. No server, database, queue or paid dependency.

| Module | Responsibility |
|---|---|
| `pipeline/source_onboarding.py` | Candidate lifecycle and append-only candidate ledger |
| `pipeline/editorial_workflow.py` | Story lifecycle and editorial decision ledger |
| `pipeline/publication_gate.py` | Composite gate; refuses only, never grants |
| `pipeline/translation_governance.py` | Translation lifecycle, staleness, language integrity |
| `pipeline/readiness.py` | Sixteen readiness dimensions and seven-day evidence validation |

All state is append-only, hash-chained JSON under `.cache/phase6/`. Each ledger
reuses `digest` and `writer_lock` from `pipeline.review_governance`, and
`confined_file`/`atomic_json` from the existing filesystem and storage helpers.
Loads check bounded JSON, chain consistency, legal prior states and identity
continuity. These are unkeyed hashes, not signatures: someone able to rewrite the
entire ledger can recompute them, or remove the ledger. They do not authenticate
an actor or prove complete history. Approval remains unavailable independently
of those hashes. Durable authenticated identity and an external history anchor
are prerequisites for any future approval system.

The public snapshot schema is unchanged. `docs/PHASE5_READINESS_PLAN.md` defers
that migration deliberately, so the gate reads local registries instead.

## The authority boundary

No authenticated reviewer identity exists in this project. That is a fact, not a
missing configuration. Accordingly these transitions raise `AuthorityUnavailable`
and a ledger that claims them is rejected on load, so a hand-edited file cannot
grant them either:

| Ledger | Blocked states |
|---|---|
| Source candidates | `RIGHTS_EVIDENCE_RECORDED`, `ELIGIBLE_FOR_ACTIVATION`, `ACTIVATED` |
| Editorial | `APPROVED`, `PUBLICATION_ELIGIBLE`, `PUBLISHED` |
| Translation | `NATIVE_REVIEW_COMPLETE`, `APPROVED_TRANSLATION`, `PUBLISHED_TRANSLATION` |

Reducing exposure does not require approval. Suspension/revocation, editorial
retraction/correction/archival, and translation withdrawal remain available with
their required reasons and references. Terminal withdrawal cannot be reversed
into an approval. Actor names are recorded claims, not authenticated identities.

## Source onboarding

```
DISCOVERED → TECHNICALLY_VALIDATED → RIGHTS_REVIEW_REQUIRED
   → RIGHTS_EVIDENCE_RECORDED → EDITORIAL_REVIEW_REQUIRED
   → ELIGIBLE_FOR_ACTIVATION → ACTIVATED → SUSPENDED / REVOKED
```

A candidate records technical, rights, attribution, reproduction, summary, image,
retention and AI-submission permissions **independently**. Unknown is `null` and is
never treated as permitted. Asserting any permission while rights are
`RIGHTS_UNVERIFIED`, `RIGHTS_DENIED` or `REVOKED` is refused at validation time.

Identity is `sha256(host | fetch method | language)`. A duplicate publisher
identity is refused, and changing the publisher identity mid-lifecycle requires
registering a new candidate.

## Rights review procedure

1. Discover the candidate and register it (`register`). State becomes `DISCOVERED`.
2. Confirm the endpoint is reachable and parses (`transition` →
   `TECHNICALLY_VALIDATED`). A feed URL that moves is a new observation, not an
   inherited approval.
3. Move to `RIGHTS_REVIEW_REQUIRED`.
4. A human records the licence or terms evidence as a URL plus a note.
5. `RIGHTS_EVIDENCE_RECORDED` is **blocked** until an accountable reviewer exists.
6. Only then may the owner enable the source in `config/sources.yaml` and record
   `publication: allow` in `config/source-rights.json`.

Source discovery grants no reproduction rights, and `robots.txt` permission is not
a licence. Absence of a rights statement is not permission.

## Editorial review procedure

```
DISCOVERED → SOURCE_VALIDATED → RIGHTS_ELIGIBLE → DRAFT_READY
   → FACT_CHECK_PENDING → FACT_CHECKED → EDITORIAL_APPROVAL_PENDING
   → APPROVED → PUBLICATION_ELIGIBLE → PUBLISHED
   → CORRECTED / RETRACTED / ARCHIVED
```

`FACT_CHECKED` requires a checklist reference, `CORRECTED` a correction reference
and `RETRACTED` a reason. None can be declared without evidence.

Timestamps stay distinct: publication, first observation, last verification, last
editorial update and build time are separate fields. `date_violations()` reports
unknown, future and build-time-matched publication dates instead of repairing them.
Story kind is derived from source metadata only — a recent build never makes
research or evergreen material current news.

## Publication eligibility

`pipeline/publication_gate.py` evaluates five independent dimensions. Publication
requires **all** of them; denials are additive, so satisfying one never publishes a
story.

| Dimension | Refuses when |
|---|---|
| `rights_evidence` | Source not `allow`, licence/scope missing, item held for review, non-news source, missing evidence |
| `source_validation` | No cited sources, demo content, unattributed publisher |
| `editorial_approval` | No authenticated approval, no provenance history, AI generation |
| `date_integrity` | Publication unknown, in the future, or equal to build time |
| `language_review` | Machine translation presented as reviewed Bangla |

The compatibility `require_approval=False` argument requests diagnostics only;
it cannot suppress the authority refusal. An empty edition is not publishable.
Neither an arbitrary reviewer name nor a recomputed hash supplies authority.

### Existing build isolation

Live builds and build verification invoke the local Python governance preflight.
Before authenticated editorial authority exists, only the unchanged frozen legacy
snapshot (`d146d528ed8b00bc4e3a1e379ceffa300f46ce5a17ee9d34e8291410e9973eb5`)
can use the established legacy rights checks. New live snapshots fail closed;
adding a draft to generated JSON is not a publication path. Updating this frozen
identity requires a separately reviewed authority design and owner decision.

Matching local source candidates, editorial decisions, or draft/withdrawn Bangla
records invalidate stale generated content. Matching uses the registry id/source
identity and story identities, including the legacy id-only form. The build
checks before and after generation, and standalone build verification repeats
the guard. It refuses rather than deleting stories, archives, or evidence.
Synthetic fixture builds remain explicitly synthetic; production rights checks
and release gates continue to reject them.

This is a negative guard, not an authenticated publication system or automatic
withdrawal of already hosted assets. Removal of local history cannot be detected
without an independent trusted anchor. Preserve denial history and keep all
activation/deployment blocked pending that design; do not claim that local files
alone provide revocation durability.

`evaluate_snapshot()` fails the whole edition when any story is denied, and
`assert_publishable()` raises `PermissionError` with the specific dimensions.

## Bangla translation review

```
NOT_TRANSLATED → DRAFT_TRANSLATION → LANGUAGE_REVIEW_PENDING
   → NATIVE_REVIEW_COMPLETE → APPROVED_TRANSLATION → PUBLISHED_TRANSLATION
```

A translation binds to an exact English source version. When the source changes
materially — including facts, limitations, numbers, claims and evidence — the
translation returns to `LANGUAGE_REVIEW_PENDING` and its reviewer reference and
review time are cleared. Canonical versions already exclude operational metadata,
so metadata-only churn retains the same canonical hash and does not downgrade
review. A different hash always requires re-review; caller-supplied content
projections cannot prove that rebinding a review is safe.

`integrity_findings()` reports English fallback mislabelled as Bangla, empty
fields, replacement characters, mojibake, control characters, Bangla leaking into
the English source and invalid slugs. These are preparation for human review, not
proof of native-language quality. No reviewer identity is ever invented.

## Seven-day observation evidence

Only retained **live** receipts contribute to the structural window. Synthetic
runs contribute no elapsed time. Hashes, run identities, stable source coverage,
healthy collection, UTC dates, monotonic ordering and a maximum 36-hour gap/age
are checked; corrupt retained files are refused rather than silently omitted.
`observation_evidence()` rejects, and reports as anomalies: future, naive and
unparsable timestamps, duplicate observation days, overlapping runs, copied run
evidence, and stale evidence. Missing calendar days inside the observed span are
listed explicitly. Seven elapsed days requires eight observed days.

Real elapsed time has not been manufactured. No schedule is enabled. Receipt
hashes are not signatures and cannot prove a run actually occurred at its stated
time. `elapsed_window_satisfied` describes structural consistency only;
`provenance_verified` and `eligible` remain false until trustworthy observation
provenance is designed. A consistent local window therefore remains INCONCLUSIVE
for production readiness, not PASS.

## Operational readiness

Sixteen dimensions resolve to `PASS`, `FAIL`, `BLOCKED` or `INCONCLUSIVE` with
evidence. `INCONCLUSIVE` means the evidence does not exist and is never treated as
a pass. Assessment itself never authorises publication.

Pass an explicit `sources` mapping to assess freshness and revoked-source
contamination. Category names alone cannot establish news; the public categories
are technology topics, not a `news` enum. Missing/unknown diagnostics are not
success, future publisher dates are not fresh news, and publisher age does not
prove our publication delay. Snapshot health needs a schema-valid live edition
and a trusted expected digest. Security checks need explicit false AI/schedule/
initial-seed flags; an empty accessibility object is not a completed check.

```sh
uv run python -m pipeline.source_onboarding report
uv run python -m pipeline.editorial_workflow report
uv run python -m pipeline.translation_governance report
```

## Running the tests

```sh
uv run pytest pipeline/tests/test_phase6_source_onboarding.py
uv run pytest pipeline/tests/test_phase6_editorial_gate.py
uv run pytest pipeline/tests/test_phase6_translation_governance.py
uv run pytest pipeline/tests/test_phase6_readiness.py
pnpm test
```

## Deferred owner-controlled prerequisites

Coding cannot supply these. The system is prepared so each can be decided safely:

- Publisher permission or licensing for any news source.
- Copyright and reuse approvals, per item.
- Appointment of an accountable human editor.
- Appointment of a qualified native Bangla reviewer.
- Seven actual elapsed days of live observation.
- Cloudflare preview deployment approval and free-plan evidence.
- Public production launch approval.
- Paid AI authorization.
- Activation of scheduled ingestion.

Until an authenticated reviewer authority exists, approval and activation remain
structurally unavailable in code — not merely disabled by configuration.
