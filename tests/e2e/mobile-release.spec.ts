import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
for (const locale of ['en','bn']) {
  const prefix = locale === 'bn' ? '/bn' : '';
  test(`${locale}: search tap restores focus and scrolling with a reduced viewport`, async ({page}) => {
    await page.goto(prefix + '/');
    const trigger = page.locator('.search-trigger');
    await trigger.tap();
    const edition = await (await page.request.get('/data/latest.json')).json();
    const term = edition.stories[0].headline.match(/[A-Za-z]{5,}/)?.[0];
    expect(term).toBeTruthy();
    await page.locator('#search-query').fill(term);
    await expect(page.locator('.search-results a').first()).toBeVisible();
    const width = page.viewportSize()!.width;
    await page.setViewportSize({width,height:320});
    await page.locator('.search-dialog-head button').tap();
    await expect(trigger).toBeFocused();
    await page.evaluate(() => window.scrollTo(0,document.body.scrollHeight));
    expect(await page.evaluate(() => window.scrollY)).toBeGreaterThan(0);
    await page.keyboard.press('/');
    await page.keyboard.press('Escape');
    await expect(trigger).toBeFocused();
  });
  test(`${locale}: portrait and landscape preserve header, themes and menus`, async ({page}) => {
    for (const viewport of [{width:375,height:812},{width:812,height:375}]) for (const theme of ['light','dark']) {
      await page.setViewportSize(viewport);
      await page.goto(prefix + '/');
      await page.locator(`.appearance-option[data-theme="${theme}"]`).tap();
      await page.reload();
      await expect(page.locator('html')).toHaveAttribute('data-theme',theme);
      expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
      const menu = page.locator('.more-nav');
      await menu.locator('summary').tap();
      await page.keyboard.press('Escape');
      await expect(menu).not.toHaveAttribute('open','');
      await expect(menu.locator('summary')).toBeFocused();
      expect((await new AxeBuilder({page}).analyze()).violations).toEqual([]);
    }
  });
  test(`${locale}: native fields avoid small fonts and saved stories survive navigation`, async ({page}) => {
    await page.goto(prefix + '/settings/');
    for (const select of await page.locator('.preference-selects select').all()) expect(await select.evaluate(el => parseFloat(getComputedStyle(el).fontSize))).toBeGreaterThanOrEqual(16);
    await page.goto(prefix + '/');
    const lead = page.locator('.lead-section a[href*="/story/"]').first();
    const route = await lead.getAttribute('href');
    await lead.tap();
    await expect(page.locator('h1')).toBeVisible();
    await page.locator('[data-bookmark]').first().tap();
    await page.goto(prefix + '/saved/');
    await expect(page.locator('[data-story]:visible')).toHaveCount(1);
    await page.goBack();
    await expect(page).toHaveURL(new RegExp(route!.replace(/[.*+?^${}()|[\]\\]/g,'\\$&') + '$'));
    await page.goForward();
    await expect(page).toHaveURL(new RegExp(prefix + '/saved/$'));
  });
}
