import { t, localeFor, storyCount } from './i18n';
import { LocalRepository } from './repositories';
import { periodStart } from './filters';
import type { Period } from '../../../../packages/contracts';
const locale = localeFor(window.location.pathname);
const ui = (key:string)=>t(locale,key);
const memory = new Map<string, string>();
let storage;
try { storage = window.localStorage; } catch { storage = {getItem:(key:string) => memory.get(key) || null, setItem:() => { throw new Error('Storage unavailable'); }, removeItem:() => undefined}; }
const repo = new LocalRepository(storage);
const validPeriods = new Set<Period>(['latest', 'today', 'week', 'month', 'year']);
function urlPeriod(): Period {
  const value = new URL(window.location.href).searchParams.get('period') as Period;
  return validPeriods.has(value) ? value : 'latest';
}
let period: Period = urlPeriod();
function status(message: string, target?: HTMLElement) {
  if (target) {
    const container = target.closest('.story-card,.detail-actions,.detail-heading,.header-actions') || target.parentElement;
    if (!container) return;
    let feedback = container.querySelector<HTMLElement>('[data-action-status],[data-action-slot]');
    if (!feedback) {feedback = document.createElement('p');feedback.dataset.actionStatus = '';feedback.className = 'storage-status';feedback.setAttribute('role','status');container.append(feedback);}
    feedback.dataset.actionStatus = '';
    feedback.textContent = message;
  } else document.querySelectorAll<HTMLElement>('[data-storage-status]').forEach(element => {element.textContent = message;});
}
function syncTheme() {
  const dark = document.documentElement.dataset.theme === 'dark';
  document.querySelectorAll<HTMLMetaElement>('meta[name="theme-color"]').forEach(meta => {meta.removeAttribute('media');meta.content=dark?'#101c2d':'#f4f2eb';});
  document.querySelectorAll('button[data-theme]').forEach(button => {
    button.setAttribute('aria-pressed',String(button.getAttribute('data-theme')===(dark?'dark':'light')));
  });
}
function expandFeed(feed: HTMLElement, count = Infinity) {
  const remaining = feed.querySelector<HTMLTemplateElement>('[data-feed-remainder]');
  const grid = feed.querySelector('.story-grid');
  if (!remaining || !grid) return null;
  const cards = [...remaining.content.querySelectorAll<HTMLElement>('[data-story]')].slice(0, count);
  const fragment = document.createDocumentFragment();
  cards.forEach(card => fragment.append(card));
  grid.append(fragment);
  const button = feed.querySelector<HTMLButtonElement>('[data-feed-more]');
  if (button) button.hidden = !remaining.content.childElementCount;
  return cards[0];
}
function update() {
  const preferences = repo.get();
  const bookmarks = new Set(repo.ids('bookmarks'));
  const readStories = new Set(repo.ids('read'));
  const feeds = [...document.querySelectorAll<HTMLElement>('[data-feed]')];
  for (const feed of feeds) {
    if (period !== 'latest' || preferences.sort !== 'importance' || preferences.categories.length || preferences.hideRead || feed.dataset.saved === 'true') expandFeed(feed);
  }
  document.querySelectorAll<HTMLElement>('[data-period]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.period === period)));
  if (preferences.density === 'compact') document.documentElement.dataset.density = 'compact';
  else if (document.documentElement.dataset.density) delete document.documentElement.dataset.density;
  document.querySelectorAll<HTMLButtonElement>('[data-bookmark]').forEach(button => {
    const saved = bookmarks.has(button.dataset.bookmark!);
    const label = ui(saved ? 'Saved ✓' : 'Save');
    const name = button.dataset.storyTitle || button.getAttribute('aria-label')?.replace(/^(Save story|Saved story|Remove saved story): /, '') || 'story';
    button.setAttribute('aria-label', `${ui(saved ? 'Saved story' : 'Save story')}: ${name}`);
    button.setAttribute('aria-pressed', String(saved)); if (button.textContent !== label) button.textContent = label;
  });
  document.querySelectorAll<HTMLButtonElement>('[data-read]').forEach(button => {
    const read = readStories.has(button.dataset.read!);
    const label = ui(read ? 'Read ✓' : 'Mark read');
    button.setAttribute('aria-pressed', String(read)); if (button.textContent !== label) button.textContent = label;
  });
  feeds.forEach(feed => {
    const sort = feed.querySelector<HTMLSelectElement>('[data-sort]');
    if (sort) sort.value = preferences.sort;
    const start = periodStart(period, new Date().toISOString());
    const cards = [...feed.querySelectorAll<HTMLElement>('[data-story]')];
    let visible = 0;
    for (const card of cards) {
      const saved = bookmarks.has(card.dataset.story!);
      const read = readStories.has(card.dataset.story!);
      card.hidden = (feed.dataset.saved === 'true' && !saved) || (Date.parse(card.dataset.published!) < start) || (preferences.hideRead && read);
      if (!card.hidden) visible++;
    }
    const pinned = (card: HTMLElement) => { const index = preferences.categories.indexOf(card.dataset.category as typeof preferences.categories[number]); return index < 0 ? 100 : index; };
    const ordered = [...cards].sort((a, b) => pinned(a) - pinned(b) || (preferences.sort === 'latest' ? Date.parse(b.dataset.published!) - Date.parse(a.dataset.published!) : Number(b.dataset.importance) - Number(a.dataset.importance)));
    const grid = feed.querySelector('.story-grid');
    if (grid && ordered.some((card, index) => card !== cards[index])) {
      const fragment = document.createDocumentFragment();
      ordered.forEach(card => fragment.append(card));
      grid.append(fragment);
    }
    const empty = feed.querySelector<HTMLElement>('[data-empty]'); if (empty) empty.hidden = visible !== 0;
    const count = feed.querySelector('[data-result-count]'); if (count) count.textContent = storyCount(visible,locale);
  });
}
document.addEventListener('click', async event => {
  const target = event.target instanceof Element ? event.target.closest<HTMLButtonElement>('button') : null;
  const language = event.target instanceof Element ? event.target.closest<HTMLAnchorElement>('[data-language]') : null;
  if (language) {
    try {localStorage.setItem('ti:v1:language',language.dataset.language!);} catch { /* The explicit localized URL remains usable without storage. */ }
    const url = new URL(language.href);url.search=window.location.search;url.hash=window.location.hash;language.href=url.href;
  }
  if (!target) return;
  if (target.hasAttribute('data-feed-more')) {
    const feed = target.closest<HTMLElement>('[data-feed]');
    if (feed) {
      const first = expandFeed(feed, 24);
      update();
      first?.querySelector<HTMLAnchorElement>('h3 a')?.focus({preventScroll:true});
    }
  }
  const id = target.dataset.bookmark;
  if (id) {
    try { if (repo.ids('bookmarks').includes(id)) await repo.remove(id); else await repo.add(id); status(ui('Reading list updated on this device.'), target); } catch { status(ui('Browser storage is unavailable. Enable local storage to save stories.'), target); }
    update();
    window.dispatchEvent(new CustomEvent('ti:reading'));
  }
  if (target.dataset.read) { if (!repo.toggleRead(target.dataset.read)) status(ui('Browser storage is unavailable.'), target); update(); window.dispatchEvent(new CustomEvent('ti:reading')); }
  if (target.dataset.period) {
    period = target.dataset.period as Period;
    const url = new URL(window.location.href);
    if (period === 'latest') url.searchParams.delete('period'); else url.searchParams.set('period', period);
    window.history.pushState(null, '', url);
    document.querySelectorAll('[data-period]').forEach(button => button.setAttribute('aria-pressed', String((button as HTMLElement).dataset.period === period)));
    update();
  }
  if (target.hasAttribute('data-theme')) {
    const theme = target.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
    if (!repo.set({...repo.get(), theme})) status(ui('Theme changed for this visit. Browser storage is unavailable.'), target);
    document.documentElement.dataset.theme = theme;
    syncTheme();
  }
});
document.querySelectorAll<HTMLSelectElement>('[data-sort]').forEach(select => select.addEventListener('change', () => {repo.set({...repo.get(), sort: select.value === 'latest' ? 'latest' : 'importance'}); update();}));
window.addEventListener('storage', update);
window.addEventListener('ti:preferences', update);
window.addEventListener('popstate', () => {period = urlPeriod(); update();});
update();
syncTheme();
new MutationObserver(syncTheme).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});

const more = document.querySelector<HTMLDetailsElement>('.more-nav');
document.addEventListener('keydown',event => {
  if (event.key === 'Escape' && more?.open) {
    const inside = more.contains(document.activeElement);
    more.open = false;
    if (inside) more.querySelector('summary')?.focus();
  }
});
document.addEventListener('click',event => {
  if (more?.open && event.target instanceof Node && !more.contains(event.target)) more.open = false;
});

document.addEventListener('click', event => {
  const link = event.target instanceof Element ? event.target.closest<HTMLAnchorElement>('a[href]') : null;
  if (!link || link.hasAttribute('data-language') || link.target || link.hasAttribute('download')) return;
  const url = new URL(link.href);
  if (url.origin !== location.origin || /^\/(?:data|pagefind|_astro|rss\.xml|favicon\.svg)(?:\/|$)/.test(url.pathname) || url.pathname === location.pathname) return;
  try {
    if (localStorage.getItem('ti:v1:language') === 'bn' && !url.pathname.startsWith('/bn/')) {
      url.pathname = '/bn' + url.pathname;link.href=url.href;
    }
  } catch { /* Explicit URL remains the default. */ }
});
