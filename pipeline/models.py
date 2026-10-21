import re
from datetime import UTC, date, datetime
from ipaddress import ip_address
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Category = Literal["ai", "research", "dev-apis", "freebies", "jobs-skills", "chips", "devices", "security", "open-source"]
Evidence = Literal["primary-confirmed", "multi-source", "single-source", "community-report", "needs-verification"]
SourceClass = Literal["primary", "independent", "aggregator", "community"]

# Shared by translation ingress, stored content and publication-time review.
# English/Bangla are left-to-right; ZWJ/ZWNJ remain valid Bangla joining marks.
DIRECTION_CONTROLS = frozenset("\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069")


def is_public_address(address) -> bool:
    # Python's is_global includes multicast and deprecated IPv6 site-local ranges.
    return address.is_global and not address.is_multicast and not getattr(address, "is_site_local", False)


def safe_url(value: str) -> str:
    if not isinstance(value, str) or re.search(r"[\s\x00-\x20\x7f\\]", value):
        raise ValueError("URL contains whitespace, controls or backslashes")
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise ValueError("Only credential-free HTTPS URLs are accepted")
    if parts.port not in (None, 443) or parts.hostname.lower() in {"localhost", "localhost.localdomain"}:
        raise ValueError("Unsafe URL host or port")
    try:
        address = ip_address(parts.hostname)
    except ValueError:
        host = parts.hostname
        if (not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", host)
                or "." not in host or host.endswith((".local", ".internal", ".localhost"))
                or not re.fullmatch(r"[a-z]{2,63}", host.rsplit(".", 1)[-1])
                or any(not label or len(label) > 63 or label.startswith("-") or label.endswith("-") for label in host.split("."))):
            raise ValueError("Unsafe hostname") from None
    else:
        if not is_public_address(address):
            raise ValueError("Non-public address")
    return value


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="after")
    @classmethod
    def plain_text(cls, value):
        if isinstance(value, datetime) and value.tzinfo is None:
            raise ValueError("Timezone-aware timestamps are required")
        def check(item):
            if isinstance(item, str) and ("<" in item or ">" in item or "\x00" in item):
                raise ValueError("Markup and control characters are forbidden")
            if isinstance(item, list):
                for child in item:
                    check(child)
        check(value)
        return value


class FetchPolicy(Contract):
    max_items: int = Field(default=30, ge=1, le=100)
    min_interval_seconds: float = Field(default=0.5, ge=0.1, le=60)
    max_response_bytes: int = Field(default=3_000_000, ge=100, le=3_000_000)
    conditional_requests: bool = True


class SourceConfig(Contract):
    id: str = Field(pattern=r"^[a-z0-9_-]+$")
    name: str
    adapter: Literal["rss", "hacker_news", "github_releases", "github_document", "arxiv", "json_api", "html"]
    source_class: SourceClass
    enabled: bool = False
    endpoint: str
    allowed_hosts: list[str] = Field(min_length=1)
    categories: list[Category] = Field(min_length=1)
    independence_group: str
    terms_url: str
    verified_at: str | None = None
    fetch_policy: FetchPolicy = Field(default_factory=FetchPolicy)
    repositories: list[str] = Field(default_factory=list)
    item_path: str = "items"
    field_map: dict[str, str] = Field(default_factory=dict)
    # Optional per-field format templates applied to the raw JSON item, e.g.
    # {"url": "https://example.com/catalog?q={cveID}"}. A field whose
    # template references a missing key resolves to None and is quarantined
    # downstream. URL templates require a separately pinned origin.
    field_templates: dict[str, str] = Field(default_factory=dict)
    template_url_origin: str | None = None
    identifier_format: Literal["cve"] | None = None
    editorial_kind: Literal["news", "security-advisory"] = "news"
    # Manual origin review is independent of lexical reservation screening.
    rights_review_required: bool = False
    rights_guard: bool = False
    html_selector: str = "main"
    html_permission: bool = False
    query_groups: list[str] = Field(default_factory=list)
    document_url: str | None = None
    excerpt_patterns: list[str] = Field(default_factory=list)
    discovery_keywords: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def check_policy(self):
        safe_url(self.endpoint)
        safe_url(self.terms_url)
        if self.document_url:
            safe_url(self.document_url)
        if urlsplit(self.endpoint).hostname not in self.allowed_hosts:
            raise ValueError("Endpoint must be allowlisted")
        if "url" in self.field_templates and not self.template_url_origin:
            raise ValueError("URL templates require an explicit origin")
        if self.template_url_origin:
            safe_url(self.template_url_origin)
            origin = urlsplit(self.template_url_origin)
            if (origin.hostname not in self.allowed_hosts or origin.path not in ("", "/")
                    or origin.query or origin.fragment):
                raise ValueError("Template origin must be an allowlisted HTTPS origin")
        if self.editorial_kind == "security-advisory" and self.identifier_format != "cve":
            raise ValueError("Security advisory sources require CVE identifiers")
        if self.enabled and not self.verified_at:
            raise ValueError("Enabled sources require verification date")
        if self.adapter == "html" and self.enabled and not self.html_permission:
            raise ValueError("HTML requires explicit terms permission")
        if any(not re.fullmatch(r"[A-Za-z0-9][\w.-]*/[A-Za-z0-9][\w.-]*", repo) for repo in self.repositories):
            raise ValueError("Invalid GitHub repository")
        return self


class SourceRegistry(Contract):
    version: Literal[1] = 1
    sources: list[SourceConfig]

    @model_validator(mode="after")
    def unique_ids(self):
        if len({source.id for source in self.sources}) != len(self.sources):
            raise ValueError("Source registry IDs must be unique")
        return self


class RightsReview(Contract):
    # There is deliberately no approval state or decision loader in this wave.
    state: Literal["REVIEW_REQUIRED", "REJECTED"]
    reasons: list[str] = Field(min_length=1)
    origin_signals: list[str] = Field(default_factory=list)
    evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    canonical_evidence_urls: list[str] = Field(default_factory=list)
    invalid_canonical_sha256: list[str] = Field(default_factory=list)

    @field_validator("canonical_evidence_urls")
    @classmethod
    def urls(cls, value):
        return [safe_url(url) for url in value]


class SecurityAdvisoryDates(Contract):
    catalog_added_on: date
    remediation_due_on: date | None = None

    @field_validator("catalog_added_on", "remediation_due_on", mode="before")
    @classmethod
    def date_only(cls, value):
        if value is None or type(value) is date:
            return value
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            raise ValueError("Advisory date must be a date-only YYYY-MM-DD value")
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise ValueError("Invalid advisory date") from error

    def presentation(self):
        return {"catalog_added": f"Added to the CISA KEV catalog on {self.catalog_added_on.isoformat()}",
                "remediation_due": (f"CISA remediation due date: {self.remediation_due_on.isoformat()}"
                                    if self.remediation_due_on else None)}


class SourceItem(Contract):
    id: str
    source_registry_id: str
    canonical_url: str
    original_url: str
    domain: str
    publisher: str
    title: str = Field(min_length=5, max_length=180)
    author: str | None = None
    # Local advisories have dates, never a fabricated publication timestamp.
    published_at: datetime | None
    fetched_at: datetime
    source_type: str
    source_class: SourceClass
    source_independence_group: str
    language: str = "en"
    content_hash: str
    excerpt: str = Field(max_length=600)
    external_id: str | None = None
    http_etag: str | None = None
    http_last_modified: str | None = None
    category: Category
    tags: list[str] = Field(default_factory=list)
    community_score: int = Field(default=0, ge=0)
    missing_publication_time: bool = False
    is_demo: bool = False
    rights_review: RightsReview | None = None
    editorial_kind: Literal["news", "security-advisory"] = "news"
    advisory: SecurityAdvisoryDates | None = None

    _urls = field_validator("canonical_url", "original_url")(safe_url)

    @field_validator("published_at", "fetched_at")
    @classmethod
    def aware(cls, value):
        if value is None:
            return value
        if value.tzinfo is None:
            raise ValueError("Timezone-aware timestamp required")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def publication_contract(self):
        if self.editorial_kind == "security-advisory":
            if not self.advisory or self.published_at is not None or not self.missing_publication_time:
                raise ValueError("Advisory dates cannot be publication timestamps")
        elif self.published_at is None or self.advisory is not None:
            raise ValueError("News evidence requires a publication timestamp")
        return self

    @property
    def publication_eligible(self):
        # Item-level eligibility only; source rights and editorial gates still apply.
        return self.rights_review is None and self.editorial_kind == "news"


class Fact(Contract):
    text: str = Field(min_length=5, max_length=300)
    source_ids: list[str] = Field(min_length=1)
    attribution: Literal["primary", "independent", "community", "aggregator"]
    status: Literal["supported", "conflicting", "uncertain", "retracted/updated"] = "supported"
    id: str | None = None
    story_id: str | None = None
    claim_type: str = "general"
    normalized_value: str | None = None
    unit: str | None = None
    notes: str | None = None


class Number(Contract):
    value: str = Field(max_length=60)
    label: str = Field(max_length=100)
    source_ids: list[str] = Field(min_length=1)
    context: str = Field(max_length=220)


class Change(Contract):
    at: datetime
    text: str
    source_ids: list[str]
    previous_facts: list[Fact] = Field(default_factory=list)


class AIMetadata(Contract):
    generation_mode: Literal["extractive", "ai"] = "extractive"
    provider: str = "extractive"
    model: str = "deterministic-v1"
    prompt_version: str = "1"
    evidence_hash: str


class Summary(Contract):
    headline: str = Field(min_length=10, max_length=180)
    summary_bullets: list[str] = Field(min_length=3, max_length=3)
    why_it_matters: str = Field(min_length=5, max_length=280)
    broader_summary: str = Field(max_length=1800)
    key_facts: list[Fact] = Field(min_length=1, max_length=8)
    key_numbers: list[Number] = Field(default_factory=list, max_length=3)
    limitations: list[str] = Field(default_factory=list)
    category: Category
    subcategory: str | None = None
    tags: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    claim_map: list[Fact] = Field(min_length=3)

    @field_validator("summary_bullets")
    @classmethod
    def bullets(cls, value):
        if any(not 5 <= len(bullet) <= 220 for bullet in value) or len(set(value)) != 3:
            raise ValueError("Three distinct concise bullets required")
        return value


class TranslationContent(Contract):
    headline: str = Field(min_length=10, max_length=260)
    summary_bullets: list[str] = Field(min_length=3, max_length=3)
    why_it_matters: str = Field(min_length=5, max_length=420)
    broader_summary: str = Field(min_length=5, max_length=2700)
    key_fact_texts: list[str] = Field(min_length=1, max_length=8)
    number_labels: list[str] = Field(default_factory=list, max_length=3)
    number_contexts: list[str] = Field(default_factory=list, max_length=3)
    limitations: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("*", mode="after")
    @classmethod
    def direction_safe(cls, value):
        texts = value if isinstance(value, list) else [value]
        if any(char in DIRECTION_CONTROLS for text in texts for char in text):
            raise ValueError("Hidden direction controls are forbidden in translated content")
        return value


class StoryTranslation(Contract):
    language: Literal["bn"]
    content: TranslationContent
    canonical_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    cache_key: str = Field(pattern=r"^[a-f0-9]{64}$")
    provider: str
    model: str
    generated_at: datetime
    review_status: Literal["automated", "fixture-reviewed"] = "automated"


class Story(Summary):
    id: str
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    canonical_topic: str
    source_ids: list[str] = Field(min_length=1)
    primary_source_id: str | None = None
    evidence_state: Evidence
    published_at: datetime
    first_seen_at: datetime
    updated_at: datetime
    last_verified_at: datetime
    importance_score_internal: float = Field(ge=0, le=1)
    novelty_score_internal: float = Field(default=1, ge=0, le=1)
    language: str = "en"
    change_log: list[Change]
    ai_metadata: AIMetadata
    schema_version: int = 1
    is_demo: bool = False
    translations: dict[Literal["bn"], StoryTranslation] = Field(default_factory=dict)


class Offer(Contract):
    id: str
    story_id: str | None = None
    provider: str
    title: str
    offer_type: str
    value_text: str
    eligibility: list[str]
    regions: list[str]
    card_required: bool | None
    claim_steps: list[str]
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    last_verified_at: datetime
    status: Literal["active", "expiring", "expired", "unverified"]
    official_source_url: str
    source_ids: list[str]
    integration_notes: str
    is_demo: bool = False
    _url = field_validator("official_source_url")(safe_url)


class ModelRelease(Contract):
    id: str
    story_id: str
    provider: str
    model: str
    release_date: datetime
    modality: list[str]
    context_window: str | None = None
    pricing: str | None = None
    api_available: bool | None = None
    weights: Literal["open", "closed", "unknown"] = "unknown"
    benchmark_claims: list[str] = Field(default_factory=list)
    independent_references: list[str] = Field(default_factory=list)
    key_change: str
    source_ids: list[str]
    is_demo: bool = False

    @field_validator("independent_references")
    @classmethod
    def references(cls, value):
        return [safe_url(url) for url in value]


class Digest(Contract):
    id: str
    period_type: Literal["daily", "weekly", "monthly", "yearly"]
    period_start: datetime
    period_end: datetime
    status: Literal["in-progress", "finalized"]
    story_ids: list[str]
    top_by_category: dict[str, list[str]]
    summary: str
    what_changed: list[str]
    watch_next: list[Fact] = Field(default_factory=list)
    generated_at: datetime
    schema_version: int = 1


class AnnouncedEvent(Contract):
    at: datetime
    evidence_date_text: str
    fact: Fact


class Snapshot(Contract):
    schema_version: int = 1
    mode: Literal["fixture", "live"]
    generated_at: datetime
    last_successful_fetch_at: datetime
    categories: dict[str, dict]
    stories: list[Story]
    sources: dict[str, SourceItem]
    digests: list[Digest]
    offers: list[Offer]
    model_releases: list[ModelRelease]
    archive_index: list[dict] = Field(default_factory=list)

    @field_validator("archive_index")
    @classmethod
    def archive_paths(cls, value):
        seen = set()
        for entry in value:
            key = entry.get("key", "")
            if (not re.fullmatch(r"[0-9]{4}-(?:0[1-9]|1[0-2])", key) or key in seen
                    or entry.get("url") != f"/archives/{key}/"
                    or not isinstance(entry.get("count"), int) or entry["count"] < 0):
                raise ValueError("Invalid archive index entry")
            seen.add(key)
        return value

    @model_validator(mode="after")
    def relationships(self):
        from pipeline.verification import numeric_tokens, offer_status, validate_story
        if any(not source.publication_eligible for source in self.sources.values()):
            raise ValueError("Local-only review/advisory evidence cannot enter a published snapshot")
        ids = {story.id for story in self.stories}
        if any(key != source.id for key, source in self.sources.items()):
            raise ValueError("Source map identity mismatch")
        if len(ids) != len(self.stories) or len({s.slug for s in self.stories}) != len(ids):
            raise ValueError("Duplicate story identity")
        for story in self.stories:
            validate_story(story, self.sources, self.generated_at)
            from pipeline.translation import validate_translation
            for language, translation in story.translations.items():
                if language != translation.language:
                    raise ValueError("Translation locale mismatch")
                if self.mode == "live" and translation.review_status == "fixture-reviewed":
                    raise ValueError("Fixture translation cannot be published live")
                validate_translation(translation, story)
        for digest in self.digests:
            if not set(digest.story_ids) <= ids:
                raise ValueError("Digest contains missing story")
            if not re.fullmatch(r"[a-zA-Z0-9-]+", digest.id):
                raise ValueError("Unsafe digest identity")
            for category, selected in digest.top_by_category.items():
                if category not in self.categories or not set(selected) <= set(digest.story_ids):
                    raise ValueError("Invalid digest category references")
            for event in digest.watch_next:
                if not set(event.source_ids) <= self.sources.keys():
                    raise ValueError("Watch-next event contains missing sources")
        for offer in self.offers:
            if not set(offer.source_ids) <= self.sources.keys():
                raise ValueError("Offer contains missing source")
            if self.mode == "live" and offer.is_demo:
                raise ValueError("Demo offers cannot be published live")
            if offer.status != offer_status(offer, self.generated_at):
                raise ValueError("Offer status is inconsistent with expiry or verification freshness")
            if not offer.source_ids or not any(self.sources[key].source_class == "primary" for key in offer.source_ids):
                raise ValueError("Tracker offers require official evidence")
            evidence = " ".join(self.sources[key].title + " " + self.sources[key].excerpt for key in offer.source_ids)
            if not numeric_tokens(offer.value_text) <= numeric_tokens(evidence):
                raise ValueError("Offer value is not supported by cited evidence")
        for release in self.model_releases:
            if release.story_id not in ids or not set(release.source_ids) <= self.sources.keys():
                raise ValueError("Model release contains missing story or sources")
            if not any(self.sources[key].source_class == "primary" for key in release.source_ids):
                raise ValueError("Model tracker requires official evidence")
            evidence = " ".join(self.sources[key].title + " " + self.sources[key].excerpt for key in release.source_ids)
            for text in [release.model, release.context_window or "", release.pricing or "", *release.benchmark_claims, release.key_change]:
                if not numeric_tokens(text) <= numeric_tokens(evidence):
                    raise ValueError("Model tracker number is not supported by cited evidence")
        if self.mode == "live" and any(s.is_demo for s in [*self.stories, *self.sources.values(), *self.model_releases]):
            raise ValueError("Demo content cannot be published live")
        return self
