# API and Service Contracts

V1 uses static implementations. Define interfaces now so future dynamic infrastructure is easy.

## FeedRepository

```ts
interface FeedRepository {
  getLatest(filter?: FeedFilter): Promise<StorySummary[]>;
  getStory(slug: string): Promise<StoryDetail | null>;
  getDigest(period: DigestPeriod, key: string): Promise<Digest | null>;
}
```

## BookmarkRepository

```ts
interface BookmarkRepository {
  list(): Promise<string[]>;
  add(storyId: string): Promise<void>;
  remove(storyId: string): Promise<void>;
}
```

V1 implementation: IndexedDB/localStorage.
V2: Worker API + D1.

## AIProvider

```py
class AIProvider(Protocol):
    async def generate_structured(self, request: AIRequest) -> AIResult: ...
    async def health(self) -> ProviderHealth: ...
```

## SourceAdapter

```py
class SourceAdapter(Protocol):
    async def fetch(self, source: SourceConfig, state: FetchState) -> FetchResult: ...
```

## Future HTTP endpoints

If V2 is enabled:

```text
GET  /api/v1/feed
GET  /api/v1/stories/:slug
GET  /api/v1/digests/:period/:key
POST /api/v1/bookmarks
DELETE /api/v1/bookmarks/:storyId
GET  /api/v1/preferences
PUT  /api/v1/preferences
POST /api/v1/alerts
```

All mutations require authenticated user, validation, CSRF strategy appropriate to the chosen auth mechanism, and rate limiting.
