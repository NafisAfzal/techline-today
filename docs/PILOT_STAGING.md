# Reproducible local pilot staging

Run the disabled pilots against synthetic fixtures:

```powershell
.venv/Scripts/python.exe -m pipeline.pilot_staging
```

Output: `.cache/phase3/staging/report.json`, plus a synthetic item binding and pending-review example. Use `--scenario normal` for a short single case or `--as-of 2026-10-16T12:00:00+00:00` for an explicit synthetic clock. The default clock is fixed for reproducibility. There is no live mode, arbitrary endpoint option, approval option or publication command.

The report and CLI expose `status`, aggregate `outcome`, and each source's identity, attempted flag, status and error category. Outcomes distinguish `success`, `empty`, `partial_degradation` and `total_failure`. Nominal runs require both sources to process records; any unexpected required-source failure makes the CLI exit 1. Partial results are retained only for diagnostics. Each deliberate outage/attack case passes only when the expected source, status and error category match; a different failure cannot masquerade as an expected refusal. The normal scenario controls aggregate health when included. Legitimate empty feeds have their own scenario and outcome. Configuration refusals exit 1; invalid arguments exit 2.

Rights rejection is a completed collection with a negative policy result, not an empty or failed fetch. Held Kubernetes observations retain their rejected review state. Guarded CISA rejections use a typed normalization refusal and a separate `rights-rejected` source status/count; malformed data remains invalid/quarantined. Neither route permits publication.

## Isolation

The simulator explicitly invokes the configured disabled adapters through `httpx.MockTransport`, existing `SafeFetcher`, normalization and deduplication. It never changes `enabled` flags, rights policy or production collection. It refuses if either pilot becomes enabled, allowed or AI-submission-enabled.

Canonical snapshot/run report, source/rights/release/AI configuration, workflows, lockfiles and deployment configuration are hashed before and after. Any change aborts the run. Results are metadata and internal contracts; titles, excerpts, article bodies and third-party linked text are not persisted. Synthetic full response bodies exist only in memory.

Every result denies publication and AI. Production does not import the simulator, operator ledger or internal attribution contract. The existing snapshot and JavaScript rights gates also reject the local pilot evidence. Setting `PIPELINE_AI_ENABLED=true` cannot instantiate an AI provider or real HTTP transport in this tool; regression tests exercise that condition.

## Evaluation cases

Twenty-five cases cover normal RSS/JSON, bounded volume, partial/total outages, retry, conditional response, oversized response, private/off-domain/looping redirects, DTD/entity XML including UTF-32, malformed/duplicate-key/deep JSON, malformed CVEs, unsafe item URLs, URL-template origin manipulation, HTML injection, distinct forged feed approval, empty feeds, bounded timeouts, malformed XML, reordered feeds and rights rejection.

Normal fixtures include duplicate IDs, distinct observations sharing GUIDs, stale records and a future timestamp. The reordered case reverses the original response before adapter selection. Separate seeded permutation tests compare complete normalized outputs across truncation boundaries. Review observations survive display-level deduplication. KEV remains date-only advisory intelligence, outside current news.

RSS and JSON selection scans the bounded fetched response before applying the configured 20/30 retention cap. Supplied timestamps sort newest first; missing/malformed timestamps sort last; URL and payload digest break ties. Deduplication also resolves identical-ID/content ties by complete serialized metadata. XML scanning remains byte-bounded and expensive feedparser work remains entry-bounded. Malformed XML now fails collection rather than using partial recovery. `post_selection_dedupe_stable` describes the specific runtime assertion. Completeness covers only fetched response entries and the retained newest subset, before downstream freshness/rights validation. Unseen API pages, upstream feed truncation and records beyond the retention budget are outside the guarantee. No historical crawl or pagination was added.

The volume fixture contains 5,000 RSS entries and 4,000 JSON records. The configured 20/30 item limits bound retention. The existing 3 MB ceiling bounds each response. Oversize and hostile cases must fail or quarantine; their failures are expected scenario results, never permission to weaken validation.

Local JSON preflight rejects duplicate keys, nonfinite numbers and excessive nesting before the existing JSON adapter. This wrapper applies only to the simulator. It does not claim the production adapter has gained that stricter contract. Production parsing remains bounded and publication-blocked; any future adapter hardening needs separate review.

## Measurements and reproducibility

The report separates deterministic observations/contracts/outcomes from variable measurements. It records a SHA-256 of the deterministic section, actual fixture response bytes and requests/statuses, normalized/invalid/duplicate counts, parser time, fixture fetch time, normalization time, throughput, evaluation runtime, traced Python allocation peak and exact report file size. `total_seconds` measures simulation evaluation after configuration loading and before report persistence; it includes fixture generation and retry/rate-limit waits, but excludes imports and file writes. The newline convention of the operating system is included in the on-disk byte count.

Fixture fetch time includes existing retry/rate-limit waits. Parser time includes local JSON security preflight. Throughput is a small synthetic benchmark, not a production capacity estimate. Tracemalloc covers Python allocations, not total process RSS or a hosted runner's memory.

Synthetic 304 responses prove conditional-request handling only. They do not measure Kubernetes/CISA ETag support, live 304 rate, bandwidth, TLS, DNS, latency, quotas, availability or publisher feed freshness. No live requests were used in this execution. Historical live measurements in the earlier audits remain historical.

Rerunning unchanged inputs preserves deterministic results and IDs. Runtime/memory naturally vary. The latest report always records its verdict, including failures. `last-successful-report.json` retains the last verified run separately and is never consumed as current collection evidence. Interrupted temporary files are ignored; a subsequent complete run reconstructs the report. Failed atomic replacement preserves the previous completed report. No interrupted simulation can replace the canonical edition. Retries retain the existing three-attempt fetch budget and 120-second adapter deadline. See the [corrective handoff](PHASE3_CORRECTIVE_HANDOFF.md) for current evidence.

## Verification

```powershell
.venv/Scripts/python.exe -m pytest -q pipeline/tests/test_phase3_governance.py pipeline/tests/test_phase3_staging.py
.venv/Scripts/ruff.exe check pipeline
```

The tests cover failed writes, source isolation, unsafe/ambiguous input, conditional/retry behavior, deterministic reruns, no live transport or AI calls, retained item limits, accurate attribution fields and rejection by the existing JavaScript publication gate. See the [engineering handoff](PHASE3_ENGINEERING_HANDOFF.md) for the final measured run and full-suite results.
