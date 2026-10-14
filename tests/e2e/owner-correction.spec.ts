import {expect,test} from '@playwright/test';

test('secondary titles and inline metadata retain clear word boundaries',async({page})=>{
  for(const prefix of ['','/bn']) {
    for(const route of ['/all/','/freebies/','/models/','/settings/','/digests/']) {
      await page.goto(prefix+route);
      await expect(page.locator('.page-intro>.eyebrow')).toHaveCount(0);
    }
    await page.goto(prefix+'/all/');
    const introduction=await page.locator('.page-intro>p').innerText();
    if(!prefix) expect(introduction).toContain('with reading preferences');
    await page.goto(prefix+'/models/');
    for(const date of await page.locator('.tracker-heading time,.tracker-body .small time').all()) {
      const text=await date.evaluate(element=>element.parentElement!.textContent!);
      expect(text).toMatch(/\s/);
      const before=await date.evaluate(element=>element.previousSibling?.textContent);
      expect(before).toMatch(/\s$/);
      const after=await date.evaluate(element=>element.nextSibling?.textContent);
      if(after) expect(after).toMatch(/^\s/);
    }
  }
});

test('category navigation, further news and trackers are separate named sections',async({page})=>{
  for(const route of ['/','/bn/']) {
    await page.goto(route);
    await expect(page.locator('.category-index nav')).toHaveCount(1);
    await expect(page.locator('.category-tile')).toHaveCount(9);
    for(const tile of await page.locator('.category-tile').all()) {
      await expect(tile).toHaveAttribute('href',/\/category\//);
      await expect(tile.locator('.category-description')).not.toHaveText('');
      await expect(tile.locator('.category-open')).toBeVisible();
      await expect(tile.locator('h3,[data-category-preview]')).toHaveCount(0);
    }
    await expect(page.locator('.more-stories h2')).toHaveText(route==='/'?'More stories':'আরও খবর');
    await expect(page.locator('.more-stories [data-story]')).toHaveCount(3);
    for(const story of await page.locator('.more-stories [data-story]').all()) await expect(story.locator('a[target="_blank"]')).toBeVisible();
    await expect(page.locator('.tools-section h2')).toHaveText(route==='/'?'Tools & trackers':'টুল ও ট্র্যাকার');
    await expect(page.locator('.tools-section h3')).toHaveCount(2);
    await expect(page.locator('.latest-entry')).toHaveCount(0);
    expect(await page.locator('.tools-section').evaluate(element=>getComputedStyle(element).backgroundColor)).not.toBe(await page.locator('.category-index').evaluate(element=>getComputedStyle(element).backgroundColor));
  }
});

test('appearance has visible state and a stable target in both languages and all widths',async({page})=>{
  for(const width of [320,390,834,1280,1366,1440]) for(const route of ['/','/bn/']) {
    await page.setViewportSize({width,height:960});await page.goto(route);
    const original=await page.locator('html').getAttribute('data-theme');
    const group=page.getByRole('group',{name:route==='/'?'Appearance':'থিম',exact:true});
    const before=await group.boundingBox();
    await expect(group.getByRole('button')).toHaveCount(2);
    for(const choice of ['light','dark']) {
      const option=group.locator(`[data-theme="${choice}"]`);
      await expect(option.locator('span')).toBeVisible();
      await expect(option).toHaveAttribute('aria-pressed',String(original===choice));
      expect((await option.boundingBox())!.height).toBeGreaterThanOrEqual(44);
    }
    const button=group.locator(`[data-theme="${original==='dark'?'light':'dark'}"]`);
    await button.click();
    const theme=await page.locator('html').getAttribute('data-theme');expect(theme).not.toBe(original);
    await expect(button).toHaveAttribute('aria-pressed','true');
    await button.click();await expect(page.locator('html')).toHaveAttribute('data-theme',theme!);
    const after=await group.boundingBox();expect(after!.width).toBe(before!.width);expect(after!.height).toBe(before!.height);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  }
  await page.reload();await expect(page.locator(`button[data-theme="${await page.locator('html').getAttribute('data-theme')}"]`)).toHaveAttribute('aria-pressed','true');
});

test('focus headlines rotate through actual stationary stories without shifting the page',async({page})=>{
  await page.clock.install();await page.goto('/');
  const strip=page.locator('[data-news-focus]');await expect(strip).toHaveAttribute('data-motion','running');
  const headline=page.locator('[data-focus-link]');const first=await headline.textContent();
  const lead=await page.locator('.lead-card h2').textContent();
  const before=await strip.boundingBox();const leadBefore=await page.locator('.lead-card').boundingBox();
  const hrefs=await page.locator('.lead-card h2 a,#briefing h3 a').evaluateAll(links=>links.map(link=>link.getAttribute('href')));
  await page.clock.fastForward(12500);
  await expect(headline).not.toHaveText(first!);expect(hrefs).toContain(await headline.getAttribute('href'));
  await expect(page.locator('.lead-card h2')).toHaveText(lead!);
  const after=await strip.boundingBox();const leadAfter=await page.locator('.lead-card').boundingBox();
  expect(after!.height).toBe(before!.height);expect(leadAfter!.y).toBe(leadBefore!.y);
  await headline.focus();await headline.click();await expect(page).toHaveURL(/\/story\//);
});

test('headline rotation pauses on hover and keyboard focus',async({page})=>{
  await page.clock.install();await page.goto('/');
  const strip=page.locator('[data-news-focus]');await expect(strip).toHaveAttribute('data-motion','running');
  const headline=page.locator('[data-focus-link]');const first=await headline.textContent();
  await page.locator('.focus-label').hover();await expect(strip).toHaveAttribute('data-motion','paused');
  await page.clock.fastForward(25000);await expect(headline).toHaveText(first!);
  await page.mouse.move(2,2);await expect(strip).toHaveAttribute('data-motion','running');
  await page.locator('.focus-headline').hover();await expect(strip).toHaveAttribute('data-motion','paused');
  await page.clock.fastForward(25000);await expect(headline).toHaveText(first!);
  await page.mouse.move(2,2);await expect(strip).toHaveAttribute('data-motion','running');
  await headline.focus();await expect(strip).toHaveAttribute('data-motion','paused');
  const focus=await headline.evaluate(element=>({visible:element.matches(':focus-visible'),wrapperWidth:parseFloat(getComputedStyle(element.parentElement!).outlineWidth),wrapperStyle:getComputedStyle(element.parentElement!).outlineStyle}));
  expect(focus.visible).toBe(true);expect(focus.wrapperWidth).toBeGreaterThanOrEqual(3);expect(focus.wrapperStyle).toBe('solid');
  await page.clock.fastForward(25000);await expect(headline).toHaveText(first!);
  await page.keyboard.press('Tab');await expect(page.locator('[data-focus-previous]')).toBeFocused();await expect(strip).toHaveAttribute('data-motion','paused');
});

test('visible Pause and Resume work with pointer and keyboard',async({page})=>{
  await page.clock.install();await page.goto('/');
  const strip=page.locator('[data-news-focus]'),button=page.locator('[data-focus-toggle]'),headline=page.locator('[data-focus-link]');
  await expect(button).toBeEnabled();const first=await headline.textContent();
  await button.click();await expect(button).toHaveText('Resume');await expect(button).toHaveAttribute('aria-pressed','true');
  await page.mouse.move(2,2);await page.clock.fastForward(25000);await expect(headline).toHaveText(first!);
  await button.click();await expect(button).toHaveText('Pause');await page.mouse.move(2,2);
  await expect(strip).toHaveAttribute('data-motion','running');await page.clock.fastForward(12500);await expect(headline).not.toHaveText(first!);
  await button.focus();await page.keyboard.press('Enter');await expect(button).toHaveText('Resume');
  await page.keyboard.press('Enter');await expect(button).toHaveText('Pause');await expect(strip).toHaveAttribute('data-motion','paused');
  await page.keyboard.press('Tab');await expect(page.locator('[data-focus-next]')).toBeFocused();await expect(strip).toHaveAttribute('data-motion','paused');
  await page.keyboard.press('Tab');await expect(strip).toHaveAttribute('data-motion','running');
});

test('hidden and offscreen headlines stop, then resume with a fresh reading interval',async({page})=>{
  await page.clock.install();await page.goto('/');
  const strip=page.locator('[data-news-focus]'),headline=page.locator('[data-focus-link]');
  await expect(strip).toHaveAttribute('data-motion','running');const first=await headline.textContent();
  await page.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'));});
  await expect(strip).toHaveAttribute('data-motion','paused');await page.clock.fastForward(25000);await expect(headline).toHaveText(first!);
  await page.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,get:()=>false});document.dispatchEvent(new Event('visibilitychange'));});
  await expect(strip).toHaveAttribute('data-motion','running');
  await page.evaluate(()=>scrollTo(0,document.body.scrollHeight));await expect(strip).toHaveAttribute('data-motion','paused');
  await page.clock.fastForward(25000);await expect(headline).toHaveText(first!);
  await page.evaluate(()=>scrollTo(0,0));await expect(strip).toHaveAttribute('data-motion','running');
  await page.clock.fastForward(6000);await expect(headline).toHaveText(first!);
  await page.clock.fastForward(6500);await expect(headline).not.toHaveText(first!);
});

test('reduced motion supplies stationary headlines and disables decorative color movement',async({page})=>{
  await page.clock.install();await page.emulateMedia({reducedMotion:'reduce'});await page.goto('/bn/');
  const strip=page.locator('[data-news-focus]'),headline=page.locator('[data-focus-link]');
  await expect(strip).toHaveAttribute('data-motion','paused');await expect(page.locator('[data-focus-toggle]')).toBeDisabled();
  const first=await headline.textContent();await page.clock.fastForward(36000);await expect(headline).toHaveText(first!);
  expect(await page.locator('[data-focus-progress]').evaluate(element=>getComputedStyle(element).animationName)).toBe('none');
  expect(await page.evaluate(()=>document.getAnimations().length)).toBe(0);
  await page.emulateMedia({reducedMotion:'no-preference'});await expect(page.locator('[data-focus-toggle]')).toBeEnabled();
  await expect(strip).toHaveAttribute('data-motion','running');
});

test('working masthead is consistent, translation-protected and available without JavaScript',async({browser})=>{
  const context=await browser.newContext({javaScriptEnabled:false});const page=await context.newPage();
  await page.goto('/');await expect(page.locator('.wordmark').first()).toHaveText('Techline Today');
  await expect(page.locator('.wordmark').first()).toHaveAttribute('translate','no');await expect(page).toHaveTitle(/Techline Today/);
  await expect(page.locator('.brand-tagline')).toHaveText('Technology News & Insights');
  await expect(page.locator('[data-focus-link]')).toHaveAttribute('href',/\/story\//);
  await expect(page.locator('[data-focus-toggle]')).toBeDisabled();await page.locator('.category-tile').first().click();await expect(page).toHaveURL(/\/category\/ai\//);
  await page.goto('/rss.xml');expect(await page.content()).toContain('Techline Today');
  await context.close();
});
