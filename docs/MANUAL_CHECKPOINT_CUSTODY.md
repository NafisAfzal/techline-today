# Independent checkpoint custody: manual exchange

This is a production adapter for the existing signed current-head protocol. It
creates no identity, key, reviewer, publisher permission or deployment. Current
production authority stays blocked until a human completes an independent
custodian ceremony and configures authentic public pins. Do not run a real
ceremony or transfer production checkpoints under the local launch program.

## Selected architecture and actual independence

Use a trusted person operating a separate device, account, encrypted Ed25519
key and durable custody database. That person authenticates the owner and
custodian public fingerprints over a separate channel, verifies the complete
signed journal and retains each accepted checkpoint before releasing a signed
response. The operator cannot administer that device, replace its retained
history, retrieve its private key or authorize its recovery. Both people must
independently check UTC against an authenticated time source before a ceremony.
This is a human trust prerequisite; a label, checkbox or local file cannot prove
it. A single person controlling both devices must declare the missing
independence and must not provision this adapter as independent custody.

| Option | Independence, freshness and recovery | Cost and choice |
| --- | --- | --- |
| Independent signed receipt service | Separate administration and durable monotonic state can answer fresh challenges automatically. Requires authenticated server/key lifecycle, secure clock, transactional persistence, monitored backups and incident handling. | Hosting may be cheap; operation adds work. Deferred. No service is created. |
| Separate owner-controlled storage | Different storage location or account alone cannot answer an authenticated current-head challenge. Immutable retention helps historical continuity but does not prove currency. Shared administrator credentials defeat independence. | May be low cost; unsupported as a current-state oracle. |
| Independent human custodian | Separate operator, key, retained state and clock; manual signed challenge responses. Availability depends on the person. Lost state, uncertainty or expired responses stop the operation. | Existing separate equipment and human time; selected for the small newsroom. |

Neither a second folder, local clone, GitHub history nor a copied digest is
independent current trust. SQLite supplies local crash and concurrency safety;
it does not authenticate the operator's machine or protect against a malicious
administrator. Custodian honesty, key custody, clock and retained state remain
explicit external assumptions. No network connection is needed by this adapter.

## Wire and implementation contract

`pipeline.operations.custodian` retains the existing v1 Receipt, Commitment,
canonical JSON, Ed25519 domain and verifier conventions. There is no replacement
authority ledger, owner registry or publication engine. The manual adapter
requires the `CurrentChallenge` extension in
`pipeline.authority.manual_custodian`:

- Existing custodian/environment/ledger/nonce, current registry revision,
  minimum event count, issuance and expiry.
- `adapter=manual-independent-v1`, owner identity and current owner key fingerprint.
- Strictly increasing `checkpoint_revision`, predecessor checkpoint digest,
  predecessor journal head and event count.

The unchanged signed Commitment binds the entire extended request through
`request_sha256`, and binds the exact signed owner checkpoint through
`checkpoint_sha256`. The owner checkpoint binds current owner identity/key,
environment, ledger, journal head/count, registry revision, challenge nonce and
validity interval. A receipt cannot substitute any of these fields. A plain v1
mock challenge lacks the required extension and is refused by this adapter.

The custodian must inspect the full request, verify the complete owner journal
and current root rotation history, compare the predecessor with its independent
database, and reject conflicting heads, skipped revisions or a rollback. It
must durably retain the accepted receipt and checkpoint before exporting the
response. `respond` implements that order. Challenges last at most 120 seconds;
expiry includes key-unlock time. Start again after an expired exchange through
the reviewed recovery procedure; do not extend timestamps or disable checks.

The live `run` process creates a new challenge itself, retains the expected
nonce in memory, exports it and waits at most 120 seconds for the response.
There is no standalone resumable challenge CLI. `consume`
requires the live caller's expected nonce; it never learns that value from a
checkpoint, receipt or restored pending state. Restoring an old pending client
database and old valid receipt cannot choose the current process's nonce, even
while the old receipt is still within its validity window.

The client atomically consumes this request before starting one explicit local
command. SQLite `BEGIN IMMEDIATE`, `synchronous=FULL` and integrity/schema
checks serialize duplicate responses. Success advances the checkpoint floor and
archives the independent receipt; failure consumes the request and freezes the
exchange. A duplicate response freezes the state, including an existing lease.
Replacing a pending, unanswered client challenge invalidates the older nonce.

An unpredictable operation token exists only in memory and the child process
environment. Only its digest is stored. Production `load_authority` and
`verify_anchor` revalidate the receipt, owner signature, exact current journal,
expiry, pin and active lease each time. Repeated verification within that command
works; another command requires a new exchange. The wrapper closes the lease
even when the child returns an error. Tokens are never printed or put in argv.
Do not run untrusted child code or expose its environment to another user.

Historical research decisions require the archived independent receipt at the
decision's signed issuance time. Replaying an old journal does not demand that
an old receipt remain fresh today. New positive decisions require a current
lease; the final publication checkpoint must cover the resulting journal and
use a fresh nonce. Missing historical archives fail closed. Risk-reducing signed
research revocation retains the existing local verification path.

## Human ceremony inputs

Use public JSON `CustodianPin` outside Git and outside the custody database. It
contains `version=1`, `adapter=manual-independent-v1`, custodian identity and
existing Ed25519 `Key`, owner identity, ledger/environment, and
`owner_pin_sha256`: SHA-256 of the canonical parsed owner TrustPin JSON, without
a terminal LF. Inspect the schema locally:

```powershell
py -3.12 -m uv run python -c "import json; from pipeline.authority.manual_custodian import CustodianPin; print(json.dumps(CustodianPin.model_json_schema(), indent=2))"
```

The owner and custodian must personally authenticate identities and consent,
compare fingerprints through an independent channel, confirm empty genesis on
both devices, check key encryption/backup, test restore and independently check
UTC. A typed name does not establish human identity. Use the existing owner
ceremony and encrypted PKCS8 signing guidance. Custodian key creation is a
separately authorized human act; this adapter never generates a key.

Do not keep pins, state, checkpoints, receipts, keys or operational reports in
the repository, Astro content, public assets or a synced folder administered
by the other party. The two state files below must be on different independently
administered devices. Their different example filenames do not establish that.
No existing state file is overwritten. Genesis is never a recovery mechanism.

## Separately authorized operation on Windows

These are instructions for a future real ceremony, not actions performed during
local development. Run from the project root. On the independent device, use
the reviewed exact source SHA and its own retained journal/history and owner
public pin. Transfer only public signed evidence through an authenticated
channel approved by both humans. No automated transfer is implemented.

Set the existing `TECHLINE_AUTHORITY_TRUST_FILE` on each device to its separately
authenticated owner public pin. Set custody pin/state environment variables when
inspecting historical journals outside the wrapper; these permit historical
inspection and do not grant a live lease:

```powershell
$env:TECHLINE_CUSTODIAN_PIN_FILE = 'C:\PrivateCustody\custodian-pin.json'
$env:TECHLINE_CUSTODIAN_STATE_FILE = 'C:\PrivateCustody\client.db'
```

1. After both humans verify genuinely empty genesis, initialize each device's
   own database once. Confirm the exact intended ledger ID:

```powershell
py -3.12 -m uv run python -m pipeline.checkpoint_exchange --pin C:\PrivateCustody\custodian-pin.json --state C:\PrivateCustody\client.db initialize --confirm-genesis EXACT_LEDGER_ID
```

2. Arrange both people's terminals and authenticated transfer channel before
   starting. On the operator device, start the live session using three fresh,
   absent file paths. The process prints its nonce and waits for the owner
   checkpoint and custodian receipt. This example will inspect status after the
   response; a separately authorized decision or build supplies that command:

```powershell
py -3.12 -m uv run python -m pipeline.checkpoint_exchange --pin C:\PrivateCustody\custodian-pin.json --state C:\PrivateCustody\client.db run --challenge-output C:\PrivateCustody\challenge-001.json --checkpoint C:\PrivateCustody\owner-checkpoint-001.json --receipt C:\PrivateCustody\receipt-001.json -- py -3.12 -m uv run python -m pipeline.authority checkpoint-status
```

3. While that process remains running, in a second terminal the owner personally
   prepares and signs the existing owner checkpoint with the returned nonce,
   using the existing authority CLI and encrypted key.
   Preparation, signing and transport are human-controlled steps. Transfer the
   challenge, signed owner checkpoint and complete latest signed journal to the
   independent custodian. Preserve the original authority outbox evidence.

4. The independent custodian personally verifies the full journal, identity,
   fingerprints, root rotation, checkpoint/head, predecessor and UTC. Compute
   SHA-256 of the exact canonical challenge file. On that device, sign using its
   existing protected encrypted key and its independently retained database:

```powershell
py -3.12 -m uv run python -m pipeline.checkpoint_exchange --pin C:\PrivateCustody\custodian-pin.json --state C:\PrivateCustody\custodian.db respond --challenge C:\PrivateCustody\challenge-001.json --checkpoint C:\PrivateCustody\owner-checkpoint-001.json --key C:\PrivateCustody\custodian-encrypted.pem --confirm-request EXACT_CHALLENGE_SHA256 --output C:\PrivateCustody\receipt-001.json
```

5. Return the retained signed receipt through the agreed independent channel.
   Materialize the complete canonical checkpoint and receipt at the watched
   paths on the operator device. Transfer to temporary `.incoming` names first,
   then rename the completed files on the same filesystem, so partial transfers
   are not mistaken for complete responses. The still-running session verifies
   its own in-memory nonce against the response and the reread current journal,
   consumes it once, runs the explicit command, then closes the lease. If it
   expires, discard that exchange for live use and start a new live session with
   new filenames; never restart using a saved pending nonce or receipt.

A separately authorized local research decision or build uses the same wrapper
with that explicit command. A successful receipt authenticates current custody;
it is never an item approval, publisher right, deployment approval or permission
to execute an external mutation. The wrapper accepts explicit argv without a
shell. Operators remain responsible for choosing an authorized command. A saved
challenge cannot be resumed as a trusted live operation. Commands
whose authorization check occurs after expiry are refused. Do not persist or
manually reuse `TECHLINE_CUSTODIAN_RUN_TOKEN`.

## Failure, recovery and rotation boundaries

Unavailable custodian, interrupted transfer, stale response, wrong environment,
forged key/signature, wrong head/registry, unknown key rotation, source journal
rollback, incomplete archive, corrupted database, emergency STOP and backwards
clock all refuse current trust. There is no network fallback or trust-on-first-use.
No alternate folder, old receipt, auto-recreated database or reduced check is
accepted. The existing STOP mechanism remains available without credentials.

If a process dies after consuming a receipt, its lease remains active and blocks
another request. If power/storage failure damages SQLite or loses the archive,
verification blocks. Windows/storage power-loss durability is not guaranteed by
this program; retain independently protected backups and receipt history. A
client backup restored behind the independent custodian is detected by the next
predecessor check. A backup of both devices under one administrator defeats the
independence assumption.

The adapter detects rollback only below heads actually retained by the independent
custodian. A local revocation, withdrawal or STOP rolled back before the
custodian sees it is undetectable from older evidence. Existing `append` returns
a local journal result, **not an independent acknowledgment**. After every
authority mutation, retain the complete new signed head with the custodian and
obtain a post-mutation checkpoint/receipt before treating the operation as
operationally completed. Do not publish while acknowledgment is pending. For
STOP, immediately contact the custodian through the agreed authenticated channel,
activate its own independent STOP and obtain human acknowledgment before any
further response. The adapter checks that device's STOP before signing and
acceptance; it cannot deliver the notification. Uncertain, unacknowledged or
potentially lost mutations require independent suspension and reconciliation.
The custodian must refuse to attest an older head merely because the client
supplies a self-consistent older journal. This acknowledgment and notification
discipline is an external trust requirement; automatic cross-device mutation
acknowledgment is not implemented.

Lost key, frozen exchange, interrupted active lease, divergent heads, lost state,
custodian key rotation and nonempty genesis migration require a new documented
human recovery ceremony. Automatic reset/rotation and nonempty state import are
deliberately unsupported. Preserve both devices' state and archives, invoke STOP,
authenticate the most recent independent retained head, reconcile all receipts,
verify journal continuity and agree a separately reviewed migration before
resuming. Never initialize an empty replacement against an existing custodian
history. A custodian losing both key and independent state cannot prove the old
current head; do not claim software can recover that trust. Existing signed owner
root rotation is supported through journal replay; custodian-key changes are
refused until separately authenticated migration.

SQLite state is capped at 4 MB and the authority journal retains its existing
capacity limits. Plan reviewed archival/migration before either cap; capacity
failure does not authorize truncation. A malicious local administrator, dishonest
custodian, compromised independent clock or simultaneous rollback of all trusted
external state lies outside the guarantee. Signatures cannot prove unreported
events or prevent a trusted human from withholding a later head.

## Local proof

`pipeline/tests/test_manual_custodian.py` uses temporary public synthetic fixture
keys and production-shaped messages. It covers real loader integration,
single-use leases, duplicate concurrent response, request replacement, forgery,
cross-environment/ledger/owner context, registry/head conflict, expiry, clock
regression, durable floors, predecessor rollback, independent retained-state
rejection, historical research replay, STOP, key rotation refusal and missing or
corrupt state. Synthetic success never supplies real custody or public content.

```powershell
py -3.12 -m uv run pytest pipeline/tests/test_manual_custodian.py pipeline/tests/test_phase10_checkpoint.py pipeline/tests/test_phase12_operations.py pipeline/tests/test_research_approval.py
```
