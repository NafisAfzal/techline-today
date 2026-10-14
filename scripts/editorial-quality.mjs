import fs from 'node:fs';
import { pathToFileURL } from 'node:url';

export function editorialQuality(snapshot, { production = false, now = Date.now() } = {}) {
  const errors = [], warnings = [];
  const prose = story => story.source_ids.some(id => {
    const source = snapshot.sources[id];
    return source && ['primary', 'independent'].includes(source.source_class) && source.excerpt.trim().length >= 80 && source.excerpt.trim().toLowerCase() !== source.title.trim().toLowerCase();
  });
  const ranked = [...snapshot.stories].sort((a,b) => b.importance_score_internal-a.importance_score_internal || Date.parse(b.published_at)-Date.parse(a.published_at) || a.id.localeCompare(b.id));
  const eligible = ranked.filter(prose);
  const missingReferences = ranked.filter(story => !story.source_ids.length || story.source_ids.some(id => !snapshot.sources[id]));
  const headlineOnly = ranked.filter(story => story.source_ids.every(id => !snapshot.sources[id]?.excerpt.trim()));
  const names = ranked.map(story => story.headline.toLowerCase().replace(/\W/g, ''));
  const duplicateTitles = names.length - new Set(names).size;
  const ageHours = (now - Date.parse(snapshot.last_successful_fetch_at)) / 3600000;
  const translated = ranked.filter(story => story.translations?.bn).length;
  if (missingReferences.length) errors.push(`${missingReferences.length} stories have missing source references.`);
  if (duplicateTitles) warnings.push(`${duplicateTitles} repeated normalized titles require editorial review.`);
  if (headlineOnly.length) warnings.push(`${headlineOnly.length} headline-only stories remain explicitly limited.`);
  if (!translated) warnings.push('No production Bangla story translations: launch as a localized interface with English fallback.');
  if (production) {
    if (snapshot.mode !== 'live' || ranked.some(story => story.is_demo) || Object.values(snapshot.sources).some(source => source.is_demo)) errors.push('Synthetic content cannot be published.');
    if (!Number.isFinite(ageHours) || ageHours > 24 || ageHours < -1/6) errors.push('Live collection is outside the 24-hour freshness window.');
    if (eligible.length < Math.min(5, ranked.length) || !eligible.length) errors.push('Insufficient prose-backed front-page stories.');
    if (!eligible.some(story => now - Date.parse(story.published_at) <= 72 * 3600000)) errors.push('No prose-backed story has been published within 72 hours.');
    if (ranked.some(story => story.translations?.bn?.review_status === 'fixture-reviewed')) errors.push('Fixture translations cannot be published.');
  }
  return { mode: snapshot.mode, stories: ranked.length, proseBacked: eligible.length, headlineOnly: headlineOnly.length, translatedBangla: translated, duplicateTitles, collectionAgeHours: Number(ageHours.toFixed(2)), errors, warnings };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const result = editorialQuality(JSON.parse(fs.readFileSync('content/generated/snapshot.json', 'utf8')), { production: process.argv.includes('--production') });
  console.log(JSON.stringify(result, null, 2));
  if (result.errors.length) process.exitCode = 1;
}
