from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from pipeline.models import Digest


def period_bounds(at: datetime, kind: str, timezone="Asia/Dhaka"):
    local = at.astimezone(ZoneInfo(timezone))
    day = local.replace(hour=0, minute=0, second=0, microsecond=0)
    if kind == "daily":
        return day.date().isoformat(), day, day + timedelta(days=1)
    if kind == "weekly":
        start = day - timedelta(days=day.weekday())
        year, week, _ = start.isocalendar()
        return f"{year}-W{week:02}", start, start + timedelta(days=7)
    if kind == "monthly":
        start = day.replace(day=1)
        end = start.replace(year=start.year + 1, month=1) if start.month == 12 else start.replace(month=start.month + 1)
        return start.strftime("%Y-%m"), start, end
    start = day.replace(month=1, day=1)
    return str(start.year), start, start.replace(year=start.year + 1)


def build_digests(stories, now, timezone="Asia/Dhaka", announced_events=()):
    digests = []
    for kind in ("daily", "weekly", "monthly", "yearly"):
        groups = defaultdict(list)
        bounds = {}
        for story in stories:
            key, start, end = period_bounds(story.published_at, kind, timezone)
            groups[key].append(story)
            bounds[key] = start, end
        for key, group in groups.items():
            start, end = bounds[key]
            ordered = sorted(group, key=lambda story: (-story.importance_score_internal, story.id))
            categories = defaultdict(list)
            for story in ordered:
                if len(categories[story.category]) < 3:
                    categories[story.category].append(story.id)
            local_now = now.astimezone(ZoneInfo(timezone))
            final_run = (local_now.hour, local_now.minute) >= (19, 17)
            finalized = end <= now or (kind == "daily" and local_now.date() == start.date() and final_run) or (kind == "weekly" and local_now.weekday() == 6 and final_run and start <= now < end)
            digests.append(Digest(id=key, period_type=kind, period_start=start, period_end=end,
                                  status="finalized" if finalized else "in-progress",
                                  story_ids=[story.id for story in ordered], top_by_category=dict(categories),
                                  summary=ordered[0].headline,
                                  what_changed=[f"{story.headline}: {change.text}" for story in ordered for change in story.change_log[-1:] if start <= change.at < end][:5],
                                  watch_next=[event.fact for event in announced_events if event.at > now and set(event.fact.source_ids) & {key for story in group for key in story.source_ids}], generated_at=now))
    return sorted(digests, key=lambda digest: digest.period_start, reverse=True)
