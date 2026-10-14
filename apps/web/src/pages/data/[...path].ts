import { previewLine } from '../../lib/editorial';
import type { APIRoute } from 'astro';
import { data } from '../../lib/data';
import { localizedStory } from '../../lib/i18n';
export function getStaticPaths() {
  return [
    {params:{path:'story-index.json'},props:{payload:Object.fromEntries(data.stories.map(story=>[story.id,story.slug]))}},
    {params:{path:'latest.json'},props:{payload:{generated_at:data.generated_at,mode:data.mode,stories:data.stories.slice(0,120)}}},
    {params:{path:'search.json'},props:{payload:data.stories.map(story => ({url:`/story/${story.slug}/`,title:story.headline,excerpt:previewLine(story),language:story.language,searchable:[...story.summary_bullets,...story.tags,...story.entities,story.category].join(' ')}))}},
    {params:{path:'search-bn.json'},props:{payload:data.stories.map(canonical => {const story=localizedStory(canonical,'bn');return {url:`/bn/story/${story.slug}/`,title:story.headline,excerpt:previewLine(story),language:story.language,searchable:[...story.summary_bullets,...story.tags,...story.entities,story.category].join(' ')};})}},
    {params:{path:'offers.json'},props:{payload:data.offers}},
    {params:{path:'models.json'},props:{payload:data.model_releases}},
    ...Object.keys(data.categories).map(category => ({params:{path:`categories/${category}.json`},props:{payload:{generated_at:data.generated_at,stories:data.stories.filter(story => story.category === category)}}})),
    ...data.stories.map(story => ({params:{path:`stories/${story.slug}.json`},props:{payload:{...story,sources:story.source_ids.map(id => data.sources[id])}}})),
    ...data.digests.map(digest => ({params:{path:`digests/${digest.period_type}/${digest.id}.json`},props:{payload:digest}})),
  ];
}
export const GET: APIRoute = ({props}) => new Response(JSON.stringify(props.payload), {headers:{'Content-Type':'application/json; charset=utf-8'}});
