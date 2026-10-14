import { test, expect } from '@playwright/test';

test('Pagefind previews remain inert plain text and preserve literal metadata', async ({page}) => {
  let resourceRequests = 0;
  page.on('request', request => {
    if(request.url().includes('/__inert_template_must_not_fetch__')) resourceRequests++;
  });
  const metadata:{description?:string} = {};
  const markup = '<mark>Safety</mark> &amp; 2 <img src="http://127.0.0.1:4327/__inert_template_must_not_fetch__" onerror="window.fixtureScriptExecuted=true"><script>window.fixtureScriptExecuted=true</script><style>.fixture { display:none }</style>';
  await page.route('**/pagefind/pagefind.js', async route => {
    const item = {url:'/',meta:{title:'Safety preview',...metadata},excerpt:markup};
    await route.fulfill({contentType:'application/javascript',body:'export async function search() { return { results: [{ data: async () => (' + JSON.stringify(item) + ') }] }; }'});
  });
  await page.goto('/');
  await page.locator('.search-trigger').click();
  await page.locator('#search-query').fill('safety');
  await expect(page.locator('.search-results span').first()).toHaveText('Safety & 2');
  await expect(page.locator('.search-results img, .search-results script, .search-results style')).toHaveCount(0);
  expect(await page.evaluate(() => Boolean((window as Window & {fixtureScriptExecuted?:boolean}).fixtureScriptExecuted))).toBe(false);
  expect(resourceRequests).toBe(0);

  metadata.description = 'Literal <threshold> & 2 stays text.';
  await page.reload();
  await page.locator('.search-trigger').click();
  await page.locator('#search-query').fill('safety');
  await expect(page.locator('.search-results span').first()).toHaveText(metadata.description);
  await expect(page.locator('.search-results threshold')).toHaveCount(0);
  expect(resourceRequests).toBe(0);
});
