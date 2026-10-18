import { describe, expect, it } from 'vitest';
import type { Story, SourceItem } from '../../packages/contracts';
import { contentLanguage, localizedStory, t } from '../../apps/web/src/lib/i18n';
import { preprint, publicationTime, storyDate, translationLabel } from '../../apps/web/src/lib/trust';
import { prominentStories, rankedStories, previewLine } from '../../apps/web/src/lib/editorial';

const dated = { id: 'p', source_class: 'primary', source_registry_id: 'arxiv', source_type: 'arxiv',
  publisher: 'arXiv', missing_publication_time: false } as unknown as SourceItem;
const undated = { ...dated, id: 'u', missing_publication_time: true } as unknown as SourceItem;

const base = {
  id: 'story_1', slug: 'synthetic-story', category: 'research', source_ids: ['p'],
  published_at: '2026-10-18T06:00:00Z', first_seen_at: '2026-10-18T07:00:00Z',
  updated_at: '2026-10-18T09:00:00Z', importance_score_internal: 0.6, novelty_score_internal: 1,
  language: 'en', evidence_state: 'primary-confirmed',
  ai_metadata: { generation_mode: 'extractive', evidence_hash: 'a'.repeat(64) },
  change_log: [], summary_bullets: ['First bullet for the synthetic test.', 'Second bullet for the synthetic test.',
    'Third bullet for the synthetic test.'], headline: 'A synthetic headline for verification',
  key_numbers: [], why_it_matters: '', key_facts: [],
} as unknown as Story;

const bnContent = { headline: 'কৃত্রিম শিরোনাম', summary_bullets: ['প্রথম', 'দ্বিতীয়', 'তৃতীয়'],
  why_it_matters: 'কেন গুরুত্বপূর্ণ', broader_summary: 'বিস্তারিত', key_fact_texts: [],
  number_labels: [], number_contexts: [], limitations: [] };

describe('Phase 6 reader-facing content states', () => {
  it('never presents a collection time as a publication date', () => {
    expect(publicationTime(base, dated)).toBe(base.published_at);
    const shown = storyDate(base, dated);
    expect(shown.label).toBe('Published');
    expect(shown.value).toBe(base.published_at);
    expect(shown.value).not.toBe(base.updated_at);
  });

  it('labels an unknown publication time as first seen instead of inventing one', () => {
    expect(publicationTime(base, undated)).toBeNull();
    const shown = storyDate(base, undated);
    expect(shown.label).toBe('First seen');
    expect(shown.value).toBe(base.first_seen_at);
    expect(shown.value).not.toBe(base.updated_at);
  });

  it('keeps research distinguishable from news on every card', () => {
    expect(preprint(base, { p: dated })).toBe(true);
    const news = { ...dated, id: 'n', source_registry_id: 'reporter', source_type: 'rss' } as unknown as SourceItem;
    expect(preprint({ ...base, source_ids: ['n'] }, { n: news })).toBe(false);
  });

  it('never labels a machine translation as native or reviewed', () => {
    const automated = { ...base, translations: { bn: { language: 'bn', content: bnContent,
      canonical_hash: 'b'.repeat(64), cache_key: 'c'.repeat(64), provider: 'p', model: 'm',
      generated_at: '2026-10-18T09:00:00Z', review_status: 'automated' } } } as unknown as Story;
    const fixture = { ...automated, translations: { bn: { ...automated.translations!.bn,
      review_status: 'fixture-reviewed' } } } as unknown as Story;
    expect(translationLabel(base)).toBe('English content');
    expect(translationLabel(automated)).toBe('Machine-translated content');
    expect(translationLabel(fixture)).toBe('Synthetic translation');
    for (const label of [translationLabel(automated), translationLabel(fixture)]) {
      expect(label).not.toMatch(/native|reviewed Bangla|verified/i);
    }
  });

  it('renders both translation states in Bangla rather than leaking English', () => {
    expect(t('bn', 'Machine-translated content')).toMatch(/[ঀ-৿]/u);
    expect(t('bn', 'Synthetic translation')).toMatch(/[ঀ-৿]/u);
    expect(t('bn', 'English content')).toMatch(/[ঀ-৿]/u);
  });

  it('returns the identical canonical record when no Bangla translation exists', () => {
    // Identity, not a copy: a fallback page can never present English as Bangla.
    expect(localizedStory(base, 'bn')).toBe(base);
    expect(contentLanguage(base, 'bn')).toBe('en');
  });

  it('marks Bangla content language only when a translation exists', () => {
    const translated = { ...base, translations: { bn: { language: 'bn', content: bnContent,
      canonical_hash: 'b'.repeat(64), cache_key: 'c'.repeat(64), provider: 'p', model: 'm',
      generated_at: '2026-10-18T09:00:00Z', review_status: 'automated' } } } as unknown as Story;
    expect(contentLanguage(translated, 'bn')).toBe('bn');
    expect(contentLanguage(translated, 'en')).toBe('en');
  });

  it('does not manufacture a preview line when the source provided only a headline', () => {
    const headlineOnly = { ...base, summary_bullets: ['Only the headline was collected. Open the source for more detail.'] } as unknown as Story;
    expect(previewLine(headlineOnly)).toMatch(/headline-only|open the cited source/i);
  });

  it('keeps ranking deterministic and does not promote a build-time story', () => {
    const first = { ...base, id: 'a', importance_score_internal: 0.9 } as unknown as Story;
    const second = { ...base, id: 'b', importance_score_internal: 0.1 } as unknown as Story;
    expect(rankedStories([second, first]).map(s => s.id)).toEqual(['a', 'b']);
    expect(prominentStories([second, first], {}).map(s => s.id)).toEqual(['a', 'b']);
  });
});