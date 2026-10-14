import { t, localizedPath, localizedStory, storyCount, type Locale } from '../lib/i18n';
import { useEffect, useState } from 'react';
import type { Story, SourceItem } from '../../../../packages/contracts';
import { LocalRepository } from '../lib/repositories';
import { previewLine } from '../lib/editorial';
type SavedRecord = {id:string; story:Story|null; sources:SourceItem[]};
const labels: {[key:string]:string} = {'primary-confirmed':'Primary confirmed','multi-source':'Multiple independent sources','single-source':'Single credible source','community-report':'Community report','needs-verification':'Needs verification'};
export default function SavedStories({archivesAvailable=false,categoryLabels={},locale='en'}: {locale?:Locale;archivesAvailable?:boolean;categoryLabels?:Record<string,string>}) {
  const ui = (key:string)=>t(locale,key);
  const [records,setRecords] = useState<SavedRecord[]>([]);
  const [loaded,setLoaded] = useState(false);
  const [read,setRead] = useState<string[]>([]);
  const [error,setError] = useState('');
  useEffect(()=>{
    let active=true;
    let revision=0;
    let indexRequest:Promise<Record<string,string>>|undefined;
    const storyRequests = new Map<string,Promise<SavedRecord>>();
    const controller = new AbortController();
    const load=async()=>{
      const currentRevision = ++revision;
      try {
        const repo=new LocalRepository(localStorage);
        const ids=await repo.list();
        if(ids.length && !indexRequest) indexRequest=fetch('/data/story-index.json',{signal:controller.signal}).then(async response=>{if(!response.ok) throw Error('Archive index unavailable');return await response.json() as Record<string,string>;}).catch(error=>{indexRequest=undefined;throw error;});
        const index = ids.length ? await indexRequest! : {};
        const loadedRecords:SavedRecord[]=[];
        for(let start=0;start<ids.length;start+=8) {
          const batch=await Promise.all(ids.slice(start,start+8).map(async id=>{
            const slug=index[id];
            if(!slug || !/^[a-z0-9-]+$/.test(slug)) return {id,story:null,sources:[]};
            if (!storyRequests.has(id)) storyRequests.set(id,(async()=>{
              try { const response=await fetch(`/data/stories/${slug}.json`,{signal:controller.signal}); if(!response.ok) return {id,story:null,sources:[]}; const payload=await response.json() as Story & {sources:SourceItem[]}; return {id,story:localizedStory(payload,locale),sources:payload.sources}; } catch {return {id,story:null,sources:[]};}
            })());
            const record = await storyRequests.get(id)!;
            if (!record.story) storyRequests.delete(id); // A transient failure remains retryable.
            return record;
          }));
          loadedRecords.push(...batch);
        }
        if(active && currentRevision===revision) {setRecords(loadedRecords.filter(record=>!(repo.get().hideRead && repo.ids('read').includes(record.id))));setRead(repo.ids('read'));setLoaded(true);setError('');}
      } catch {if(active && currentRevision===revision) {setError(ui('Your reading list could not be loaded. Check browser storage and try again.'));setLoaded(true);}}
    };
    void load();
    window.addEventListener('ti:reading',load);window.addEventListener('storage',load);window.addEventListener('ti:preferences',load);
    return()=>{active=false;controller.abort();window.removeEventListener('ti:reading',load);window.removeEventListener('storage',load);window.removeEventListener('ti:preferences',load);};
  },[locale]);
  return <section className="feed-section" aria-label={ui("Saved story feed")}><div className="feed-heading"><h2>{ui("Your reading list")}</h2><span className="mono">{storyCount(records.length,locale)}</span></div>
    {!loaded && <p role="status">{ui("Loading your reading list…")}</p>}{error && <p role="alert">{error}</p>}
    <div className="story-grid">{records.map(({id,story,sources})=>{
      if(!story) return <article key={id} className="story-card" data-story={id}><h3>{ui("This saved story is unavailable in this edition.")}</h3><p>{ui("It may be older than this edition or its evidence may have changed.")}</p><div className="card-links"><a className="control-link" href={localizedPath("/all/",locale)}>{ui("Browse all stories →")}</a>{archivesAvailable && <a className="control-link" href={localizedPath("/archives/",locale)}>{ui("Browse archives →")}</a>}</div><button type="button" data-bookmark={id} aria-pressed="true" aria-label={ui("Saved story: unavailable record")}>{ui("Saved ✓")}</button></article>;
      const source=sources.find(source=>source.id===story.primary_source_id)||sources[0];
      return <article key={id} className="story-card" data-variant="feed" data-story={id}><div className="story-meta"><a className="category-tag" href={localizedPath(`/category/${story.category}/`,locale)}>{ui(categoryLabels[story.category] || story.category.replaceAll('-',' '))}</a><a href={localizedPath("/about/#evidence",locale)} className={`evidence ${story.evidence_state}`}>{ui(labels[story.evidence_state]!)}</a></div><h3 lang={story.language}><a href={localizedPath(`/story/${story.slug}/`,locale)}>{story.headline}</a></h3><p className="story-summary" lang={story.language}>{previewLine(story)}</p>{locale==='bn' && !story.translations?.bn && <p className="translation-note">{ui('Bangla unavailable for this story. Showing English.')}</p>}<div className="chips" lang={story.language}>{story.key_numbers.slice(0,2).map(number=><span key={number.value} title={number.context}>{number.value} · {number.label}</span>)}</div><div className="card-footer"><div className="card-links"><a href={localizedPath(`/story/${story.slug}/`,locale)}>{ui("Details →")}</a>{source && <a href={source.original_url} target="_blank" rel="noopener noreferrer">{ui("Original source ↗")}</a>}</div><div className="story-actions"><button type="button" data-read={id} aria-pressed={read.includes(id)} aria-label={`${ui("Mark read")}: ${story.headline}`}>{ui(read.includes(id)?'Read ✓':'Mark read')}</button><button type="button" data-bookmark={id} aria-pressed="true" data-story-title={story.headline} aria-label={`${ui("Saved story")}: ${story.headline}`}>{ui("Saved ✓")}</button></div></div></article>;
    })}</div>
    {loaded && !records.length && !error && <div className="empty-state" data-empty><span className="eyebrow">{ui("A little quiet here")}</span><h3>{ui("Make room for a good read.")}</h3><p>{ui("Use Save on any story. Your reading list stays on this device.")}</p><a href={localizedPath("/",locale)}>{ui("Browse the briefing →")}</a></div>}
    <p role="status" data-storage-status className="storage-status"></p></section>;
}
