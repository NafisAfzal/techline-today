import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('explicit language choice persists across reading and refresh, preserves theme and query',async({page})=>{
  await page.goto('/all/?period=week');
  const initial=await page.locator('html').getAttribute('data-theme');
  await page.locator(`button[data-theme="${initial==='dark'?'light':'dark'}"]`).click();
  const bangla=page.locator('[data-language="bn"]');await bangla.focus();await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/\/bn\/all\/\?period=week/);await expect(page.locator('html')).toHaveAttribute('lang','bn');
  await expect(page.locator('html')).not.toHaveAttribute('data-theme',initial!);
  expect(await page.evaluate(()=>localStorage.getItem('ti:v1:language'))).toBe('bn');
  await page.reload();await expect(page.locator('[data-language="bn"]')).toHaveAttribute('aria-current','true');
  await page.locator('.brand').click();await expect(page).toHaveURL(/\/bn\/$/);
  await page.locator('[data-language="en"]').click();await expect(page).toHaveURL(/\/$/);
  await expect(page.locator('html')).toHaveAttribute('lang','en');
  expect(await page.evaluate(()=>localStorage.getItem('ti:v1:language'))).toBe('en');
});

test('five authored Bangla examples preserve numbers, technical names and source citations',async({page})=>{
  const snapshot=await (await page.request.get('/data/latest.json')).json();
  for(const category of ['ai','research','chips','security','freebies']) {
    const story=snapshot.stories.find((story:{category:string;translations?:{bn:unknown}})=>story.category===category && story.translations?.bn);
    expect(story,category).toBeTruthy();
    await page.goto(`/bn/story/${story.slug}/`);
    await expect(page.locator('h1')).toHaveText(story.translations.bn.content.headline);
    await expect(page.getByRole('heading',{name:'সারসংক্ষেপ',exact:true})).toBeVisible();
    for(const number of story.key_numbers) await expect(page.locator('main')).toContainText(number.value);
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute('href',new RegExp(`/bn/story/${story.slug}/$`));
    await expect(page.locator('link[hreflang="en"]')).toHaveAttribute('href',new RegExp(`/story/${story.slug}/$`));
    await expect(page.locator('link[hreflang="bn"]')).toHaveAttribute('href',new RegExp(`/bn/story/${story.slug}/$`));
    await expect(page.locator('.translation-note')).toContainText('মূল প্রমাণ');
    const citation=page.locator('.citation').first();await citation.click();
    await expect(page.locator((await citation.getAttribute('href'))!)).toBeVisible();
  }
});

test('missing translation has English fallback, correct SEO and a localized recovery page',async({page})=>{
  const snapshot=await (await page.request.get('/data/latest.json')).json();
  const story=snapshot.stories.find((story:{translations?:{bn:unknown}})=>!story.translations?.bn);
  await page.goto(`/bn/story/${story.slug}/`);
  await expect(page.locator('h1')).toHaveText(story.headline);await expect(page.locator('h1')).toHaveAttribute('lang',story.language || 'en');
  await expect(page.locator('.translation-note')).toContainText('বাংলা অনুবাদ নেই');
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content',/noindex/);
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute('href',new RegExp(`/story/${story.slug}/$`));
  await expect(page.locator('link[hreflang="bn"]')).toHaveCount(0);
  const response=await page.goto('/bn/missing-story/');expect(response?.status()).toBe(404);
  await expect(page.locator('html')).toHaveAttribute('lang','bn');await expect(page.locator('h1')).toHaveText('খবরটির ঠিকানা বদলে গেছে।');
  await page.getByRole('link',{name:'সব খবর দেখুন'}).click();await expect(page).toHaveURL(/\/bn\/all\/$/);
});

test('Bangla pages remain readable, wrap without overflow and pass axe in both themes',async({page})=>{
  for(const width of [320,390,834,1280,1366,1440]) {
    await page.setViewportSize({width,height:900});
    for(const theme of ['light','dark']) {
      for(const route of ['/bn/','/bn/all/','/bn/settings/','/bn/freebies/','/bn/models/']) {
        await page.goto(route);await page.waitForFunction(()=>!document.querySelector('astro-island[ssr]'));
        await page.evaluate(theme=>{document.documentElement.dataset.theme=theme;},theme);
        expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${width} ${theme} ${route}`).toBe(true);
        expect(await page.locator('body').evaluate(element=>parseFloat(getComputedStyle(element).fontSize))).toBeGreaterThanOrEqual(18);
        const overlap=await page.evaluate(()=>{
          const brand=document.querySelector('.brand')!.getBoundingClientRect();
          const actions=document.querySelector('.header-actions')!.getBoundingClientRect();
          return brand.right>actions.left+1 && brand.bottom>actions.top+1;
        });
        expect(overlap,`Header controls overlap at ${width}px`).toBe(false);
      }
    }
  }
  for(const theme of ['light','dark']) {
    await page.goto('/bn/all/');await page.evaluate(theme=>{document.documentElement.dataset.theme=theme;},theme);
    expect((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()).violations).toEqual([]);
  }
});

test('Bangla search, saved stories and preferences stay localized',async({page})=>{
  await page.goto('/bn/');await page.getByRole('button',{name:'খবর খুঁজুন'}).click();
  await page.getByLabel('খবরের সংগ্রহে খুঁজুন').fill('Meridian');
  await expect(page.locator('.search-results a').first()).toHaveAttribute('href',/^\/bn\/story\//);
  await page.keyboard.press('Escape');await page.locator('[data-bookmark]').first().click();
  await expect(page.locator('[data-bookmark]').first()).toHaveText('সংরক্ষিত ✓');
  await page.goto('/bn/saved/');await expect(page.locator('[data-story]:visible')).toHaveCount(1);
  await expect(page.locator('[data-bookmark]')).toHaveText('সংরক্ষিত ✓');
  await page.goto('/bn/settings/');await page.getByLabel('নিরাপত্তা',{exact:true}).check();
  await page.goto('/bn/all/');await expect(page.locator('[data-story]').first()).toHaveAttribute('data-category','security');
});

test('larger editorial typography and duration-free labels are rendered',async({page})=>{
  await page.setViewportSize({width:1280,height:900});await page.goto('/');
  expect(await page.locator('.wordmark').first().evaluate(element=>parseFloat(getComputedStyle(element).fontSize))).toBeGreaterThanOrEqual(38);
  expect(await page.locator('.lead-card h2').evaluate(element=>parseFloat(getComputedStyle(element).fontSize))).toBeGreaterThanOrEqual(30);
  expect(await page.locator('.lead-card .story-summary').evaluate(element=>parseFloat(getComputedStyle(element).fontSize))).toBe(18);
  expect(await page.locator('main').innerText()).not.toMatch(/\b(?:30|60)[- ]second/);
  await page.locator('.lead-card h2 a').click();
  expect(await page.locator('.detail-content li').first().evaluate(element=>parseFloat(getComputedStyle(element).fontSize))).toBe(18);
  await expect(page.getByRole('heading',{name:'Summary',exact:true})).toBeVisible();
  await expect(page.locator('.timeline')).not.toBeVisible();
  await page.getByText('View update history',{exact:true}).focus();await page.keyboard.press('Enter');
  await expect(page.locator('.timeline')).toBeVisible();
  await expect(page.locator('.timeline li').first()).toContainText('First published');
});

test('localized static reading works without JavaScript and blocked storage',async({browser,baseURL})=>{
  const context=await browser.newContext({javaScriptEnabled:false});const page=await context.newPage();
  await page.goto(`${baseURL}/bn/`);await page.locator('#briefing h3 a').first().click();
  await expect(page.locator('html')).toHaveAttribute('lang','bn');
  await expect(page.getByRole('heading',{name:'সারসংক্ষেপ',exact:true})).toBeVisible();
  await page.locator('[data-language="en"]').click();await expect(page.locator('html')).toHaveAttribute('lang','en');
  await context.close();
});
