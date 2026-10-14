import { expect, test } from '@playwright/test';

test('header controls stay named, visible and separate through intermediate widths', async ({ page }) => {
  for (const width of [320, 390, 720, 721, 768, 800, 834, 900, 1000, 1001, 1024, 1100, 1101, 1280, 1366, 1440]) for (const route of ['/', '/bn/']) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto(route);
    const group = page.getByRole('group', { name: route === '/' ? 'Appearance' : 'থিম', exact: true });
    await expect(group.getByRole('button')).toHaveCount(2);
    await expect(page.locator('.appearance-label')).toHaveCount(0);
    for (const button of await group.getByRole('button').all()) await expect(button.locator('span')).toBeVisible();
    const metrics = await page.evaluate(() => {
      const selectors = ['.brand', '.header-search', '.language-control', '.appearance-control'];
      const boxes = selectors.map(selector => {
        const box = document.querySelector(selector)!.getBoundingClientRect();
        return { left: box.left, right: box.right, top: box.top, bottom: box.bottom };
      });
      const collisions = boxes.flatMap((box, i) => boxes.slice(i + 1).filter(other => box.left < other.right - 1 && box.right > other.left + 1 && box.top < other.bottom - 1 && box.bottom > other.top + 1));
      const search = document.querySelector('.header-search')!.getBoundingClientRect();
      const mark = document.querySelector('.wordmark')!.getBoundingClientRect();
      const navTops = [...document.querySelectorAll('.category-nav>a,.more-nav>summary')].filter(element => element.getClientRects().length).map(element => element.getBoundingClientRect().top);
      return { collisions, navSpread: Math.max(...navTops) - Math.min(...navTops), overflow: document.documentElement.scrollWidth > innerWidth, width: search.width, mastheadHeight: mark.height, lineHeight: parseFloat(getComputedStyle(document.querySelector('.wordmark')!).lineHeight) };
    });
    expect(metrics.collisions, `${width} ${route}`).toEqual([]);
    expect(metrics.overflow, `${width} ${route}`).toBe(false);
    expect(metrics.navSpread, `${width} ${route} navigation wraps`).toBeLessThanOrEqual(1);
    expect(metrics.mastheadHeight).toBeLessThanOrEqual(metrics.lineHeight + 1);
    if (width > 1000) {
      await expect(page.locator('.header-search-input')).toBeVisible();
      expect(metrics.width).toBeGreaterThanOrEqual(280);
      expect(metrics.width).toBeLessThanOrEqual(360);
    } else await expect(page.locator('.header-search-input')).not.toBeVisible();
    if (width < 500) {
      await page.locator('.more-nav>summary').click();
      const nav = page.locator('.category-nav');
      for (const [label, topic] of [[route === '/' ? 'Chips' : 'চিপ', 'chips'], [route === '/' ? 'Security' : 'নিরাপত্তা', 'security']]) {
        const link = nav.getByRole('link', { name: label, exact: true });
        await expect(link).toHaveCount(1);
        await expect(link).toHaveAttribute('href', `${route === '/' ? '' : '/bn'}/category/${topic}/`);
      }
      await page.locator('.more-nav>summary').click();
    }
  }
});

test('desktop search accepts a query before opening and restores keyboard focus on Escape', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 960 });
  for (const route of ['/', '/bn/']) {
    await page.goto(route);
    const field = page.locator('.header-search-input');
    await field.fill('Meridian');
    await expect(page.locator('dialog')).not.toBeVisible();
    await field.press('Enter');
    await expect(page.locator('#search-query')).toBeFocused();
    await expect(page.locator('#search-query')).toHaveValue('Meridian');
    await expect(page.locator('.search-results a').first()).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(field).toBeFocused();
    await field.fill('Research');
    await page.locator('.search-trigger').click();
    await expect(page.locator('#search-query')).toHaveValue('Research');
    await page.keyboard.press('Escape');
    await expect(page.locator('.search-trigger')).toBeFocused();
    await page.keyboard.press('/');
    await expect(page.locator('#search-query')).toBeFocused();
    await page.keyboard.press('Escape');
  }
});

test('search text, placeholder, icon and its shared keyboard outline contrast in both themes', async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 960 });
  for (const route of ['/', '/bn/']) for (const theme of ['light', 'dark']) {
    await page.goto(route);
    await page.evaluate(theme => { document.documentElement.dataset.theme = theme; }, theme);
    await page.locator('.header-search-input').focus();
    const metrics = await page.evaluate(() => {
      const rgb = (color: string) => color.match(/[\d.]+/g)!.slice(0, 3).map(Number);
      const luminance = (color: string) => rgb(color).map(c => c / 255).map(c => c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4).reduce((sum, c, i) => sum + c * [.2126, .7152, .0722][i]!, 0);
      const ratio = (a: string, b: string) => { const x = luminance(a), y = luminance(b); return (Math.max(x, y) + .05) / (Math.min(x, y) + .05); };
      const field = document.querySelector('.header-search-input')!, form = document.querySelector('.header-search')!;
      const surface = getComputedStyle(form).backgroundColor, header = getComputedStyle(document.querySelector('.site-header')!).backgroundColor;
      const outline = getComputedStyle(form);
      return { text: ratio(getComputedStyle(field).color, surface), placeholder: ratio(getComputedStyle(field, '::placeholder').color, surface), icon: ratio(getComputedStyle(document.querySelector('.search-trigger svg')!).color, surface), focus: ratio(outline.outlineColor, header), outlineWidth: parseFloat(outline.outlineWidth), outlineStyle: outline.outlineStyle };
    });
    expect(metrics.text).toBeGreaterThanOrEqual(4.5);
    expect(metrics.placeholder).toBeGreaterThanOrEqual(4.5);
    expect(metrics.icon).toBeGreaterThanOrEqual(3);
    expect(metrics.focus).toBeGreaterThanOrEqual(3);
    expect(metrics.outlineWidth).toBeGreaterThanOrEqual(3);
    expect(metrics.outlineStyle).toBe('solid');
  }
});
