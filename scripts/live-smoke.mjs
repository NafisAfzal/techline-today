import assert from 'node:assert/strict';
import fs from 'node:fs';
import { spawn } from 'node:child_process';
import { chromium } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const snapshot = JSON.parse(fs.readFileSync('content/generated/snapshot.json', 'utf8'));
assert.equal(snapshot.mode, 'live', 'Run live ingestion and build first');
assert(snapshot.stories.length > 0);
assert(snapshot.stories.every(story => !story.is_demo));
const story = snapshot.stories[0];
const detail = `/story/${story.slug}/`;
const base = 'http://127.0.0.1:4323';
const server = spawn(process.execPath, ['scripts/preview.mjs'], {env: {...process.env, PORT: '4323'}, stdio: 'ignore'});
let browser;
try {
  let ready = false;
  for (let attempt = 0; attempt < 60; attempt++) {
    try { ready = (await fetch(base)).ok; } catch { /* Preview is starting. */ }
    if (ready) break;
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  assert(ready, 'Local preview did not start');
  const built = await (await fetch(base + '/data/latest.json')).json();
  assert.equal(built.generated_at, snapshot.generated_at, 'Rebuild after ingestion');
  browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {
    // Deliberate recovery-page requests produce a browser network diagnostic.
    const expected404=message.location().url===base+'/missing-page/' && message.text()==='Failed to load resource: the server responded with a status of 404 (Not Found)';
    if(message.type()==='error' && !expected404) errors.push(message.text());
  });
  const response = await page.goto(base);
  assert.equal(response.headers()['content-encoding'], 'gzip');
  assert(response.headers()['content-security-policy'].includes("frame-ancestors 'none'"));
  assert.equal(await page.getByLabel('Demonstration notice').count(), 0);
  assert.equal(await page.locator('#briefing h3 a').count(), Math.min(4, Math.max(0,snapshot.stories.length-1)));
  await page.goto(base + '/all/');
  if (snapshot.stories.length > 24) {
    assert.equal(await page.locator('.story-grid [data-story]').count(), 24);
    const more = page.getByRole('button', {name:'Show more stories'});
    await more.click();
    assert.equal(await page.locator('.story-grid [data-story]').count(), Math.min(48, snapshot.stories.length, 120));
    while (await more.isVisible()) await more.click();
    assert.equal(await page.locator('.story-grid [data-story]').count(), Math.min(120, snapshot.stories.length));
    await page.reload();
    await page.getByRole('button', {name:'Today', exact:true}).click();
    assert.equal(await page.locator('.story-grid [data-story]').count(), Math.min(120, snapshot.stories.length));
  }
  await page.goto(base + detail);
  assert.equal(await page.locator('h1').textContent(), story.headline);
  const original = page.getByRole('link', {name: 'Read the original source'});
  assert.equal(await original.getAttribute('href'), snapshot.sources[story.primary_source_id || story.source_ids[0]].original_url);
  assert.equal(await original.getAttribute('rel'), 'noopener noreferrer');
  await page.goto(base);
  const save = page.locator('[data-bookmark]').first();
  await save.click();
  await page.goto(base + '/saved/');
  await page.locator('[data-story]:visible').waitFor();
  assert.equal(await page.locator('[data-story]:visible').count(), 1);
  await page.goto(base);
  await page.getByRole('button', {name: 'Search stories'}).click();
  const query = story.headline.match(/[A-Za-z]{5,}/)?.[0];
  assert(query, 'Expected a searchable headline');
  await page.getByLabel('Search the intelligence archive').fill(query);
  await page.locator('.search-results a').first().waitFor();
  await page.keyboard.press('Escape');
  for (const width of [320, 390, 834, 1280, 1366, 1440]) {
    await page.setViewportSize({width, height: 900});
    for (const route of ['/', '/all/', detail, '/freebies/', '/models/', '/category/ai/', '/category/chips/', '/digests/', '/settings/', '/saved/', '/about/', '/archives/', '/missing-page/']) {
      const result = await page.goto(base + route);
      assert.equal(result.status(), route==='/missing-page/'?404:200);
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), `Overflow at ${width}px on ${route}`);
    }
  }
  if (!snapshot.archive_index.length) {
    await page.goto(base+'/archives/');
    assert((await page.locator('.empty-state').textContent()).includes('Monthly bundles appear'));
    await page.goto(base+'/missing-page/');
    assert.equal(await page.locator('main a[href="/archives/"]').count(),0,'Do not direct recovery into an empty archive');
  }
  for (const offer of snapshot.offers) {
    await page.goto(base + '/freebies/');
    assert((await page.locator('main').textContent()).includes(offer.value_text));
    const link = page.locator('a').filter({hasText: 'Official offer terms'});
    assert((await link.evaluateAll(elements => elements.map(element => element.getAttribute('href')))).includes(offer.official_source_url));
  }
  for (const theme of ['light', 'dark']) {
    for (const route of ['/', detail, '/freebies/', '/models/']) {
      await page.goto(base + route);
      await page.evaluate(value => {document.documentElement.dataset.theme = value;}, theme);
      const result = await new AxeBuilder({page}).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
      assert.deepEqual(result.violations, [], `Accessibility on ${route} in ${theme}`);
    }
  }
  for (const route of ['/rss.xml', '/sitemap-index.xml', '/robots.txt', '/data/story-index.json']) {
    assert.equal((await fetch(base + route)).status, 200);
  }
  assert.deepEqual(errors, []);
  fs.mkdirSync('.cache/audit', {recursive:true});
  await page.goto(base);
  await page.evaluate(() => {document.documentElement.dataset.theme = 'light';});
  await page.setViewportSize({width:1280,height:960});
  await page.screenshot({path:'.cache/audit/desktop.png'});
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:'.cache/audit/mobile.png'});
  console.log(JSON.stringify({status: 'passed', mode: snapshot.mode, stories: snapshot.stories.length, offers: snapshot.offers.length, widths: [320,390,834,1280,1366,1440], accessibility: 'warm and dark', consoleErrors: errors.length}, null, 2));
} finally {
  await browser?.close();
  server.kill();
}
