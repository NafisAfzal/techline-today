import bn from '../i18n/bn.json';
import type { Story } from '../../../../packages/contracts';
// English keys already are their display text. Keep only actual overrides in
// the reader bundle; the dictionary parity test guards future copy changes.
const englishOverrides: Record<string, string> = { supported: 'Supported by cited text' };
export type Locale = 'en' | 'bn';
export const locales = ['en', 'bn'] as const;
export const brandName = 'Techline Today';
export function localeFor(pathname: string): Locale { return /^\/bn(?:\/|$)/.test(pathname) ? 'bn' : 'en'; }
export function withoutLocale(pathname: string) { return pathname.replace(/^\/bn(?=\/|$)/, '') || '/'; }
export function localizedPath(pathname: string, locale: Locale) {
  const path = withoutLocale(pathname);
  // Validate after removing the locale as well: /bn//host must not become a
  // protocol-relative URL. Browsers strip TAB/CR/LF before parsing a link.
  if (!path.startsWith('/') || path.startsWith('//') || path.includes('\\') ||
      [...path].some(char => char.charCodeAt(0) < 32 || char.charCodeAt(0) === 127)) return locale === 'bn' ? '/bn/' : '/';
  if (/^\/(?:data|rss\.xml|pagefind|_astro|favicon\.svg)(?:\/|$)/.test(path)) return path;
  return locale === 'bn' ? `/bn${path}` : path;
}
export function t(locale: Locale, key: string): string {
  const dictionary: Record<string, string> = locale === 'bn' ? bn : englishOverrides;
  if (Object.hasOwn(dictionary, key)) return dictionary[key]!;
  const suffix = key.match(/^(.*?)(\s*[→↗])$/);
  return suffix && Object.hasOwn(dictionary, suffix[1]!.trim()) ? dictionary[suffix[1]!.trim()] + suffix[2] : key;
}
export function storyCount(count: number, locale: Locale) {
  return locale === 'bn' ? `${new Intl.NumberFormat('bn').format(count)}টি খবর` : `${count} ${count === 1 ? 'story' : 'stories'}`;
}
export function localizedStory(story: Story, locale: Locale): Story {
  const translated = locale === 'bn' ? story.translations?.bn?.content : undefined;
  if (!translated) return story;
  return {...story, headline: translated.headline, summary_bullets: translated.summary_bullets,
    why_it_matters: translated.why_it_matters, broader_summary: translated.broader_summary,
    key_facts: story.key_facts.map((fact, index) => ({...fact, text: translated.key_fact_texts[index]!})),
    key_numbers: story.key_numbers.map((number, index) => ({...number, label: translated.number_labels[index]!, context: translated.number_contexts[index]!})),
    limitations: translated.limitations, language: 'bn'};
}
export function contentLanguage(story: Story, locale: Locale) { return locale === 'bn' && story.translations?.bn ? 'bn' : story.language || 'en'; }
