# Inactive local rights-review contract

`pipeline/review_governance.py` provides a metadata-only local operator workflow. Production does not import it. It cannot approve reuse: only `REVIEW_REQUIRED`, `REJECTED` and `REVOKED` decisions are accepted. Every evaluation returns publication false, AI submission false and approval-path-active false, including when evidence looks complete.

The independent review required for a future approval pathway has not occurred. Adding an approval enum or connecting this ledger to production would require a separate reviewed implementation and authorization. No article or source is approved here.

## Record contract

The separate [JSON schema](../schemas/local-rights-review.schema.json) describes the inactive ledger. It does not extend the public snapshot schema.

| Fields | Meaning |
|---|---|
| `binding.item_id`, `source_id`, `canonical_url` | Exact reviewed item/source/URL; ID must match the pipeline's deterministic derivation |
| `binding.content_sha256`, `evidence_sha256` | Bind normalized content and the complete adapter-returned observation; changed evidence invalidates the match. This is not a capture of the original publisher page or every unmapped feed field. |
| `binding.provenance` | `synthetic` or conservative `unknown`; missing origin never means verified publisher content |
| `original_publication_url` | Optional; requires explicitly scoped original-publication evidence |
| `publisher`, `original_creator` | Publisher identification; creator stays unknown without scoped evidence |
| `applicable_license` | Unknown unless a scoped license-grant evidence record is supplied; still unapproved |
| `evidence[].url`, `scope`, `note`, `captured_sha256` | Evidence location and scope, with optional capture digest; URLs are never fetched by this module |
| `permitted_fields`, `permitted_transformations` | Inert proposals only; default empty; never executable permission |
| `attribution_obligations`, `license_exceptions` | Explicit operator-recorded constraints; no invented defaults |
| `review_status`, `reviewer_identity`, `reviewed_at`, `review_reason` | Human review metadata; explicit timezone required; not reviewer authentication |
| `expires_at`, `rereview_triggers`, `policy_version` | Re-review on content/origin/license/policy changes, or expiry; maximum 90 days |
| `synthetic` | Derived from binding provenance by draft/CLI; contradictory flags reject; no synthetic record grants real rights |

Evidence scope distinguishes specific item, license grant, creator, publisher, original publication, exception and source policy. A source-domain match or source-policy record alone cannot grant item rights. Untrusted feed approval/reviewer fields are never imported as decisions.

Required labels/reasons reject blank or whitespace-only text, unsafe Unicode control/format/surrogate characters and excess length (200 characters for labels, 2,000 for notes). Multilingual text is supported. Stored ledgers require explicit strict integer version 1; booleans, floats, strings, missing versions and future versions refuse. Serialization remains deterministic; strings are validated without silent rewriting. Older synthetic decisions whose binding omitted provenance fail closed and must be regenerated in isolated fixture state, never silently relabelled. No existing owner ledger is migrated by staging. See the [corrective handoff](PHASE3_CORRECTIVE_HANDOFF.md).

## Local operator workflow

Run from the repository root with the existing Python environment:

```powershell
.venv/Scripts/python.exe -m pipeline.pilot_staging
.venv/Scripts/python.exe -m pipeline.review_governance draft --file .cache/phase3/staging/binding-example.json --publisher SyntheticFixture --reviewer synthetic-operator --synthetic
.venv/Scripts/python.exe -m pipeline.review_governance record --file .cache/phase3/reviews/draft.json
.venv/Scripts/python.exe -m pipeline.review_governance inspect
.venv/Scripts/python.exe -m pipeline.review_governance evaluate --file .cache/phase3/staging/binding-example.json
```

These commands demonstrate a synthetic pending review. Evaluation must deny. The staging-generated evidence URL uses the reserved `.example` namespace and is explicitly fictional. It is never an assertion about a publisher's license. For real observations, an operator must independently establish identity, scope, evidence and obligations; this implementation still cannot approve them.

An operator may edit a draft to record rejection or revocation and append it. Do not mutate ledger history. Changed evidence requires a new item-bound record; a stale or mismatched record does not carry forward. A malformed or forged record raises/refuses instead of treating it as an empty successful review.

## Audit and failure behavior

Events carry monotonic sequence and review timestamps, previous-event SHA-256, canonical event SHA-256 and ledger head. The same complete inputs produce the same audit digest. Loading checks the entire chain and rejects corruption, reordering, duplicate JSON keys, extra fields, unsupported decisions, excessive size and excessive history.

Append uses an exclusive writer lock, revalidation under lock and the existing atomic JSON replacement. Failed writes preserve the previous ledger. A hard-killed writer may leave `.cache/phase3/reviews/writer.lock`; inspect the process and previous ledger before explicitly removing that local lock. The tool never guesses that a lock is stale. Capacity is 500 events/2 MB; preservation and operator-reviewed archival are required before growth beyond that bound.

Hashes are integrity checks, not signatures. A malicious local writer can recompute a chain or replace it with an older valid chain. Reviewer identity is a recorded field, not authenticated identity. These limitations cannot grant publication because approval is inactive. Future activation needs authenticated reviewer authority, protected head/checkpoint storage, rollback/revocation handling and independent security review.

All writes are confined to `.cache/phase3`; traversal, symlink and junction paths are rejected. Inputs are bounded local JSON files. No database, external service, environment secrets, network fetch or AI provider is used.
