# Authenticated Research Edition review

The Research Edition adapter uses the existing Ed25519 editorial authority,
owner trust pin, scoped reviewer grants, `.cache/authority/journal.json`, sticky
revocations, checkpoint verifier and composite publication gate. It introduces
no owner, signing keys, reviewers, rights grants or operational checkpoints.
`config/research-edition.json` remains publication disabled. The ordinary news
gate and synthetic rehearsal build retain their existing restrictions.

## Decision contract

`research-decision` is an explicitly typed extension of the existing envelope.
Historical `decision`, `admin`, `checkpoint` and binding wire representations
remain unchanged. Research grants must explicitly include the `research`
workflow and the relevant decision capabilities; existing grants do not acquire
those capabilities automatically.

Every research decision signs the canonical record ID, source registry identity,
exact source digest, full story and cited-source digest (including translations),
rights-policy evidence digest, metadata/extractive publication scope, reviewer,
role, grant, registry revision, authority and research policy versions, signing
key fingerprint, issuance/expiry, environment, ledger, journal position, evidence
references and optional superseded record. It also includes the complete signed
owner checkpoint payload, its signature and exact envelope digest. Evidence
references are SHA-256 digests; private evidence bodies never enter the journal.
Every positive stage must reference its bound source-rights digest.

| Stage | Existing authorized role | Human decision |
| --- | --- | --- |
| `RESEARCH_METADATA_APPROVED` | `source-rights` | Item origin, license, metadata reuse and allowed scope |
| `RESEARCH_EXTRACTIVE_APPROVED` | `english-editor` | Exact summary stays within permitted extractive scope |
| `RESEARCH_FACTUAL_APPROVED` | `fact-checker` | Claims, numbers, attribution and limitations match evidence |
| `RESEARCH_CLASSIFICATION_APPROVED` | `english-editor` | Research/reference classification, dates and reader framing |
| `RESEARCH_PUBLICATION_APPROVED` | `publisher` | This exact item/version/scope may enter Research Edition |
| `RESEARCH_BANGLA_APPROVED` | `native-bn` | Required separately when this version contains native Bangla |

The first five stages are ordered for every cited source. Bangla is a separate
language binding. Existing signed rights and editorial approvals remain mandatory,
as do source validation, date integrity, translation integrity and local editorial
withdrawals. No research decision converts research into current news or clears a
source hold. Changing content, dates, translations, source evidence, rights or
scope invalidates exact bindings. Administrative changes invalidate the prior
registry epoch; appoint the complete team before reviewing content.
When the publication scope includes Bangla, the rights reviewer and publisher
must each hold an explicit grant covering both English and Bangla. The native
reviewer's Bangla grant cannot expand another reviewer's publication authority.

## Offline operator commands

Use the locked environment (`uv sync --frozen`) in the isolated checkout. These
commands inspect or write private review documents only:

```powershell
uv run python -m pipeline.research_cli report --output .cache/authority/outbox/readiness.json
uv run python -m pipeline.research_cli inspect --story RECORD_ID
uv run python -m pipeline.research_cli blockers --story RECORD_ID
uv run python -m pipeline.research_cli packet --story RECORD_ID --output .cache/authority/outbox/item-packet.json
uv run python -m pipeline.research_cli demo
node scripts/research-inventory.mjs
```

The readiness report lists every missing/inactive stage, exact existing gate
failures, expired or revoked reviewer authority, superseded or mismatched
bindings, and independently recomputed checkpoint custody. Reports and packets
are unsigned diagnostics and are never accepted as decisions. Output commands
refuse overwrites and restrict files to the existing private authority outbox.
The JavaScript selector invokes Python for the exact current snapshot; absent
Python, malformed evidence or an unsigned cached report cannot select an item.

After real human provisioning and checkpoint review, the software interfaces are:

```powershell
uv run python -m pipeline.research_cli prepare --story RECORD_ID --source SOURCE_ITEM_ID --reviewer REVIEWER_ID --grant GRANT_ID --stage RESEARCH_METADATA_APPROVED --checkpoint SIGNED_CHECKPOINT_FILE --evidence RIGHTS_SHA256 --evidence REVIEW_EVIDENCE_SHA256 --output .cache/authority/outbox/unsigned-decision.json
uv run python -m pipeline.authority sign --input .cache/authority/outbox/unsigned-decision.json --key-file ENCRYPTED_EXTERNAL_KEY_FILE --confirm RECORD_ID_FROM_PAYLOAD --output .cache/authority/outbox/signed-decision.json
uv run python -m pipeline.research_cli validate --story RECORD_ID --input .cache/authority/outbox/signed-decision.json
uv run python -m pipeline.research_cli record --story RECORD_ID --input .cache/authority/outbox/signed-decision.json --confirm RECORD_ID_FROM_PAYLOAD
```

The existing signer requires a private interactive terminal and an operator-held
encrypted Ed25519 key outside the checkout. No key generation command is added.
Preparation does not assert that custody exists; production validation and
recording of positive research decisions remain blocked by the current custody
limitation. One transaction changes the journal head. Prepare a new checkpoint
and decision for the next transaction; never bulk-sign stale packets.

`supersede` accepts the same arguments as `prepare` plus `--supersedes OLD_ID`.
Re-review of an earlier stage withdraws downstream approvals and requires fresh
reviews. `revoke` requires a scoped `suspension` reviewer, `--supersedes OLD_ID`
and the same item/checkpoint/evidence arguments; it prepares `RESEARCH_REVOKED`
for the existing signer and validator. Record it through the same signed flow.
A signed research revocation denies every version/language of that story and
source, remains sticky after expiry and cannot be undone by an approval.
Risk reduction uses locally verified signed checkpoint position without claiming
independent custody. Existing owner-signed grant/key/reviewer/source revocations
and the emergency publication hold remain available through `pipeline.authority`.

## Checkpoint boundary

The embedded review checkpoint must describe the exact pre-decision journal
head, count, registry, environment and ledger. Its signature, lifetime, digest
and challenge are checked. A review challenge can occur only once in the signed
journal. Historical checkpoints are checked at issuance; newly submitted positive
decisions also require a checkpoint still valid at submission. The final
publication checkpoint must cover the resulting journal and use another challenge.

An owner signature, external file, copied hash, locally filled
`CURRENTLY_TRUSTED` label, or `independently-signed` custody claim does not prove
an independent custodian's current state. The existing production checkpoint
verifier deliberately refuses these. No current adapter establishes durable,
independently authenticated freshness or replay protection across production
publication sessions. The real gate therefore remains **BLOCKED**, with zero
approved canonical records. The synthetic demo establishes software behavior
only; it cannot provision production authority.

## Owner ceremony and reviewer onboarding

1. Owner verifies the frozen local revision and private validation evidence,
   unchanged 37-record canonical SHA-256, content scope and source-rights evidence.
   Resolve legal permissions per item with the actual rights holders as needed.
2. Owner chooses real custodians and an independent authenticated channel, confirms
   public key fingerprints out of band, and approves a separate implementation
   and security review of durable current-head custody, challenge consumption,
   clock/failure behavior and rollback protection. Local file attestation is
   insufficient. This workflow cannot complete that operational provisioning.
3. Humans establish the real owner root and encrypted external keys through the
   existing authority ceremony. Confirm owner identity and key custody personally.
   Owner signs enrollment with possession proof and narrowly scoped grants for
   the real reviewers, sources, canonical IDs, languages, stages and expiry.
   Complete all administrative appointments before content decisions.
4. Each reviewer verifies their fingerprint, role and scope, learns the unsigned
   packet/sign/validate/record sequence and reviews exact content and private
   evidence. A hash identifies evidence; it does not prove a permission or fact.
   Record explicit item decisions through the existing journal. A native Bangla
   reviewer must review any included Bangla version; automated status is insufficient.
5. After custody can actually verify current state, repeat item eligibility and
   all existing publication gates at a trusted current clock. Owner independently
   authorizes any later GitHub/publication destination and release. No push,
   PR, merge, deployment, source activation, AI enablement, ingestion schedule or
   external operational checkpoint write is part of this local software work.

Run the regression suite and synthetic demo after any verifier change. The demo
uses authored reserved-domain evidence and the existing published synthetic
drill keys in a temporary directory; no credentials or authority survive it.

For a full clean-checkout regression on Windows, create a fresh local worktree
at the reviewed revision and run [the validation script](../scripts/validate-research-approvals.ps1)
with `-AuditDirectory PRIVATE_EVIDENCE_DIRECTORY -CanonicalSnapshot PRIVATE_CANONICAL_SNAPSHOT`.
It verifies the canonical hash, runs the full test/build/browser/accessibility,
dependency, workerd and refusal checks, then restores the exact canonical copy
in that isolated checkout. It never changes the supplied private original.
