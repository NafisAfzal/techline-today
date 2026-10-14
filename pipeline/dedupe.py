import hashlib
import math
import re
from collections import Counter
from datetime import timedelta

from pipeline.normalize import title_tokens


def simhash(text: str) -> int:
    bits = [0] * 64
    for token in title_tokens(text):
        value = int.from_bytes(hashlib.sha256(token.encode()).digest()[:8])
        for bit in range(64):
            bits[bit] += 1 if value & (1 << bit) else -1
    return sum(1 << bit for bit, weight in enumerate(bits) if weight >= 0)


def cosine(left: set[str], right: set[str], idf: dict[str, float]) -> float:
    numerator = sum(idf[token] ** 2 for token in left & right)
    denominator = math.sqrt(sum(idf[token] ** 2 for token in left) * sum(idf[token] ** 2 for token in right))
    return numerator / denominator if denominator else 0


def deduplicate(items):
    unique = []
    keys = set()
    for item in sorted(items, key=lambda item: (item.source_class == "primary", item.fetched_at), reverse=True):
        identity = item.canonical_url
        external = (item.source_registry_id, item.external_id) if item.external_id else identity
        title = (item.source_independence_group, " ".join(re.findall(r"\w+", item.title.lower())), item.published_at.date().isoformat())
        if identity in keys or external in keys or title in keys:
            continue
        keys.update((identity, external, title))
        unique.append(item)
    return unique, len(items) - len(unique)


def cluster(items, hours=72):
    tokens = {item.id: title_tokens(item.title) for item in items}
    frequency = Counter(token for values in tokens.values() for token in values)
    idf = {token: math.log((len(items) + 1) / (count + 1)) + 1 for token, count in frequency.items()}
    groups = []
    hashes = {item.id: simhash(item.title) for item in items}
    for item in sorted(items, key=lambda item: (item.published_at, item.id)):
        match = None
        for group in groups:
            representative = group[0]
            if abs(item.published_at - representative.published_at) > timedelta(hours=hours):
                continue
            left, right = tokens[item.id], tokens[representative.id]
            pattern = r"\b(?:v(?:ersion\s*)?|model\s+version\s+)(\d+(?:\.\d+)*)\b|\b(?:gpt|claude|llama|gemini)[ -]?(\d+(?:\.\d+)*)\b"
            version_left = set(re.findall(pattern, item.title.lower()))
            version_right = set(re.findall(pattern, representative.title.lower()))
            if version_left and version_right and version_left != version_right:
                continue
            if item.source_type == representative.source_type == "github_releases":
                if set(re.findall(r"\b\d+\.\d+(?:\.\d+)*\b", item.title)) != set(re.findall(r"\b\d+\.\d+(?:\.\d+)*\b", representative.title)):
                    continue
            similarity = cosine(left, right, idf)
            same_event = item.canonical_url == representative.canonical_url
            hash_close = (hashes[item.id] ^ hashes[representative.id]).bit_count() <= 3
            if same_event or (len(left & right) >= 3 and (similarity >= 0.67 or hash_close)):
                match = group
                break
        if match is None:
            groups.append([item])
        else:
            match.append(item)
    return groups
