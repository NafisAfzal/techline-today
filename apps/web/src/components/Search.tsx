import { t, localizedPath, type Locale } from '../lib/i18n';
import { useEffect, useRef, useState } from 'react';
import { searchExcerptText } from '../lib/search-excerpt';
type Result = { url: string; title: string; excerpt: string; searchable?:string; language?:string };
type Pagefind = { search: (query: string) => Promise<{results: {data: () => Promise<{url:string;meta:{title:string;description?:string;language?:string};excerpt:string}>}[]}> };
export default function Search({locale='en'}: {locale?:Locale}) {
  const ui = (key:string)=>t(locale,key);
  const dialog = useRef<HTMLDialogElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);
  const fallbackIndex = useRef<Promise<Result[]> | null>(null);
  const [opened, setOpened] = useState(false);
  const [query, setQuery] = useState('');
  const [ready, setReady] = useState(false);
  const [results, setResults] = useState<Result[]>([]);
  const [status, setStatus] = useState(ui('Type a model, tool, topic or source.'));
  const updateQuery = (value: string) => {
    setQuery(value); setResults([]);
    setStatus(ui(value.trim() ? 'Searching…' : 'Type a model, tool, topic or source.'));
  };
  const open = (invoker?: HTMLElement) => {
    if (dialog.current?.open) return;
    previousFocus.current = invoker || (document.activeElement instanceof HTMLElement ? document.activeElement : null);
    dialog.current?.showModal(); setOpened(true); input.current?.focus();
  };
  useEffect(() => {
    setReady(true);
    const listener = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && dialog.current?.open) {event.preventDefault(); dialog.current.close(); return;}
      if (event.key === 'Tab' && dialog.current?.open) {
        const stops = [...dialog.current.querySelectorAll<HTMLElement>('button:not(:disabled), input, a[href]')].filter(element=>element.getClientRects().length);
        const first=stops[0], last=stops.at(-1);
        if (event.shiftKey && document.activeElement===first) {event.preventDefault();last?.focus();}
        else if (!event.shiftKey && document.activeElement===last) {event.preventDefault();first?.focus();}
      }
      const typing = event.target instanceof HTMLElement && (['INPUT','TEXTAREA','SELECT'].includes(event.target.tagName) || event.target.isContentEditable);
      if (!typing && (event.key === '/' || ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k'))) { event.preventDefault(); open(); }
    };
    document.addEventListener('keydown', listener);
    return () => document.removeEventListener('keydown', listener);
  }, []);
  useEffect(() => {
    let cancelled = false;
    if (!opened || !query.trim()) return;
    const timer = setTimeout(async () => {
      if (cancelled) return;
      setStatus(ui('Searching…'));
      try {
        let found: Result[];
        try {
          const moduleUrl = '/pagefind/pagefind.js';
          const pagefind = await import(/* @vite-ignore */ moduleUrl) as Pagefind;
          if (cancelled) return;
          const search = await pagefind.search(query);
          found = await Promise.all(search.results.slice(0, 8).map(async result => { const item = await result.data(); return {url:item.url, title:item.meta.title, language:item.meta.language, excerpt:item.meta.description || searchExcerptText(item.excerpt)}; }));
        } catch {
          if (cancelled) return;
          fallbackIndex.current ??= fetch(locale==='bn'?'/data/search-bn.json':'/data/search.json').then(async response => {
            if (!response.ok) throw new Error('Index unavailable');
            return await response.json() as Result[];
          }).catch(error => {fallbackIndex.current = null; throw error;});
          const index = await fallbackIndex.current;
          const words = query.toLowerCase().split(/\s+/).filter(Boolean);
          found = index.filter(item => words.every(word => (item.title + ' ' + (item.searchable || item.excerpt)).toLowerCase().includes(word))).slice(0, 8);
        }
        if (!cancelled) { setResults(found); setStatus(found.length ? `${found.length} ${ui("results")}` : ui('No results. Try a different term.')); }
      } catch { if (!cancelled) { setResults([]); setStatus(ui('Search is temporarily unavailable. Browse categories instead.')); } }
    }, 120);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [query,locale,opened]);
  return <><form className="header-search" role="search" aria-label={ui('Search stories')} onSubmit={event => {
      event.preventDefault();
      // Safari does not focus a button when it is tapped. Retain the actual
      // invoking control, including the input when submitted with Enter.
      const active = document.activeElement;
      open(active instanceof HTMLElement && event.currentTarget.contains(active) ? active : event.currentTarget.querySelector<HTMLElement>('button') || undefined);
    }}>
      <input className="header-search-input" type="search" name="q" autoComplete="off" maxLength={200} disabled={!ready} aria-label={ui('Search news, topics, sources')} aria-haspopup="dialog" placeholder={ui('Search news, topics, sources')} value={query} onChange={event => updateQuery(event.target.value)}/>
      <kbd aria-hidden="true">/</kbd>
      <button type="submit" className="search-trigger" disabled={!ready} aria-label={ui("Search stories")} aria-haspopup="dialog"><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4.5 4.5"/></svg><span className="search-word">{ui("Search")}</span></button>
    </form>
    <dialog ref={dialog} className="search-dialog" aria-labelledby="search-title" onClose={() => {setOpened(false); previousFocus.current?.focus();}} onClick={event => {
      if(event.target !== dialog.current) return;
      const bounds = dialog.current.getBoundingClientRect();
      if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.current.close();
    }}>
      <div className="search-dialog-head"><p id="search-title">{ui("Find your next read")}</p><button onClick={() => dialog.current?.close()} aria-label={ui("Close search")}>×</button></div>
      <label htmlFor="search-query" className="eyebrow">{ui("Search the intelligence archive")}</label>
      <input ref={input} id="search-query" name="q" type="search" autoComplete="off" maxLength={200} value={query} placeholder={ui("Models, APIs, research, releases\u2026")} onChange={event => updateQuery(event.target.value)} />
      <p role="status" className="search-status">{status}</p>
      <ul className="search-results">{results.map(result => <li key={result.url}><a href={result.url.startsWith('/') && !result.url.startsWith('//') && !result.url.includes(String.fromCharCode(92)) ? localizedPath(result.url,locale) : localizedPath('/',locale)} lang={result.language}><strong>{result.title}</strong><span>{result.excerpt}</span></a></li>)}</ul>
      <p className="search-note">{ui("Search runs on this device.")}<kbd>{ui("esc")}</kbd>{ui("to close.")}</p>
    </dialog></>;
}
