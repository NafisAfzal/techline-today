# Content Schedule

Timezone for editorial periods: `Asia/Dhaka`.

## Collection

Default: four runs/day.

Local target times:
- 01:17
- 07:17
- 13:17
- 19:17

A six-hour cadence is a balance between freshness and free API/AI budgets. Each run looks back 12 hours and deduplicates, so one missed job is recovered by the next run.

## Per-run priorities

1. official model/tool releases
2. critical security updates
3. expiring free API/developer offers
4. high-impact platform/pricing changes
5. major research/open-source releases
6. chips/devices
7. jobs/skills pulse
8. lower-priority community discussion

## Daily digest

After the final local-day collection, build the final daily view. If a later delayed story has a publication time inside the day, the next run may revise that day's digest and record `updated_at`.

## Weekly

Sunday evening local time. Use the seven completed local calendar days. Do not simply concatenate daily summaries; rank and cluster the week's events again from validated story records.

## Monthly

At the beginning of a new month, summarize the completed previous calendar month.

Sections:
- top changes
- AI/model releases
- developer/API economics
- important research
- chips/devices
- free offers that appeared/expired

## Yearly

After year close. Emphasize factual milestones and meaningful changes, not predictions.

Useful sections:
- major model/platform shifts
- benchmark/evaluation milestones
- hardware/device milestones
- developer ecosystem shifts
- notable free/open-source availability changes
- most consequential security/platform events

## Expiring offer recheck

Active freebie/credit items with an expiry within seven days should be revalidated every ingestion run or at least daily, depending on source rate limits.

## Urgent update path

Do not build a complex real-time system in V1. If real usage demonstrates demand, add a lightweight urgent-source job for a small allowlist of official feeds, while preserving the same normalization/validation pipeline.
