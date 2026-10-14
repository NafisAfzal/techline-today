import { chromium } from '@playwright/test';
import { spawn } from 'node:child_process';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import assert from 'node:assert/strict';
import path from 'node:path';
import os from 'node:os';
const label = process.argv[2] || 'refined';
assert(/^[a-z-]+$/.test(label));
const directory = process.argv[3] || `.cache/visual/${label}`;
const output=path.resolve(directory);
assert([path.resolve('.cache/visual'),path.join(os.tmpdir(),'techline-deep-review')].some(root=>output.startsWith(root+path.sep)),'Visual output must stay inside the review workspace or its dedicated temporary folder');
await mkdir(directory, {recursive:true});
const snapshot = JSON.parse(await readFile('content/generated/snapshot.json', 'utf8'));
const server = spawn(process.execPath, ['scripts/preview.mjs'], {env:{...process.env,PORT:'4329'},stdio:'ignore'});
let browser;
try {
  for(let i=0;i<100;i++){try{if((await fetch('http://127.0.0.1:4329')).ok)break;}catch{/* Startup. */}await new Promise(resolve=>setTimeout(resolve,100));}
  const built=await (await fetch('http://127.0.0.1:4329/data/latest.json')).json();
  assert.equal(built.generated_at,snapshot.generated_at,'Rebuild after changing the edition');
  assert.equal(built.mode,snapshot.mode,'Inspect the intended dataset');
  browser = await chromium.launch();
  const page = await browser.newPage();
  const measurements=[];
  const locales=label.startsWith('baseline')?['en']:['en','bn'];
  for(const width of [320,390,834,1280,1366,1440]) {
    await page.setViewportSize({width,height:width===1366?768:width<500?844:960});
    for(const locale of locales) for(const theme of ['light','dark']) {
      const prefix=locale==='bn'?'/bn':'';
      const routes=['/', '/all/', '/freebies/', '/models/', '/settings/', '/digests/'];
      for(const category of ['ai','research','chips','security','freebies']) {
        const story=snapshot.stories.find(story=>story.category===category);
        if(story)routes.push(`/story/${story.slug}/`);
      }
      for(const route of routes) {
        await page.goto(`http://127.0.0.1:4329${prefix}${route}`);
        await page.waitForFunction(()=>!document.querySelector('astro-island[ssr]'));
        await page.evaluate(theme=>{document.documentElement.dataset.theme=theme;},theme);
        await page.evaluate(()=>Promise.all(document.getAnimations().filter(animation=>animation.effect?.getComputedTiming().iterations!==Infinity && !(animation instanceof window.CSSAnimation && animation.animationName==='focus-progress')).map(animation=>animation.finished.catch(()=>{}))));
        const metrics=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>window.innerWidth,lang:document.documentElement.lang,headline:document.querySelector('h1')?.textContent,leadSize:document.querySelector('.lead-card h2')?window.getComputedStyle(document.querySelector('.lead-card h2')).fontSize:null,bodySize:window.getComputedStyle(document.body).fontSize,proseSize:document.querySelector('.detail-content li')?window.getComputedStyle(document.querySelector('.detail-content li')).fontSize:null}));
        measurements.push({width,locale,theme,route,...metrics});
        assert(!metrics.overflow,`Overflow: ${width} ${locale} ${theme} ${route}`);
        const name=route==='/'?'home':route.startsWith('/story/')?`story-${snapshot.stories.find(story=>route.includes(story.slug)).category}`:route.split('/')[1];
        if(route==='/' || [390,1280].includes(width)) await page.screenshot({path:`${directory}/${locale}-${theme==='light'?'warm':'dark'}-${name}-${width}.png`,fullPage:route==='/' || route.startsWith('/story/')});
        if(route==='/' && [390,834,1440].includes(width)) {
          const clip=await page.locator('.category-index').evaluate(element=>{const box=element.getBoundingClientRect();return {x:box.x+window.scrollX,y:box.y+window.scrollY,width:box.width,height:box.height};});
          await page.screenshot({path:`${directory}/${locale}-${theme==='light'?'warm':'dark'}-categories-${width}.png`,fullPage:true,clip});
        }
      }
    }
  }
  await writeFile(`${directory}/measurements.json`,JSON.stringify({mode:snapshot.mode,generated_at:snapshot.generated_at,measurements},null,2));
  console.log(JSON.stringify({directory,mode:snapshot.mode,states:measurements.length,overflows:measurements.filter(item=>item.overflow).length},null,2));
} finally {await browser?.close();server.kill();}
