# Editorial authority: security model and offline operation

Status: **UNPROVISIONED**. This implementation does not appoint real reviewers,
grant reuse rights, activate sources, or authorize production. The canonical
edition remains unchanged. Synthetic examples establish software behavior only.

## Trust boundary and architecture

The trusted owner appoints reviewers after independently establishing their
identity, rights expertise, editorial role, or native Bangla qualifications.
Rights reviewers, fact checkers, English editors, native Bangla reviewers,
publishers and suspension officers have separate grants. Repository contributors,
CI jobs, source content, editable story fields and local ledgers cannot appoint
themselves. A compromised reviewer can misuse only their current scoped grant;
the owner can revoke it. The owner root is the administrative trust boundary.

Use Ed25519 through maintained `cryptography` and PyNaCl/libsodium libraries.
`cryptography` handles signing and encrypted PKCS8; libsodium performs strict
canonical prime-subgroup public-point checks and signature verification. A
neutral-point forgery probe exposed why accepting arbitrary 32-byte Ed25519
public keys is insufficient for this appointment protocol. There is no custom
curve arithmetic or cryptographic primitive. PyNaCl 1.6.2 includes its upstream
libsodium point-validation security fix; reassess locked crypto dependencies on
upgrade. Public keys are
SHA-256 identified; no algorithm negotiation or unsigned approval fallback exists.
A verifier receives an independently pinned owner public key; it never discovers
its root by trusting the registry it is checking. Default application operation has
no pin. Owner-signed administrative journal entries establish reviewer keys, grants,
rotations and revocations. Reviewer-signed entries extend the existing editorial
and translation lifecycles. Existing local draft ledgers cannot grant authority.

One bounded journal stores administrative changes, signed decisions and emergency
holds. A shared exclusive writer lock and atomic replacement avoid multi-file
transactions. An interrupted replacement leaves the prior complete journal or the
new complete journal. A stale lock requires human inspection; recovery never
silently discards denials, clears a lock, or promotes a partial journal.

| Mechanism | Guarantee | Boundary |
|---|---|---|
| Ed25519 | Exact payload was signed by the pinned key | Does not prove legal rights, human qualifications, custody or truth |
| Grants and scope checks | Only the appointed role/source/story/language can authorize an action | Owner appointment remains a real-world act |
| Signed hash-linked journal | Detects corruption, reordering, duplicate IDs and invalid transitions | Local append-only behavior cannot stop a filesystem administrator replacing the entire history |
| Independent checkpoint | Detects forks/truncation relative to the specific externally trusted head | Cannot detect a denial never included in that checkpoint |
| Protected external history | Can independently preserve a reviewed checkpoint | Not automatically configured, fabricated or implied by a local Git commit |

Publication requires an exact, fresh owner-signed checkpoint and its independently
trusted digest and per-publication challenge. These inputs must arrive through
operator-controlled configuration outside the repository. A checkpoint copied
alongside an old backup is not independently trusted. Missing, stale or mismatched
anchors deny activation. Authority expiry uses the verifier's current clock,
never the edition's editable generation timestamp. Reusing an old challenge or ignoring newer denials breaks
the operator's currentness assumption; no local hash chain repairs that mistake.
An attacker controlling both the OS user and the external trust inputs can defeat
this boundary. Signatures do not protect compromised executable/verifier code.

Lost reviewer keys are replaced by an owner-authorized rotation with possession
proof from the replacement key. Retired/revoked keys and old registry revisions
cannot reactivate approvals. Lost/compromised owner roots require an independently
verified recovery trust decision; an arbitrary replacement JSON file is not one.
History gaps or corrupt journals require trusted complete restoration and fresh
checkpoint verification. Authentic historical rights archives remain unavailable;
fixtures do not fill that evidence gap.

## Format choice

The protocol uses an intentionally restricted canonical JSON profile: ASCII
signed fields, explicit required fields, sorted ASCII object keys, no whitespace,
UTF-8, bounded nonnegative integers, and no floating-point numbers. Unicode story
and rights evidence is bound by exact SHA-256 digests, not reserialized as signed
prose. This is a specified subset, not an assertion of general RFC 8785 compliance.
Duplicate keys, alternate encodings, noncanonical JSON and unknown fields/versions
are rejected. Signing uses a fixed protocol/domain prefix and the entire typed
payload, including environment, policy, workflow, previous head and sequence.

This design avoids a hosted CMS, login service and new database. A hosted identity
provider could simplify accounts but adds availability, operating cost and remote
key custody. Plain hashes do not authenticate reviewers. An offline signed journal
fits a small static-first newsroom while keeping the trust and rollback limits
visible.

Primary references: [Ed25519 API](https://cryptography.io/en/stable/hazmat/primitives/asymmetric/ed25519/),
[key serialization](https://cryptography.io/en/stable/hazmat/primitives/asymmetric/serialization/),
and [RFC 8785 canonicalization considerations](https://www.rfc-editor.org/rfc/rfc8785.html).
Strict validation uses the [PyNaCl bindings](https://github.com/pyca/pynacl/blob/1.6.2/src/nacl/bindings/crypto_core.py)
and [PyNaCl 1.6.2 security update](https://pynacl.readthedocs.io/en/latest/changelog/).

## Normative format and policy

`pipeline/authority/protocol.py` contains strict Pydantic contracts. Export their
JSON Schema with `uv run python -m pipeline.authority schema --type envelope`
(`trust-pin`, `journal`, and `grant` are also supported). Validation also checks
semantic conditions not expressible in JSON Schema.

The signature input is exactly
`b"TECHLINE-TODAY\x00EDITORIAL-AUTHORITY\x00V1\x00" + canonical(payload)`.
The envelope has exactly `algorithm`, `payload`, `signature`, and `proof`.
`algorithm` must be `Ed25519`. Public keys are raw 32-byte Ed25519 keys and
signatures are 64 bytes, encoded as canonical unpadded base64url. Key IDs are the
lowercase SHA-256 of raw public-key bytes. Enrollment/rotation requires a second
signature over the same payload by the replacement private key. It does not
replace the current owner's administrative signature.

Every payload includes protocol/version, environment, ledger ID, policy version,
record ID, signer ID, key ID, issued/expiry UTC timestamps, exact sequence and
previous journal head. Decisions additionally include role, immutable grant ID,
registry revision, full binding, decision/from/to state, evidence digests and an
explicit nullable superseded decision ID. Bindings include source and story IDs,
source-derived kind, English-content digest, source-record digest, rights-policy
digest, language, translation digest and workflow. All fields are required;
`null` is allowed only where specified. Exact UTC whole seconds ending in `Z`
are required. A record may have one terminal LF; it is not signed or hashed.

The journal hash covers the canonical event object excluding `event_sha256`.
That object contains sequence, previous hash and the entire signed envelope.
The journal supports at most 2,000 events and 8 MB; a signed record is at most
64 KB. It refuses capacity overflow and never prunes history automatically.
Review decisions expire within 30 days; checkpoints within 24 hours. Positive
transactions must remain valid at ingestion, and active approvals are checked
again at publication. Historical signatures remain verifiable after expiration;
historical denials remain effective rather than expiring into permission.

| Role | Capabilities | Never inferred |
|---|---|---|
| Owner administration | Enrollment, grant changes, rotation, revocation, checkpoints | Editorial qualifications or publisher rights |
| Source rights | Rights decisions and rights lifecycle evidence | English quality, native Bangla or final publication |
| Fact checker | Recorded factual review | Reuse rights or publication |
| English editor | Draft/editorial lifecycle and English approval | Rights or native Bangla |
| Native Bangla | Translation preparation and native review | Final publication |
| Publisher | Publication and translation publication transitions | Native-language quality or rights |
| Suspension officer | Scoped denial, correction, withdrawal and retraction | Any positive approval |

Grants have explicit source IDs, story scopes (including an explicitly appointed
`*` story scope), languages, workflows, allowed decisions and validity periods.
There is no source wildcard or owner self-enrollment through a reviewer grant.
Administrative changes conservatively advance a global registry revision and
invalidate all older active approvals. Batch owner changes before review. This
deliberate small-team tradeoff requires fresh review after administrative changes;
it favors simple revocation correctness over automatic approval migration.

Existing Phase 6 draft ledgers remain preserved and cannot contain approvals.
`editorial_workflow.record_authenticated` and
`translation_governance.record_authenticated` append signature-verified extensions
using the same lifecycle edges; `source_onboarding.authenticated_review` projects
the same onboarding lifecycle without activating a source. The composite
publication gate independently checks current factual, English, rights, publisher
and relevant Bangla signatures against exact content and the anchored journal.
Editable story approval fields are ignored. Existing rights exclusions, source
holds, date checks, research classification and translation integrity still apply.
The content digest binds `{"story": STORY_WITHOUT_TRANSLATIONS, "cited_sources":
{SOURCE_ITEM_ID: COMPLETE_SOURCE_ITEM}}` using the existing deterministic evidence
serialization. Every cited source is included, not just the primary source.
`bind_story(..., sources=edition.sources)` is required for multi-source content;
missing, mismatched or substituted source identities fail closed. Changing any
cited evidence invalidates factual, editorial, rights and native-language reviews;
a rights-only reapproval cannot carry those older decisions forward. This
pre-release correction invalidates earlier Phase 8 binding hashes; there is no
production history to migrate or silently rebind.
Neither `require_approval=False` nor a signed editor decision bypasses rights.
Production verification also requires the explicit source configuration: disabled
or unknown sources and adapter/type relabeling are refused. Signed reviews never
enable a source. For new editions, preserved unsigned proposals can reconcile only
with signed source eligibility for the exact candidate digest/identity; historical
local suspension/revocation remains a blocker. Preserved draft notes do not grant
authority, and historical editorial/translation withdrawals cannot be erased by
returning an unsigned cache to a pending state. The legacy canonical exception
keeps its stricter existing refusals.

## CLI and publication behavior

Use `uv run python -m pipeline.authority COMMAND`:

| Command | Purpose |
|---|---|
| `status` | Explicit UNPROVISIONED/BLOCKED/VERIFIED identity-history status |
| `queue` | Local candidate story IDs and remaining independent review requirements |
| `inspect --story ID` | Provenance, source identity, rights state and exact version binding |
| `reviewers` | Current public key IDs, roles, scopes and revoked grants |
| `prepare` | Unsigned scoped decision against the current head and lifecycle state |
| `prepare-admin` | Unsigned owner administrative change from a typed JSON request |
| `prepare-checkpoint` | Unsigned checkpoint for an independently obtained publication challenge |
| `sign` | Sign an inspected payload using a protected encrypted external Ed25519 key |
| `verify --input FILE` | Independently verify a proposed signature, scope and transition without writing |
| `record --input FILE --confirm RECORD_ID` | Append the exact reviewed transaction; no activation |
| `history` | Verify and inspect administrative/decision history |
| `validate` | Require a current independently pinned checkpoint; exits nonzero if unavailable |
| `report` | Run the actual composite publication gate over the local edition |
| `hold --reason TEXT --confirm STOP_PUBLICATION` | Persist a global fail-closed stop without keys |
| `demo` | Ephemeral synthetic positive, version mismatch and revocation verification |
| `schema` | Export machine-readable contracts without provisioning anything |

Decision/administrative preparation and signing write only fresh files under
`.cache/authority/outbox/`; existing files are never overwritten. Signing/recording
requires an explicit matching record-ID confirmation. Private keys must be
encrypted PKCS8 files outside the checkout. Passphrases use `getpass`, never argv,
environment, JSON or logs. POSIX group/other key-file access is rejected.
Signing requires a private interactive terminal and refuses getpass's echoed-input
fallback. Key and trust paths must be regular files without linked/reparse parents.
Windows ACL correctness remains the operator's responsibility; no credential-vault
integration or reliable in-memory zeroization is claimed. No key-generation or
interactive production-provisioning command runs automatically.

Production loading uses operator-supplied `TECHLINE_AUTHORITY_TRUST_FILE` outside
the repository, `TECHLINE_AUTHORITY_CHECKPOINT_FILE`, independently trusted
`TECHLINE_AUTHORITY_CHECKPOINT_SHA256`, and `TECHLINE_AUTHORITY_CHALLENGE`.
The expected digest is SHA-256 of exact canonical checkpoint-envelope bytes
without the optional terminal LF. The challenge must be unique to the operator's
publication attempt and must not be learned from the untrusted checkpoint itself.
Loading a local file never establishes that independent provenance.

The default environment has none of these trust inputs. Full publication remains
blocked. The unchanged rights-reviewed legacy edition retains its narrow byte-hash
build exception; this does not make it approved current news. Authority history
matching a canonical story, malformed/unverifiable history, revoked sources or an
emergency stop blocks that exception. New live content uses the full authority
gate. Fixture builds cannot grant real authority; production refuses synthetic
pins even when an operator accidentally points at one.

## Revocation and recovery

Signed denials survive key retirement and later registry changes. Rights denial
persists for the exact story/source; source revocation blocks that source;
translation withdrawal blocks that story/language. Retraction/withdrawal blocks
the story across versions. Correction must name an exact prior decision and
supersedes that evidence version; a changed version starts a fresh lifecycle.
Registry revisions prevent reinstatement or key rotation reusing old approvals.
Returning to an earlier review stage supersedes later native/editorial/publisher
decisions; a fresh review cannot revive an old publication signature.
Revoked key and grant IDs can never be reused. No denial-clearing API exists.

Administrative/reviewer records are verified while holding the existing
`.cache/pipeline-writer.lock`, with the existing generation recovery barrier.
The supported build wrapper holds the same lock; only its matching read token
can inspect state under that lock. A caught replacement error leaves the old
complete journal, or (after replacement) the new complete journal. Always reload
the head before retrying a transaction whose outcome is uncertain. Temporary
files are not silently promoted. A killed writer leaves a lock for inspection.
Windows directory-fsync/power-loss durability is limited by the OS/storage; an
independent backup and checkpoint remain necessary.

The emergency stop uses an exclusive create; its existence blocks publication
even if a process is killed before the reason digest finishes writing. It
preserves the first stop and is never automatically cleared. New positive
journal decisions are refused while it exists; only denials and other
risk-reducing records may still append. It is a denial of service boundary, not
authenticated approval. Signed revocations remain available
without a fresh publication checkpoint; if credentials or history are broken,
use this stop first. Clearing a stop, a corrupt-history restore, or stale-lock
removal requires human investigation under the [owner runbook](PHASE8_OWNER_RUNBOOK.md).
A newer unanchored denial omitted by a malicious whole-history rollback is not
detectable from an older checkpoint. Acquire and preserve a genuinely current
external anchor before every publication; never describe local checks as complete
rollback resistance.
