import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
test('briefing, details, evidence and safe original link',async({page})=>{
  const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));
  const response=await page.goto('/');
  expect(response?.headers()['content-security-policy']).toContain("frame-ancestors 'none'");
  await expect(page.getByRole('heading',{name:'In this edition'})).toBeVisible();
  await expect(page.getByLabel('Demonstration notice')).toBeVisible();
  await page.locator('#briefing h3 a').first().click();
  await expect(page.getByRole('heading',{name:'Summary',exact:true})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Sources',exact:true})).toBeVisible();
  const link=page.getByRole('link',{name:'Read the original source'});
  await expect(link).toHaveAttribute('target','_blank');await expect(link).toHaveAttribute('rel','noopener noreferrer');
  expect(await link.getAttribute('href')).toMatch(/^https:\/\//);
  expect(errors).toEqual([]);
});
test('bookmark and read state persist; saved list can remove items',async({page})=>{
  await page.goto('/');const save=page.locator('[data-bookmark]').first();await save.click();await expect(save).toHaveAttribute('aria-pressed','true');
  await page.reload();await expect(page.locator('[data-bookmark]').first()).toHaveAttribute('aria-pressed','true');
  await page.goto('/saved/');await expect(page.locator('[data-story]:visible')).toHaveCount(1);
  await page.locator('[data-read]:visible').click();await page.reload();await expect(page.locator('[data-read]:visible')).toHaveAttribute('aria-pressed','true');
  await page.locator('[data-bookmark]:visible').click();await expect(page.locator('[data-empty]')).toBeVisible();
});
test('keyboard search finds model, routes to a result, and closes with Escape',async({page})=>{
  await page.goto('/');await page.getByRole('button',{name:'Search stories'}).click();await page.getByLabel('Search the intelligence archive').fill('Meridian');
  await expect(page.locator('.search-results a').first()).toBeVisible();await expect(page.locator('.search-results')).toContainText('Meridian');
  await page.keyboard.press('Escape');await expect(page.locator('dialog')).not.toBeVisible();
  await page.keyboard.press('/');await expect(page.locator('dialog')).toBeVisible();await page.locator('.search-results a').first().click();await expect(page.locator('h1')).toContainText('Meridian');
});
test('theme, category preferences, empty period and 404',async({page})=>{
  await page.goto('/');const initial=await page.locator('html').getAttribute('data-theme');await page.locator(`button[data-theme="${initial==='dark'?'light':'dark'}"]`).click();await page.reload();expect(await page.locator('html').getAttribute('data-theme')).not.toBe(initial);
  await page.goto('/settings/');await page.getByLabel('Security',{exact:true}).check();await page.getByLabel('Reading density').selectOption('compact');await page.goto('/all/');await expect(page.locator('[data-story]').first()).toHaveAttribute('data-category','security');
  await page.goto('/category/dev-apis/');await expect(page.getByRole('heading',{name:'Dev & APIs',exact:true})).toBeVisible();
  const response=await page.goto('/missing-route/');expect(response?.status()).toBe(404);await expect(page.getByRole('heading',{name:'This story took another turn.'})).toBeVisible();
});
test('trackers, digests and archived sources',async({page})=>{
  await page.goto('/freebies/');await expect(page.getByRole('heading',{name:'Expired offer archive'})).toBeVisible();await expect(page.locator('.badge.expiring')).toBeVisible();
  await page.goto('/models/');await expect(page.locator('.tracker-card')).toContainText('128K');
  await page.goto('/digests/');await page.locator('.digest-list a').first().click();await expect(page.getByRole('heading',{name:'Watch next'})).toBeVisible();
  await page.goto('/archives/');await page.locator('.digest-list a').first().click();await expect(page.getByRole('link',{name:'Download structured archive'})).toBeVisible();
});
test('no horizontal overflow at phone, tablet and desktop sizes',async({page})=>{
  for(const width of [320,360,390,430,768,834,1280,1440]) {
    await page.setViewportSize({width,height:900});
    for(const route of ['/','/models/','/freebies/','/settings/']) {
      await page.goto(route);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
    }
  }
});
test('core routes pass axe in light and dark themes',async({page})=>{
  for(const theme of ['light','dark']) {
    await page.goto('/');await page.evaluate(value=>{document.documentElement.dataset.theme=value;},theme);
    const routes=['/','/models/','/freebies/','/about/','/settings/'];
    for(const route of routes) {
      await page.goto(route);await page.evaluate(value=>{document.documentElement.dataset.theme=value;},theme);
      const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();expect(result.violations).toEqual([]);
    }
    await page.goto('/');await page.locator('#briefing h3 a').first().click();await page.evaluate(value=>{document.documentElement.dataset.theme=value;},theme);
    expect((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()).violations).toEqual([]);
  }
});

test('period filters survive reload and browser back', async({page}) => {
  await page.goto('/all/');
  await page.getByRole('button',{name:'Today',exact:true}).click();
  await expect(page).toHaveURL(/period=today/);
  await page.reload();
  await expect(page.getByRole('button',{name:'Today',exact:true})).toHaveAttribute('aria-pressed','true');
  await page.getByRole('button',{name:'This month',exact:true}).click();
  await page.goBack();
  await expect(page.getByRole('button',{name:'Today',exact:true})).toHaveAttribute('aria-pressed','true');
});

test('blocked storage and unavailable search show usable error states', async({page}) => {
  await page.addInitScript(() => Object.defineProperty(window,'localStorage',{get(){throw new Error('Storage blocked');}}));
  await page.route('**/pagefind/**', route=>route.abort());
  await page.route('**/data/search.json', route=>route.abort());
  await page.goto('/');
  await page.locator('[data-bookmark]').first().click();
  await expect(page.locator('[data-action-status]')).toContainText('Browser storage is unavailable');
  await page.getByRole('button',{name:'Search stories'}).click();
  await page.getByLabel('Search the intelligence archive').fill('Meridian');
  await expect(page.locator('.search-status')).toContainText('Search is temporarily unavailable');
  await page.keyboard.press('Escape');
  await expect(page.locator('dialog')).not.toBeVisible();
});

test('briefings and original citations work without JavaScript', async({browser,baseURL}) => {
  const context=await browser.newContext({javaScriptEnabled:false});
  const page=await context.newPage();
  await page.goto(baseURL!);
  await page.locator('#briefing h3 a').first().click();
  await expect(page.getByRole('heading',{name:'Summary',exact:true})).toBeVisible();
  await expect(page.getByRole('link',{name:'Read the original source'})).toHaveAttribute('href',/^https:\/\//);
  await context.close();
});
