import { expect, test } from '@playwright/test';
test('mobile reading actions remain within reach and citations clear the sticky controls',async({page})=>{
  await page.setViewportSize({width:320,height:844});await page.goto('/');
  await page.locator('[data-variant="lead"] h2 a').click();
  await page.locator('.detail-content section').last().scrollIntoViewIfNeeded();
  const actions=page.locator('.detail-actions');
  const bounds=await actions.boundingBox();
  expect(bounds!.y).toBeGreaterThanOrEqual(0);expect(bounds!.y).toBeLessThan(10);expect(bounds!.height).toBeLessThanOrEqual(80);
  await expect(actions.locator('[data-bookmark]')).toBeVisible();
  await page.locator('.citation').first().click();
  const source=page.locator('.source-panel li').first();
  expect((await source.boundingBox())!.y).toBeGreaterThanOrEqual(70);
});
