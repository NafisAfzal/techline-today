# Phase 10 — owner custody, recovery and key management runbook

Status: **no production trust root, credentials or appointed editors exist**.
This runbook is preparation, not permission to provision, grant rights,
publish, activate a feed, enable AI, schedule ingestion or deploy. Those
require the owner's separate real-world authorisation.

Phase 11 correction: [operational trust limits](PHASE11_TRUST_LIMITS.md)
supersede earlier currency claims. Packs omit the generated edition and retained
evidence bodies; arrange separate lawful backups for those assets. Export,
restore and explicit drill work directories must be new. Complete preflight
precedes writes; existing/partial destinations are refused. The clean recovery
drill and lost-owner-key drill are BLOCKED for operational recovery.

## 1. What must be protected

`python -m pipeline.recovery inventory` prints the machine-readable inventory.
The important split is data versus credential:

**Recoverable data** — the signed authority journal, the revocations inside it,
the source rights policy, the source candidate ledger, retained rights and
translation evidence, the generated edition, and the recovery manifests.

**Irrecoverable credentials** — the owner private signing key, every reviewer
private signing key, and any externally held trusted checkpoint that the
custodian did not retain. Here, irrecoverable means unavailable from this
project's packs. Separately held verified encrypted key backups may permit
human-controlled recovery; independently held receipts need their own retention.
If every usable key copy is lost, the journal cannot recreate it and normal
rotation cannot be signed with the missing key. Remain blocked pending an
independently reviewed new trust-establishment policy and owner-controlled ceremony.

A recovery pack carries only allowlisted public authority, policy and candidate
index material. It omits other inventory assets, including the generated edition,
retained evidence bodies and private keys; recognised private key markers cause
export refusal. Separate lawful custody and backups are still required.

## 2. Recovery pack

```sh
uv run python -m pipeline.recovery export --destination D:/backups/pack-YYYYMMDD
uv run python -m pipeline.recovery verify D:/backups/pack-YYYYMMDD \
  --expected-ledger-id YOUR-LEDGER-ID --expected-environment production
uv run python -m pipeline.recovery verify D:/backups/pack-YYYYMMDD \
  --checkpoint D:/custody/attestation.json --expected-checkpoint-sha256 OUT-OF-BAND-DIGEST
```

A pack that passes every local check is **locally consistent**. It is not
"trusted" and not "current". The verifier says so in its `trust_statement`,
and `current` stays false. No supported adapter authenticates the independent
current-state evidence needed to change that result.

## 3. Restore drill

```sh
uv run python -m pipeline.recovery drills
uv run python -m pipeline.recovery drill DR-04
```

The fifteen synthetic exercises cover a clean recovery, an incomplete backup, a
corrupted ledger, journal truncation, an old registry, a revoked reviewer
restored, an old approval replay, a missing trusted checkpoint, conflicting
independent checkpoints, an interrupted recovery, the wrong environment,
duplicate decision history, a compromised reviewer key, a lost owner signing
key and an emergency publication stop. Each reports its fixture, the injected
failure, the expected and actual behaviour, the trust guarantees that remain
available, the human intervention still required, and a PASS/FAIL/BLOCKED
result.

**A green drill is not a disaster-recovery certification.** It proves the
tooling refuses unsafe states using synthetic assets. It never touches the real
project state.

## 4. First owner provisioning — only after real authorisation

1. Obtain explicit written authorisation for trust-root creation and custody.
2. Choose an offline owner key, two independent backup copies of it, and a
   second verified copy of its public fingerprint.
3. Choose the checkpoint custodian channel **before** provisioning. Decide who
   can reach the trust file, the custody document and the expected digest.
4. Generate the key with a separately inspected program using
   `Ed25519PrivateKey.generate()` and
   `serialization.BestAvailableEncryption(passphrase)`. Write it with
   exclusive creation into an operator-managed directory outside the checkout.
   Never derive a real key from a password, a test seed, a story ID or an
   example. The procedure is documented in the
   [Phase 8 owner runbook](PHASE8_OWNER_RUNBOOK.md); the CLI deliberately has
   no automatic production key-setup command.
5. Export the schemas (`python -m pipeline.authority schema --type trust-pin`,
   `--type grant`) and build the public trust pin outside the checkout.
6. Verify the pin bytes and fingerprint through the independent custody
   channel. A self-made JSON file is not a root.

## 5. Owner key backup

- Encrypt the key with a passphrase of at least 16 bytes and store the
  encrypted file separately from the signing machine.
- Store the recovery passphrase separately again. Two backups of the same
  thing are one backup with two failure modes.
- Rehearse passphrase access offline before you need it. A rehearsed restore
  is worth more than an extra copy.
- Never store the key, the passphrase or a recovery plan in this repository,
  in `.env`, in the outbox, in CI, in shell history, in a report or on a
  clipboard.

## 6. Reviewer invitation

1. Identify the person independently and establish their actual authority:
   rights expertise, editorial judgement, factual competence or native Bangla
   qualification. Technical enrolment is not legal permission, an employment
   appointment, expertise or a qualification.
2. Keep the evidence of that act privately. This repository holds none of it.
3. Produce a typed `prepare-admin --input` request with exactly `operation`,
   `target_id`, `key` and `grant`, and use `enroll` with the replacement key's
   public key.
4. Sign with the current owner key and `--confirm RECORD_ID`. Enrolment and
   rotation also need `--possession-key-file` for the replacement key's proof.
5. Verify the signed record, then `record --input FILE --confirm RECORD_ID`.
6. Grant separately and narrowly: role, decisions, sources, stories,
   languages, workflows and a validity window. There is no source wildcard and
   no owner self-enrolment through a reviewer grant.
7. Batch appointments before review. Every administrative change advances the
   registry revision and invalidates older active approvals. That is a
   deliberate small-team trade: revocation correctness over automatic approval
   migration.

## 7. Signing key handling

- Keys live on the reviewer's own machine or an operator-managed directory.
- They are never in this repository, never in the outbox, never in a report.
- The signer refuses an echoed passphrase, requires a private interactive
  terminal, refuses POSIX group/other key-file access and rejects linked or
  reparse-point paths.
- Windows ACL correctness is the operator's responsibility. POSIX `0o600`
  does not establish an equivalent Windows ACL.

## 8. Reviewer suspension and revocation

| Situation | Action | Effect |
|---|---|---|
| Reviewer temporarily unavailable | `suspend_reviewer` | Their grant stops working; a fresh owner `reinstate_reviewer` is needed to restore it |
| Suspected compromise | `revoke_reviewer` **and** `revoke_key`, then `revoke_grant` | Permanent. The reviewer cannot be re-enrolled under the same ID |
| Key may be exposed but the identity is not compromised | `rotate_key` with possession proof | The old key is disabled; every approval signed with it becomes inactive |
| Wrong scope or a mistaken grant | `revoke_grant` | The grant ID is permanently unusable |

Revocation does not remove static files already delivered to a website, a
cache or a reader. Coordinate any correction, retraction notice or takedown
through a separately authorised publication action. The offline tooling
performs none.

## 9. Key rotation

1. Prepare a new key with the same procedure as provisioning.
2. `rotate_key` with the new public key and possession proof from the new
   private key.
3. Every approval signed with the old key becomes inactive. Re-review the
   affected scope. Do not try to carry old approvals forward.
4. Rotate a potentially compromised key while the reviewer is suspended.

## 10. Key loss and recovery authorisation

**Reviewer key lost.** The owner rotates to a freshly verified key with
possession proof. Old approvals lapse. Nothing needs to be recovered from a
backup.

**Owner root lost or compromised without a trusted successor.** The root cannot
recover itself. Use an independent owner identity and custody decision,
preserve the complete old history and denials, and commission a reviewed new
bootstrap. Replacing a JSON file silently is not recovery, and this project
offers no automatic import-as-trusted command.

## 11. Emergency stop

```sh
uv run python -m pipeline.authority hold --reason "Susppected compromise" --confirm STOP_PUBLICATION
```

The stop requires no signer and no checkpoint. It blocks publication even if a
process is killed before the reason digest finishes writing, preserves the
first stop and is never automatically cleared. Use it first when rights,
credentials or history are uncertain.

Clearing a stop is a manual owner act after a fresh independent verification
of the current history and the cause of the stop.

## 12. Independent checkpoint custody

1. Prepare, sign and record the checkpoint as described in
   [Phase 10 external checkpoints](PHASE10_EXTERNAL_CHECKPOINTS.md).
2. Wrap it in a custody document and move that document to the custodian.
3. Record the document's SHA-256 out of band. Never derive the expected digest
   from the copy being checked, and never from the backup that also holds the
   journal.
4. Capture a fresh checkpoint after every publication and confirm the
   custodian actually retained it.
5. If two custodians hold conflicting checkpoints, neither is authoritative
   until the owner resolves the conflict and retires one of them.

## 13. What still needs a human

- A named owner and a named rights reviewer.
- A real rights decision for every source candidate.
- A native Bangla reviewer for any Bangla publication.
- A decided retention period per source.
- A decided publication cadence and a payer for the hosting plan.
- The out-of-band custody of the checkpoint digest.

Related: [external checkpoints](PHASE10_EXTERNAL_CHECKPOINTS.md) ·
[Phase 8 owner runbook](PHASE8_OWNER_RUNBOOK.md) ·
[backup and recovery](BACKUP_RECOVERY.md) ·
[newsroom operations](PHASE10_NEWSROOM_OPERATIONS.md)
