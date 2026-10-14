import { describe, expect, it } from 'vitest';
import { LocalRepository, defaults } from '../../apps/web/src/lib/repositories';
import { filterStories, periodStart } from '../../apps/web/src/lib/filters';
import type { Story } from '../../packages/contracts';
function storage() {const map=new Map<string,string>();return {getItem:(key:string)=>map.get(key)||null,setItem:(key:string,value:string)=>{map.set(key,value);},removeItem:(key:string)=>{map.delete(key);}};}
describe('local repositories',()=>{
  it('persists bookmarks without duplicates',async()=>{const store=storage();const repo=new LocalRepository(store);await repo.add('one');await repo.add('one');expect(await new LocalRepository(store).list()).toEqual(['one']);await repo.remove('one');expect(await repo.list()).toEqual([]);});
  it('recovers corrupt and wrong-shaped storage',async()=>{const store=storage();store.setItem('ti:v1:bookmarks','not json');const repo=new LocalRepository(store);expect(await repo.list()).toEqual([]);store.setItem('ti:v1:bookmarks','{}');expect(await repo.list()).toEqual([]);store.setItem('ti:v1:preferences','{"theme":"script","categories":["ai","ai","wrong"]}');expect(repo.get()).toEqual({...defaults,categories:['ai']});});
  it('reports storage failure instead of claiming to save',async()=>{const repo=new LocalRepository({getItem:()=>null,setItem:()=>{throw Error('quota');},removeItem:()=>{}});expect(repo.set(defaults)).toBe(false);await expect(repo.add('id')).rejects.toThrow('unavailable');});
  it('keeps ordered preferences and read state',()=>{const repo=new LocalRepository(storage());repo.set({...defaults,categories:['security','ai']});expect(repo.get().categories).toEqual(['security','ai']);repo.toggleRead('one');expect(repo.ids('read')).toEqual(['one']);repo.toggleRead('one');expect(repo.ids('read')).toEqual([]);repo.reset();expect(repo.get().categories).toEqual([]);});
});
describe('editorial periods and filters',()=>{
  const stories=[{id:'a',category:'ai',published_at:'2026-10-02T20:00:00Z',importance_score_internal:.5},{id:'b',category:'security',published_at:'2026-10-02T15:00:00Z',importance_score_internal:.9}] as Story[];
  it('starts the Dhaka day at 18:00 UTC',()=>{expect(new Date(periodStart('today','2026-10-03T12:00:00Z')).toISOString()).toBe('2026-10-02T18:00:00.000Z');});
  it('filters calendar day, category and sort',()=>{expect(filterStories(stories,{period:'today',now:'2026-10-03T12:00:00Z'}).map(story=>story.id)).toEqual(['a']);expect(filterStories(stories,{category:'security'})[0]?.id).toBe('b');expect(filterStories(stories,{sort:'latest'})[0]?.id).toBe('a');});
  it('selects calendar week month and year',()=>{expect(new Date(periodStart('week','2026-10-03T12:00:00Z')).toISOString()).toBe('2026-09-27T18:00:00.000Z');expect(new Date(periodStart('month','2026-10-03T12:00:00Z')).toISOString()).toBe('2026-09-30T18:00:00.000Z');expect(new Date(periodStart('year','2026-10-03T12:00:00Z')).toISOString()).toBe('2025-12-31T18:00:00.000Z');});
});
