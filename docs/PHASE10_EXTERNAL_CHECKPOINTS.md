# Phase 10 — external checkpoint custody and verification

Status: **UNPROVISIONED**. Nothing here appoints a reviewer, grants a
permission, publishes or deploys. The canonical edition is unchanged.

Phase 11 correction: read [operational trust limits](PHASE11_TRUST_LIMITS.md).
The file adapters cannot authenticate independent custody or the current head.
Matching signatures and local history remain BLOCKED. The workflow below
prepares evidence only; it cannot establish current trust.

## Why this exists

Phase 8 signs a journal head as a `Checkpoint` envelope. That proves *which key*
signed a head. It does not prove that the head is *current*. A journal that is
rolled back to an older but internally consistent state rolls back any
checkpoint stored beside it, and a hash chain cannot repair that: the chain
proves continuity with itself, not with the trusted past.

Phase 10 adds the missing half — a custody envelope that travels to an
independently held custodian, and a verifier that reports plainly how far the
evidence actually reaches.

## Five trust levels, never collapsed

| Level | Meaning | Reached by |
|---|---|---|
| `LOCAL_SNAPSHOT` | Generated locally, never signed | Nothing. The starting point. |
| `LOCAL_SIGNED` | Signed locally, still only local evidence | A local signature |
| `EXTERNAL_STORED` | Written outside the authority state directory | An operator-held custodian file, a materialised protected branch, or a read-only mirror |
| `INDEPENDENTLY_AUTHENTICATED` | Authenticated evidence from an independently controlled custodian | Reserved; unavailable through current adapters |
| `CURRENTLY_TRUSTED` | Additionally authenticated current-head evidence with a fresh, single-use challenge response | Reserved; unavailable through current adapters |

Only `CURRENTLY_TRUSTED` is a pass. `EXTERNAL_STORED` is **custody, not
authenticity**: a file copied into another folder is still a file on the same
disk. A supplied digest establishes equality with that value; it cannot prove
its independent origin or currency. Moving the file never establishes those properties.

A checkpoint whose effective custody is the authority state directory is
refused with `checkpoint_custody_insufficient`. It cannot act as an external
anchor while it sits beside the state it is supposed to anchor.

## What a checkpoint binds

The signed `Checkpoint` envelope (unchanged Phase 8 payload) binds the ledger
identity, the journal revision (`event_count`), the latest event digest
(`head_sha256`), the trust registry revision, the policy version, the capture
and expiry timestamps, the environment, the record/sequence position, the
previous head and the per-publication challenge.

The Phase 10 custody document (`pipeline/authority/checkpoint.py`) wraps that
envelope and adds the custody statement, the capture time, the canonical
document format version and the custodian's own claim. The canonical
representation is `canonical(document.model_dump(mode="json"))`; the digest an
independent channel must carry is the SHA-256 of exactly those bytes.

Document format: `techline.editorial.external-checkpoint/v1`, format version 1.

## Detection codes

The verifier names the defect instead of collapsing everything into "rollback".

| Code | Meaning |
|---|---|
| `checkpoint_missing` | No custodian document was supplied |
| `checkpoint_malformed` | The document is unreadable, non-canonical or invalid |
| `unsupported_protocol_version` | An unknown authority protocol, record version or document format |
| `unknown_ledger` | The checkpoint belongs to another authority ledger |
| `cross_environment_replay` | The checkpoint environment does not match the verifier |
| `unknown_signer` | It was not signed by the pinned current owner root |
| `invalid_signature` | The signature does not verify |
| `expected_digest_mismatch` | The supplied digest differs from the independently trusted digest |
| `challenge_mismatch` | It is not for this publication challenge |
| `checkpoint_stale` | Expired, future-dated or older than the operator freshness policy |
| `registry_mismatch` | The trust registry revision differs |
| `journal_revision_regression` | The local journal is shorter than the trusted checkpoint |
| `journal_hash_mismatch` | The local head differs at the same length |
| `incomplete_history` | The local history does not extend the trusted checkpoint |
| `checkpoint_not_current` | The trusted checkpoint does not cover the current head |
| `conflicting_checkpoints` | Two independently held checkpoints disagree |
| `checkpoint_custody_insufficient` | The document is stored inside the authority state directory |
| `independent_evidence_missing` | No independently obtained digest was supplied |
| `independent_freshness_unverified` | Local agreement exists, but independent current-state evidence cannot be authenticated |
| `emergency_hold` | A persistent publication stop is present |

Verdicts are `PASS`, `FAIL`, `BLOCKED` or `INCONCLUSIVE`. Missing evidence is
never `PASS`.

## Operator workflow

1. **Prepare.** `python -m pipeline.authority prepare-checkpoint --challenge CHALLENGE --output .cache/authority/outbox/CHECKPOINT.json`
2. **Sign and record** with the existing owner key flow, then
   `python -m pipeline.authority record --input ... --confirm RECORD_ID`.
3. **Attest.** Wrap the signed envelope in a custody document:
   `python -m pipeline.authority checkpoint-attest --input .cache/authority/outbox/SIGNED.json --custody operator-offline-file --authentication operator-attested --challenge CHALLENGE --output .cache/authority/outbox/ATTESTATION.json`
   This writes only into the outbox. Moving the document to the custodian is a
   separate, manual act.
4. **Custody.** Place the attestation document with the custodian and record
   its SHA-256 through a channel the checkout does not control. Never derive
   the expected digest from the same copy being checked.
5. **Verify.** `python -m pipeline.authority checkpoint-status` uses
   `TECHLINE_EXTERNAL_CHECKPOINT_FILE`, `TECHLINE_EXTERNAL_CHECKPOINT_SHA256`
   and `TECHLINE_EXTERNAL_CHECKPOINT_CHALLENGE` (falling back to
   `TECHLINE_AUTHORITY_CHALLENGE`). `python -m pipeline.authority checkpoint-verify --input FILE --expected-sha256 HEX --challenge CHALLENGE`
   verifies one document explicitly.

The Phase 8 environment variables (`TECHLINE_AUTHORITY_CHECKPOINT_FILE`,
`TECHLINE_AUTHORITY_CHECKPOINT_SHA256`, `TECHLINE_AUTHORITY_CHALLENGE`) keep
their existing meaning for the bare-envelope anchor and are unchanged.

## Storage adapters

| Adapter | Custody | Network |
|---|---|---|
| `OperatorFileCheckpointStore` | An operator-held regular file outside the checkout | None |
| `ProtectedHistoryCheckpointStore` | A checkpoint the operator materialised from a protected branch | **None — this project never contacts GitHub** |
| `MissingCheckpointStore` | No custodian configured | None |

The protected-history adapter reads a file from a directory the operator
materialised themselves. It performs no API call, creates no branch and writes
nothing to GitHub. The protection guarantee a protected branch provides —
retained, access-controlled, independently reviewable history — depends on
repository settings this project cannot configure or verify for itself.

## What this still does not give you

- A denial that was never included in the trusted checkpoint is not detectable
  from that checkpoint. Capture a fresh anchor after every publication.
- An attacker who controls the operating-system account **and** the independent
  channel defeats this boundary.
- Signatures do not protect compromised verifier code.
- Windows power-loss durability is bounded by the OS and the storage device.
  An independent backup and an independent checkpoint remain necessary.

## Commands

| Command | Purpose |
|---|---|
| `python -m pipeline.authority checkpoint-status` | Report the current trusted-checkpoint status |
| `python -m pipeline.authority checkpoint-verify --input FILE --expected-sha256 HEX` | Verify one held document |
| `python -m pipeline.authority checkpoint-attest --input FILE --output FILE` | Build the custody document |
| `python -m pipeline.authority prepare-checkpoint --challenge C --output FILE` | Prepare the unsigned checkpoint payload |
| `python -m pipeline.newsroom_readiness` | Consolidated launch readiness including the checkpoint item |

Related: [Phase 8 authority model](PHASE8_EDITORIAL_AUTHORITY.md) ·
[owner runbook](PHASE8_OWNER_RUNBOOK.md) ·
[Phase 10 recovery runbook](PHASE10_RECOVERY_RUNBOOK.md) ·
[Phase 10 newsroom operations](PHASE10_NEWSROOM_OPERATIONS.md)
