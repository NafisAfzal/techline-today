# Phase 3 local engineering baseline

Phase 2 released main: `ebe7f071512efd0cee19dc2849ba6650f86b0839`.
Local Phase 3 branch: `feat/phase3-activation-readiness-local`.
See the [verified GitHub release](PHASE2_GITHUB_RELEASE.md).

The branch began with no tracked modifications and one preserved unrelated pending document, `GITHUB_WAVE1_RELEASE.md`. Phase 3 changes remain local and uncommitted. They are excluded from the merged Phase 2 PR. Existing reports, owner documents and earlier worktrees are preserved.

| Baseline dimension | Verified value |
|---|---|
| Registry | 11 sources: 2 enabled, 9 disabled |
| Enabled | `arxiv`, `cloudflare_ai_terms` |
| Disabled pilots | `kubernetes`, `cisa_kev` |
| Rights | 2 allowed sources, 7 explicit exclusions; 2 example sources have no rights record and fail closed |
| Pilot rights | Both excluded; AI submission false |
| Canonical edition | Live; 37 stories, 37 evidence records, 9 digests |
| Editorial coverage | 36 research, 1 reference, 0 current news |
| Research freshness | 24 within seven days, 12 stale at the baseline measurement clock |
| News gate | Refuses: no eligible prose-backed current news within 72 hours; collection overdue |
| Bangla/corroboration | 0 translated stories; 0 multisource stories |
| Tests | 269 Python, 130 JavaScript, 184 hosted fixture browser cases |
| Deployment/schedules/AI | Unapproved and inactive |

Canonical SHA-256:
`d146d528ed8b00bc4e3a1e379ceffa300f46ce5a17ee9d34e8291410e9973eb5`

The reference story is categorized as freebies in the stored edition; editorial classification remains reference. Research freshness is separate from collection freshness and current-news coverage. Counts describe the measured snapshot, not upstream feed availability.

Remaining governance blockers: item-specific Kubernetes license scope and creator/origin evidence; guest/mirror/third-party policy; trusted and independently reviewed future approval authority; live response-size/conditional-request measurements; advisory editorial review; hosted recovery/preview/production authorization. General engineering authorization accepts no publisher terms.

The local additions implement [inactive rights review](RIGHTS_REVIEW_CONTRACT.md), [fixture staging](PILOT_STAGING.md) and an [internal attribution specification](PILOT_ATTRIBUTION_SPEC.md). They do not change this baseline's source rights, enablement, public interface or canonical edition.
