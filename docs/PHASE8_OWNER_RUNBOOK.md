# Owner runbook: editorial identity, review and recovery

Current status: **no production trust root, credentials or appointed editors**.
This runbook is preparation, not permission to provision, grant rights, publish,
activate a feed, enable AI, schedule ingestion or deploy. Those require the
owner's separate real-world authorization. Test keys never count as appointment.

## Before provisioning

1. Obtain explicit authorization for real trust-root creation and custody. Choose
   an offline owner key, independent backup storage and a second verified copy of
   its public fingerprint. Decide who can access the verifier configuration and
   checkpoint channel. Anyone controlling both can replace the trust boundary.
2. Independently identify each reviewer and establish their actual authority.
   Technical enrollment is not legal permission, an employment appointment,
   factual expertise or native Bangla qualification. Keep evidence of these acts
   privately. Appoint rights, English, factual, native Bangla, publisher and
   suspension roles separately; assign only needed sources/stories/languages.
3. Select an independent checkpoint channel. An owner-controlled protected
   history or separately authenticated read-only medium can preserve expected
   digest/challenge inputs. This project does not automatically create one.
   Merely copying the journal and checkpoint into the same backup is insufficient.
4. Run `uv run python -m pipeline.authority status` and `demo`. The former should
   remain UNPROVISIONED until the real appointment/provisioning work is authorized;
   the latter must report synthetic-only success and production unavailable.

## Generating credentials, only after authorization

Use a supported offline tool or a separately inspected Python program using
`Ed25519PrivateKey.generate()` and
`serialization.BestAvailableEncryption(passphrase)` with PKCS8 PEM serialization.
Never derive a real key from a password, test seed, story ID or example. Write
with exclusive creation to an operator-managed directory outside the checkout.
Do not save raw keys or passphrases to source, `.env`, outbox, logs, shell history,
CI, clipboard automation or a report. The reviewer CLI deliberately has no
automatic production-key setup command.

The standard-library/PyCA operations for a separately authorized generator are:

```python
import getpass
import os
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

checkout = Path.cwd().resolve()
destination = Path(input("New key file outside this checkout: ")).resolve()
if destination.is_relative_to(checkout):
    raise ValueError("Choose a protected directory outside the checkout")
password = getpass.getpass("New passphrase: ").encode()
if len(password) < 16 or password != getpass.getpass("Repeat passphrase: ").encode():
    raise ValueError("Use matching strong passphrases of at least 16 bytes")
key = Ed25519PrivateKey.generate()
encoded = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                            serialization.BestAvailableEncryption(password))
descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(descriptor, "wb") as stream:
    stream.write(encoded)
    stream.flush()
    os.fsync(stream.fileno())
# Export only key.public_key().public_bytes_raw(), encoded as unpadded base64url,
# and its SHA-256 fingerprint through a separately checked public-key channel.
```

Run an inspected generator from the checkout so its boundary check is meaningful.
Pre-create the destination directory with appropriate protection. On Windows,
inspect NTFS ACLs and encrypted-backup policy before generation; POSIX `0o600`
does not establish an equivalent Windows ACL. Protect the entire machine from
same-user malware. File encryption cannot protect an unlocked signer process.
Back up encrypted keys and recovery passphrases through separately controlled
owner procedures, then rehearse access offline. Do not transmit a private key to
another reviewer or a server. Public fingerprints may be compared out of band.

## Bootstrap and appointments

Export schemas using `schema --type trust-pin` and `schema --type grant`. Construct
a canonical public trust pin outside the checkout containing version 1,
owner ID, a unique production ledger ID, environment `production`, policy
`phase8-authority-v1`, `synthetic: false` and the independently verified owner
root key (key ID, base64url public bytes, activation and expiry). Verify its bytes
and fingerprint through the independent custody channel. A self-made JSON file
without that operator trust decision is not a root.

Point only the current operator process at `TECHLINE_AUTHORITY_TRUST_FILE`.
Reviewer keys do not modify this pin. Produce a typed `prepare-admin --input`
request with exactly `operation`, `target_id`, `key` and `grant`:

- `enroll`: stable reviewer ID, public Key object, `grant: null`.
- `grant`: reviewer ID, `key: null`, an immutable Grant object.
- `revoke_grant`: grant ID; both nullable fields null.
- `suspend_reviewer`, `reinstate_reviewer`, `revoke_reviewer`: reviewer ID;
  both nullable fields null. Revocation is permanent; suspension needs a new owner
  reinstatement. Rotate a potentially compromised key while suspended first.
- `retire_key`, `revoke_key`: exact reviewer key ID; both fields null.
- `rotate_key`: same reviewer ID, replacement Key object, `grant: null`.
- `revoke_source`: exact source registry ID, both fields null.
- `rotate_root`: existing owner ID, replacement Key object, `grant: null`.

For each change: prepare a fresh outbox document; inspect every field; sign with
the current owner key and `--confirm RECORD_ID`; enrollment/rotation also uses
`--possession-key-file` for the new key's proof. Verify the signed record, then
`record --input FILE --confirm RECORD_ID`. All files remain private. Batch
appointments before review: every administrative revision invalidates older
active approvals conservatively. `reviewers` displays current scoped grants.

The root can administer but is not automatically an editor, rights reviewer,
native reviewer or publisher. Use separate appointed reviewer keys. Grant IDs
and key IDs are never reused; unknown, retired, revoked or out-of-scope keys fail.

## First real review, only after real appointments and rights evidence

1. `queue`, then `inspect --story STORY_ID`. Inspect primary and cited source
   identity, publisher, exact source/content/rights hashes and English/Bangla
   evidence. Do not relabel research as news. Source terms and configuration
   must independently permit the intended fields/transformations.
2. Record an independent source-rights decision in the `rights` workflow for
   each cited source, after checking real legal evidence. `prepare` requires
   reviewer, grant, decision, story, evidence SHA-256 references, optional cited
   source, workflow and language. Evidence digests refer to retained private
   evidence; a digest alone does not prove the license grant exists.
3. Walk the existing editorial lifecycle with the appropriately appointed roles:
   source validation, rights eligibility, draft, factual pending/completed,
   editorial pending/approved, publication eligible/published. No single role
   can sign all steps by assumption. Correct/retracted content needs explicit
   supersession/denial handling, not an overwritten status flag.
4. For Bangla, inspect exact translation and canonical English binding. A native
   reviewer signs the translation lifecycle through NATIVE_REVIEW_COMPLETE; a
   separately appointed publisher signs approval/publication transitions. An
   automated or fixture-reviewed label cannot substitute for native review.
   English changes, source evidence changes and translation changes invalidate
   the binding. This operation does not generate translations or call AI.
5. Use `prepare`, inspect the canonical outbox payload, then `sign --input ...
   --key-file ... --output .cache/authority/outbox/NEW.json --confirm RECORD_ID`.
   `verify` before `record`. Passphrases are prompted privately. Match displayed
   role, key ID, scope, previous state, sequence and head to the independently
   inspected content. A prepared or stored record is not activation.
6. Obtain a fresh publication challenge independently. Prepare and owner-sign a
   checkpoint of the complete latest journal, including all denials and
   administrative changes. Independently preserve and supply its exact digest
   and challenge. Configure only the operator process with checkpoint file,
   expected SHA-256 and challenge. Never derive expected trust from the same
   downloaded backup or checkpoint being checked.
7. `validate`, then `report`, and all existing content/rights/build/release
   checks. Read every denial. Technical authentication is not legal permission
   or a guarantee of editorial accuracy. Owner GitHub/deployment/source/AI
   authorization remains separate. This Phase 8 implementation performs none.

## Revocation and safe recovery

Use `hold --reason ... --confirm STOP_PUBLICATION` immediately for uncertain
rights, suspected compromise, broken keys, corrupt history or inability to
validate currentness. It requires no signer or checkpoint. Preserve the stop,
journal, outbox and independent anchor before investigation; never delete denial
evidence to get a green build.

For a valid journal, prepare/sign/verify/record the applicable scoped denial or
owner administrative revocation. Fresh publication checkpoints are unnecessary
to store risk-reducing records, but publish none of the old approvals afterward.
Update the independent anchor as soon as it is legitimate to attest complete
history. Reinstatement or rotation requires fresh reviews, not replayed signatures.

Back up the entire canonical journal, public trust pin, retained evidence and
independently preserved checkpoints. Store encrypted private keys separately.
For restoration, first stop publication, restore into an isolated directory,
verify all signatures and the exact external current checkpoint/challenge,
then inspect missing/outstanding denials and receipts. An old internally valid
backup is not current history. A missing segment is a blocker; synthetic archives
never establish authentic historical rights coverage.

An interrupted write can leave the old or new complete journal. Reload and
verify its head before any retry. Never auto-promote `.tmp` files. A stale
`.cache/pipeline-writer.lock` or generation transaction is retained for operator
inspection; determine whether its process is live, preserve evidence, then use
the existing generation recovery procedure where applicable. No automatic
lock stealing, partial-ledger repair or last-known-green approval fallback exists.

Lost reviewer key: owner rotates to a freshly verified key with possession proof;
old approvals become inactive. Compromised reviewer: suspend/revoke affected
grants/key/reviewer, inspect the complete affected scope, preserve denials, then
reappoint/rotate only after real human authorization. Lost/compromised owner root
without a trusted successor cannot recover itself: use an independent owner
identity/custody decision, preserve the complete old history and denials, and
commission a reviewed new bootstrap. Replacing a JSON file silently is not recovery.

Clearing an emergency stop or stale lock is a manual owner action after a fresh
independent verification of current history and the cause of the stop. The tool
intentionally offers no automatic clear/reset/import-as-trusted command. Windows
power-loss durability and unknown unanchored denials remain limitations even when
all local signatures verify.
