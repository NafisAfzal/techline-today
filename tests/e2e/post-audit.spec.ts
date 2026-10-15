import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('news and research remain distinct and dated without promising fresh coverage',async({page})=>{
  await page.goto('/');
  await expect(page.locator('h1')).toHaveText('Technology news & research');
  await expect(page.getByRole('complementary',{name:'Coverage and freshness'})).toBeVisible();
  await page.getByRole('link',{name:'Browse news',exact:true}).click();
  await expect(page).toHaveURL(/\/news\/$/);
  await expect(page.locator('h1')).toHaveText('News & official announcements');
  const cards=page.locator('[data-story]');
  if (await cards.count()) {
    for (const card of await cards.all()) await expect(card).not.toHaveAttribute('data-category','research');
  } else {
    await expect(page.locator('[data-empty-news]')).toContainText('No current-news coverage in this edition.');
    await expect(page.getByRole('link',{name:'Research & technical analysis',exact:true})).toHaveAttribute('href','/category/research/');
  }
});

test('Bangla English-content indicators agree on cards, article and saved list',async({page})=>{
  const snapshot=await (await page.request.get('/data/latest.json')).json();
  const story=snapshot.stories.find((item:{translations?:{bn:unknown}})=>!item.translations?.bn);
  expect(story,'Dataset must include an untranslated story for this regression').toBeTruthy();
  await page.goto('/bn/');
  for (const row of await page.locator('[data-variant="briefing"]').all()) {
    const link=await row.locator('h3 a').getAttribute('href');
    const canonical=snapshot.stories.find((item:{slug:string})=>link===`/bn/story/${item.slug}/`);
    expect(canonical).toBeTruthy();
    await expect(row.locator('[data-language-fallback]')).toHaveCount(canonical.translations?.bn ? 0 : 1);
  }
  await page.goto('/bn/all/');
  const card=page.locator(`[data-story="${story.id}"]`);
  await expect(card.locator('[data-language-fallback]')).toHaveText('ইংরেজি লেখা');
  await expect(card.locator('[data-language-fallback]')).toHaveAttribute('aria-label',/বাংলা অনুবাদ নেই/);
  await card.locator('h3 a').click();
  await expect(page.locator('h1')).toHaveAttribute('lang','en');
  await expect(page.locator('[data-language-fallback]')).toBeVisible();
  await expect(page.locator('.translation-note')).toContainText('ইংরেজি দেখানো হচ্ছে');
  await page.locator('[data-bookmark]').click();
  await page.goto('/bn/saved/');
  await expect(page.locator('[data-language-fallback]')).toHaveText('ইংরেজি লেখা');
});

test('primary provenance and preprint uncertainty remain clear on article details',async({page})=>{
  const snapshot=await (await page.request.get('/data/latest.json')).json();
  const story=snapshot.stories.find((item:{category:string})=>item.category==='research');
  expect(story,'Dataset must include research for the trust regression').toBeTruthy();
  const payload=await (await page.request.get(`/data/stories/${story.slug}.json`)).json();
  const arxiv=payload.sources.some((source:{source_registry_id:string;source_type:string})=>source.source_type==='arxiv' || source.source_registry_id==='arxiv');
  for (const theme of ['light','dark']) {
    await page.goto(`/story/${story.slug}/`);
    await page.evaluate(value=>{document.documentElement.dataset.theme=value;},theme);
    await expect(page.locator('.evidence')).toHaveText('Primary source');
    await expect(page.locator('[data-trust-explanation]')).toContainText('No independent reporting');
    await expect(page.locator('.evidence')).toHaveAttribute('title',/does not establish peer review/);
    if (arxiv) {
      await expect(page.locator('.content-indicator')).toHaveText('Preprint');
      await expect(page.locator('#uncertainty')).toContainText('peer review has not been established');
      await expect(page.locator('#uncertainty')).toContainText('limitations have not been assessed');
    }
    await expect(page.getByRole('heading',{name:'Before you act',exact:true})).toHaveCount(0);
    await expect(page.getByRole('heading',{name:'Editorial interpretation',exact:true})).toHaveCount(0);
  }
});

for (const width of [320,390,1280]) test(`coverage, language chips and news states wrap accessibly at ${width}px`,async({page})=>{
  await page.setViewportSize({width,height:900});
  for (const theme of ['light','dark']) for (const route of ['/','/bn/','/news/','/bn/news/']) {
    await page.goto(route);
    await page.evaluate(value=>{document.documentElement.dataset.theme=value;},theme);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${route} ${theme}`).toBe(true);
  }
  await page.goto('/bn/all/');
  expect((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()).violations).toEqual([]);
});
