import hashlib
import re
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from pipeline.models import SourceItem, safe_url

TRACKING = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "ref_src", "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"}


def release_text(markdown: str) -> str:
    """Keep release prose, never render Markdown or expose raw tracking/link syntax."""
    text = re.sub(r"!\[[^\]\n]*\]\([^\s)]*\)", "", markdown)
    text = re.sub(r"\[([^\]\n]+)\]\([^\s)]*\)", r"\1", text)
    text = re.sub(r"\\([\\`*_{}\[\]()#+.!-])", r"\1", text)
    text = re.sub(r"\(?#[0-9]+\)?", "", text).replace("`", "")
    # Changesets may put the actual fix after the thanks on the SAME line.
    # Strip only the prefix, never the remaining evidence.
    text = re.sub(r"(?m)^[ \t]*[-*+]?[ \t]*[a-f0-9]{7,40}[ \t]*:?[ \t]*Thanks[ \t]+@[^\s!]+![ \t]*", "", text)
    lines = text.splitlines()
    for index, line in enumerate(lines):
        heading = re.match(r"^\s*#{1,6}\s+(.+?)\s*#*\s*$", line)
        if not heading:
            continue
        title = heading.group(1).strip()
        following = next((next_line.strip() for next_line in lines[index + 1:] if next_line.strip()), "")
        # Remove only duplicated headings and generic document labels. Retain
        # meaningful labels such as breaking changes, preview and known issues.
        if title.casefold() in {"release notes", "new model additions", "what's changed", "patch changes"} or following.casefold().startswith(title.casefold() + " "):
            lines[index] = ""
        else:
            lines[index] = title.rstrip(":") + ":"
    text = "\n".join(lines)
    text = re.sub(r"(?m)^\s*(?:#{1,6}\s+|[-*+]\s+|```[^\n]*)", "", text)
    return text.replace("`", "").replace("**", "").replace("__", "")


def canonicalize(url: str) -> str:
    safe_url(url)
    parts = urlsplit(url)
    parameters = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key.lower() not in TRACKING and not key.lower().startswith("utm_")]
    query = urlencode(sorted(parameters, key=lambda pair: pair[0]))
    return urlunsplit(("https", parts.netloc.lower(), parts.path or "/", query, ""))


def clean_text(text: str, limit: int = 600) -> str:
    soup = BeautifulSoup(text or "", "html.parser")
    for node in soup(["script", "style", "iframe", "noscript"]):
        node.decompose()
    result = re.sub(r"\s+", " ", soup.get_text(" ")).strip().replace("<", "").replace(">", "").replace("\x00", "")
    if len(result) > limit:
        result = result[:limit - 1].rsplit(" ", 1)[0].rstrip(".,;:") + "…"
    return result


def title_tokens(text: str) -> set[str]:
    stop = {"the", "a", "an", "and", "for", "with", "of", "to", "in", "on", "is", "new", "release", "releases", "announces", "announced"}
    return {token for token in re.findall(r"[\w]+", text.lower()) if token not in stop}


def discovery_relevant(title: str, excerpt: str, keywords: list[str]) -> bool:
    corpus = title + " " + excerpt
    return not keywords or any(re.search(r"\b" + re.escape(keyword) + r"\b", corpus, re.I) for keyword in keywords)


def parse_date(value, now: datetime) -> tuple[datetime, bool]:
    if isinstance(value, (int, float)):
        try:
            result = datetime.fromtimestamp(value, UTC)
        except (ValueError, OverflowError, OSError):
            return now, True
    elif value:
        try:
            result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            try:
                result = parsedate_to_datetime(str(value))
            except (ValueError, TypeError):
                return now, True
    else:
        return now, True
    if result.tzinfo is None:
        result = result.replace(tzinfo=UTC)
    if result > now + timedelta(minutes=10) or result.year < 1990:
        return now, True
    return result.astimezone(UTC), False


def classify(title: str, text: str, defaults: list[str]) -> str:
    corpus = (title + " " + text).lower()
    rules = [
        ("security", r"\b(cve|vulnerability|ransomware|security patch|breach|exploit)\b"),
        ("freebies", r"\b(free credit|student pack|free tier|developer credit)\b"),
        ("jobs-skills", r"\b(hiring|layoff|internship|fellowship|skills demand)\b"),
        ("chips", r"\b(gpus?|semiconductor|chip|accelerator|cuda|processor|dgx|unified memory)\b"),
        ("devices", r"\b(laptop|phone|smartphone|tablet|battery)\b"),
        ("research", r"\b(arxiv|paper|dataset|research|preprint)\b"),
        ("ai", r"\b(llm|model|ai|gemini|claude|gpt|inference|agent)\b"),
        ("dev-apis", r"\b(api|sdk|pricing|cloud|developer)\b"),
        ("open-source", r"\b(release|open source|framework|library)\b"),
    ]
    title_category = next((category for category, pattern in rules if re.search(pattern, title.lower())), None)
    if title_category:
        return title_category
    # Incidental mentions of "research" in product/company announcements
    # should not turn them into research papers.
    body_rules = [(category, pattern) for category, pattern in rules if category != "research"]
    if defaults[0] == "research" or re.search(r"\b(arxiv|preprint|paper|dataset)\b", text, re.I):
        body_rules = rules
    return next((category for category, pattern in body_rules if re.search(pattern, corpus)), defaults[0])


def normalize(raw: dict, source, now: datetime) -> SourceItem:
    if not raw.get("url") or not raw.get("title"):
        raise ValueError("Source URL and title are required")
    original = str(raw["url"])
    canonical = canonicalize(original)
    title = clean_text(str(raw["title"]), 180)
    if len(title) < 10:
        title = f"{source.name}: {title}"
    body = str(raw.get("text", ""))
    excerpt = clean_text(release_text(body) if source.adapter == "github_releases" else body, 600)
    published, missing = parse_date(raw.get("published_at"), now)
    item_id = "src_" + hashlib.sha256((source.id + canonical).encode()).hexdigest()[:20]
    return SourceItem(
        id=item_id, source_registry_id=source.id, canonical_url=canonical, original_url=original,
        domain=urlsplit(original).hostname, publisher=source.name, title=title,
        author=clean_text(str(raw["author"]), 100) if raw.get("author") else None,
        published_at=published, fetched_at=now, source_type=source.adapter,
        source_class=source.source_class, source_independence_group=source.independence_group,
        language=raw.get("language", "en"), content_hash=hashlib.sha256((title + excerpt).encode()).hexdigest(),
        excerpt=excerpt, external_id=str(raw["external_id"]) if raw.get("external_id") else None,
        category=raw.get("category") or classify(title, excerpt, source.categories),
        tags=[clean_text(str(tag), 60) for tag in raw.get("tags", [])][:8],
        community_score=max(0, int(raw.get("score", 0))), missing_publication_time=missing,
        is_demo=raw.get("is_demo", False),
    )
