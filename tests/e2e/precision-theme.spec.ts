import { expect, test } from '@playwright/test';

test('major homepage titles keep their hierarchy and fit narrow screens in either language', async ({ page }) => {
  for (const width of [320, 390, 834, 1280, 1366, 1440]) for (const route of ['/', '/bn/']) {
    await page.setViewportSize({ width, height: 960 });
    await page.goto(route);
    for (const theme of ['light', 'dark']) {
      await page.evaluate(theme => { document.documentElement.dataset.theme = theme; }, theme);
      const metrics = await page.evaluate(() => {
        const titles = [...document.querySelectorAll('.home-section>.section-top h2')].map(element => {
          const css = getComputedStyle(element), box = element.getBoundingClientRect();
          return { size: parseFloat(css.fontSize), weight: Number(css.fontWeight), height: box.height, lineHeight: parseFloat(css.lineHeight), tracking: css.letterSpacing, color: css.color };
        });
        return { titles, body: parseFloat(getComputedStyle(document.body).fontSize), lead: parseFloat(getComputedStyle(document.querySelector('.lead-card h2')!).fontSize), briefing: parseFloat(getComputedStyle(document.querySelector('#briefing-title')!).fontSize), overflow: document.documentElement.scrollWidth > innerWidth };
      });
      expect(metrics.titles).toHaveLength(3);
      expect(metrics.overflow).toBe(false);
      expect(metrics.body).toBe(18);
      expect(metrics.briefing).toBe(23);
      expect(metrics.lead).toBe(width <= 380 ? 27 : width <= 720 ? 29 : 36);
      for (const title of metrics.titles) {
        expect(title.size).toBeGreaterThanOrEqual(width <= 720 ? 26 : width <= 1100 ? 27 : 29);
        expect(title.size).toBeLessThanOrEqual(width <= 720 ? 27 : width <= 1100 ? 29 : 32);
        expect(title.weight).toBeGreaterThanOrEqual(700);
        expect(title.height).toBeLessThanOrEqual(title.lineHeight + 1);
        if (route === '/bn/') {
          expect(title.lineHeight / title.size).toBeGreaterThanOrEqual(1.5);
          expect(title.tracking).toBe('normal');
        }
      }
      expect(new Set(metrics.titles.map(title => title.color)).size).toBe(3);
    }
  }
});

test('section text, icons and utility hover and keyboard focus retain measured contrast', async ({ page }) => {
  for (const width of [320, 1366]) for (const route of ['/', '/bn/']) for (const theme of ['light', 'dark']) {
    await page.setViewportSize({ width, height: 960 });
    await page.goto(route);
    await page.evaluate(theme => { document.documentElement.dataset.theme = theme; }, theme);
    for (const state of ['default', 'hover', 'focus']) {
      const utility = page.locator('.tracker-signal a').first();
      if (state === 'hover') await utility.hover();
      if (state === 'focus') { await page.mouse.move(0, 0); await utility.focus(); }
      const failures = await page.evaluate(state => {
        const rgb = (value: string) => value.match(/[\d.]+/g)!.map(Number);
        const luminance = (value: number[]) => value.slice(0, 3).map(c => c / 255).map(c => c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4).reduce((sum, c, i) => sum + c * [.2126, .7152, .0722][i]!, 0);
        const background = (element: Element | null): number[] => {
          if (!element) return [255, 255, 255];
          const color = rgb(getComputedStyle(element).backgroundColor), alpha = color[3] ?? 1;
          const parent = alpha < 1 ? background(element.parentElement) : [0, 0, 0];
          return color.slice(0, 3).map((c, i) => c * alpha + parent[i]! * (1 - alpha));
        };
        const contrast = (color: string, element: Element) => {
          const fg = luminance(rgb(color)), bg = luminance(background(element));
          return (Math.max(fg, bg) + .05) / (Math.min(fg, bg) + .05);
        };
        const selectors = '.home-section h2,.home-section>.section-top p,.category-tile,.category-index-label,.category-description,.category-tile-footer,.category-open,.topic-icon,.tracker-signal h3,.tracker-signal p,.tracker-fields,.tracker-signal a';
        const results = [...document.querySelectorAll(selectors)].flatMap(element => {
          const css = getComputedStyle(element), icon = element.matches('svg'), size = parseFloat(css.fontSize);
          const minimum = icon || size >= 24 || (size >= 18.66 && Number(css.fontWeight) >= 700) ? 3 : 4.5;
          const ratio = contrast(css.color, element);
          return ratio < minimum ? [{ selector: element.className.toString(), ratio, minimum }] : [];
        });
        if (state === 'focus') {
          const element = document.querySelector('.tracker-signal a')!, css = getComputedStyle(element);
          if (!element.matches(':focus-visible') || parseFloat(css.outlineWidth) < 3 || contrast(css.outlineColor, element) < 3) results.push({ selector: 'utility keyboard focus', ratio: contrast(css.outlineColor, element), minimum: 3 });
        }
        return results;
      }, state);
      expect(failures, `${width} ${route} ${theme} ${state}`).toEqual([]);
    }
  }
});

test('desktop tracker fields and actions align when English and Bangla descriptions wrap', async ({ page }) => {
  for (const width of [834, 1366]) for (const route of ['/', '/bn/']) {
    await page.setViewportSize({ width, height: 960 });
    await page.goto(route);
    for (const selector of ['h3', '.tracker-fields', 'a']) {
      const positions = await page.locator(`.tracker-signal ${selector}`).evaluateAll(elements => elements.map(element => element.getBoundingClientRect().top));
      expect(Math.abs(positions[0]! - positions[1]!), `${width} ${route} ${selector}`).toBeLessThanOrEqual(1);
    }
  }
});
