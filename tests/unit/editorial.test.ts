import { describe, expect, it } from 'vitest';
import type { Story } from '../../packages/contracts';
import { rankedStories, previewLine, categoryPreview, readingSummary } from '../../apps/web/src/lib/editorial';
const story = (id:string, score:number, date='2026-10-01T00:00:00Z') => ({id,importance_score_internal:score,published_at:date,headline:'Source announcement',summary_bullets:['Source announcement','Publisher is the cited source for this update.','The original source provides the available detail and context.']} as Story);
describe('editorial presentation',()=>{
  it('selects by pipeline importance, then publication and stable id without mutating input',()=>{
    const input=[story('low',.1),story('b',.9),story('a',.9),story('fresh',.9,'2026-10-02T00:00:00Z')];
    expect(rankedStories(input).map(item=>item.id)).toEqual(['fresh','a','b','low']);
    expect(input[0]?.id).toBe('low');
  });
  it('discloses headline-only evidence rather than repeating attribution filler',()=>{
    expect(previewLine(story('a',1))).toContain('Headline-only');
  });
  it('preserves an actual summary sentence verbatim',()=>{
    const value=story('a',1);value.summary_bullets.splice(1,0,'The API is available to developers.');
    expect(previewLine(value)).toBe('The API is available to developers.');
  });
  it('uses the next ranked category story outside the lead and briefing',()=>{
    const input=[{...story('lead',1),category:'ai'},{...story('brief',.9),category:'ai'},{...story('next',.8),category:'ai'}] as Story[];
    expect(categoryPreview(input,'ai',new Set(['lead','brief']))?.id).toBe('next');
  });
  it('does not fill a sparse category with a repeated featured story',()=>{
    expect(categoryPreview([{...story('lead',1),category:'security'}] as Story[],'security',new Set(['lead']))).toBeUndefined();
  });
  it('keeps headline-only notices visible without repeating title and provenance',()=>{
    const value=story('a',1);value.summary_bullets[2]='Only the headline was collected. Open the source for more detail.';
    expect(readingSummary(value)).toEqual(['Only the headline was collected. Open the source for more detail.']);
    expect(value.summary_bullets).toHaveLength(3);
  });
  it('preserves uncertainty and supported prose in the article summary',()=>{
    const value=story('a',1);value.summary_bullets=['The vendor reports 64 GB.','Independent results are not available.','Access may require registration.'];
    expect(readingSummary(value)).toEqual(value.summary_bullets);
  });
});
