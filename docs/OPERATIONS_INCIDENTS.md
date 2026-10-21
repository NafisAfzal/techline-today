# Newsroom incident actions

These are human-operated procedures, not automatic grants or recovery promises.
Use the [offline console](OFFLINE_NEWSROOM_OPERATIONS.md) and [existing authority runbook](PHASE8_OWNER_RUNBOOK.md).
Do not publish while the relevant evidence is missing or conflicting. Keep raw
signed records, receipt hashes, logs and timestamps privately; do not put source
bodies, credentials or incident evidence in the public build. Never delete an
incriminating record to make verification pass.

| Incident / detection | Immediate containment and evidence | Verification and human decision | Recovery and closure |
|---|---|---|---|
| Suspected reviewer compromise: unexpected signed decision or fingerprint | Freeze publication; preserve envelopes, registry revision and independent checkpoint | Replay exact key/role/scope/time and revocations. Owner establishes whether the key is compromised | Owner-controlled revocation/rotation and fresh scoped reviews; close only after current independent evidence and affected approvals are reconciled |
| Wrong-source approval: source binding differs | Hold the story and retain both source digests | Check source identity, content, evidence and signed scope; qualified rights/editorial reviewers decide | New exact-bound decisions; old approval cannot transfer; gate must reject the old binding |
| Ledger rollback: event count/head/revision regresses | Freeze, stop writers and preserve journal/receipt copies | Compare independently held current receipts and backup manifest without replacing history | Human-authorized isolated recovery; close only with reconciled current head, never a local flag |
| Missing independent checkpoint: freshness unavailable | Keep publication blocked; retain request, nonce, receipt and failure times | Distinguish outage, stale response, wrong key and custodian conflict | Restore the independently authenticated channel or remain blocked; local mock receipts cannot close the incident |
| Rights withdrawal: publisher notice or revoked grant | Hold affected stories and sources; preserve notice provenance | Qualified reviewer verifies scope, effective date, text/image/AI obligations | Authorized revocation/correction/removal workflow and fresh checkpoint; close after affected publication eligibility is denied |
| Feed poisoning: unexpected source identity or hostile metadata | Stop collection for that source; retain bounded diagnostics and digests | Check allowlisted hosts, redirects, MIME, size, schema and attribution; investigate publisher identity | Fix the narrow defect and replay synthetic failure tests; human authorizes any later collection |
| Malformed response: parser/schema/encoding failure | Keep last good edition; preserve status/error categories without retaining unlicensed bodies | Reproduce with a bounded synthetic payload; distinguish publisher drift and parser defect | Targeted parser test and validated fixture; no source activation or rights inference |
| Unauthorized editorial mutation: local state differs from signed journal | Freeze and preserve files before repair | Replay journal signatures, chain, scopes and current revocations; assess compromised access | Human-authorized recovery to isolated destination and new exact-bound reviews; no hand-edited approval flag |
| Stale Bangla translation: source or translation digest changed | Block Bangla publication; retain honest English fallback | Compare version/evidence/language bindings and native-review scope | Authorized native review of the exact new translation; text generation alone cannot close the incident |
| Source API unavailable: timeout, DNS, 429 or outage | Keep source disabled/held; preserve attempt/status/timeout observations | Respect rate limits; distinguish local failure and publisher outage without repeated live polling | Bounded retry after permission and verified recovery; backlog/freshness labels remain honest |
| Emergency freeze: stop marker or credible risk | Preserve the hold, stop publication and preserve signed state | Identify cause and affected scope; independent human verifies containment | Owner-controlled release of hold after verification; never remove a marker merely to pass a test |
| Failed build: schema, provenance, rights or browser gate red | Publish nothing; retain failing logs/build identity and last good artifact | Reproduce from the same committed source and documented fixtures | Narrow fix, full affected gates and new exact-SHA approval before source publication |
| Dependency advisory: scanner or publisher notice | Preserve advisory/version/lock evidence; do not suppress the check | Determine affected path, reachability and official patched release; respect reassessment dates | Narrow compatible patch and tests, or explicit documented unresolved risk; no unauthorized alert dismissal |
| Accidental private-data exposure: scanner finding or visible artifact | Stop distribution; preserve hashes privately and restrict exposure using authorized controls | Determine actual secret vs literal fixture marker; owner/security assesses recipients and revocation | Owner-controlled credential revocation if needed, corrected artifacts and independent scan; never claim deletion guarantees recall |

For restore preparation use `uv run python -m pipeline.recovery inventory` and
`uv run python -m pipeline.recovery verify --help`. The verifier does not grant
production currency. Keep restores isolated from real authority/journals and
require an independently authenticated expected checkpoint. Rehearse with
`uv run python -m pipeline.operations recovery`; never exercise destructive
recovery against an operator's real journal or key backup.
