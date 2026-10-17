import type { Story, SourceItem } from '../../../../packages/contracts';
import { isPreprint, significanceUnknown, timestamp } from '../../../../scripts/coverage.mjs';

export const evidenceLabels = {
  'primary-confirmed': 'Primary source', 'multi-source': 'Multiple independent sources',
  'single-source': 'Single reporting source', 'community-report': 'Community report', 'needs-verification': 'Needs verification',
};

export function trustExplanation(story: Story, sources: Record<string, SourceItem>) {
  const groups = new Set(story.source_ids.map(id => sources[id]).filter(source => source?.source_class === 'independent').map(source => source.source_independence_group || source.id));
  if (story.evidence_state === 'primary-confirmed') return groups.size
    ? 'Primary source with independent reporting. Source presence does not establish every claim or peer review.'
    : 'Primary source only. No independent reporting is cited; publication does not establish peer review or validate the claims.';
  if (story.evidence_state === 'multi-source') return 'Multiple independent reporting groups are cited. Their presence does not prove every claim.';
  return 'Source availability describes provenance, not proof. Read the cited evidence and uncertainty.';
}

export function showSignificance(story: Story) {
  return story.ai_metadata.generation_mode !== 'extractive' && !!story.why_it_matters && story.why_it_matters !== significanceUnknown;
}

export function preprint(story: Story, sources: Record<string, SourceItem>) { return isPreprint(story, sources); }

export function translationLabel(story: Story) {
  const translation = story.translations?.bn;
  if (!translation) return 'English content';
  return translation.review_status === 'fixture-reviewed' ? 'Synthetic translation' : 'Machine-translated content';
}

// A normalization placeholder cannot establish when a source was published.
// First-seen comes from the story history, independently of collection refreshes.
export function storyDate(story: Story, source: SourceItem) {
  const publication = publicationTime(story, source);
  return { label: publication ? 'Published' : 'First seen', value: publication || story.first_seen_at };
}

export function publicationTime(story: Story, source: SourceItem) {
  return source.missing_publication_time === false && Number.isFinite(timestamp(story.published_at))
    ? story.published_at : null;
}
