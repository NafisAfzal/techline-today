import type { APIRoute } from 'astro';
import { brandName } from '../lib/i18n';
import { data, original } from '../lib/data';
import { publicationTime } from '../lib/trust';
import policy from '../../../../config/source-rights.json';
import { researchRehearsal } from '../../../../scripts/research-policy.mjs';
const rights = policy.sources as Record<string, {license?: string; license_url?: string}>;
const xml = (value: string) => value.replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[character]!));
export const GET: APIRoute = ({site}) => {
  const items = data.stories.slice(0,50).map(story => {
    const attribution = story.source_ids.map(id => {const source=data.sources[id]!;const license=rights[source.source_registry_id];return `${source.publisher}: ${source.original_url}; ${license?.license || 'synthetic fixture'} ${license?.license_url || ''}`;}).join(' | ');
    const published = publicationTime(story, original(story));
    const publication = published ? `<pubDate>${new Date(published).toUTCString()}</pubDate>` : '';
    return `<item><title>${xml(story.headline)}</title><link>${new URL(`/story/${story.slug}/`,site)}</link><guid isPermaLink="false">${story.id}</guid>${publication}<description>${xml((data.mode === 'fixture' ? 'SYNTHETIC DEMO: ' : '') + story.summary_bullets.join(' ') + (published ? '' : ' Publication time unavailable.') + ' Sources: ' + attribution + '. Excerpted and summarized; no endorsement implied.')}</description></item>`;
  }).join('');
  return new Response(`<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>${brandName}${researchRehearsal ? ' — research/reference rehearsal' : ''}${data.mode === 'fixture' ? ' — synthetic demo' : ''}</title><link>${site}</link><description>Source-grounded technology briefings</description><language>en</language>${items}</channel></rss>`,{headers:{'Content-Type':'application/rss+xml; charset=utf-8'}});
};
