import path from 'node:path';
import type { Snapshot, Story } from '../../../../packages/contracts';
import { readBuildSnapshot } from '../../../../scripts/research-policy.mjs';
const snapshotPath = path.resolve(process.cwd(), '../../content/generated/snapshot.json');
export const data = readBuildSnapshot(snapshotPath) as Snapshot;
for (const entry of data.archive_index) {
  if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(entry.key) || entry.url !== `/archives/${entry.key}/`) throw new Error('Unsafe archive path in snapshot');
}
export const categoryEntries = Object.entries(data.categories);
export const storyById = new Map(data.stories.map(story => [story.id, story]));
export function original(story: Story) { return data.sources[story.primary_source_id || story.source_ids[0]!]!; }
export { evidenceLabels } from './trust';
export function date(value: string, full = false, locale = 'en') {
  return new Intl.DateTimeFormat(locale === 'bn' ? 'bn-BD' : 'en-GB', { timeZone: 'Asia/Dhaka', day: 'numeric', month: full ? 'long' : 'short', year: 'numeric', ...(full ? {hour: '2-digit', minute: '2-digit'} : {}) }).format(new Date(value));
}
