import {expect,test} from '@playwright/test';

test('theme metadata follows explicit choice and reload; wordmark is protected',async({page})=>{
  await page.goto('/');
  await expect(page.locator('meta[name="viewport"]')).toHaveAttribute('content',/viewport-fit=cover/);
  await expect(page.locator('.brand .wordmark')).toHaveAttribute('translate','no');
  const toggle=page.locator('button[data-theme="dark"]');
  await toggle.click();
  const theme=await page.locator('html').getAttribute('data-theme');
  await expect(toggle).toHaveAttribute('aria-pressed','true');
  await expect(page.locator('button[data-theme="light"]')).toHaveAttribute('aria-pressed','false');
  for(const meta of await page.locator('meta[name="theme-color"]').all()) await expect(meta).toHaveAttribute('content',theme==='dark'?'#101c2d':'#f4f2eb');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme',theme!);
  for(const meta of await page.locator('meta[name="theme-color"]').all()) await expect(meta).toHaveAttribute('content',theme==='dark'?'#101c2d':'#f4f2eb');
});

test('categories navigate and further stories do not repeat the lead or brief',async({page})=>{
  for(const route of ['/','/bn/']) {
    await page.goto(route);
    const featured=await page.locator('.lead-card h2 a,#briefing h3 a').evaluateAll(links=>links.map(link=>link.getAttribute('href')));
    expect(featured.length).toBe(5);
    await expect(page.locator('.category-tile')).toHaveCount(9);
    await expect(page.locator('[data-category-preview]')).toHaveCount(0);
    for(const link of await page.locator('.more-stories h3 a').all()) expect(featured).not.toContain(await link.getAttribute('href'));
  }
});

test('evidence links behave consistently in brief, cards, detail and saved view',async({page})=>{
  await page.goto('/');
  await page.locator('[data-bookmark]').first().click();
  const detail=await page.locator('.lead-card h2 a').getAttribute('href');
  for(const route of ['/','/all/',detail!,'/saved/']) {
    await page.goto(route);
    await page.waitForFunction(()=>!document.querySelector('astro-island[ssr]'));
    await expect(page.locator('.evidence').first()).toBeVisible();
    expect(await page.locator('.evidence').count()).toBeGreaterThan(0);
    for(const evidence of await page.locator('.evidence').all()) {
      await expect(evidence).toHaveAttribute('href','/about/#evidence');
      expect(await evidence.evaluate(element=>element.getBoundingClientRect().height)).toBeGreaterThanOrEqual(44);
    }
  }
  await page.locator('.evidence').first().click();
  await expect(page).toHaveURL(/\/about\/#evidence$/);
});

test('search handles debounce, stale queries, clearing and localized no-results',async({page})=>{
  await page.route('**/pagefind/**',route=>route.abort());
  let indexRequests=0;
  await page.route('**/data/search-bn.json',async route=>{
    indexRequests++;
    await new Promise(resolve=>setTimeout(resolve,250));
    await route.continue();
  });
  await page.goto('/bn/');await page.locator('.search-trigger').click();
  const input=page.locator('#search-query');
  await input.fill('Meridian');
  await expect.poll(()=>indexRequests).toBe(1);
  await input.fill('zzzz-no-match');
  await expect(page.locator('.search-status')).toHaveText('কোনো ফল পাওয়া যায়নি। অন্য শব্দ দিয়ে খুঁজুন।');
  await expect(page.locator('.search-results a')).toHaveCount(0);
  expect(indexRequests).toBe(1);
  await input.fill('Meridian');await input.fill('');
  await expect(page.locator('.search-results a')).toHaveCount(0);
  await page.keyboard.press('Escape');await expect(page.locator('.search-trigger')).toBeFocused();
});

test('search dialog keeps internal padding clicks open and closes at the backdrop',async({page})=>{
  await page.goto('/');const trigger=page.locator('.search-trigger');await trigger.click();
  const dialog=page.locator('dialog');const bounds=await dialog.boundingBox();
  await page.mouse.click(bounds!.x+5,bounds!.y+5);await expect(dialog).toBeVisible();
  await page.mouse.click(2,2);await expect(dialog).not.toBeVisible();await expect(trigger).toBeFocused();
});

test('search previews show story prose without reader-control labels',async({page})=>{
  await page.goto('/');await page.locator('.search-trigger').click();await page.locator('#search-query').fill('Meridian');
  const preview=page.locator('.search-results span').first();
  await expect(preview).toContainText('Meridian');
  await expect(preview).not.toContainText('Original source');await expect(preview).not.toContainText('Extractive summary');
  expect((await preview.textContent())!.length).toBeLessThanOrEqual(220);
  await expect(page.locator('.search-results a').first()).toHaveAttribute('lang','en');
});

test('save feedback preserves card geometry and original sources stay visible',async({page})=>{
  await page.goto('/');const lead=page.locator('.lead-card');
  const before=await lead.boundingBox();await lead.locator('[data-bookmark]').click();
  await expect(lead.locator('[data-action-status]')).toContainText('Reading list updated');
  const after=await lead.boundingBox();expect(after!.height).toBe(before!.height);
  await page.goto('/all/');
  for(const card of await page.locator('.story-grid [data-story]').all()) await expect(card.locator('a[target="_blank"]')).toHaveAttribute('rel','noopener noreferrer');
});

test('reduced motion keeps headlines stable and all page motion disabled',async({page})=>{
  await page.emulateMedia({reducedMotion:'reduce'});await page.goto('/');
  const headline=await page.locator('.lead-card h2').textContent();
  expect(await page.locator('.intro').evaluate(element=>getComputedStyle(element,'::after').animationName)).toBe('none');
  await page.locator('button[data-theme="dark"]').click();
  expect(await page.locator('.appearance-option svg').first().evaluate(element=>getComputedStyle(element).transitionDuration)).toBe('0s');
  await page.locator('.search-trigger').click();
  expect(await page.evaluate(()=>document.getAnimations().length)).toBe(0);
  await page.keyboard.press('Escape');await expect(page.locator('.lead-card h2')).toHaveText(headline!);
});

test('More closes with Escape and outside press; article contents navigate to evidence',async({page})=>{
  await page.goto('/');const summary=page.locator('.more-nav summary');await summary.focus();await page.keyboard.press('Enter');
  await page.locator('.more-menu a').first().focus();await page.keyboard.press('Escape');
  await expect(page.locator('.more-nav')).not.toHaveAttribute('open');await expect(summary).toBeFocused();
  await summary.click();await page.locator('.intro h1').click({position:{x:5,y:5}});await expect(page.locator('.more-nav')).not.toHaveAttribute('open');
  await page.locator('.lead-card h2 a').click();await page.locator('.reading-nav a[href="#sources"]').click();
  await expect(page).toHaveURL(/#sources$/);await expect(page.locator('#sources')).toBeInViewport();
});

test('saved downloads are bounded and reused when read state changes',async({page})=>{
  const snapshot=await (await page.request.get('/data/latest.json')).json();
  const ids=snapshot.stories.map((story:{id:string})=>story.id);
  await page.addInitScript(ids=>localStorage.setItem('ti:v1:bookmarks',JSON.stringify(ids)),ids);
  let active=0,maxActive=0,downloads=0;
  await page.route('**/data/stories/*.json',async route=>{
    active++;downloads++;maxActive=Math.max(maxActive,active);
    await new Promise(resolve=>setTimeout(resolve,100));
    await route.continue();active--;
  });
  await page.goto('/saved/');await expect(page.locator('[data-story]')).toHaveCount(ids.length);
  expect(maxActive).toBeGreaterThan(1);expect(maxActive).toBeLessThanOrEqual(8);
  expect(downloads).toBe(ids.length);
  await page.locator('[data-read]').first().click();await expect(page.locator('[data-read]').first()).toHaveAttribute('aria-pressed','true');
  expect(downloads).toBe(ids.length);
});
