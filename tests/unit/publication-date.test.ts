import { expect, it } from 'vitest';
import type { Story, SourceItem } from '../../packages/contracts';
import { publicationTime, storyDate, translationLabel } from '../../apps/web/src/lib/trust';
import { t } from '../../apps/web/src/lib/i18n';

const story = { published_at: '2026-10-01T00:00:00Z', first_seen_at: '2026-10-17T10:20:00Z' } as Story;

it('uses first-seen history instead of a normalization placeholder for unknown publication', () => {
  expect(storyDate(story, { missing_publication_time: true } as SourceItem))
    .toEqual({ label: 'First seen', value: story.first_seen_at });
});

it('preserves validated publication timestamps', () => {
  expect(storyDate(story, { missing_publication_time: false } as SourceItem))
    .toEqual({ label: 'Published', value: story.published_at });
});

it('fails closed for missing quality metadata and invalid dates', () => {
  expect(storyDate(story, {} as SourceItem).label).toBe('First seen');
  expect(storyDate({ ...story, published_at: 'invalid' }, { missing_publication_time: false } as SourceItem).value)
    .toBe(story.first_seen_at);
});

it('localizes unavailable publication without pretending article translation exists', () => {
  expect(t('bn', 'Publication time unavailable')).toBe('প্রকাশের সময় জানা নেই');
  expect(t('en', 'Publication time unavailable')).toBe('Publication time unavailable');
});

it.each(['2026-10-17', '2026-10-17T10:00:00', '2026-02-30T10:00:00Z'])('does not export ambiguous RSS publication timestamps: %s', value => {
  expect(publicationTime({ ...story, published_at: value }, { missing_publication_time: false } as SourceItem)).toBeNull();
});

it('distinguishes fallback, synthetic translation and machine translation', () => {
  expect(translationLabel(story)).toBe('English content');
  expect(translationLabel({ ...story, translations: { bn: { review_status: 'fixture-reviewed' } } } as Story))
    .toBe('Synthetic translation');
  expect(translationLabel({ ...story, translations: { bn: { review_status: 'automated' } } } as Story))
    .toBe('Machine-translated content');
  expect(t('bn', 'Synthetic translation')).toMatch(/[\u0980-\u09ff]/);
  expect(t('bn', 'Machine-translated content')).toMatch(/[\u0980-\u09ff]/);
});
