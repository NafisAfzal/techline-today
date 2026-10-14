import assert from 'node:assert/strict';
import { chromium } from '@playwright/test';
import { spawn } from 'node:child_process';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';

const label = process.argv[2] || 'after';
assert(/^[a-z-]+$/.test(label));
const directory = path.join(os.tmpdir(), 'techline-precision', label);
await mkdir(directory, { recursive: true });
const snapshot = JSON.parse(await readFile('content/generated/snapshot.json', 'utf8'));
const story = snapshot.stories.find(item => item.translations?.bn) || snapshot.stories[0];
const server = spawn(process.execPath, ['scripts/preview.mjs'], { env: { ...process.env, PORT: '4330' }, stdio: 'ignore' });
let browser;
try {
  let ready = false;
  for (let attempt = 0; attempt < 100; attempt++) {
    try { ready = (await fetch('http://127.0.0.1:4330')).ok; } catch { /* Startup. */ }
    if (ready) break;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  assert(ready);
  const built = await (await fetch('http://127.0.0.1:4330/data/latest.json')).json();
  assert.equal(built.generated_at, snapshot.generated_at);
  assert.equal(built.mode, snapshot.mode);
  browser = await chromium.launch();
  const page = await browser.newPage({ reducedMotion: 'reduce' });
  const measurements = [];
  for (const width of [320, 390, 834, 1280, 1366, 1440]) {
    await page.setViewportSize({ width, height: width < 500 ? 844 : 960 });
    for (const locale of ['en', 'bn']) for (const theme of ['light', 'dark']) {
      const prefix = locale === 'bn' ? '/bn' : '';
      await page.addInitScript(theme => localStorage.setItem('ti:v1:preferences', JSON.stringify({ theme })), theme);
      for (const [name, route] of [['home', '/'], ['category', '/category/ai/'], ['story', `/story/${story.slug}/`], ['search', '/']]) {
        await page.goto(`http://127.0.0.1:4330${prefix}${route}`);
        await page.waitForFunction(() => !document.querySelector('astro-island[ssr]'));
        await page.evaluate(theme => { document.documentElement.dataset.theme = theme; }, theme);
        if (name === 'search') {
          await page.locator('.search-trigger').click();
          await page.locator('#search-query').fill(story.headline.match(/[A-Za-z]{5,}/)[0]);
          await page.locator('.search-results a').first().waitFor();
        }
        const metrics = await page.evaluate(() => {
          const style = element => {
            if (!element) return null;
            const css = window.getComputedStyle(element), box = element.getBoundingClientRect();
            return { text: element.textContent.trim(), size: css.fontSize, weight: css.fontWeight, lineHeight: css.lineHeight, tracking: css.letterSpacing, color: css.color, background: css.backgroundColor, width: box.width, height: box.height, marginBottom: css.marginBottom, padding: css.padding };
          };
          return {
            overflow: document.documentElement.scrollWidth > window.innerWidth,
            headings: ['#categories-title', '#more-stories-title', '#tools-title'].map(selector => ({ selector, ...style(document.querySelector(selector)) })),
            surfaces: ['body', '.category-index', '.more-stories', '.tools-section'].map(selector => ({ selector, ...style(document.querySelector(selector)) })),
            lead: style(document.querySelector('.lead-card h2')),
            prose: style(document.querySelector('.prose p')),
            bodySize: window.getComputedStyle(document.body).fontSize,
            header: Object.fromEntries(['.wordmark', '.header-actions', '.header-search', '.appearance-control'].map(selector => [selector, style(document.querySelector(selector))])),
            tokens: Object.fromEntries(['bg', 'surface', 'secondary', 'featured', 'header-bg', 'text', 'muted', 'navy', 'accent', 'brand-secondary', 'indigo', 'warm', 'green', 'amber', 'coral', 'line', 'soft-line', 'directory-bg', 'utility-bg', 'utility-text', 'utility-muted', 'utility-link', 'utility-teal', 'utility-gold', 'utility-line', 'section-category', 'section-stories', 'section-tools'].map(token => [token, window.getComputedStyle(document.documentElement).getPropertyValue(`--${token}`).trim()]))
          };
        });
        assert(!metrics.overflow, `Overflow: ${width} ${locale} ${theme} ${name}`);
        measurements.push({ width, locale, theme, name, route: prefix + route, ...metrics });
        const stem = `${locale}-${theme === 'light' ? 'warm' : 'dark'}-${width}`;
        if (name === 'home' || [390, 1366].includes(width)) await page.screenshot({ path: path.join(directory, `${stem}-${name}.jpg`), type: 'jpeg', quality: 88, fullPage: name !== 'search' });
        if (name === 'home' && [320, 390, 1366].includes(width)) {
          for (const [section, selector] of [['categories', '.category-index'], ['stories', '.more-stories'], ['tools', '.tools-section']]) {
            const element = page.locator(selector);
            if (await element.count()) await element.screenshot({ path: path.join(directory, `${stem}-${section}.jpg`), type: 'jpeg', quality: 90 });
          }
          const clip = await page.locator('.category-index').evaluate(element => {
            const start = element.getBoundingClientRect(), end = document.querySelector('.tools-section').getBoundingClientRect();
            return { x: start.x + window.scrollX, y: start.y + window.scrollY, width: start.width, height: end.bottom - start.top };
          });
          await page.screenshot({ path: path.join(directory, `${stem}-sections.jpg`), type: 'jpeg', quality: 88, fullPage: true, clip });
        }
        if (name === 'home') await page.locator('.site-header').screenshot({ path: path.join(directory, `${stem}-header.jpg`), type: 'jpeg', quality: 90 });
      }
    }
  }
  await writeFile(path.join(directory, 'measurements.json'), JSON.stringify({ label, mode: snapshot.mode, generated_at: snapshot.generated_at, measurements }, null, 2));
  console.log(JSON.stringify({ directory, mode: snapshot.mode, states: measurements.length, overflows: 0, headings: measurements.filter(item => item.name === 'home' && item.locale === 'en' && item.theme === 'light').map(({ width, headings }) => ({ width, headings })) }, null, 2));
} finally { await browser?.close(); server.kill(); }
