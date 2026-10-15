import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import sitemap from '@astrojs/sitemap';
import tailwind from '@tailwindcss/vite';
import { siteUrl } from '../../scripts/site-url.mjs';
import { readSnapshot } from '../../scripts/read-snapshot.mjs';
const snapshot = readSnapshot(new URL('../../content/generated/snapshot.json', import.meta.url));
const translated = new Set(snapshot.stories.filter(story=>story.translations?.bn).map(story=>story.slug));
function publicPage(page) {
  const pathname = new URL(page).pathname;
  if (/\/(?:saved|settings|404)(?:\/|\.html|$)/.test(pathname)) return false;
  const slug = pathname.match(/^\/bn\/story\/([^/]+)\/$/)?.[1];
  return !slug || translated.has(slug);
}

export default defineConfig({
  site: siteUrl(process.env.SITE_URL).origin,
  output: 'static',
  integrations: [react(), sitemap({ filter: publicPage })],
  vite: { plugins: [tailwind()] },
  build: { inlineStylesheets: 'never' },
  prefetch: { defaultStrategy: 'hover' },
  devToolbar: { enabled: false },
});
