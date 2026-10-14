import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {spawn} from 'node:child_process';
import {chromium} from '@playwright/test';

const directory=process.argv[2] || 'docs/assets';
assert(/^docs\/assets(?:\/[a-z-]+)?$/.test(directory));
const snapshot=JSON.parse(await readFile('content/generated/snapshot.json','utf8'));
assert.equal(snapshot.mode,'fixture','Use the authored synthetic translations');
const story=snapshot.stories.find(story=>story.category==='ai' && story.translations?.bn);
assert(story);
const server=spawn(process.execPath,['scripts/preview.mjs'],{env:{...process.env,PORT:'4330'},stdio:'ignore'});
let browser;
try {
  for(let i=0;i<100;i++){try{if((await fetch('http://127.0.0.1:4330')).ok)break;}catch{/* Startup. */}await new Promise(resolve=>setTimeout(resolve,100));}
  const built=await (await fetch('http://127.0.0.1:4330/data/latest.json')).json();
  assert.equal(built.mode,'fixture');assert.equal(built.generated_at,snapshot.generated_at);
  browser=await chromium.launch();const page=await browser.newPage();
  for(const [width,theme,file] of [[1280,'light','story-bangla-fixture.jpg'],[390,'dark','story-bangla-fixture-mobile.jpg']]) {
    await page.setViewportSize({width,height:width===390?844:960});
    await page.goto(`http://127.0.0.1:4330/bn/story/${story.slug}/`);
    await page.waitForFunction(()=>!document.querySelector('astro-island[ssr]'));
    await page.evaluate(theme=>{document.documentElement.dataset.theme=theme;},theme);
    await page.evaluate(()=>Promise.all(document.getAnimations().filter(animation=>animation.effect?.getComputedTiming().iterations!==Infinity && !(animation instanceof window.CSSAnimation && animation.animationName==='focus-progress')).map(animation=>animation.finished.catch(()=>{}))));
    await page.screenshot({path:`${directory}/${file}`,type:'jpeg',quality:85,fullPage:width===390});
  }
  const readme=await readFile(`${directory}/README.md`,'utf8');
  await writeFile(`${directory}/README.md`,readme.replace(/\n## Authored Bangla fixture examples[\s\S]*$/,'')+`\n## Authored Bangla fixture examples\n\nThese two real browser renders use synthetic, authored test content generated on ${snapshot.generated_at}. They are not live reporting, provider output or evidence of production Bangla coverage. The visible demonstration notice remains.\n\n- [Desktop Bangla article](story-bangla-fixture.jpg): 1280 × 960, warm theme.\n- [Mobile Bangla article](story-bangla-fixture-mobile.jpg): 390px, full page, dark theme.\n\nReproduce with fixture generation/build and \`node scripts/capture-localized-fixture.mjs ${directory}\`.\n`);
  console.log('Captured two explicitly labelled authored Bangla fixture articles.');
  await writeFile(`${directory}/fixture-capture.json`,JSON.stringify({mode:'fixture',generated_at:snapshot.generated_at,captured_at:new Date().toISOString(),images:['story-bangla-fixture.jpg','story-bangla-fixture-mobile.jpg']},null,2)+'\n');
} finally {await browser?.close();server.kill();}
