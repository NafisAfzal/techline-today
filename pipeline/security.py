import asyncio
import hashlib
import ipaddress
import socket
import time
from urllib.parse import urljoin, urlsplit

import httpcore
import httpx
from httpcore._backends.anyio import AnyIOBackend

from pipeline.models import is_public_address, safe_url

SOURCE_TRANSFORM_VERSION = "13"


def public_addresses(addresses: list[str]) -> list[str]:
    if not addresses or any(not is_public_address(ipaddress.ip_address(ip)) for ip in addresses):
        raise ValueError("Destination resolved to a non-public address")
    return addresses


class PublicNetworkBackend(AnyIOBackend):
    """Pin the validated DNS answer at connect time; TLS retains the original SNI."""

    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        try:
            async with asyncio.timeout(timeout or 10):
                entries = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
                addresses = public_addresses(list(dict.fromkeys(entry[4][0] for entry in entries)))
                last_error = None
                for address in addresses[:4]:
                    try:
                        return await super().connect_tcp(address, port, min(timeout or 10, 3), local_address, socket_options)
                    except (httpcore.ConnectError, httpcore.ConnectTimeout) as error:
                        last_error = error
                raise httpcore.ConnectError("All validated addresses failed") from last_error
        except TimeoutError as error:
            raise httpcore.ConnectTimeout("Public destination connect timed out") from error
        except OSError as error:
            raise httpcore.ConnectError("Public destination DNS lookup failed") from error


def public_transport() -> httpx.AsyncHTTPTransport:
    transport = httpx.AsyncHTTPTransport(retries=0)
    # httpx 0.28/httpcore 1.0 are locked; the backend closes DNS-rebinding and redirect SSRF gaps.
    transport._pool = httpcore.AsyncConnectionPool(network_backend=PublicNetworkBackend())
    return transport


class SafeFetcher:
    def __init__(self, client: httpx.AsyncClient, state: dict, user_agent: str):
        self.client = client
        self.state = state
        self.user_agent = user_agent
        self.last_request: dict[str, float] = {}
        self.lock = asyncio.Lock()
        self.host_locks: dict[str, asyncio.Lock] = {}
        self.revalidated_ids: set[str] = set()
        self.modified_keys: dict[str, set[str]] = {}

    async def request(self, url, headers, source, accept):
        for attempt in range(3):
            host = urlsplit(url).hostname
            async with self.lock:
                delay = source.fetch_policy.min_interval_seconds - (time.monotonic() - self.last_request.get(host, 0))
                if delay > 0:
                    await asyncio.sleep(delay)
                self.last_request[host] = time.monotonic()
            try:
                async with asyncio.timeout(30):
                    async with self.client.stream("GET", url, headers=headers, follow_redirects=False) as response:
                        status = response.status_code
                        response_headers = dict(response.headers)
                        if status in (301, 302, 303, 307, 308, 304):
                            return status, response_headers, None
                        if status in (429, 502, 503, 504) and attempt < 2:
                            try:
                                delay = min(float(response.headers.get("retry-after", 2 ** attempt)), 5)
                            except ValueError:
                                delay = 2 ** attempt
                            await asyncio.sleep(max(0, delay))
                            continue
                        response.raise_for_status()
                        if response.headers.get("content-encoding", "identity").strip().lower() != "identity":
                            raise ValueError("Compressed source responses are not permitted")
                        mime = response.headers.get("content-type", "").split(";")[0].lower()
                        if not any(mime == kind or mime.endswith("+" + kind.split("/")[-1]) for kind in accept):
                            raise ValueError("Unexpected source content type")
                        body = bytearray()
                        async for chunk in response.aiter_bytes(chunk_size=65536):
                            body.extend(chunk)
                            if len(body) > source.fetch_policy.max_response_bytes:
                                raise ValueError("Response size limit exceeded")
                        return status, response_headers, bytes(body)
            except (httpx.TimeoutException, httpx.NetworkError, TimeoutError):
                if attempt == 2:
                    raise
                await asyncio.sleep(2 ** attempt)
        raise ValueError("Source retries exhausted")

    async def get(self, url: str, source, *, accept: tuple[str, ...], conditional=True):
        for redirect in range(4):
            safe_url(url)
            host = urlsplit(url).hostname
            if host not in source.allowed_hosts:
                raise ValueError("Fetch host not allowlisted")
            state_key = source.id + "|" + url
            cached = self.state.get(state_key, {})
            policy_hash = hashlib.sha256((SOURCE_TRANSFORM_VERSION + source.model_dump_json()).encode()).hexdigest()
            headers = {"User-Agent": self.user_agent, "Accept": ", ".join(accept), "Accept-Encoding": "identity"}
            if conditional and source.fetch_policy.conditional_requests and cached.get("policy_hash") == policy_hash and "item_ids" in cached:
                if cached.get("etag"):
                    headers["If-None-Match"] = cached["etag"]
                if cached.get("modified"):
                    headers["If-Modified-Since"] = cached["modified"]
            async with self.host_locks.setdefault(host, asyncio.Lock()):
                status, response_headers, body = await self.request(url, headers, source, accept)
            if status in (301, 302, 303, 307, 308):
                if source.adapter == "html":
                    raise ValueError("HTML redirects require review of the endpoint and robots policy")
                if redirect == 3:
                    raise ValueError("Redirect limit exceeded")
                url = urljoin(url, response_headers.get("location", ""))
                continue
            if status == 304:
                if not any(key in headers for key in ("If-None-Match", "If-Modified-Since")):
                    raise ValueError("Unsolicited 304 without validated cached evidence")
                self.revalidated_ids.update(cached["item_ids"])
                return None
            if conditional:
                self.state[state_key] = {"etag": response_headers.get("etag"), "modified": response_headers.get("last-modified"), "policy_hash": policy_hash, "item_ids": []}
                self.modified_keys.setdefault(source.id, set()).add(state_key)
            return body
        raise ValueError("Source fetch did not complete")
