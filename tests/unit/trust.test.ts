import { describe, expect, it } from 'vitest';
import type { Story, SourceItem } from '../../packages/contracts';
import { evidenceLabels, preprint, showSignificance, trustExplanation } from '../../apps/web/src/lib/trust';
import { significanceUnknown } from '../../scripts/coverage.mjs';

const source={id:'p',source_class:'primary',source_registry_id:'arxiv',source_type:'arxiv'} as SourceItem;
const story={source_ids:['p'],evidence_state:'primary-confirmed',why_it_matters:'Generic legacy category advice.',ai_metadata:{generation_mode:'extractive'}} as Story;
describe('editorial trust presentation',()=>{
  it('retains the legacy enum while removing confirmation language',()=>{
    expect(evidenceLabels[story.evidence_state]).toBe('Primary source');
    expect(trustExplanation(story,{p:source})).toContain('No independent reporting');
    expect(preprint(story,{p:source})).toBe(true);
  });
  it('distinguishes independent reporting from primary provenance',()=>{
    const secondary={...source,id:'i',source_class:'independent',source_registry_id:'reporter',source_type:'rss'};
    expect(trustExplanation({...story,source_ids:['p','i']},{p:source,i:secondary})).toContain('with independent reporting');
    expect(preprint(story,{p:{...source,source_type:undefined}})).toBe(true);
  });
  it('omits boilerplate and unknown significance but allows explicit editorial interpretation',()=>{
    expect(showSignificance(story)).toBe(false);
    const ai={...story,ai_metadata:{generation_mode:'ai'}} as Story;
    expect(showSignificance(ai)).toBe(true);
    expect(showSignificance({...ai,why_it_matters:significanceUnknown})).toBe(false);
  });
});
