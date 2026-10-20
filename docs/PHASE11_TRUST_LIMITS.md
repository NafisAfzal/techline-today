# Operational trust limits

The independent Phase 11 review corrects the earlier Phase 10 trust claims.
Production authority remains unprovisioned and publication remains blocked.

## What verification establishes

| Property | Evidence and limit |
|---|---|
| File corruption | Size and SHA-256 equality with a supplied manifest; an attacker can rewrite both. |
| Journal integrity | Canonical signed events, sequence, hash chain, context and replayed revocations. A complete older history can still be internally valid. |
| Checkpoint authenticity | An owner signature verified with the current root obtained by replaying the pinned history, including rotations. |
| Independent custody | Ordinary files, directories named protected history, and supplied digests do not authenticate an independently controlled custodian. |
| Freshness | Local expiry checks reject some stale inputs. Caller clocks, copied challenges and old digests cannot establish the independently current head. |
| Rollback after compromise | A separately trusted later checkpoint detects an older journal. Rolling back every local input together cannot be detected from those inputs alone. |

`LOCAL_SNAPSHOT`, `LOCAL_SIGNED` and `EXTERNAL_STORED` describe local evidence
and storage. `INDEPENDENTLY_AUTHENTICATED` and `CURRENTLY_TRUSTED` are reserved
for evidence the supported adapters cannot currently establish. Matching local
evidence returns `BLOCKED / independent_freshness_unverified`. No caller claim,
digest, timestamp or adapter label enables either higher level. Production
verification of the older Phase 8 anchor also refuses the missing property.
Explicit synthetic Phase 8 exercises authorize nothing.

Before future publication, a reviewed independent channel must authenticate the
custodian identity, exact ledger/environment and current retained head, bind a
verifier-generated unpredictable challenge to that head, and prevent replay
with state outside the compromised local boundary. Its trust root, clock
assumptions, retention and recovery procedures need independent verification.
This release supplies no such service and creates no external authority.

## Recovery boundary

Packs contain only allowlisted public journal/pin, policy and candidate-index
members. They omit the generated edition, retained licence bodies, translation
evidence, private keys and an independent current-state anchor. The inventory
describes assets needing separate recovery arrangements; it is broader than
the pack format.

Export and restore require a new destination and reject links, junctions,
reserved names, alternate streams and unexpected members before writing.
Manifest parsing, members, file counts and aggregate bytes are bounded.
Restore validates the complete pack before claiming the destination with an
exclusive directory creation. Existing or interrupted destinations are never
merged or overwritten. After interruption, inspect the partial directory and
use a new destination. No command promotes restored data into operational state.
An integrity-valid restored pack still needs independent trust verification.

These controls do not sandbox a hostile process with the same OS privileges.
Marker scans detect recognized encoded private keys, not every raw or obfuscated
secret. Windows ACLs, storage durability, off-machine custody and permanent loss
of an owner key require separate operational arrangements. The clean recovery
drill and lost-owner-key drill are BLOCKED for operational recovery. Synthetic
drill success is not recovery certification.

## Readiness evidence

Local observation hashes and `live` labels cannot prove seven genuine elapsed
days. Observation provenance remains INCONCLUSIVE. Historical rights policy
fields do not prove retained licence archives or authenticated human review;
that evidence remains INCONCLUSIVE too. Current-news coverage counts only live,
fresh, publication-eligible news, excluding research metadata and missing dates.
Translation age checks include every translation and reject future timestamps.
Unreadable candidate history and incomplete advisory records cannot become PASS.

Known licences remain scoped to particular metadata or documentation. Technical
API access, accessible terms and research dossiers grant no article, image,
AI-processing or production-activation permission. Source policy, appointments
and release authorization remain separate gates.
