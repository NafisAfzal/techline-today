# Phase 5 readiness plan

Phase 4 remains local and subject to independent review. This plan authorizes no source activation, rights approval, AI submission, scheduling, commit, push or deployment. The [Phase 4 handoff](PHASE4_ENGINEERING_HANDOFF.md) describes the implemented boundary.

The engineering continuation adds recoverable generation promotion, a shared build
lock, stricter XML/transport and retained-rights boundaries, manual observation
receipts and English dictionary payload reduction. See [local operations and
remaining editorial contracts](ENGINEERING_OPERATIONS.md). These changes also await
independent review; they do not close rights, native review or hosted evidence gates.

## Ordered dependencies

| Work | State | Prerequisite and acceptance |
|---|---|---|
| Review the complete local patch | READY | Review new files as well as the tracked diff against released main; reproduce isolated fixture checks and the unchanged canonical checksum. |
| Establish useful official-release coverage | BLOCKED_EXTERNAL | Resolve the exact item/field license, original creator, exceptions and required notices, then obtain separate activation authority. Public API access or a repository code license is insufficient. |
| Activate an affirmative rights-review route | BLOCKED_EXTERNAL | Authenticated reviewer authority, protected checkpoints, policy/source/item binding, expiry, revocation and rollback resistance require a reviewed design. The current local ledger accepts no affirmative approval. |
| Extend the public editorial contract | DEFERRED_WITH_REASON | Add explicit NEWS, OFFICIAL_RELEASE, RESEARCH, SECURITY_ADVISORY and EVERGREEN identities only with a schema migration and display/export tests. Current research/reference distinctions remain; security advisories and unapproved research-source observations stay local. |
| Preserve richer public date evidence | DEFERRED_WITH_REASON | Local diagnostics already separate publication, source update and release creation. A public schema migration must distinguish unknown timestamps, calendar dates, first observation, catalog addition and remediation deadlines without rewriting historical evidence. |
| Introduce reviewed Bangla stories | BLOCKED_EXTERNAL | Obtain a permitted corpus and a native reviewer. Define a real review state and canonical-content binding before presenting any translation as reviewed. Current labels distinguish English fallback, automated translation and synthetic examples. |
| Establish sustained collection reliability | READY for manual isolated work | At least seven days of bounded manual observations within the existing research scope, with outage/empty/429 classification and recovery evidence. Scheduling requires separate authorization. Store metadata, not publisher bodies or private approval records. |
| Complete accessibility validation | PARTIAL | Automated keyboard/axe/mobile checks are supplemented by NVDA/VoiceOver, physical touch-device and zoom review. Preserve the approved navy/teal/ivory design and current bundle budgets. |
| Prepare a noindex Cloudflare preview | BLOCKED_EXTERNAL | Exact reviewed revision, actual preview origin/account, free-plan and zero-spend evidence, valid content edition and explicit preview approval. Dry-run success does not close these gates. |
| Approve production | BLOCKED_EXTERNAL | Current permitted news, editorial review, source/item rights, translation decisions, sustained operations, hosted checks and a separately authorized release must all be satisfied. |

## Preview architecture and acceptance

Use the existing separate preview Worker name and static-assets configuration. Build with the approved preview origin and noindex enabled; retain restrictive CSP, nosniff, frame denial and HSTS. No preview token or private operational file belongs in static assets. Canonical URLs must match the approved origin, and untranslated Bangla story routes must retain their fallback canonical/noindex behavior.

Verify the generated `_headers`, immutable hashed asset caching, revalidated data/search assets, sitemap/RSS exclusion rules and custom 404 locally. [Cloudflare's static asset headers documentation](https://developers.cloudflare.com/workers/static-assets/headers/) describes the hosting mechanism; local preview tests do not establish actual CDN behavior. Run the existing nonpublishing `pnpm deploy:check`; do not invoke deployment scripts during preparation.

Before an eventual authorized preview, retain a manifest-bound known-good artifact and confirm the account's applicable [rollback behavior](https://developers.cloudflare.com/workers/versions-and-deployments/rollbacks/). Practice local restoration and compare snapshot/source/asset checksums. After authorization, verify real TLS, CSP, cache headers, noindex and rollback against the approved destination. No new source or AI setting changes as a side effect of a release.

## Safe continuation

Default source diagnostics are synthetic: `uv run python -m pipeline.source_diagnostics`. The optional `--live` flag performs bounded research observations; it is not a production ingestion or activation flag. Preserve report JSON and its matching Markdown digest before further observation. A left-behind writer lock after an abrupt termination must be inspected with process and report evidence; never remove it merely because it is old.

The general pipeline's custom snapshot destination accepts `.cache/source-review.json` or JSON files beneath `.cache/source-review/`, in addition to the canonical target. This destination option does not isolate all of the general runner's state writes. Use the dedicated diagnostics/staging commands for inactive sources and use an isolated checkout for fixture generation and browser tests. Never generate fixtures over an owner edition.

Allow roughly 4–8 focused engineering days for the remaining review and preview preparation after external inputs are available, plus at least seven elapsed days for sustained observations. A broader multilingual production candidate may require 8–15+ engineering/editorial days. These are planning estimates, exclude external waiting time and are not release commitments.
