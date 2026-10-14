# Independent public-release review

A separate review agent/context inspected actual code and challenged the prior readiness claims. The reviewer performed read-only inspection and redacted scanning; it did not implement the parent's fixes or perform external writes. **Final recheck: original P1 implementation findings resolved; publication remains NO-GO for owner dependencies.**

Initial verdict: NO-GO. Confirmed P1 implementation findings were an unreferenced synthetic archive entering live backup packs and missing license notices for bundled reader software. External P1 dependencies were source ownership/license, news/screenshot rights, brand decision, exact account/origin/publication approval and durable off-machine restoration.

| Finding | Resolution / remaining severity | Independent evidence |
|---|---|---|
| P1 synthetic archive in live backups | Resolved: export derives exact referenced month/year paths; verification rejects extras; original data preserved | 19 focused tests passed in 4.37s; preserved old pack now raises ValueError; referenced live archive validation also rejects demo records |
| P1 missing bundled notices | Resolved: exact installed license texts accompany static bundle; every build checks inventory | Nine-package notice check passed; 20,703-byte built file equals committed source byte-for-byte |
| Shared artifact-storage overclaim | Code/docs corrected; owner account check remains P1 for USD 0 launch | Two-day artifact retention, 25 MiB total production bundle guard; free public runner minutes distinguished from storage |
| Public cache exposure | Documentation corrected; rights/privacy approval remains P1 | Public-fork cache scope explicitly recorded; credentials excluded from state packs |
| Hosted cache restoration after eviction | P1 before scheduling; depends on selected durable destination | v2 verified pack restore/save implemented; destination-specific import remains unprovisioned and scheduling disabled |
| Interrupted local archive writes | P2 residual | Recovery guide requires restoring a whole good generation; no all-files transaction is claimed |
| Stale localization wording / rollback retention / dispatch wait | Resolved in current documents | Manual/no-cron wording, two-day retention and explicit run-watch instruction added |

The parent additionally found setup-uv/CodeQL pins that identified annotated tag objects. Official GitHub API tag peeling supplied actual commit hashes; current pins and workflow policy tests were verified locally. This is recorded as an additional preparation fix, not a claim that hosted workflows have executed.

Remaining **P1**: actual publication authorization and exact destinations/revision; source ownership/license; brand/content/screenshot rights; durable encrypted off-machine source/data backup with independent restoration; account free-storage and zero-spend checks. **P2**: physical devices/screen readers, hosted Actions/CodeQL, edge behavior/rollback and field performance. **P3**: semantic no-change optimization and optional monitoring enhancements. Production AI/full Bangla reporting retain separate cost/provider/native-review blockers and are excluded from the launch scope. No P0 was found.

Additional findings: shared Actions artifact-storage risk; public cache access and missing destination-specific hosted cache recovery; possible mixed local archive generations after interrupted writes; stale localization wording. Fixes, regressions and remaining risks are assessed in the final recheck. No historical commits/refs/remotes existed; the initial redacted scan covered 252 prospective text files with no detected secrets.
