import { expect, test } from '@playwright/test';

for (const locale of ['en', 'bn']) {
  test(`publication display respects timestamp quality in ${locale}`, async ({ page, request }) => {
    const snapshot = await (await request.get('/data/latest.json')).json();
    // The compact listing intentionally omits evidence; inspect public detail
    // payloads instead of assuming the private snapshot shape is exposed.
    let unknown;
    for (const candidate of snapshot.stories) {
      const detail = await (await request.get(`/data/stories/${candidate.slug}.json`)).json();
      const source = detail.sources.find((source: { id: string }) => source.id === (candidate.primary_source_id || candidate.source_ids[0]));
      if (source.missing_publication_time) { unknown = candidate; break; }
    }
    const story = unknown || snapshot.stories[0];
    const prefix = locale === 'bn' ? '/bn' : '';
    await page.goto(`${prefix}/story/${story.slug}/`);
    const xml = await (await request.get('/rss.xml')).text();
    const rssDate = await page.evaluate(({ xml, id }) => {
      const document = new DOMParser().parseFromString(xml, 'application/xml');
      const item = [...document.querySelectorAll('item')].find(item => item.querySelector('guid')?.textContent === id);
      return item?.querySelector('pubDate')?.textContent || null;
    }, { xml, id: story.id });
    const notice = locale === 'bn' ? 'প্রকাশের সময় জানা নেই' : 'Publication time unavailable';
    if (unknown) {
      expect(rssDate).toBeNull();
      await expect(page.locator('[data-story-publication]')).toHaveText(notice);
      await expect(page.locator('[data-story-publication] time')).toHaveCount(0);
      await expect(page.locator('[data-source-publication]').first()).toContainText(notice);
    } else {
      expect(Date.parse(rssDate!)).toBe(Math.floor(Date.parse(story.published_at) / 1000) * 1000);
      await expect(page.locator('[data-story-publication] time')).toHaveAttribute('datetime', story.published_at);
      await expect(page.locator('[data-story-publication]')).not.toContainText(notice);
    }
    await expect(page.locator('h1')).toHaveAttribute('lang', story.translations?.bn && locale === 'bn' ? 'bn' : 'en');
    if (locale === 'bn') {
      const translation = story.translations?.bn;
      if (translation) {
        await expect(page.locator('[data-translation-status]')).toHaveText(
          translation.review_status === 'fixture-reviewed' ? 'নমুনা অনুবাদ' : 'যন্ত্রের অনুবাদ');
      } else {
        await expect(page.locator('[data-language-fallback]')).toBeVisible();
      }
    }
  });
}
