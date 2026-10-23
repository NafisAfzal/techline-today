import fs from 'node:fs';
import path from 'node:path';
import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const latest = JSON.parse(fs.readFileSync('apps/web/dist-research/data/latest.json','utf8'));
const fallbackStory = latest.stories.find(story => !story.translations?.bn);
const slug = fallbackStory.slug;
test('research notice, headers, search and English fallback preserve the reading flow', async ({page},testInfo) => {
  const errors:string[] = [];
  const external:string[] = [];
  page.on('pageerror',error => errors.push(error.message));
  page.on('request',request => {if (!request.url().startsWith('http://127.0.0.1:4337')) external.push(request.url());});
  const response = await page.goto('/');
  expect(response?.headers()['x-robots-tag']).toContain('noindex');
  expect(response?.headers()['cache-control']).toContain('no-store');
  await expect(page.getByLabel('Research edition notice')).toContainText('Synthetic examples only');
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content','noindex, nofollow');
  await page.getByRole('button',{name:'Search stories'}).click();
  await page.getByLabel('Search the intelligence archive').fill('retrieval');
  await expect(page.locator('.search-results a').first()).toBeVisible();
  await page.getByLabel('Search the intelligence archive').fill('Meridian');
  await expect(page.locator('.search-results a')).toHaveCount(0);
  await page.keyboard.press('Escape');
  await page.goto(`/bn/story/${slug}/`);
  await expect(page.locator('.research-edition-notice')).toBeVisible();
  expect(await page.locator('link[rel="canonical"]').getAttribute('href')).toContain(`/story/${slug}/`);
  expect(await page.locator('link[rel="canonical"]').getAttribute('href')).not.toContain('/bn/');
  await expect(page.locator('h1')).toContainText(fallbackStory.headline);
  expect(errors).toEqual([]);
  expect(external).toEqual([]);
  await page.goto('/');
  if (process.env.RESEARCH_SCREENSHOT_DIR && ['desktop','mobile'].includes(testInfo.project.name)) {
    fs.mkdirSync(process.env.RESEARCH_SCREENSHOT_DIR,{recursive:true});
    await page.screenshot({path:path.join(process.env.RESEARCH_SCREENSHOT_DIR,`${testInfo.project.name}.png`),fullPage:true});
  }
});

test('all generated HTML routes and key assets serve without redirects to a SPA', async ({request}) => {
  const root = 'apps/web/dist-research';
  const walk = (directory:string):string[] => fs.readdirSync(directory,{withFileTypes:true}).flatMap(entry => entry.isDirectory() ? walk(path.join(directory,entry.name)) : [path.join(directory,entry.name)]);
  const files = walk(root).filter(file => file.endsWith('.html') || /(?:\.wasm|favicon\.svg|theme\.js|rss\.xml|robots\.txt|content-attribution\.json)$/.test(file));
  for (const file of files) {
    const url = '/' + path.relative(root,file).replaceAll('\\','/').replace(/index\.html$/,'');
    const response = await request.get(url);
    expect(response.status(),url).toBe(200);
    expect(response.headers()['x-robots-tag'],url).toContain('noindex');
  }
  expect((await request.get('/missing-research-route/')).status()).toBe(404);
  expect((await request.get('/bn/missing-research-route/')).status()).toBe(404);
  for (const url of ['/data/offers.json','/data/models.json']) expect(await (await request.get(url)).json()).toEqual([]);
  for (const url of ['/.env','/.cache/authority/journal.json','/data/archives/2020-01.json']) expect((await request.get(url)).status()).toBe(404);
});

test('research routes are accessible and fit narrow screens in both themes', async ({page}) => {
  test.setTimeout(120000);
  for (const theme of ['light','dark']) for (const url of ['/','/bn/',`/story/${slug}/`,`/bn/story/${slug}/`,'/all/','/freebies/','/models/']) {
    await page.goto(url);
    await page.evaluate(value => {document.documentElement.dataset.theme=value;},theme);
    expect((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()).violations).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
});
