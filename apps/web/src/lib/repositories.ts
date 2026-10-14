import type { AnalyticsRepository, BookmarkRepository, Category, FeedFilter, FeedRepository, PreferenceRepository, Preferences, Snapshot } from '../../../../packages/contracts';
import { filterStories } from './filters';
export interface StorageLike { getItem(key: string): string | null; setItem(key: string, value: string): void; removeItem(key: string): void }
const CATEGORIES = new Set(['ai', 'research', 'dev-apis', 'freebies', 'jobs-skills', 'chips', 'devices', 'security', 'open-source']);
export const defaults: Preferences = { categories: [], theme: 'system', density: 'comfortable', sort: 'importance', hideRead: false };
export class LocalRepository implements BookmarkRepository, PreferenceRepository {
  constructor(private storage: StorageLike) {}
  read<T>(key: string, fallback: T): T {
    try { return JSON.parse(this.storage.getItem('ti:v1:' + key) || 'null') ?? fallback; } catch { return fallback; }
  }
  write(key: string, value: unknown): boolean {
    try { this.storage.setItem('ti:v1:' + key, JSON.stringify(value)); return true; } catch { return false; }
  }
  ids(key: string): string[] { const value = this.read<unknown>(key, []); return Array.isArray(value) ? [...new Set(value.filter((id): id is string => typeof id === 'string' && id.length < 100))] : []; }
  async list() { return this.ids('bookmarks'); }
  async add(id: string) { if (!this.write('bookmarks', [...new Set([...this.ids('bookmarks'), id])])) throw new Error('Browser storage is unavailable'); }
  async remove(id: string) { if (!this.write('bookmarks', this.ids('bookmarks').filter(item => item !== id))) throw new Error('Browser storage is unavailable'); }
  toggleRead(id: string) { const ids = this.ids('read'); return this.write('read', ids.includes(id) ? ids.filter(value => value !== id) : [...ids, id]); }
  get(): Preferences {
    const value = this.read<Partial<Preferences> | null>('preferences', null);
    if (!value || typeof value !== 'object') return {...defaults, categories: []};
    return { categories: Array.isArray(value.categories) ? [...new Set(value.categories.filter((category): category is Category => CATEGORIES.has(category)))]: [],
      theme: ['light','dark','system'].includes(value.theme || '') ? value.theme! : 'system',
      density: value.density === 'compact' ? 'compact' : 'comfortable', sort: value.sort === 'latest' ? 'latest' : 'importance', hideRead: value.hideRead === true };
  }
  set(value: Preferences) { return this.write('preferences', value); }
  reset() { try { this.storage.removeItem('ti:v1:preferences'); } catch { /* Storage may be blocked by the browser. */ } }
}
export class StaticFeedRepository implements FeedRepository {
  constructor(private snapshot: Snapshot) {}
  async getLatest(filter?: FeedFilter) { return filterStories(this.snapshot.stories, filter); }
  async getStory(slug: string) { return this.snapshot.stories.find(story => story.slug === slug) ?? null; }
  async getDigest(period: Snapshot['digests'][number]['period_type'], key: string) { return this.snapshot.digests.find(digest => digest.period_type === period && digest.id === key) ?? null; }
}
export const analytics: AnalyticsRepository = { track: () => undefined };
