import { describe, expect, it } from 'vitest';
import { contentKind, coverage, timestamp } from '../../scripts/coverage.mjs';
import { editorialQuality } from '../../scripts/editorial-quality.mjs';

const now = Date.parse('2026-10-15T00:00:00Z');
const at = (hours=0) => new Date(now-hours*3600000).toISOString();
const source = {id:'s',source_registry_id:'official',source_type:'rss',source_class:'primary',missing_publication_time:false,published_at:at(1),fetched_at:at(),title:'Official release announcement',excerpt:'The publisher describes the release, its documented access conditions and the changes that are available in this version.',is_demo:false};
const story = {id:'one',category:'ai',headline:source.title,published_at:at(1),source_ids:['s'],importance_score_internal:.8,is_demo:false};
const snapshot = {mode:'live',generated_at:at(),last_successful_fetch_at:at(),stories:[story],sources:{s:source}};

describe('publication freshness and coverage',()=>{
  it('accepts validated current news and keeps exact boundaries',()=>{
    expect(coverage(snapshot,now).currentNews).toEqual(['one']);
    expect(editorialQuality(snapshot,{production:true,now}).errors).toEqual([]);
    expect(coverage({...snapshot,stories:[{...story,published_at:at(72)}]},now).currentNews).toEqual(['one']);
    expect(coverage({...snapshot,stories:[{...story,published_at:at(72.001)}]},now).currentNews).toEqual([]);
  });
  it('never counts research or an evergreen document as current news',()=>{
    const research = {...snapshot,stories:[{...story,category:'research'}],sources:{s:{...source,source_type:'arxiv'}}};
    expect(coverage(research,now).counts.research).toBe(1);
    expect(coverage(research,now).currentNews).toEqual([]);
    expect(editorialQuality(research,{production:true,now}).errors.join(' ')).toContain('current technology news');
    const reference={...source,source_type:'github_document',missing_publication_time:true};
    expect(contentKind(story,{s:reference})).toBe('reference');
    expect(coverage({...snapshot,sources:{s:reference}},now).currentNews).toEqual([]);
  });
  it('distinguishes collection freshness from publication freshness and unchanged editions',()=>{
    const stale={...snapshot,stories:[{...story,published_at:at(200)}]};
    expect(coverage(stale,now).collectionStale).toBe(false);
    expect(coverage(stale,now).stale['current-news']).toBe(1);
    expect(coverage({...snapshot,sources:{s:{...source,published_at:at(200)}}},now).currentNews).toEqual([]);
    expect(coverage(snapshot,now+25*3600000).collectionStale).toBe(true);
    // A legitimately unchanged, still-fresh article needs no invented update.
    expect(editorialQuality(snapshot,{production:true,now}).errors).toEqual([]);
  });
  it('supports empty and legacy snapshots conservatively',()=>{
    const empty={...snapshot,stories:[],sources:{}};
    expect(coverage(empty,now).currentNews).toEqual([]);
    expect(editorialQuality(empty,{production:true,now}).errors.length).toBeGreaterThan(0);
    expect(contentKind(story,{s:{...source,source_type:undefined,missing_publication_time:undefined}})).toBe('unclassified');
    expect(contentKind(story,{s:{...source,missing_publication_time:true}})).toBe('unclassified');
  });
  it.each(['invalid','2026-10-15','2026-10-15T00:00:00','2026-02-30T00:00:00Z','2026-10-15T24:00:00Z','2026-10-15T00:00:00+25:00'])('rejects invalid timestamps: %s',value=>{
    expect(Number.isNaN(timestamp(value))).toBe(true);
    expect(coverage({...snapshot,stories:[{...story,published_at:value}]},now).invalidTimestamps).toContain('one:published_at');
    expect(editorialQuality({...snapshot,stories:[{...story,published_at:value}]},{production:true,now}).errors.length).toBeGreaterThan(0);
  });
  it('rejects future source dates even when the story date looks plausible',()=>{
    const bad={...snapshot,sources:{s:{...source,published_at:at(-1)}}};
    expect(coverage(bad,now).currentNews).toEqual([]);
    expect(coverage(bad,now).invalidTimestamps).toContain('s:published_at');
  });
  it('preserves source timezones and rejects corrupt collection metadata',()=>{
    expect(timestamp('2026-10-15T06:00:00+06:00')).toBe(now);
    expect(coverage({...snapshot,last_successful_fetch_at:'bad'},now).collectionStale).toBe(true);
    expect(coverage({...snapshot,sources:{s:{...source,fetched_at:'bad'}}},now).currentNews).toEqual([]);
  });
});
