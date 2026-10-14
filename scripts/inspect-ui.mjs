import { chromium } from '@playwright/test';
import { spawn } from 'node:child_process';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
const label = process.argv[2] || 'current';
if (!/^[a-z-]+$/.test(label)) throw Error('Use a simple inspection label');
const directory = path.resolve('.cache/visual', label);
await mkdir(directory, {recursive:true});
const snapshot = JSON.parse(await readFile('content/generated/snapshot.json','utf8'));
const routes = ['/', '/category/ai/', '/category/chips/', '/all/', `/story/${snapshot.stories[0].slug}/`, '/digests/', ...(snapshot.digests.length?[`/digests/${snapshot.digests[0].period_type}/${snapshot.digests[0].id}/`]:[]), '/models/', '/freebies/', '/saved/', '/settings/', '/about/', '/archives/', '/missing-page/'];
const server = spawn(process.execPath,['scripts/preview.mjs'],{env:{...process.env,PORT:'4326'},stdio:'ignore'});
let browser;
try {
  for (let attempt=0;attempt<100;attempt++) {try {if ((await fetch('http://127.0.0.1:4326')).ok) break;} catch { /* Server startup. */ } await new Promise(resolve=>setTimeout(resolve,100));}
  const built=await (await fetch('http://127.0.0.1:4326/data/latest.json')).json();
  assert.equal(built.generated_at,snapshot.generated_at,'Rebuild after ingestion before inspecting');
  assert.equal(built.mode,snapshot.mode);
  browser=await chromium.launch();
  const page=await browser.newPage();
  const measurements=[], dialogs=[];
  for (const width of [320,390,834,1280,1366,1440]) {
    await page.setViewportSize({width,height:width<500?844:900});
    for (const route of routes) {
      const response=await page.goto(`http://127.0.0.1:4326${route}`);
      await page.locator('astro-island[ssr]').count().then(async count=>{if(count) await page.waitForFunction(()=>!document.querySelector('astro-island[ssr]'),{},{timeout:10000});});
      measurements.push(await page.evaluate(({route,width,status})=>{
        const visible=element=>element.getClientRects().length && window.getComputedStyle(element).visibility!=='hidden';
        const text=[...document.querySelectorAll('body *')].filter(element=>visible(element) && [...element.childNodes].some(node=>node.nodeType===window.Node.TEXT_NODE && node.textContent.trim()));
        const tiny=text.filter(element=>parseFloat(window.getComputedStyle(element).fontSize)<12).map(element=>({text:element.textContent.trim().slice(0,70),size:window.getComputedStyle(element).fontSize}));
        const card=document.querySelector('.story-card');
        return {route,width,status,overflow:document.documentElement.scrollWidth>width,minText:Math.min(...text.map(element=>parseFloat(window.getComputedStyle(element).fontSize))),tiny,firstStory:card?{top:card.getBoundingClientRect().top,height:card.getBoundingClientRect().height}:null};
      },{route,width,status:response.status()}));
      if(route==='/' && [390,1280].includes(width)) await page.screenshot({path:path.join(directory,`home-${width}.png`)});
    }
    await page.goto('http://127.0.0.1:4326');
    await page.getByRole('button',{name:'Search stories'}).click();
    await page.getByLabel('Search the intelligence archive').fill(snapshot.stories[0].headline.match(/[A-Za-z]{5,}/)[0]);
    await page.locator('.search-results a').first().waitFor();
    dialogs.push(await page.evaluate(width=>({width,overflow:document.documentElement.scrollWidth>width,results:document.querySelectorAll('.search-results a').length,inputFocused:document.activeElement?.id==='search-query'}),width));
    await page.keyboard.press('Escape');
    await page.locator('.more-nav summary').click();
    if(width===320) await page.screenshot({path:path.join(directory,'navigation-320.png')});
    await page.locator('.more-nav summary').click();
    await page.evaluate(()=>{document.documentElement.dataset.theme='dark';});
    if([320,1280].includes(width)) await page.screenshot({path:path.join(directory,`dark-${width}.png`)});
  }
  await page.setViewportSize({width:1366,height:768});await page.goto('http://127.0.0.1:4326');
  await page.evaluate(()=>{document.documentElement.dataset.theme='light';});
  const laptop=await page.locator('.lead-card').evaluate(element=>({width:window.innerWidth,height:window.innerHeight,top:element.getBoundingClientRect().top,bottom:element.getBoundingClientRect().bottom}));
  await page.screenshot({path:path.join(directory,'laptop-1366.png')});
  await writeFile(path.join(directory,'measurements.json'),JSON.stringify({mode:snapshot.mode,generated_at:snapshot.generated_at,measurements,dialogs,laptop},null,2));
  console.log(JSON.stringify({mode:snapshot.mode,routes:routes.length,states:measurements.length,overflow:measurements.filter(item=>item.overflow).map(({route,width})=>({route,width})),tinyTextStates:measurements.filter(item=>item.tiny.length).length,home:measurements.filter(item=>item.route==='/').map(({width,firstStory,minText})=>({width,firstStory,minText})),dialogs,laptop,directory},null,2));
} finally {await browser?.close();server.kill();}
