import assert from 'node:assert/strict';
import { chromium } from '@playwright/test';
import { readFile, writeFile } from 'node:fs/promises';

const snapshot=JSON.parse(await readFile('content/generated/snapshot.json','utf8'));
assert.equal(snapshot.mode,'live','Capture the source-backed edition separately from fixtures');
const base='http://127.0.0.1:4321';
const built=await (await fetch(`${base}/data/latest.json`)).json();
assert.equal(built.generated_at,snapshot.generated_at,'Rebuild the local preview first');
assert.equal(built.mode,'live');
const directory='docs/assets/owner-portal';
const fixtureCapture=JSON.parse(await readFile(`${directory}/fixture-capture.json`,'utf8'));
assert.equal(fixtureCapture.mode,'fixture');
const browser=await chromium.launch();
try {
  const page=await browser.newPage({reducedMotion:'reduce'});
  for(const width of [1366,390]) {
    await page.setViewportSize({width,height:width===390?844:960});
    await page.goto(base,{waitUntil:'networkidle'});
    await page.evaluate(()=>{document.documentElement.dataset.theme='light';});
    const clip=await page.locator('.category-index').evaluate(element=>{
      const first=element.getBoundingClientRect();
      const last=document.querySelector('.tools-section').getBoundingClientRect();
      return {x:first.x+window.scrollX,y:first.y+window.scrollY,width:first.width,height:last.bottom-first.top};
    });
    await page.screenshot({path:`${directory}/category-through-trackers-${width}.jpg`,type:'jpeg',quality:85,fullPage:true,clip});
  }
  const readme=(await readFile(`${directory}/README.md`,'utf8')).replace('The complete six-width, two-theme, two-language screenshot matrices remain under ignored .cache/visual/.','The current matrices are in the local %TEMP%/techline-deep-review/owner-approval-live/ and owner-approval-fixture/ review directories.');
  await writeFile(`${directory}/README.md`,readme+`\n\n## Complete complaint area\n\nThese local live captures show the entire topic directory, More stories and Tools & trackers in one image. Reduced motion was enabled to settle the strip during capture. Reproduce with \`node scripts/capture-owner-area.mjs\` while localhost:4321 serves the current build.\n\n- [Desktop category-through-trackers](category-through-trackers-1366.jpg): 1366px.\n- [Mobile category-through-trackers](category-through-trackers-390.jpg): 390px.\n\n## Authored Bangla fixture examples\n\nThe two article images below were captured before live ingestion from the synthetic fixture generated at ${fixtureCapture.generated_at}. They retain the demonstration notice and are not live translations or evidence of provider quality. The capture metadata is in \`fixture-capture.json\`.\n\n- [Desktop Bangla fixture article](story-bangla-fixture.jpg): 1280px, light.\n- [Mobile Bangla fixture article](story-bangla-fixture-mobile.jpg): 390px, dark.\n`);
  console.log('Captured complete owner complaint area on desktop and mobile.');
} finally {await browser.close();}
