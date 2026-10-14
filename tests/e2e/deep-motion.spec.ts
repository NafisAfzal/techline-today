import {expect,test} from '@playwright/test';

test('Resume restarts while the pointer stays over its button and exposes real playback state',async({page})=>{
  await page.clock.install();await page.goto('/');
  const strip=page.locator('[data-news-focus]'),headline=page.locator('[data-focus-link]'),button=page.locator('[data-focus-toggle]');
  await expect(strip).toHaveAttribute('data-motion','running');
  await expect(page.locator('[data-focus-state]')).toHaveText('Playing');
  const first=await headline.textContent();
  await button.click();await expect(strip).toHaveAttribute('data-motion','paused');
  await expect(page.locator('[data-focus-state]')).toHaveText('Paused');
  expect(await page.locator('[data-focus-progress]').evaluate(element=>getComputedStyle(element).animationPlayState)).toBe('paused');
  await page.clock.fastForward(25000);await expect(headline).toHaveText(first!);
  await button.click();await expect(strip).toHaveAttribute('data-motion','running');
  await expect(page.locator('[data-focus-state]')).toHaveText('Playing');
  expect(await page.locator('[data-focus-progress]').evaluate(element=>getComputedStyle(element).animationPlayState)).toBe('running');
  await page.clock.fastForward(8500);await expect(headline).not.toHaveText(first!);
  await expect(page.locator('[data-focus-position]')).toHaveText('2 / 4');
  const second=await headline.textContent();await page.locator('.search-trigger').click();
  await expect(strip).toHaveAttribute('data-pause-reason','modal');await expect(strip).toHaveAttribute('data-motion','paused');
  await expect(page.locator('[data-focus-state]')).toHaveText('Paused');
  expect(await page.locator('[data-focus-progress]').evaluate(element=>getComputedStyle(element).animationPlayState)).toBe('paused');
  await page.clock.fastForward(17000);await expect(headline).toHaveText(second!);
  await page.keyboard.press('Escape');await expect(strip).toHaveAttribute('data-motion','running');
  await page.clock.fastForward(8500);await expect(headline).not.toHaveText(second!);
});

test('one-item input is static and exposes no fake playback or navigation controls',async({page})=>{
  await page.clock.install();
  await page.route('http://127.0.0.1:4327/',async route=>{
    const response=await route.fetch();const html=await response.text();
    const body=html.replace(/<script\b[^>]*data-focus-items[^>]*>([\s\S]*?)<\/script>/, (whole,json)=>whole.replace(json,JSON.stringify([JSON.parse(json)[0]])));
    expect(body).not.toBe(html);
    await route.fulfill({response,body});
  });
  await page.goto('/');const strip=page.locator('[data-news-focus]'),headline=page.locator('[data-focus-link]');
  await expect(strip).toHaveAttribute('data-mode','static');await expect(strip).toHaveAttribute('data-motion','paused');
  await expect(page.locator('[data-focus-state]')).toHaveText('One headline');
  await expect(page.locator('[data-focus-position]')).toHaveText('1 / 1');
  await expect(page.locator('.focus-controls')).toBeHidden();await expect(page.locator('.focus-meter')).toBeHidden();
  const first=await headline.textContent();await page.clock.fastForward(36000);await expect(headline).toHaveText(first!);
  expect(await page.evaluate(()=>document.getAnimations().length)).toBe(0);
});

test('manual headline navigation remains useful with reduced motion and announces only requested changes',async({page})=>{
  await page.clock.install();await page.emulateMedia({reducedMotion:'reduce'});await page.goto('/');
  const headline=page.locator('[data-focus-link]');const first=await headline.textContent();
  await expect(page.locator('[data-focus-state]')).toHaveText('Motion off');
  await expect(page.locator('[data-focus-announcement]')).toHaveText('');
  await page.clock.fastForward(36000);await expect(headline).toHaveText(first!);
  await page.locator('[data-focus-next]').focus();await page.keyboard.press('Enter');await expect(headline).not.toHaveText(first!);
  await expect(page.locator('[data-focus-announcement]')).toHaveText((await headline.textContent())!);
  await page.locator('[data-focus-previous]').focus();await page.keyboard.press('Enter');await expect(headline).toHaveText(first!);
  await expect(page.locator('[data-news-focus]')).toHaveAttribute('data-motion','paused');
  expect(await page.evaluate(()=>document.getAnimations().length)).toBe(0);
});

test('pause preserves elapsed reading time instead of silently restarting the timer',async({page})=>{
  await page.clock.install();await page.goto('/');await expect(page.locator('[data-news-focus]')).toHaveAttribute('data-motion','running');
  const headline=page.locator('[data-focus-link]'),button=page.locator('[data-focus-toggle]');const first=await headline.textContent();
  await page.clock.fastForward(6000);await button.click();await page.clock.fastForward(25000);
  await page.locator('.search-trigger').click();await page.clock.fastForward(17000);await page.keyboard.press('Escape');
  await expect(page.locator('[data-news-focus]')).toHaveAttribute('data-manual-pause','true');
  await expect(page.locator('[data-news-focus]')).toHaveAttribute('data-motion','paused');
  await expect(headline).toHaveText(first!);await button.click();
  await page.clock.fastForward(1000);await expect(headline).toHaveText(first!);
  await page.clock.fastForward(1800);await expect(headline).not.toHaveText(first!);
});

test('automatic headline changes preserve the strip and lead geometry at all six widths and both locales',async({page})=>{
  await page.clock.install();
  for(const width of [320,390,834,1280,1366,1440]) for(const route of ['/','/bn/']) {
    await page.setViewportSize({width,height:960});await page.goto(route);await page.mouse.move(1,1);
    const strip=page.locator('[data-news-focus]'),headline=page.locator('[data-focus-link]');
    await expect(strip).toHaveAttribute('data-motion','running');
    const before=await strip.boundingBox(),leadBefore=await page.locator('.lead-card').boundingBox(),first=await headline.textContent();
    await page.clock.fastForward(8500);await expect(headline).not.toHaveText(first!);
    const after=await strip.boundingBox(),leadAfter=await page.locator('.lead-card').boundingBox();
    expect(after!.height).toBe(before!.height);expect(after!.y).toBe(before!.y);expect(leadAfter!.y).toBe(leadBefore!.y);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  }
});
