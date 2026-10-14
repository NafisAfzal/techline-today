# Independent owner-launch review

2026-10-14. A separate review context inspected code/configuration read-only and challenged release boundaries, source rights, AI eligibility, state recovery and public inventory. It did not publish, modify files or grant legal clearance. Findings were addressed locally and covered by the checks below.

| Finding | Severity | Resolution and evidence |
|---|---|---|
| Preview authorization could use production Worker/origin | P1 | Explicit distinct-destination gate plus exact confirmed workers.dev subdomain matching. Unit regression and independent in-memory reproduction now reject collision. |
| Reused alternate index retained 168 historical images | P1 | Reinitialize from HEAD/empty every scan and include real staged paths. Explicit historical-image exclusion assertion. Final prospective scan includes only six launch images and leaves real index unchanged. |
| License/change attribution missing from RSS/downloads | P1 | Per-source content-attribution JSON includes current/archive sources, publisher/original URL/license/change notice; response Link header references it. RSS carries explicit source/license/change attribution; detail notice remains. Build rights verification checks attribution presence. Real edge headers remain a hosted test. |
| Local optional inference ignored source-submission policy | P2 | Runner checks source policy for summary and translation requests. Mocked live integration enables AI/providers and proves zero requests for disallowed source evidence. Production inference remains independently prohibited. |
| Raw archive hashes caused timestamp-only deployments | P2 | Archive fingerprint reuses semantic normalization. Independent in-memory probe confirmed verification-only changes skip publication. |
| Successful state promoted before hosted smoke | P1 | Move hosted smoke before receipt/save/cache; workflow regression asserts ordering. On failed hosted smoke implicit success conditions prevent promotion; already deployed edge needs explicit authorized rollback. |
| Tracked ignored files could evade a future fresh-index scan | P2 | Initialize from HEAD when available and union real-index paths before all checks. An ignored tracked secret cannot disappear from inventory. |

| Initial disabled push could not be manually revalidated | P2 | Nonpublishing CI now supports workflow_dispatch; the runbook includes explicit post-authorization enable/dispatch commands. Enabling Actions does not replay the earlier push. |

Other current fixes positively rechecked: owner MIT/notice, permitted-source configuration, retained mixed-source/correction pruning, referenced archive/built-JSON guard, six-image public whitelist, source detail notice, arXiv retry intervals/serialization and prospective Markdown-link membership.

No additional current source-scope or authorization bypass was found in that review after corrections. This does not establish account eligibility, hosted CI/edge behavior, physical-device quality, trademark clearance or off-machine recovery. The next release decision remains NO-GO while applicable owner gates are open. [Current verification](OWNER_LAUNCH_VERIFICATION.md) and [owner decisions](OWNER_GITHUB_LAUNCH_PLAN.md).
