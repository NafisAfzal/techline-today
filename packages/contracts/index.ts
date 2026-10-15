export type Category = 'ai' | 'research' | 'dev-apis' | 'freebies' | 'jobs-skills' | 'chips' | 'devices' | 'security' | 'open-source';
export type Evidence = 'primary-confirmed' | 'multi-source' | 'single-source' | 'community-report' | 'needs-verification';
export interface Fact { text: string; source_ids: string[]; attribution: string; status: string }
export interface KeyNumber { value: string; label: string; context: string; source_ids: string[] }
export interface SourceItem {
  id: string; source_registry_id: string; original_url: string; canonical_url: string; title: string;
  publisher: string; source_class: string; published_at: string; fetched_at: string; excerpt: string; language: string;
  source_type?: string; source_independence_group?: string; missing_publication_time?: boolean;
}
export interface StoryTranslation {
  language: 'bn'; canonical_hash: string; cache_key: string; provider: string; model: string;
  generated_at: string; review_status: 'automated' | 'fixture-reviewed';
  content: {headline: string; summary_bullets: string[]; why_it_matters: string; broader_summary: string;
    key_fact_texts: string[]; number_labels: string[]; number_contexts: string[]; limitations: string[]};
}
export interface Story {
  id: string; slug: string; category: Category; headline: string; summary_bullets: string[];
  why_it_matters: string; broader_summary: string; key_facts: Fact[]; key_numbers: KeyNumber[];
  limitations: string[]; evidence_state: Evidence; source_ids: string[]; primary_source_id: string | null;
  published_at: string; updated_at: string; first_seen_at: string; last_verified_at: string;
  importance_score_internal: number; language: string; tags: string[]; entities: string[];
  change_log: {at: string; text: string; source_ids: string[]; previous_facts: Fact[]}[];
  ai_metadata: {generation_mode: 'extractive' | 'ai'; provider: string; model: string}; is_demo: boolean;
  translations?: Partial<Record<'bn', StoryTranslation>>;
}
export interface Digest {
  id: string; period_type: 'daily' | 'weekly' | 'monthly' | 'yearly'; period_start: string;
  period_end: string; status: 'finalized' | 'in-progress'; story_ids: string[];
  top_by_category: Record<string, string[]>; summary: string; what_changed: string[]; watch_next: Fact[]; generated_at: string;
}
export interface Offer {
  id: string; story_id: string | null; provider: string; title: string; offer_type: string; value_text: string;
  eligibility: string[]; regions: string[]; card_required: boolean | null; claim_steps: string[];
  starts_at: string | null; expires_at: string | null; last_verified_at: string;
  status: 'active' | 'expiring' | 'expired' | 'unverified'; official_source_url: string;
  integration_notes: string; source_ids: string[]; is_demo: boolean;
}
export interface ModelRelease {
  id: string; story_id: string; provider: string; model: string; release_date: string;
  modality: string[]; context_window: string | null; pricing: string | null; api_available: boolean | null;
  weights: string; benchmark_claims: string[]; independent_references: string[]; key_change: string; source_ids: string[];
}
export interface Snapshot {
  mode: 'fixture' | 'live'; generated_at: string; last_successful_fetch_at: string;
  categories: Record<Category, {label: string; priority: number; subcategories: string[]}>;
  stories: Story[]; sources: Record<string, SourceItem>; digests: Digest[]; offers: Offer[];
  model_releases: ModelRelease[]; archive_index: {key: string; count: number; url: string}[];
}
export type Period = 'latest' | 'today' | 'week' | 'month' | 'year';
export interface FeedFilter { category?: Category; period?: Period; now?: string; sort?: 'importance' | 'latest' }
export interface FeedRepository {
  getLatest(filter?: FeedFilter): Promise<Story[]>;
  getStory(slug: string): Promise<Story | null>;
  getDigest(period: Digest['period_type'], key: string): Promise<Digest | null>;
}
export interface BookmarkRepository { list(): Promise<string[]>; add(id: string): Promise<void>; remove(id: string): Promise<void> }
export interface Preferences { categories: Category[]; theme: 'light' | 'dark' | 'system'; density: 'compact' | 'comfortable'; sort: 'importance' | 'latest'; hideRead: boolean }
export interface PreferenceRepository { get(): Preferences; set(value: Preferences): boolean; reset(): void }
export interface AlertRepository { available: boolean }
export interface AnalyticsRepository { track(event: string, detail?: Record<string, string>): void }
export const features = { accounts: false, alerts: false, paid: false, analytics: false } as const;
