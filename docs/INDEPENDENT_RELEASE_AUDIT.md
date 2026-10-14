# Independent release audit ? 2026-10-14

> Historical evidence from the earlier pass. [Current verification](PUBLIC_RELEASE_VERIFICATION.md), [independent re-review](PUBLIC_RELEASE_REVIEW.md) and the [A–T owner handoff](PUBLIC_RELEASE_PREPARATION.md) supersede earlier counts/readiness claims. Public GitHub and Cloudflare Free are confirmed preferences; actual publication remains unauthorized.

A separate reviewer context inspected sources and controls without relying on implementation claims. It made no edits, ingestion, builds, external publication, credential access or schedule changes. The implementer fixed findings; the reviewer rechecked revised sources and adversarial cases.

| Finding | Original severity | Resolution |
|---|---|---|
| Stale assets/new snapshot could pass publication; modified local checkout could claim approved HEAD | P1 | Build manifest binds actual revision, relevant source bytes, snapshot, monthly/yearly inputs and complete assets. Verification rejects mismatches; release requires a clean checkout and actual HEAD. |
| Any positive AI budget could enable unmetered production inference | P1 | Production inference is rejected regardless of a nominal budget until model-specific monetary enforcement/durable quota accounting is reviewed. Defaults remain off. |
| Evicted publication cache silently discarded history | P1 | Cache misses block collection. First-ever seed needs plan approval and a default-false manual dispatch input. Revoke seed authorization after first publication and review the new revision. |
| Annual archive indexes excluded; malformed archived data could pass checksums | P1/P2 | Monthly/yearly files are allowlisted and required; monthly evidence contracts and annual month/count identity are validated before restoration. |
| Local repository visibility had no evidence | P2 | Missing actual visibility fails closed; approved local publication requires real GitHub metadata. No credentials are used while approval is absent. |
| Invalid summaries bypassed per-run candidate limit | P2 | Reserve each candidate before processing, including failed validation; targeted regression preserves the cap. |
| Methodology advertised a four-times-daily schedule before activation | P2 | Cadence-neutral English/Bangla wording now says periodic collection. |

Independent checks: 33 release/editorial Vitest assertions, 23 Python mock/config/ranking checks and six locale/browser mobile-search cases passed. Open search dialogs had no axe violations across Chromium, Firefox and WebKit; focus and scrolling returned after closing a reduced viewport. In-memory adversarial cases verified archive-input provenance and archive contract rejection. These overlap the full project gates and are not added to their totals.

No P0 was found. No confirmed implementation P1 remains after the reviewed fixes. External P1 launch blockers: exact owner/publication/account/origin approval; ownership/license/content/brand rights; durable off-machine backup with independent restoration. These are not satisfied by local tests.

P2 residual limits: physical phones, screen readers, hosted CI/CodeQL, Cloudflare edge/rollback, native Bangla review and field performance are unverified. One identical arXiv/Hacker News headline appears across events more than the 72-hour clustering window apart; source dates/links remain explicit and the community headline is deprioritized. Evidence-length/structural gates do not certify semantic editorial quality. Cache-policy mitigation review remains due 2026-11-03.

[Full verification](RELEASE_VALIDATION.md) ? [Release approval gate](RELEASE_APPROVAL_GATE.md).
