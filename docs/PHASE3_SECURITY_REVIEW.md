# Phase 3 local adversarial review

Scope: the new local governance ledger, fixture simulator and internal attribution contract. Production fetch/security mechanisms, public rendering, source rights, source enablement and editorial gates are unchanged. This is engineering verification, not an independent activation review or legal clearance.

| Threat | Boundary and verification |
|---|---|
| SSRF/private networks | No real transport exists in staging. Existing SafeFetcher rejects private redirect URLs and off-allowlist hosts before another request; fixture request logs contain only configured endpoints. Existing DNS-pinning tests remain in the full suite. No live DNS/TLS claim is made. |
| Redirect boundaries | Private, off-domain and looping redirects are explicit cases; redirect limits and original host restrictions remain intact. |
| Unsafe item/canonical URLs | Existing URL/model validation rejects unsafe schemes/private literals; item/source/canonical binding must reproduce the deterministic ID. External origin evidence is held, never permission to fetch or publish. |
| Template origin manipulation | Malicious template literal host produces invalid/quarantined records; existing origin pinning is retained. The earlier same-origin encoded literal path refinement remains optional and unmodified. |
| HTML injection | Existing normalization strips active markup; no bodies are stored; contract fields use existing text validation; public rights checks reject the internal contract. |
| Malformed CVEs | Existing strict ASCII full-string validation rejects before URL synthesis and normalization; local malformed-CVE case produces zero valid advisory records. |
| Excessive response size | Existing 3 MB cap rejects synthetic oversize responses; 5,000-entry RSS and 4,000-record JSON exercises retain only configured 20/30 items. |
| XML parser abuse | Existing preparse DTD/entity rejection tested with UTF-8/UTF-32 fixtures, plus the full earlier encoding/bounded-XML suite. |
| JSON parser abuse | Local preflight rejects duplicate keys, nonfinite constants and nesting beyond 32; ledger input is bounded, duplicate-key-rejecting and schema-validated. The stricter fixture wrapper is not a production adapter change. |
| Date ambiguity | Review timestamps require explicit ISO time/timezone; integers, bare dates and naive times reject. Future source times remain flagged unknown. KEV dates remain date-only, never publication/disclosure timestamps. |
| Duplicate identifiers | Deterministic dedupe tested against reversed input; review evidence remains distinct even when display dedupe collapses shared GUIDs/CVEs. |
| Rights approval forgery | Unsupported affirmative states/extra grant fields reject, even with a recomputed event hash. There is no active approval path or production ledger consumer. |
| Queue poisoning | Original observation queue guards remain covered; the new operator ledger is separate and never imports feed decisions. Corrupted chain, head, sequence, content binding and duplicate JSON keys reject. |
| Stale/revoked review | Missing, expired, future, policy-changed, mismatched and revoked records deny. Same-domain different items do not inherit review. |
| Cross-source contamination | Source ID, item ID, canonical URL and content hash must agree across normalized item, binding, registry and optional decision. |
| Snapshot poisoning/publication | Canonical hash invariant checked per run; existing Python snapshot and JavaScript content-rights gates reject local pilot evidence/contracts. No public input/import path was added. |
| Partial writes/concurrent writers | Exclusive ledger lock, validate-under-lock, atomic replacement and capacity limits. Interrupted replace preserves the previous report; no partial files become input. |
| Interrupted collection | Stateless fixture rerun reconstructs a complete report; leftover temporary files are ignored. Canonical content never participates in commit. |
| Source outage | Partial/total synthetic outages remain visible per source; no empty canonical replacement and no falsely fresh publication. |
| Accidental AI submission | No router/provider is instantiated; regression sets the global AI flag true and makes real transport/provider construction fail if attempted. Rights evaluation still denies AI. |
| Local path redirection | Writes require `.cache/phase3` containment and reject traversal, symlinks and Windows junctions, including an actual linked-directory fixture. |

## Confirmed issues corrected during this execution

Hosted clean-checkout testing exposed two Phase 2 tests depending on ignored owner data. They now use isolated synthetic snapshots; the correction passed clean local and hosted suites before merge.

Prototype verification caught platform newline accounting in storage measurement and an ambiguous review timestamp conversion. Byte measurement now accounts for the actual newline convention; review timestamps reject implicit numeric/date-only conversion. The local JSON preflight explicitly rejects ambiguous duplicate keys and excessive depth. New assertions exercise these failures without weakening mature validation.

## Residual risks and limits

The ledger is not authenticated or tamper-proof: a same-user writer can recompute hashes or roll back a complete valid ledger. The inactive approval path makes those attacks unable to authorize reuse. A future active pathway requires authenticated reviewer authority, protected external checkpoints, policy/version migration, revocation propagation and independent review. A reviewer name alone is not identity proof.

File containment checks assume the local account is trusted against concurrent path replacement. They are not a sandbox against a malicious same-user process. All writes remain local and nonpublishing; production must not be connected to this state without a reviewed trust design.

Fixtures do not verify publisher rights, real creator identity, live feed reliability/304 support, actual network latency, hosted memory, physical devices or Cloudflare behavior. Global source rights, item approval, AI, schedules and public publication remain blocked. See the [readiness gaps](PRODUCTION_READINESS_GAPS.md).
