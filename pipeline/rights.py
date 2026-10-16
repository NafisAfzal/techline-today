"""Conservative origin assessment and a local, metadata-only review manifest.

Feed assertions are review signals, never trusted decisions. No approvals are
read or written. Any future approval implementation needs a separately trusted
decision with evidence URL, permitted-use scope, reviewer and decision timestamp.
"""

import hashlib
import json
import re
from urllib.parse import urlsplit

from pipeline.models import RightsReview, safe_url
from pipeline.storage import atomic_json, read_json

INCOMPATIBLE_RIGHTS_MARKERS = ("all rights reserved", "reproduced with permission", "used with permission")
ORIGIN_SIGNALS = re.compile(
    r"\b(guest|mirror\w*|originally appeared|originally published|cross[- ]posted|"
    r"republished|syndicat\w*|third[- ]party|contributed by|copyright)\b", re.I)


def assess_rights(raw, source, canonical, corpus):
    reasons = {"origin_evidence_missing"}
    if not raw.get("author"):
        reasons.add("author_missing")
    if raw.get("license") or raw.get("rights"):
        reasons.add("post_specific_license")
    else:
        reasons.add("license_missing")
    signals = sorted({match.group(0).lower()[:40] for match in ORIGIN_SIGNALS.finditer(corpus)})
    if signals:
        reasons.add("origin_review_trigger")
    state = "REVIEW_REQUIRED"
    if any(marker in corpus.lower() for marker in INCOMPATIBLE_RIGHTS_MARKERS):
        state = "REJECTED"
        reasons.add("incompatible_rights_marker")
    allowed = {host.lower().removeprefix("www.") for host in source.allowed_hosts}
    valid, invalid = set(), set()
    candidates = raw.get("canonical_urls", [])
    if not isinstance(candidates, list):
        candidates = [candidates]
    candidates = [canonical, *candidates]
    if raw.get("canonical_url") is not None:
        candidates.append(raw["canonical_url"])
    for candidate in candidates:
        try:
            safe_url(candidate)
            if "<" in candidate or ">" in candidate:
                raise ValueError("Markup in canonical URL")
            host = urlsplit(candidate).hostname.lower().removeprefix("www.")
        except (TypeError, ValueError, AttributeError):
            reasons.add("invalid_canonical_url")
            invalid.add(hashlib.sha256(str(candidate).encode()).hexdigest())
            continue
        if host not in allowed:
            reasons.add("off_domain_canonical")
        if candidate != canonical:
            valid.add(candidate)
    if len(valid) > 1:
        reasons.add("ambiguous_canonical_urls")
    evidence = {key: raw.get(key) for key in ("url", "title", "text", "author", "rights", "license", "canonical_url", "canonical_urls")}
    fingerprint = hashlib.sha256(json.dumps(evidence, sort_keys=True, default=str).encode()).hexdigest()
    return RightsReview(state=state, reasons=sorted(reasons), origin_signals=signals, evidence_sha256=fingerprint,
                        canonical_evidence_urls=sorted(valid),
                        invalid_canonical_sha256=sorted(invalid))


def review_record(item):
    record = {"item_id": item.id, "source_registry_id": item.source_registry_id,
              "item_url": item.canonical_url, "content_sha256": item.content_hash,
              **item.rights_review.model_dump(mode="json")}
    # Distinct observations survive duplicate GUIDs, changed prose and reordering.
    record["record_id"] = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
    return record


def merge_review_queue(path, records):
    existing = read_json(path, {"version": 1, "items": []})
    if existing.get("version") != 1 or not isinstance(existing.get("items"), list):
        raise ValueError("Invalid local review manifest")
    for item in existing["items"]:
        observation = dict(item)
        identity = observation.pop("record_id", None)
        if (observation.get("state") not in ("REVIEW_REQUIRED", "REJECTED")
                or identity != hashlib.sha256(json.dumps(observation, sort_keys=True).encode()).hexdigest()):
            raise ValueError("Invalid local review manifest; approval decisions are not accepted")
    merged = {item["record_id"]: item for item in existing["items"]}
    merged.update({record["record_id"]: record for record in records})
    atomic_json(path, {"version": 1, "items": [merged[key] for key in sorted(merged)]})
