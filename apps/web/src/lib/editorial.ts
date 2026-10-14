import type { Story, SourceItem } from '../../../../packages/contracts';
// Consume pipeline ranking rather than introducing browser ranking signals.
export function rankedStories(stories: Story[]) {
  return [...stories].sort((a,b) => b.importance_score_internal-a.importance_score_internal || Date.parse(b.published_at)-Date.parse(a.published_at) || a.id.localeCompare(b.id));
}
// Front-page prominence requires useful prose from a primary or independent
// source. Preserve pipeline order within each evidence group.
export function prominentStories(stories: Story[], sources: Record<string, SourceItem>) {
  const eligible = (story: Story) => story.source_ids.some(id => {
    const source = sources[id];
    return source && ['primary','independent'].includes(source.source_class) && source.excerpt.trim().length >= 80 && source.excerpt.trim().toLowerCase() !== source.title.trim().toLowerCase();
  });
  return rankedStories(stories).sort((a,b) => Number(eligible(b)) - Number(eligible(a)));
}
// Category teasers must add a story, rather than repeat the edition's lead or brief.
export function categoryPreview(stories: Story[], category: string, featuredIds: Set<string>) {
  return stories.find(story => story.category === category && !featuredIds.has(story.id));
}
export function previewLine(story: Story) {
  return story.summary_bullets.find(text => text !== story.headline && !text.endsWith('is the cited source for this update.') && !['The original source provides the available detail and context.', 'Read the source for details that this summary does not cover.', 'Only the headline was collected. Open the source for more detail.'].includes(text)) || 'Headline-only report. Open the cited source for details.';
}
export function readingSummary(story: Story) {
  return story.summary_bullets.filter(text => text !== story.headline && !text.endsWith('is the cited source for this update.'));
}
