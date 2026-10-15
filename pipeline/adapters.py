import base64
import json
import re
from typing import Protocol
from urllib.parse import urlencode, urlsplit
from urllib.robotparser import RobotFileParser

import feedparser
from bs4 import BeautifulSoup

from pipeline.normalize import clean_text


class SourceAdapter(Protocol):
    async def fetch(self, source, fetcher) -> list[dict] | None: ...


class RSSAdapter:
    async def fetch(self, source, fetcher):
        data = await fetcher.get(source.endpoint, source, accept=("application/rss+xml", "application/atom+xml", "application/xml", "text/xml", "text/plain"))
        if data is None:
            return None
        # feedparser expands internal entities. RSS/Atom evidence needs no DTD;
        # reject declarations before parsing, including UTF-16/32 ASCII markup.
        if re.search(br"<!\s*(?:DOCTYPE|ENTITY)\b", data.replace(b"\x00", b""), re.I):
            raise ValueError("RSS DTD and entity declarations are not permitted")
        parsed = feedparser.parse(data)
        if parsed.bozo and not parsed.entries:
            raise ValueError("Malformed or empty feed response")
        return [{"url": entry.link, "title": entry.title, "text": entry.get("summary", ""),
                 "published_at": entry.get("published") or entry.get("updated"), "external_id": entry.get("id"),
                 "author": entry.get("author"), "language": parsed.feed.get("language", "en"),
                 "tags": [tag.get("term", "") for tag in entry.get("tags", [])]}
                for entry in parsed.entries[:source.fetch_policy.max_items] if entry.get("link") and entry.get("title")]


class HackerNewsAdapter:
    async def fetch(self, source, fetcher):
        data = await fetcher.get(source.endpoint + "topstories.json", source, accept=("application/json",), conditional=False)
        ids = json.loads(data)[:source.fetch_policy.max_items]
        items = []
        for item_id in ids:
            raw = await fetcher.get(source.endpoint + f"item/{int(item_id)}.json", source, accept=("application/json",), conditional=False)
            item = json.loads(raw)
            if not item or item.get("deleted") or item.get("dead") or item.get("type") not in ("story", "job"):
                continue
            # Cite the discussion itself. A linked article was not fetched and cannot inherit its evidence status.
            items.append({"url": f"https://news.ycombinator.com/item?id={item_id}", "title": item.get("title", "Untitled discussion"),
                          "text": item.get("text", ""), "published_at": item.get("time"), "external_id": str(item_id),
                          "score": item.get("score", 0), "category": "jobs-skills" if item.get("type") == "job" else None})
        return items


class GitHubReleasesAdapter:
    async def fetch(self, source, fetcher):
        items = []
        unchanged = True
        for repo in source.repositories:
            url = f"{source.endpoint.rstrip('/')}/repos/{repo}/releases?per_page={source.fetch_policy.max_items}"
            raw = await fetcher.get(url, source, accept=("application/json",))
            if raw is None:
                continue
            unchanged = False
            for release in json.loads(raw):
                if release.get("draft") or release.get("prerelease"):
                    continue
                items.append({"url": release["html_url"], "title": f"{repo} {release.get('name') or release['tag_name']}",
                              "text": release.get("body", ""), "published_at": release.get("published_at"),
                              "external_id": f"{repo}:{release['id']}", "_fetch_url": url})
        return None if unchanged else sorted(items, key=lambda item: item.get("published_at") or "", reverse=True)[:source.fetch_policy.max_items]


class JSONAdapter:
    async def fetch(self, source, fetcher):
        raw = await fetcher.get(source.endpoint, source, accept=("application/json",))
        if raw is None:
            return None
        payload = json.loads(raw)
        for path in source.item_path.split(".") if source.item_path else []:
            payload = payload[path]
        if not isinstance(payload, list):
            raise ValueError("JSON adapter item path must resolve to an array")
        fields = {"url": "url", "title": "title", "text": "summary", "published_at": "published_at", **source.field_map}
        return [{field: item.get(key) for field, key in fields.items()} for item in payload[:source.fetch_policy.max_items]]


class GitHubDocumentAdapter:
    """Read explicitly configured, openly licensed official docs through the Contents API."""

    async def fetch(self, source, fetcher):
        raw = await fetcher.get(source.endpoint, source, accept=("application/json",))
        if raw is None:
            return None
        document = json.loads(raw)
        if document.get("encoding") != "base64" or document.get("type") != "file":
            raise ValueError("Expected a GitHub documentation file")
        text = base64.b64decode(document["content"]).decode("utf-8")
        excerpts = []
        for pattern in source.excerpt_patterns:
            found = re.search(pattern, text, re.S)
            if found:
                excerpts.append(found.group(0))
        if not excerpts:
            raise ValueError("Official documentation excerpt patterns no longer match")
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", " ".join(excerpts)).replace("**", "")
        return [{"url": source.document_url or document["html_url"], "title": source.name + " terms",
                 "text": text, "external_id": document["sha"], "category": source.categories[0]}]


class ArxivAdapter(RSSAdapter):
    async def fetch(self, source, fetcher):
        if source.query_groups and "api/query" in source.endpoint:
            query = " OR ".join(f"cat:{group}" for group in source.query_groups)
            source = source.model_copy(update={"endpoint": source.endpoint + "?" + urlencode({"search_query": query, "max_results": source.fetch_policy.max_items, "sortBy": "submittedDate", "sortOrder": "descending"})})
        items = await super().fetch(source, fetcher)
        if items:
            for item in items:
                item["url"] = item["url"].replace("http://arxiv.org/", "https://arxiv.org/")
                item["category"] = "research"
        return items


class HTMLAdapter:
    async def fetch(self, source, fetcher):
        if not source.html_permission:
            raise ValueError("HTML extraction permission absent")
        parts = urlsplit(source.endpoint)
        robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
        raw = await fetcher.get(robots_url, source, accept=("text/plain",), conditional=False)
        robots = RobotFileParser()
        robots.parse(raw.decode("utf-8", errors="replace").splitlines())
        if not robots.can_fetch(fetcher.user_agent, source.endpoint):
            raise ValueError("Robots policy disallows extraction")
        delay = robots.crawl_delay(fetcher.user_agent)
        if delay and delay > 60:
            raise ValueError("Robots crawl delay exceeds source fetch budget")
        if delay and delay > source.fetch_policy.min_interval_seconds:
            source = source.model_copy(update={"fetch_policy": source.fetch_policy.model_copy(update={"min_interval_seconds": delay})})
        raw = await fetcher.get(source.endpoint, source, accept=("text/html",))
        if raw is None:
            return None
        soup = BeautifulSoup(raw, "html.parser")
        body = soup.select_one(source.html_selector)
        if body is None:
            raise ValueError("HTML selector yielded no evidence")
        heading = soup.find("h1") or soup.find("title")
        return [{"url": source.endpoint, "title": clean_text(str(heading), 180), "text": clean_text(str(body), 600)}]


ADAPTERS = {"rss": RSSAdapter(), "hacker_news": HackerNewsAdapter(), "github_releases": GitHubReleasesAdapter(),
            "github_document": GitHubDocumentAdapter(), "json_api": JSONAdapter(), "arxiv": ArxivAdapter(), "html": HTMLAdapter()}
