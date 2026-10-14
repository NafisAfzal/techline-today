import type { FeedFilter, Period, Story } from '../../../../packages/contracts';
export function periodStart(period: Period, now: string): number {
  if (period === 'latest') return 0;
  const local = new Date(new Date(now).getTime() + 6 * 3600000);
  let boundary = Date.UTC(local.getUTCFullYear(), local.getUTCMonth(), local.getUTCDate());
  if (period === 'week') boundary -= ((local.getUTCDay() + 6) % 7) * 86400000;
  if (period === 'month') boundary = Date.UTC(local.getUTCFullYear(), local.getUTCMonth(), 1);
  if (period === 'year') boundary = Date.UTC(local.getUTCFullYear(), 0, 1);
  return boundary - 6 * 3600000;
}
export function filterStories(stories: Story[], filter: FeedFilter = {}): Story[] {
  const start = periodStart(filter.period || 'latest', filter.now || new Date().toISOString());
  return stories.filter(story => (!filter.category || story.category === filter.category) && new Date(story.published_at).getTime() >= start)
    .sort(filter.sort === 'latest' ? (a, b) => Date.parse(b.published_at) - Date.parse(a.published_at) : (a, b) => b.importance_score_internal - a.importance_score_internal);
}
