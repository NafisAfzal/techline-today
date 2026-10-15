// Shared by the static reader and publication check. No network or AI work.
export const freshnessHours = Object.freeze({ 'current-news': 72, research: 168, reference: 720 });
export const collectionHours = 24;
const hour = 3600000;

export function timestamp(value) {
  if (typeof value !== 'string') return NaN;
  const match = value.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(Z|[+-]\d{2}:\d{2})$/);
  if (!match) return NaN;
  const [, year, month, day, hours, minutes, seconds, zone] = match;
  const days = new Date(Date.UTC(Number(year), Number(month), 0)).getUTCDate();
  if (+year < 1990 || +month < 1 || +month > 12 || +day < 1 || +day > days || +hours > 23 || +minutes > 59 || +seconds > 59) return NaN;
  if (zone !== 'Z' && (+zone.slice(1, 3) > 14 || +zone.slice(4) > 59)) return NaN;
  return Date.parse(value);
}

export function contentKind(story, sources) {
  const items = story.source_ids.map(id => sources[id]).filter(Boolean);
  if (story.category === 'research' || items.some(item => item.source_type === 'arxiv' || item.source_registry_id === 'arxiv')) return 'research';
  if (items.length && items.every(item => item.source_type === 'github_document')) return 'reference';
  // A collected timestamp substituted for a missing publication date is never news.
  if (items.length === story.source_ids.length && items.some(item =>
    ['primary', 'independent'].includes(item.source_class) &&
    ['rss', 'github_releases', 'json_api'].includes(item.source_type) &&
    item.missing_publication_time === false && Number.isFinite(timestamp(item.published_at)))) return 'current-news';
  return 'unclassified';
}

export function coverage(snapshot, now = Date.now()) {
  const invalidTimestamps = [];
  const valid = (value, label) => {
    const at = timestamp(value);
    if (!Number.isFinite(at) || at > now + hour / 6) invalidTimestamps.push(label);
    return Number.isFinite(at) && at <= now + hour / 6;
  };
  const generatedValid = valid(snapshot.generated_at, 'generated_at');
  const collectionValid = valid(snapshot.last_successful_fetch_at, 'last_successful_fetch_at');
  const counts = { 'current-news': 0, research: 0, reference: 0, unclassified: 0 };
  const stale = { 'current-news': 0, research: 0, reference: 0, unclassified: 0 };
  const currentNews = [];
  for (const story of snapshot.stories) {
    const kind = contentKind(story, snapshot.sources);
    counts[kind]++;
    let dated = valid(story.published_at, `${story.id}:published_at`);
    for (const id of story.source_ids) {
      const source = snapshot.sources[id];
      if (!source) { dated = false; continue; }
      dated = valid(source.published_at, `${id}:published_at`) && dated;
      dated = valid(source.fetched_at, `${id}:fetched_at`) && dated;
    }
    const items = story.source_ids.map(id => snapshot.sources[id]).filter(Boolean);
    const publicationKnown = items.some(source => source.missing_publication_time === false);
    const withinWindow = dated && kind !== 'unclassified' && (kind === 'reference'
      ? items.every(source => now - timestamp(source.fetched_at) <= freshnessHours.reference * hour)
      : publicationKnown && now - timestamp(story.published_at) <= freshnessHours[kind] * hour &&
        items.some(source => source.missing_publication_time === false && now - timestamp(source.published_at) <= freshnessHours[kind] * hour));
    if (!withinWindow) stale[kind]++;
    if (kind === 'current-news' && withinWindow) currentNews.push(story.id);
  }
  const collectionStale = !collectionValid || now - timestamp(snapshot.last_successful_fetch_at) > collectionHours * hour;
  return { counts, stale, currentNews, collectionStale, invalidTimestamps: [...new Set(invalidTimestamps)].sort(),
    generatedValid, collectionValid, asOf: new Date(now).toISOString() };
}

export const preprintNotice = 'arXiv preprint: peer review has not been established from the collected metadata.';
export const limitationsUnknown = 'Paper limitations have not been assessed from the collected abstract.';
export const significanceUnknown = 'Significance has not been assessed from the collected evidence.';

export function isPreprint(story, sources) {
  return story.source_ids.some(id => sources[id]?.source_type === 'arxiv' || sources[id]?.source_registry_id === 'arxiv');
}
