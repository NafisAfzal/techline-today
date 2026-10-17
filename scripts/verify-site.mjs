import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { chromium } from '@playwright/test';
import { indexingBlocked } from './site-url.mjs';

const root = path.resolve('apps/web/dist');
const files = directory => fs.readdirSync(directory, {withFileTypes:true}).flatMap(entry => entry.isDirectory() ? files(path.join(directory,entry.name)) : [path.join(directory,entry.name)]);
const htmlFiles = files(root).filter(file => file.endsWith('.html'));
const base = 'http://127.0.0.1:4324';
const server = spawn(process.execPath, ['scripts/preview.mjs'], {env:{...process.env,PORT:'4324'},stdio:'ignore'});
let browser;
try {
  let ready = false;
  for(let attempt=0;attempt<60;attempt++) {
    try {ready=(await fetch(base)).ok;} catch { /* Preview is starting. */ }
    if(ready) break;
    await new Promise(resolve=>setTimeout(resolve,250));
  }
  assert(ready,'Site preview did not start');
  browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto(base);
  const pages = new Map();
  const links = [];
  for(const file of htmlFiles) {
    const relative = path.relative(root,file).replaceAll('\\','/');
    const route = '/' + relative.replace(/(?:^|\/)index\.html$/, match=>match.startsWith('/') ? '/' : '');
    const response = await fetch(base+route);
    assert.equal(response.status,200,`Generated route failed: ${route}`);
    const html = await response.text();
    const info = await page.evaluate(markup=>{
      const document = new window.DOMParser().parseFromString(markup,'text/html');
      return {
        title:document.title, h1:document.querySelectorAll('h1').length,
        headings:[...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].map(element=>({level:Number(element.tagName.slice(1)),text:element.textContent})),
        description:document.querySelector('meta[name="description"]')?.getAttribute('content'),
        canonical:document.querySelector('link[rel="canonical"]')?.getAttribute('href'),
        language:document.documentElement.lang,
        alternates:[...document.querySelectorAll('link[hreflang]')].map(element=>({language:element.getAttribute('hreflang'),url:element.getAttribute('href')})),
        robots:document.querySelector('meta[name="robots"]')?.getAttribute('content'),
        ids:[...document.querySelectorAll('[id]')].map(element=>element.id),
        links:[...document.querySelectorAll('a[href],script[src],link[href],astro-island[component-url]')].map(element=>element.getAttribute('href') || element.getAttribute('src') || element.getAttribute('component-url')),
        unsafe:document.querySelectorAll('[onclick],[onerror],iframe,script:not([src]):not([type="application/ld+json"])').length,
      };
    },html);
    assert(info.title && info.description && info.canonical,`Missing SEO metadata: ${route}`);
    assert.equal(info.h1,1,`Expected one h1 on ${route}`);
    assert.equal(info.headings[0]?.level,1,`Heading before page h1: ${route}`);
    for(let index=1;index<info.headings.length;index++) assert(info.headings[index].level<=info.headings[index-1].level+1,`Skipped heading level on ${route}: ${info.headings[index].text}`);
    assert.equal(new Set(info.ids).size,info.ids.length,`Duplicate HTML ids: ${route}`);
    assert(!html.includes('/undefined/') && !html.includes('[object Object]'),`Broken rendered content: ${route}`);
    pages.set(route,info);
    for(const href of info.links) if(href) links.push({route,href});
  }
  let internal=0,external=0;
  for(const {route,href} of links) {
    const url=new URL(href,base+route);
    if(url.origin!==base) {assert(['https:','mailto:'].includes(url.protocol),`Unsafe scheme on ${route}`);external++;continue;}
    internal++;
    const target=path.resolve(root,'.'+decodeURIComponent(url.pathname));
    assert(target===root || target.startsWith(root+path.sep),`Path traversal: ${href}`);
    assert(fs.existsSync(target) || fs.existsSync(path.join(target,'index.html')),`Broken link ${href} on ${route}`);
    if(url.hash && pages.has(url.pathname)) assert(pages.get(url.pathname).ids.includes(decodeURIComponent(url.hash.slice(1))),`Broken anchor ${href} on ${route}`);
  }
  const missing=await fetch(base+'/audit-route-that-does-not-exist/');
  assert.equal(missing.status,404);
  const snapshot=JSON.parse(fs.readFileSync('content/generated/snapshot.json','utf8'));
  const canonicalOrigin=new URL(pages.get('/').canonical).origin;
  for(const [route,info] of pages) assert.equal(new URL(info.canonical).origin,canonicalOrigin,`Canonical origin on ${route}`);
  for(const [route,info] of pages) {
    const localized=route.startsWith('/bn/');
    assert.equal(info.language,localized?'bn':'en',`Page language on ${route}`);
    const slug=route.match(/^\/bn\/story\/([^/]+)\/$/)?.[1];
    const unavailable=slug && !snapshot.stories.find(story=>story.slug===slug)?.translations?.bn;
    if(unavailable) {assert(info.robots.includes('noindex'));assert.equal(new URL(info.canonical).pathname,route.slice(3));assert.equal(info.alternates.length,0);}
    else if(!/\/(?:404(?:\.html)?|saved|settings)\/?$/.test(route)) {
      assert.equal(new URL(info.canonical).pathname,route,`Self canonical: ${route}`);
      const englishSlug=route.match(/^\/story\/([^/]+)\/$/)?.[1];
      const hasAlternates=!englishSlug || !!snapshot.stories.find(story=>story.slug===englishSlug)?.translations?.bn;
      assert.equal(info.alternates.length,hasAlternates?3:0,`Language alternates on ${route}`);
      if(hasAlternates) {
        assert.deepEqual(info.alternates.map(item=>item.language),['en','bn','x-default']);
        for(const item of info.alternates) {const url=new URL(item.url);assert.equal(url.origin,canonicalOrigin);assert(pages.has(url.pathname),`Missing alternate ${item.url}`);}
      }
    }
  }
  const parseXml=async route=>{
    const response=await fetch(base+route);assert.equal(response.status,200);
    return page.evaluate(markup=>{const document=new window.DOMParser().parseFromString(markup,'application/xml');return {error:!!document.querySelector('parsererror'),locations:[...document.querySelectorAll('loc')].map(element=>element.textContent),items:[...document.querySelectorAll('item')].map(element=>({title:element.querySelector('title')?.textContent,url:element.querySelector('link')?.textContent,id:element.querySelector('guid')?.textContent,date:element.querySelector('pubDate')?.textContent}))};},await response.text());
  };
  const rss=await parseXml('/rss.xml');assert(!rss.error,'Malformed RSS');assert.equal(rss.items.length,Math.min(50,snapshot.stories.length));
  for(const item of rss.items) {
    const story=snapshot.stories.find(story=>story.id===item.id);assert(story,'RSS story missing');
    assert.equal(item.title,story.headline);assert.equal(item.url,new URL(`/story/${story.slug}/`,canonicalOrigin).href);
    const source=snapshot.sources[story.primary_source_id || story.source_ids[0]];
    if (source.missing_publication_time) assert(!item.date, 'Unknown publication must omit RSS pubDate');
    else assert.equal(Date.parse(item.date),Math.floor(Date.parse(story.published_at)/1000)*1000,'RSS RFC 2822 dates retain second precision');
  }
  const sitemap=await parseXml('/sitemap-index.xml');assert(!sitemap.error && sitemap.locations.length,'Malformed sitemap index');
  let sitemapRoutes=0;
  const listedRoutes=new Set();
  for(const location of sitemap.locations) {
    const url=new URL(location);assert.equal(url.origin,canonicalOrigin);
    const map=await parseXml(url.pathname);assert(!map.error,'Malformed sitemap');
    for(const location of map.locations) {const url=new URL(location);assert.equal(url.origin,canonicalOrigin);assert(pages.has(url.pathname),`Unknown sitemap route ${url.pathname}`);assert(!listedRoutes.has(url.pathname),`Duplicate sitemap route ${url.pathname}`);listedRoutes.add(url.pathname);sitemapRoutes++;}
  }
  const eligible=[...pages.keys()].filter(route=>{
    if(/\/(?:404(?:\.html)?|saved|settings)\/?$/.test(route)) return false;
    const slug=route.match(/^\/bn\/story\/([^/]+)\/$/)?.[1];
    return !slug || !!snapshot.stories.find(story=>story.slug===slug)?.translations?.bn;
  });
  assert.equal(sitemapRoutes,eligible.length,'Sitemap omits public routes or includes fallback/private pages');
  assert.deepEqual([...listedRoutes].sort(),eligible.sort(),'Sitemap membership differs from public localized routes');
  const robots=await (await fetch(base+'/robots.txt')).text();assert(robots.includes(`Sitemap: ${canonicalOrigin}/sitemap-index.xml`));
  assert(robots.includes(indexingBlocked(snapshot.mode,new URL(canonicalOrigin).hostname)?'Disallow: /':'Allow: /'));
  console.log(JSON.stringify({status:'passed',htmlRoutes:pages.size,internalLinks:internal,externalReferences:external,rssItems:rss.items.length,sitemapRoutes,checks:['rendered routes','metadata/canonical origins','heading order','unique IDs','internal assets/links/anchors','RSS/XML','sitemap/XML','robots','404']},null,2));
} finally {await browser?.close();server.kill();}
