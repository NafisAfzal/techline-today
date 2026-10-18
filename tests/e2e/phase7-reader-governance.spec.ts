import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import type { Story, SourceItem } from '../../packages/contracts';

// These are isolated synthetic fixtures, never claims of native/editorial approval.
for (const locale of ['en', 'bn']) {
  const prefix = locale === 'bn' ? '/bn' : '';
  test(`${locale}: fallback and synthetic translation states agree with public evidence`, async ({ page, request }) => {
    const snapshot = await (await request.get('/data/latest.json')).json() as { stories: Story[] };
    expect(snapshot.stories.some(story => story.translations?.bn)).toBe(true);
    expect(snapshot.stories.some(story => !story.translations?.bn)).toBe(true);
    const examples = [snapshot.stories.find(story => story.translations?.bn)!,
      snapshot.stories.find(story => !story.translations?.bn)!];
    for (const story of examples) {
      await page.goto(`${prefix}/story/${story.slug}/`);
      await expect(page.getByRole('main')).toHaveCount(1);
      await expect(page.getByRole('heading', { level: 1 })).toHaveAttribute('lang',
        locale === 'bn' && story.translations?.bn ? 'bn' : 'en');
      if (locale === 'bn' && story.translations?.bn) {
        await expect(page.locator('[data-translation-status]')).toHaveText('নমুনা অনুবাদ');
        await expect(page.locator('[data-language-fallback]')).toHaveCount(0);
      } else if (locale === 'bn') {
        await expect(page.locator('[data-language-fallback]')).toHaveAttribute('aria-label', /.+/);
      }
      const detail = await (await request.get(`/data/stories/${story.slug}.json`)).json() as { sources: SourceItem[] };
      for (const source of detail.sources) {
        await expect(page.locator(`#sources [id="${source.id}"] > a`).first()).toHaveAttribute('href', source.original_url);
      }
      expect(await page.locator('main').textContent()).not.toMatch(/native[- ]reviewed|approved translation/i);
    }
  });

  test(`${locale}: article landmarks and focus remain accessible at a narrow viewport`, async ({ page, browserName }) => {
    await page.setViewportSize({ width: 320, height: 740 });
    await page.goto(`${prefix}/all/`);
    const skip = page.locator('.skip-link');
    // iOS WebKit does not include links in Tab traversal under its default
    // keyboard policy. Verify explicit keyboard activation there; desktop and
    // Firefox still assert that Tab reaches the skip link as the first control.
    if (browserName === 'webkit') await skip.focus();
    else await page.keyboard.press('Tab');
    await expect(skip).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(page.getByRole('main')).toBeFocused();
    await expect(page.locator('html')).toHaveAttribute('lang', locale);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
    expect(result.violations).toEqual([]);
  });
}

test('private review queues and governance files are absent from the public site', async ({ page, request }) => {
  for (const path of ['/.cache/phase7/private-review-queue.json', '/.cache/phase6/editorial-decisions.json',
    '/.cache/phase6/source-candidates.json', '/.cache/phase6/translation-decisions.json',
    '/config/source-rights.json', '/pipeline/readiness.py']) {
    expect((await request.get(path)).status(), path).toBe(404);
  }
  const latest = await request.get('/data/latest.json');
  expect(await latest.text()).not.toContain('PHASE7_PRIVATE_REVIEW_SENTINEL');
  await page.goto('/');
  expect(await page.content()).not.toContain('PHASE7_PRIVATE_REVIEW_SENTINEL');
});
