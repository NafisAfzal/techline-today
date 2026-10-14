import { chromium, firefox, webkit, devices } from '@playwright/test';
import { spawn } from 'node:child_process';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import assert from 'node:assert/strict';

const label = process.argv[2] || 'final';
assert(/^[a-z-]+$/.test(label));
const output = path.join(os.tmpdir(), 'techline-release', `mobile-${label}`);
await mkdir(output, { recursive: true });
const snapshot = JSON.parse(await readFile('content/generated/snapshot.json', 'utf8'));
const story = snapshot.stories.find(item => item.translations?.bn) || snapshot.stories[0];
const widths = [320, 360, 375, 390, 393, 412, 430, 480, 600, 768, 834, 1024, 1280, 1366, 1440];
const server = spawn(process.execPath, ['scripts/preview.mjs'], { env: { ...process.env, PORT: '4331' }, stdio: 'ignore' });
const base = 'http://127.0.0.1:4331';
const measurements = [], errors = [], engines = [];
const checks = async page => page.evaluate(() => {
  const visible = element => {
    const closed = element.closest('details:not([open])');
    return element.getClientRects().length && window.getComputedStyle(element).visibility !== 'hidden' && (!closed || closed.querySelector(':scope>summary')?.contains(element));
  };
  const selector = '.header-actions button:not(:disabled),.language-control a,.category-nav>a,.more-nav>summary,.category-tile,.control-link,.citation,.checkbox-label,.preference-categories label';
  const small = [...document.querySelectorAll(selector)].filter(visible).flatMap(element => {
    const box = element.getBoundingClientRect();
    return box.width < 43.9 || box.height < 43.9 ? [{ text: element.textContent.trim().slice(0, 35), width: box.width, height: box.height }] : [];
  });
  const controls = ['.brand', '.header-search', '.language-control', '.appearance-control'].map(selector => document.querySelector(selector).getBoundingClientRect());
  const overlaps = controls.flatMap((box, index) => controls.slice(index + 1).filter(other => box.left < other.right - 1 && box.right > other.left + 1 && box.top < other.bottom - 1 && box.bottom > other.top + 1));
  const inputZoom = window.innerWidth <= 1100 || window.navigator.maxTouchPoints > 0 ? [...document.querySelectorAll('input:not([type="checkbox"]),select')].filter(visible).filter(element => Number.parseFloat(window.getComputedStyle(element).fontSize) < 16).map(element => ({ name: element.getAttribute('aria-label') || element.name || element.id, size: window.getComputedStyle(element).fontSize })) : [];
  const nav = [...document.querySelectorAll('.category-nav>a,.more-nav>summary')].filter(visible).map(element => element.getBoundingClientRect().top);
  const clipped = [...document.querySelectorAll('.appearance-option span,.language-control a,.wordmark')].filter(visible).filter(element => element.scrollWidth > element.clientWidth + 1).map(element => element.textContent.trim());
  return { overflow: document.documentElement.scrollWidth > window.innerWidth, small, overlaps: overlaps.length, inputZoom, clipped, navWrap: Math.max(...nav) - Math.min(...nav) > 1 };
});
const captureState = async (page, context, meta, name, route) => {
  await page.goto(base + route);
  await page.waitForFunction(() => !document.querySelector('astro-island[ssr]'));
  await page.locator(`.appearance-option[data-theme="${meta.theme}"]`).click();
  if (name === 'search') {
    await page.locator('.search-trigger').click();
    await page.locator('#search-query').fill(story.headline.match(/[A-Za-z]{5,}/)[0]);
    await page.locator('.search-results a').first().waitFor();
  }
  const result = await checks(page);
  measurements.push({ ...meta, name, route, ...result });
  if (name === 'home' && [375, 390, 412, 834, 1366].includes(meta.width)) {
    await page.screenshot({ path: path.join(output, `${meta.engine}-${meta.locale}-${meta.theme}-${meta.width}-${meta.profile.replaceAll(' ', '-').toLowerCase()}${meta.landscape ? '-landscape' : ''}.jpg`), type: 'jpeg', quality: 85 });
  }
  if (name === 'search') {
    await page.setViewportSize({ width: meta.width, height: Math.min(360, meta.height) });
    const close = page.locator('.search-dialog-head button');
    await close.click();
    try { await page.waitForFunction(() => document.activeElement?.matches('.search-trigger'), { }, { timeout: 1000 }); }
    catch { errors.push({ ...meta, name, message: 'Search did not restore focus to its invoking button' }); }
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    if (!(await page.evaluate(() => window.scrollY > 0))) errors.push({ ...meta, name, message: 'Body remained scroll locked after closing search' });
  }
  void context;
};
try {
  let ready = false;
  for (let i = 0; i < 100; i++) { try { ready = (await fetch(base)).ok; } catch { /* Startup. */ } if (ready) break; await new Promise(resolve => setTimeout(resolve, 100)); }
  assert(ready);
  const built = await (await fetch(base + '/data/latest.json')).json();
  assert.equal(built.mode, snapshot.mode); assert.equal(built.generated_at, snapshot.generated_at);
  await Promise.all(Object.entries({ chromium, firefox, webkit }).map(async ([engine, launcher]) => {
    const browser = await launcher.launch();
    engines.push({ engine, version: browser.version() });
    try {
      for (const width of widths) {
        const height = width < 600 ? 844 : 960;
        const context = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: width < 600 ? 3 : 1, reducedMotion: 'reduce' });
        const page = await context.newPage();
        page.on('pageerror', error => errors.push({ engine, message: error.message }));
        for (const locale of ['en', 'bn']) for (const theme of ['light', 'dark']) {
          const prefix = locale === 'bn' ? '/bn' : '';
          for (const [name, route] of [['home', '/'], ['category', '/category/ai/'], ['story', `/story/${story.slug}/`], ['settings', '/settings/'], ['saved', '/saved/'], ['search', '/']]) {
            await page.setViewportSize({ width, height });
            await captureState(page, context, { engine, locale, theme, width, height, dpr: width < 600 ? 3 : 1, profile: 'viewport' }, name, prefix + route);
          }
        }
        await context.close();
        console.log(`${engine}: ${width}px complete`);
      }
      for (const name of ['iPhone SE', 'iPhone 13', 'Pixel 7', 'iPad Pro 11']) for (const landscape of [false, true]) {
        const profile = devices[name];
        const viewport = landscape ? { width: profile.viewport.height, height: profile.viewport.width } : profile.viewport;
        const context = await browser.newContext({ ...profile, viewport, isMobile: engine !== 'firefox', reducedMotion: 'reduce' });
        const page = await context.newPage();
        page.on('pageerror', error => errors.push({ engine, message: error.message }));
        for (const locale of ['en', 'bn']) for (const theme of ['light', 'dark']) {
          await page.setViewportSize(viewport);
          await captureState(page, context, { engine, locale, theme, ...viewport, dpr: profile.deviceScaleFactor, profile: name, landscape, isMobile: engine !== 'firefox' }, 'home', locale === 'bn' ? '/bn/' : '/');
        }
        await context.close();
      }
    } finally { await browser.close(); }
  }));
  const failures = measurements.filter(item => item.overflow || item.small.length || item.overlaps || item.inputZoom.length || item.clipped.length || item.navWrap);
  const report = { label, mode: snapshot.mode, generated_at: snapshot.generated_at, captured_at: new Date().toISOString(), physical_devices: false, engines, states: measurements.length, failingStates: failures.length, errors, measurements };
  await writeFile(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ output, mode: snapshot.mode, engines, states: measurements.length, failingStates: failures.length, errors, exampleFailures: failures.slice(0, 6) }, null, 2));
  if (failures.length || errors.length) process.exitCode = 1;
} finally { server.kill(); }
