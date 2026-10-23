import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import sitemap from '@astrojs/sitemap';
import tailwind from '@tailwindcss/vite';
import { siteUrl } from '../../scripts/site-url.mjs';
import { readBuildSnapshot, researchEdition } from '../../scripts/research-policy.mjs';
const snapshot = readBuildSnapshot(new URL('../../content/generated/snapshot.json', import.meta.url));
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
  outDir: researchEdition ? './dist-research' : './dist',
  integrations: [react(), sitemap({ filter: publicPage })],
  // Bundle Astro's cookie parser into prerender output. A bare transitive
  // import can resolve an unrelated parent-directory cookie installation.
  vite: { plugins: [tailwind()], resolve: { noExternal: ['cookie'] } },
  build: { inlineStylesheets: 'never' },
  prefetch: { defaultStrategy: 'hover' },
  devToolbar: { enabled: false },
});
