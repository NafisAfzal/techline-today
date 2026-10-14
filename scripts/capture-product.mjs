import assert from 'node:assert/strict';
import { chromium } from '@playwright/test';
import { spawn } from 'node:child_process';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
const snapshot=JSON.parse(await readFile('content/generated/snapshot.json','utf8'));
const captureStartedAt=new Date().toISOString();
const directory=process.argv[2] || 'docs/assets';
assert(/^docs\/assets(?:\/[a-z-]+)?$/.test(directory));
assert.equal(snapshot.mode,'live','Repository screenshots must show live content');
assert(snapshot.stories.length>0);
const server=spawn(process.execPath,['scripts/preview.mjs'],{env:{...process.env,PORT:'4328'},stdio:'ignore'});
let browser;
try {
  for(let attempt=0;attempt<100;attempt++){try{if((await fetch('http://127.0.0.1:4328')).ok)break;}catch{/* Startup. */}await new Promise(resolve=>setTimeout(resolve,100));}
  const built=await (await fetch('http://127.0.0.1:4328/data/latest.json')).json();
  assert.equal(built.mode,'live');assert.equal(built.generated_at,snapshot.generated_at,'Rebuild before capturing screenshots');
  browser=await chromium.launch();const page=await browser.newPage({viewport:{width:1280,height:960},colorScheme:'light'});
  await mkdir(directory,{recursive:true});
  const shots=[{route:'/',file:'categories-desktop.jpg',width:1440,height:960,section:'.category-index'},{route:'/',file:'categories-mobile.jpg',width:390,height:844,section:'.category-index'},{route:'/',file:'homepage-desktop.jpg',width:1280,height:960},{route:'/',file:'homepage-mobile.jpg',width:390,height:844},{route:'/',file:'homepage-dark.jpg',width:1280,height:960,theme:'dark'},{route:'/',file:'homepage-dark-mobile.jpg',width:390,height:844,theme:'dark'},{route:'/',file:'homepage-tablet.jpg',width:834,height:960},{route:'/',file:'homepage-full.jpg',width:1280,height:960,fullPage:true},{route:'/bn/',file:'homepage-bangla.jpg',width:390,height:844},{route:`/story/${snapshot.stories.find(story=>story.key_numbers.length && story.primary_source_id)?.slug || snapshot.stories[0].slug}/`,file:'story-detail.jpg',width:1280,height:960},{route:'/freebies/',file:'free-credit.jpg',width:1280,height:960},{route:'/',file:'search-desktop.jpg',width:1280,height:960,search:true},{route:'/',file:'search-mobile.jpg',width:390,height:844,theme:'dark',search:true}];
  for(const shot of shots){await page.setViewportSize({width:shot.width,height:shot.height});await page.goto(`http://127.0.0.1:4328${shot.route}`);await page.waitForFunction(()=>!document.querySelector('astro-island[ssr]'));await page.evaluate(theme=>{document.documentElement.dataset.theme=theme;},shot.theme || 'light');if(shot.search){await page.locator('.search-trigger').click();await page.locator('#search-query').fill(snapshot.stories[0].headline.match(/[A-Za-z]{5,}/)[0]);await page.locator('.search-results a').first().waitFor();}await page.evaluate(()=>Promise.all(document.getAnimations().filter(animation=>animation.effect?.getComputedTiming().iterations!==Infinity && !(animation instanceof window.CSSAnimation && animation.animationName==='focus-progress')).map(animation=>animation.finished.catch(()=>{}))));const clip=shot.section?await page.locator(shot.section).evaluate(element=>{const box=element.getBoundingClientRect();return {x:box.x+window.scrollX,y:box.y+window.scrollY,width:box.width,height:box.height};}):undefined;await page.screenshot({path:`${directory}/${shot.file}`,type:'jpeg',quality:85,fullPage:!!shot.section || shot.fullPage || false,clip});}
  await writeFile(`${directory}/README.md`,`# Product screenshots\n\nLive capture started at ${captureStartedAt}, using a local production build of the snapshot generated at ${snapshot.generated_at}. These thirteen live images document that edition, not a deployed service, and contain no fixture data. The Bangla image shows localized UI with explicitly labelled English story fallback: no translation provider was configured.\n\n`+shots.map(shot=>`- [${shot.file}](${shot.file}): ${shot.route}, ${shot.width} × ${shot.height}, ${shot.theme==='dark'?'dark':'warm'} theme, ${shot.section?'complete category section':shot.fullPage?'full page':shot.search?'search open':'top of page'}.`).join('\n')+`\n\nRegenerate with \`node scripts/capture-product.mjs ${directory}\` after live ingestion and a production build. The complete six-width, two-theme, two-language screenshot matrices remain under ignored .cache/visual/. Restore fixture mode before release tests.\n`);
  console.log(JSON.stringify({mode:snapshot.mode,screenshots:shots.map(shot=>shot.file)},null,2));
} finally {await browser?.close();server.kill();}
