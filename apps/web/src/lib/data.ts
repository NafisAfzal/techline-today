import fs from 'node:fs';
import path from 'node:path';
import type { Snapshot, Story } from '../../../../packages/contracts';
const snapshotPath = path.resolve(process.cwd(), '../../content/generated/snapshot.json');
if (!fs.existsSync(snapshotPath)) throw new Error('No snapshot. Run pnpm fixtures or pnpm ingest before starting Astro.');
export const data = JSON.parse(fs.readFileSync(snapshotPath, 'utf8')) as Snapshot;
for (const entry of data.archive_index) {
  if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(entry.key) || entry.url !== `/archives/${entry.key}/`) throw new Error('Unsafe archive path in snapshot');
}
export const categoryEntries = Object.entries(data.categories);
export const storyById = new Map(data.stories.map(story => [story.id, story]));
export function original(story: Story) { return data.sources[story.primary_source_id || story.source_ids[0]!]!; }
export const evidenceLabels = {
  'primary-confirmed': 'Primary confirmed', 'multi-source': 'Multiple independent sources',
  'single-source': 'Single credible source', 'community-report': 'Community report', 'needs-verification': 'Needs verification',
};
export function date(value: string, full = false, locale = 'en') {
  return new Intl.DateTimeFormat(locale === 'bn' ? 'bn-BD' : 'en-GB', { timeZone: 'Asia/Dhaka', day: 'numeric', month: full ? 'long' : 'short', year: 'numeric', ...(full ? {hour: '2-digit', minute: '2-digit'} : {}) }).format(new Date(value));
}
export function age(value: string, locale = 'en') {
  const hours = Math.max(0, Math.floor((new Date(data.generated_at).getTime() - new Date(value).getTime()) / 3600000));
  if (locale === 'bn') return hours < 1 ? 'এইমাত্র সংগ্রহ' : hours < 24 ? `${new Intl.NumberFormat('bn').format(hours)} ঘণ্টা আগে` : `${new Intl.NumberFormat('bn').format(Math.floor(hours / 24))} দিন আগে`;
  return hours < 1 ? 'Just collected' : hours < 24 ? `${hours}h ago` : `${Math.floor(hours / 24)}d ago`;
}
