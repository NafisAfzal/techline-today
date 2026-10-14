import assert from 'node:assert/strict';
import { chromium } from '@playwright/test';

// Read-only against an explicitly supplied origin. No guessed live destination.
const input = process.env.SMOKE_BASE_URL;
assert(input, 'Set SMOKE_BASE_URL to the approved hosted origin (or use --local for an isolated local proof).');
let base;
try { base = new URL(input); } catch { throw Error('SMOKE_BASE_URL must be an origin.'); }
const local = process.argv.includes('--local') && ['127.0.0.1', 'localhost'].includes(base.hostname);
assert(!base.username && !base.password && base.pathname === '/' && !base.search && !base.hash
  && (base.protocol === 'https:' || (local && base.protocol === 'http:')), 'Use a credential-free HTTPS origin; --local permits loopback HTTP.');
assert(['true', 'false'].includes(process.env.SMOKE_EXPECT_INDEXING), 'Set SMOKE_EXPECT_INDEXING=true for production or false for staging/local.');
const indexable = process.env.SMOKE_EXPECT_INDEXING === 'true';
const canonicalOrigin = process.env.SMOKE_CANONICAL_ORIGIN || base.origin;
const checked = [];
const errors = [];
const secretPattern = /\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|AIza[A-Za-z0-9_-]{30,}|sk-(?:proj-)?[A-Za-z0-9_-]{25,})\b|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/;
const get = async (route, status = 200) => {
  const response = await fetch(new URL(route, base), {redirect: 'manual', signal: globalThis.AbortSignal.timeout(20000)});
  assert.equal(response.status, status, `Unexpected status on ${route}`);
  const text = await response.text();
  assert(!secretPattern.test(text), `Possible credential in response at ${route}; inspect privately.`);
  checked.push(route);
  return text;
};
const edition = JSON.parse(await get('/data/latest.json'));
assert.equal(edition.mode, 'live', 'Hosted release must contain real sources.');
assert(edition.stories?.length > 0 && edition.stories.every(story => !story.is_demo), 'Missing or synthetic stories.');
assert(Date.now() - Date.parse(edition.generated_at) < 24 * 3600000, 'Edition is stale or has an invalid generation date.');
const story = edition.stories[0];
const detail = `/story/${story.slug}/`;
const robots = await get('/robots.txt');
assert.equal(/^Allow: \/$/m.test(robots), indexable, 'robots.txt differs from the expected indexing policy.');
if (!indexable) assert(/^Disallow: \/$/m.test(robots), 'Staging must disallow indexing.');
assert(robots.includes(`Sitemap: ${canonicalOrigin}/sitemap-index.xml`), 'Incorrect sitemap origin.');
const sitemap = await get('/sitemap-index.xml');
assert(sitemap.includes('<sitemapindex'), 'Malformed sitemap index.');
const maps = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)];
assert(maps.length > 0, 'Empty sitemap.');
for (const [, location] of maps) {
  const url = new URL(location);
  assert.equal(url.origin, canonicalOrigin, 'Wrong sitemap origin.');
  const map = await get(url.pathname);
  assert(map.includes(`${canonicalOrigin}/`) && map.includes('<urlset'), 'Malformed sitemap.');
}
let browser;
try {
  browser = await chromium.launch();
  const page = await browser.newPage({viewport: {width: 390, height: 844}});
  page.on('pageerror', () => errors.push('uncaught page error'));
  page.on('console', message => { if (message.type() === 'error') errors.push('browser console error'); });
  for (const route of ['/', '/bn/', '/all/', '/category/ai/', '/models/', '/freebies/', '/digests/', detail, `/bn${detail}`, '/saved/', '/settings/']) {
    await get(route);
    const response = await page.goto(new URL(route, base).href);
    assert.equal(response.status(), 200, `Navigation failed at ${route}`);
    assert(await page.locator('h1').count() === 1, `Missing heading at ${route}`);
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), `Mobile overflow at ${route}`);
    const fallback = route === `/bn${detail}` && !story.translations?.bn;
    const canonical = await page.locator('link[rel="canonical"]').getAttribute('href');
    assert.equal(canonical, new URL(fallback ? detail : route, canonicalOrigin).href, `Wrong canonical at ${route}`);
    const noindex = /noindex/.test(await page.locator('meta[name="robots"]').evaluateAll(nodes => nodes[0]?.getAttribute('content') || ''));
    assert.equal(noindex, !indexable || fallback || ['/saved/', '/settings/'].includes(route), `Wrong indexing at ${route}`);
    assert(await page.locator('meta[property="og:title"]').getAttribute('content'), 'Missing Open Graph title.');
    assert.equal(await page.locator('[aria-label="Demonstration notice"]').count(), 0, 'Fixture notice is visible.');
  }
  await page.goto(base.href);
  await page.locator('.search-trigger').click();
  const term = story.headline.match(/[A-Za-z]{5,}/)?.[0];
  assert(term, 'No suitable search term.');
  await page.locator('#search-query').fill(term);
  const result = page.locator('.search-results a').first();
  await result.waitFor({state: 'visible'});
  await result.click();
  await page.waitForURL(/\/story\//);
  await page.goBack();
  await page.locator('h1').waitFor();
  for (const theme of ['light', 'dark']) {
    await page.locator(`.appearance-option[data-theme="${theme}"]`).click();
    assert.equal(await page.locator('html').getAttribute('data-theme'), theme);
  }
  await get('/release-smoke-missing-route/', 404);
  assert.deepEqual(errors, [], 'Browser errors occurred; inspect locally without exposing response content.');
  console.log(JSON.stringify({status: 'passed', origin: base.origin, indexing: indexable, stories: edition.stories.length, checkedRoutes: checked.length, mobileWidth: 390, consoleErrors: errors.length, physicalDeviceTested: false}));
} finally { await browser?.close(); }
