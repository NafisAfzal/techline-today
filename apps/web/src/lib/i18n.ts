import en from '../i18n/en.json';
import bn from '../i18n/bn.json';
import type { Story } from '../../../../packages/contracts';
export type Locale = 'en' | 'bn';
export const locales = ['en', 'bn'] as const;
export const brandName = 'Techline Today';
export function localeFor(pathname: string): Locale { return /^\/bn(?:\/|$)/.test(pathname) ? 'bn' : 'en'; }
export function withoutLocale(pathname: string) { return pathname.replace(/^\/bn(?=\/|$)/, '') || '/'; }
export function localizedPath(pathname: string, locale: Locale) {
  if (!pathname.startsWith('/') || pathname.startsWith('//') || pathname.includes('\\')) return locale === 'bn' ? '/bn/' : '/';
  const path = withoutLocale(pathname);
  if (/^\/(?:data|rss\.xml|pagefind|_astro|favicon\.svg)(?:\/|$)/.test(path)) return path;
  return locale === 'bn' ? `/bn${path}` : path;
}
export function t(locale: Locale, key: string): string {
  const dictionary: Record<string, string> = locale === 'bn' ? bn : en;
  if (dictionary[key]) return dictionary[key];
  const suffix = key.match(/^(.*?)(\s*[→↗])$/);
  return suffix && dictionary[suffix[1]!.trim()] ? dictionary[suffix[1]!.trim()] + suffix[2] : key;
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
