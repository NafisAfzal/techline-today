# Owner and reviewer preparation on Windows

This preparation does not create credentials, install trust, sign records, appoint
anyone or publish. Current production authority remains unprovisioned. Run from
the reviewed checkout with its frozen dependencies installed. Keep every filled
packet outside Git, public assets, cloud synchronization and shared directories.

## Owner's personal steps

1. Confirm the intended environment is **production** and choose the exact stable
   ledger identity. Personally identify the owner and independent custodian. A
   typed name, a matching fingerprint and a completed checklist cannot establish
   human identity or legal authority. Obtain separate authorization before real
   credential provisioning or enrollment.
2. Choose local owner-controlled storage outside every Git checkout, with an
   owner-only file and parent directory. In PowerShell inspect both using
   `Get-Acl -LiteralPath 'C:\private-location' | Format-List`. The signer now
   checks Windows file and parent ACLs; only the current user, SYSTEM and local
   administrators may have Allow entries. Unknown/broad access or an unavailable
   ACL inspection refuses signing. POSIX requires owner-only file and parent.
   This does not protect against administrators or malware running as you.
   Known OneDrive, Dropbox and Google Drive directories, network shares, linked
   paths and keys in any Git checkout are refused. Undetected synchronization
   still requires your inspection. The checker never changes permissions.
3. After separate authorization, use a separately reviewed offline process for an
   Ed25519 key encrypted as PKCS8 PEM. The existing [owner runbook](PHASE8_OWNER_RUNBOOK.md)
   describes the supported format. Hardware tokens are not integrated. Never put
   passphrases in arguments, environment variables, reports or shell history.
   The preparation command never asks for a passphrase or prints key material.
4. Export only the public key as PEM SubjectPublicKeyInfo or unpadded base64url
   raw Ed25519 public bytes. Compare its displayed SHA-256 fingerprint through a
   separately authenticated channel. Personally verify who controls that key.
5. Keep an encrypted backup under separate physical/control custody and retain
   the passphrase through a separately controlled recovery procedure. Personally
   rehearse decryption, restore and key/public-key correspondence offline. The
   checker compares encrypted bytes only; it cannot prove decryptability,
   off-machine custody, freshness, identity or the signing algorithm hidden by
   encryption. A second local folder is not independent backup or checkpoint
   custody. Recovery packs deliberately exclude private keys.
   PKCS8 encryption is mandatory for signing files. Whole-disk BitLocker or an
   encrypted removable volume can add protection while the device is locked;
   they do not replace file encryption, verified ACLs or an independent backup.
   Filesystems without verifiable access controls remain blocked by this checker.
6. Run the guide below. Answer YES only for work actually completed. Outstanding
   confirmations or missing files keep the report BLOCKED. A green preparation
   result is only READY_FOR_HUMAN_CEREMONY; production stays disabled.

```powershell
.venv\Scripts\python.exe -m pipeline.operations.onboarding owner --environment-id production --ledger-id YOUR-EXACT-LEDGER --interactive
```

When separately authorized credentials already exist, inspect them without
decrypting or signing (replace every placeholder personally):

```powershell
.venv\Scripts\python.exe -m pipeline.operations.onboarding owner --environment-id production --ledger-id YOUR-EXACT-LEDGER --interactive --public-file 'C:\private\owner-public.pem' --expected-fingerprint 'INDEPENDENTLY-OBTAINED-64-HEX-FINGERPRINT' --custody-file 'C:\private\owner-encrypted.pem' --backup-file 'E:\separate-custody\owner-encrypted.pem'
```

Alternatively prepare `ceremony --template` in a private editor, fill only
verified confirmations and supply `--proposal 'C:\private\ceremony.json'`.
Do not overwrite an existing registry, journal or emergency STOP. The actual
public trust pin, owner-controlled signing and independent current checkpoint
require the separately authorized [existing protocol](PHASE8_OWNER_RUNBOOK.md).

If every owner key/backup or passphrase is lost, the journal cannot recover the
key. Do not replace the pin silently. Use a newly reviewed human trust ceremony.
Planned root rotation requires the current owner signature, new-key possession
proof and a fresh independent checkpoint. If the key may be compromised,
freeze first, preserve evidence and follow the [incident runbook](OPERATIONS_INCIDENTS.md).
The existing local emergency operation is `python -m pipeline.authority hold
--reason 'reviewed incident reason' --confirm STOP_PUBLICATION`; it creates a
persistent stop and grants no authority to resume. Never remove STOP as routine
setup. Resume only after owner-reviewed recovery and refreshed external trust.

## Reviewer invitation and appointment packet

Use an existing role: `source-rights`, `fact-checker`, `english-editor`,
`publisher`, `native-bn` or `suspension`. Owner administration is a distinct
boundary. One person may hold multiple explicitly scoped grants if the owner
records conflicts and accepts that concentration of authority. The owner root
is not automatically a reviewer; use a separate reviewer identity/key. This
does not provide independent review by multiple people. Native Bangla
qualification, rights expertise and independence require human judgment.

| Research responsibility | Existing role | Relevant research decisions |
| --- | --- | --- |
| Metadata rights evidence | `source-rights` | `RESEARCH_METADATA_APPROVED` |
| Extractive summary and truthful classification | `english-editor` | `RESEARCH_EXTRACTIVE_APPROVED`, `RESEARCH_CLASSIFICATION_APPROVED` |
| Factual/source verification | `fact-checker` | `RESEARCH_FACTUAL_APPROVED` |
| Final content publication approval | `publisher` | `RESEARCH_PUBLICATION_APPROVED` |
| Native Bangla content, only when included | `native-bn` | `RESEARCH_BANGLA_APPROVED` |
| Withdrawal/retraction | `suspension` | `RESEARCH_REVOKED` |

Research grants use workflow `research` and exact intended source/item IDs;
English review uses `en`, native Bangla review uses `bn`. These roles preserve
the existing research stage requirements. They do not grant source licences.

```powershell
.venv\Scripts\python.exe -m pipeline.operations.onboarding reviewer --template english-editor
.venv\Scripts\python.exe -m pipeline.operations.onboarding schema reviewer
.venv\Scripts\python.exe -m pipeline.operations.onboarding reviewer --proposal 'C:\private\reviewer-proposal.json' --environment-id production --ledger-id YOUR-EXACT-LEDGER
```

Copy the template's **proposal object** into a private JSON file and fill it
according to the schema. Use the existing `Key` and `Grant` shapes. Include the
intended real identity, stable reviewer ID, exact sources and item IDs, permitted
decisions, language/workflow scope, public key/fingerprint, issuance, expiry,
revocation contact, conflict disclosure and digest of privately retained
acceptance/custody evidence. Invitations without actual acceptance remain BLOCKED.
Packets expire within 90 days; grants must fit within packet/key validity.
This preparation refuses wildcard item scope and role escalation. English and
native Bangla language restrictions use the existing authority validators.

PASS means the **unsigned preparation** is internally complete. The report
emits exact unsigned `enroll` and `grant` request objects accepted by the existing
`prepare-admin` flow. It does not write, sign, enroll or verify the claims. A
digest supplied by the caller is not authenticated consent. The owner personally
verifies acceptance, expertise, identity, conflicts and second-channel fingerprint;
the reviewer personally verifies role/scope and retains their encrypted key.
Enrollment/rotation requires the existing replacement-key possession proof.
The owner signs each exact request in a separately authorized ceremony, verifies
and records it, then refreshes independent checkpoint custody after completing
all appointments. Every administrative revision conservatively invalidates older
active content approvals. No filled invitation unlocks publication.

On reviewer credential loss, suspend the reviewer immediately; the owner revokes
or rotates the exact key before reinstatement and issues fresh bounded reviews
where required. Expiry and revocation remain enforced at use. A potentially
compromised owner key requires emergency suspension and reviewed recovery.

For an entirely synthetic rehearsal with published fixture keys and temporary
state, run `.venv\Scripts\python.exe -m pipeline.operations rehearse`. It exercises
appointments, scope/role refusal, signature verification, revocation, root
rotation and emergency freeze. It never creates production credentials or real
consent. Expiration and malformed/unsigned packet refusals are also covered by
the focused authority/onboarding tests.
