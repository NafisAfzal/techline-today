import base64
import hashlib
import heapq
import json
import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from string import Formatter
from typing import Protocol
from urllib.parse import quote, unquote, urlencode, urlsplit
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree

import feedparser
from bs4 import BeautifulSoup

from pipeline.models import safe_url
from pipeline.normalize import clean_text, validate_cve_id
from pipeline.strict_json import strict_json


def render_template(template, item, *, url=False):
    values = {}
    for _, field, spec, conversion in Formatter().parse(template):
        if field is None:
            continue
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", field) or spec or conversion:
            raise ValueError("Only simple template fields are accepted")
        value = item.get(field)
        if value is None or not isinstance(value, (str, int, float, bool)):
            raise ValueError("Missing or non-scalar template field")
        if url and str(value) in (".", ".."):
            raise ValueError("URL dot segments are forbidden")
        values[field] = quote(str(value), safe="") if url else str(value)
    return template.format(**values)


def template_url(template, item, source):
    if not source.template_url_origin:
        raise ValueError("URL template origin is required")
    origin = urlsplit(safe_url(source.template_url_origin))
    # A replacement field can never participate in the origin, even if its
    # current value happens to be the expected host. Recheck at runtime too.
    literal = urlsplit(template)
    if (origin.hostname not in source.allowed_hosts or origin.path not in ("", "/")
            or origin.query or origin.fragment
            or literal.scheme != "https" or literal.netloc != origin.netloc):
        raise ValueError("URL template origin mismatch")
    result = render_template(template, item, url=True)
    parts = urlsplit(safe_url(result))
    if (parts.scheme, parts.netloc) != (origin.scheme, origin.netloc):
        raise ValueError("URL template changed origin")
    return result


class SourceAdapter(Protocol):
    async def fetch(self, source, fetcher) -> list[dict] | None: ...


def selection_key(timestamp, identity, payload):
    """Newest supplied date first, missing/malformed dates last, stable ties.

    Selection covers only this bounded response, never unseen upstream pages.
    Freshness and rights eligibility are still validated downstream.
    """
    try:
        if isinstance(timestamp, (int, float)) and not isinstance(timestamp, bool):
            parsed = datetime.fromtimestamp(timestamp, UTC)
        else:
            try:
                parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
            except ValueError:
                parsed = parsedate_to_datetime(str(timestamp))
        if parsed.tzinfo is None:
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", str(timestamp)):
                raise ValueError("Selection timestamp has no authoritative timezone")
            # Calendar order is useful for KEV/date-only feeds. This internal
            # sort coordinate never establishes a public clock time.
            parsed = parsed.replace(tzinfo=UTC)
        parsed = parsed.astimezone(UTC)
        stamp = parsed.timestamp() if parsed.year >= 1990 else float("-inf")
    except (ValueError, TypeError, OverflowError, OSError):
        stamp = float("-inf")
    return -stamp, str(identity or ""), hashlib.sha256(payload).hexdigest()


class RSSAdapter:
    async def fetch(self, source, fetcher):
        data = await fetcher.get(source.endpoint, source, accept=("application/rss+xml", "application/atom+xml", "application/xml", "text/xml", "text/plain"))
        if data is None:
            return None
        # feedparser expands internal entities. RSS/Atom evidence needs no DTD;
        # reject declarations before parsing, including UTF-16/32 ASCII markup.
        if re.search(br"<!\s*(?:DOCTYPE|ENTITY)\b", data.replace(b"\x00", b""), re.I):
            raise ValueError("RSS DTD and entity declarations are not permitted")
        # Scan the byte-bounded XML tree cheaply before expensive feedparser
        # work. Keep the newest max_items regardless of input order.
        try:
            # Bound depth and node allocation incrementally. The byte ceiling
            # alone permits hundreds of thousands of tiny elements.
            parser = ElementTree.XMLPullParser(events=("start", "end"))  # noqa: S314 - DTD/entities rejected above
            root = None
            depth = nodes = 0
            for offset in range(0, len(data), 16384):
                parser.feed(data[offset:offset + 16384])
                for event, element in parser.read_events():
                    if event == "start":
                        root = element if root is None else root
                        depth += 1
                        nodes += 1
                        if depth > 32 or nodes > 100000 or len(element.attrib) > 64:
                            raise ValueError("XML allocation limit exceeded")
                    else:
                        depth -= 1
            parser.close()
            if root is None:
                raise ValueError("Response is not a feed")
            if (root.tag.rsplit("}", 1)[-1] not in {"rss", "feed", "RDF"}
                    or root.tag.rsplit("}", 1)[-1] == "rss" and not any(
                        child.tag.rsplit("}", 1)[-1] == "channel" for child in root)):
                raise ValueError("Response is not an RSS or Atom feed")
            changed = False
            for parent in (root, *(child for child in root if child.tag.rsplit("}", 1)[-1] == "channel")):
                entries = [child for child in parent if child.tag.rsplit("}", 1)[-1] in ("item", "entry")]
                if entries:
                    def key(entry):
                        fields = {child.tag.rsplit("}", 1)[-1]: child for child in entry}
                        date = next((fields[name].text for name in ("pubDate", "published", "updated")
                                     if name in fields), None)
                        link = fields.get("link")
                        identity = (link.get("href") or link.text) if link is not None else None
                        return selection_key(date, identity, ElementTree.tostring(entry, encoding="utf-8"))
                    retained = heapq.nsmallest(source.fetch_policy.max_items, entries, key=key)
                    parent[:] = [child for child in parent
                                 if child.tag.rsplit("}", 1)[-1] not in ("item", "entry")] + retained
                    changed = True
            if changed:
                data = ElementTree.tostring(root, encoding="utf-8")
        except ElementTree.ParseError as error:
            # Partial parser recovery cannot turn corrupt XML into empty or
            # apparently complete successful collection.
            raise ValueError("Malformed feed XML") from error
        parsed = feedparser.parse(data)
        if parsed.bozo:
            raise ValueError("Malformed or empty feed response")
        return [{"url": entry.get("link"), "title": entry.get("title"), "text": entry.get("summary", ""),
                 "published_at": entry.get("published"),
                 "updated_at": entry.get("updated") if "updated" in entry else None,
                 "external_id": entry.get("id"),
                 "author": entry.get("author"), "language": parsed.feed.get("language", "en"),
                 "canonical_urls": [link.get("href", "") for link in entry.get("links", [])
                                    if link.get("rel") == "canonical"],
                 "rights": entry.get("rights"), "license": entry.get("license") or next(
                     (link.get("href") for link in entry.get("links", []) if link.get("rel") == "license"), None),
                 "tags": [tag.get("term", "") for tag in entry.get("tags", [])]}
                for entry in parsed.entries[:source.fetch_policy.max_items]]


class HackerNewsAdapter:
    async def fetch(self, source, fetcher):
        data = await fetcher.get(source.endpoint + "topstories.json", source, accept=("application/json",), conditional=False)
        ids = strict_json(data)[:source.fetch_policy.max_items]
        items = []
        for item_id in ids:
            raw = await fetcher.get(source.endpoint + f"item/{int(item_id)}.json", source, accept=("application/json",), conditional=False)
            item = strict_json(raw)
            if not item or item.get("deleted") or item.get("dead") or item.get("type") not in ("story", "job"):
                continue
            # Cite the discussion itself. A linked article was not fetched and cannot inherit its evidence status.
            items.append({"url": f"https://news.ycombinator.com/item?id={item_id}", "title": item.get("title", "Untitled discussion"),
                          "text": item.get("text", ""), "published_at": item.get("time"), "external_id": str(item_id),
                          "score": item.get("score", 0), "category": "jobs-skills" if item.get("type") == "job" else None})
        return items


class GitHubReleasesAdapter:
    """One bounded page per repository; never follow upstream pagination links.

    Selection is deterministic over fetched pages only. The upstream API may
    omit newer publications whose releases were created earlier; no complete
    release-history or global newest-item guarantee is made.
    """

    async def fetch(self, source, fetcher):
        items = []
        unchanged = True
        for repo in source.repositories:
            url = f"{source.endpoint.rstrip('/')}/repos/{repo}/releases?per_page={source.fetch_policy.max_items}"
            raw = await fetcher.get(url, source, accept=("application/json",))
            if raw is None:
                continue
            unchanged = False
            releases = strict_json(raw)
            if not isinstance(releases, list):
                raise ValueError("GitHub releases must be an array")
            identities = {}
            for release in releases:
                if not isinstance(release, dict):
                    raise ValueError("GitHub release must be an object")
                if any(type(release.get(flag, False)) is not bool for flag in ("draft", "prerelease")):
                    raise ValueError("GitHub release flags must be booleans")
                if type(release.get("id")) is not int or release["id"] < 1:
                    raise ValueError("Invalid GitHub release identity")
                encoded = json.dumps(release, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
                previous = identities.setdefault(release["id"], encoded)
                if previous != encoded:
                    raise ValueError("Conflicting GitHub release identity in fetched page")
                if release.get("draft") or release.get("prerelease"):
                    continue
                if (type(release.get("id")) is not int or release["id"] < 1
                        or not isinstance(release.get("tag_name"), str) or not release["tag_name"]
                        or any(release.get(field) is not None and not isinstance(release[field], str)
                               for field in ("name", "body", "published_at", "created_at"))):
                    raise ValueError("Invalid GitHub release fields")
                release_url = safe_url(release.get("html_url"))
                if urlsplit(source.endpoint).hostname == "api.github.com":
                    parts = urlsplit(release_url)
                    decoded_path = unquote(parts.path)
                    prefix = f"/{repo}/releases/tag/"
                    if (parts.netloc != "github.com" or parts.query or parts.fragment
                            or not decoded_path.casefold().startswith(prefix.casefold())
                            or decoded_path[len(prefix):] != release["tag_name"]
                            or any(segment in {".", ".."} for segment in decoded_path.split("/"))):
                        raise ValueError("GitHub release URL does not belong to configured repository")
                    # The API object and browser URL must agree. Public release
                    # objects normally include this API URL; legacy synthetic
                    # fixtures may omit it. Never follow it as a new endpoint.
                    if "url" in release:
                        api = urlsplit(safe_url(release["url"]))
                        expected = f"/repos/{repo}/releases/{release['id']}"
                        if (api.netloc != "api.github.com" or api.query or api.fragment
                                or api.path.casefold() != expected.casefold()):
                            raise ValueError("GitHub API release identity mismatch")
                    if "repository" in release:
                        repository = release["repository"]
                        if (not isinstance(repository, dict)
                                or not isinstance(repository.get("full_name"), str)
                                or repository["full_name"].casefold() != repo.casefold()):
                            raise ValueError("GitHub repository identity mismatch")
                items.append({"url": release["html_url"], "title": f"{repo} {release.get('name') or release['tag_name']}",
                              "text": release.get("body", ""), "published_at": release.get("published_at"),
                              "release_created_at": release.get("created_at"),
                              "external_id": f"{repo}:{release['id']}", "_fetch_url": url,
                              "author": release.get("author", {}).get("login")
                              if isinstance(release.get("author"), dict) else None})
        return None if unchanged else heapq.nsmallest(source.fetch_policy.max_items, items,
            key=lambda item: selection_key(item.get("published_at"), item["url"],
                json.dumps(item, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()))


class JSONAdapter:
    async def fetch(self, source, fetcher):
        raw = await fetcher.get(source.endpoint, source, accept=("application/json",))
        if raw is None:
            return None
        payload = strict_json(raw)
        for path in source.item_path.split(".") if source.item_path else []:
            payload = payload[path]
        if not isinstance(payload, list):
            raise ValueError("JSON adapter item path must resolve to an array")
        fields = {"url": "url", "title": "title", "text": "summary", "published_at": "published_at", **source.field_map}
        items = []
        for item in payload:
            if not isinstance(item, dict):
                items.append({"_validation_error": "JSON item must be an object"})
                continue
            mapped = {field: item.get(key) for field, key in fields.items()}
            if source.identifier_format == "cve":
                try:
                    validate_cve_id(mapped.get("external_id"))
                except ValueError:
                    mapped["_validation_error"] = "Invalid CVE identifier"
            for field, template in source.field_templates.items():
                try:
                    if field == "url" and mapped.get("_validation_error"):
                        raise ValueError("Invalid identifier cannot form a URL")
                    mapped[field] = template_url(template, item, source) if field == "url" else render_template(template, item)
                except (KeyError, IndexError, ValueError, TypeError):
                    mapped[field] = None
            items.append(mapped)
        return heapq.nsmallest(source.fetch_policy.max_items, items, key=lambda item: selection_key(
            item.get("catalog_added_on") if source.editorial_kind == "security-advisory" else item.get("published_at"),
            item.get("url"), json.dumps(item, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()))


class GitHubDocumentAdapter:
    """Read explicitly configured, openly licensed official docs through the Contents API."""

    async def fetch(self, source, fetcher):
        raw = await fetcher.get(source.endpoint, source, accept=("application/json",))
        if raw is None:
            return None
        document = strict_json(raw)
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
                if isinstance(item.get("url"), str):
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
