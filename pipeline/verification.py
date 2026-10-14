import re
from datetime import timedelta

from pipeline.models import Fact, Number

NUMBERS = re.compile(r"(?<![\w])[$€£]?[-+]?\d+(?:[,.]\d+)*(?:e[-+]?\d+)?(?:\s?(?:GB|MB|TB|GHz|MHz|nm|Wh|mAh|W)|[KkMmBb%])?(?![\w])", re.I)


def numeric_tokens(text):
    return {match.lower().replace(",", "").replace(" ", "") for match in NUMBERS.findall(text)}


def evidence_state(items):
    if any(item.source_class == "primary" for item in items):
        return "primary-confirmed"
    groups = {item.source_independence_group for item in items if item.source_class == "independent"}
    if len(groups) >= 2:
        return "multi-source"
    if groups:
        return "single-source"
    if any(item.source_class == "community" for item in items):
        return "community-report"
    return "needs-verification"


def extract_claims(items):
    facts, numbers = [], []
    for item in items:
        texts = re.split(r"(?<=[.!?])\s+", item.excerpt) + [item.title]
        for text in texts:
            text = text.strip()
            if len(text) > 220:
                text = text[:217].rsplit(" ", 1)[0].rstrip(".,;:") + "…"
            if len(text) < 10 or text in {fact.text for fact in facts}:
                continue
            values = NUMBERS.findall(text)
            claim_type = "benchmark" if "benchmark" in text.lower() else "release" if re.search(r"\b(release|launch|publis\w*)\b", text, re.I) else "general"
            facts.append(Fact(text=text, source_ids=[item.id], attribution=item.source_class, claim_type=claim_type,
                              normalized_value=values[0].replace(",", "") if len(values)==1 else None,
                              status="uncertain" if item.source_class in ("community", "aggregator") else "supported"))
            for value in list(NUMBERS.findall(text))[:3]:
                if value not in {number.value for number in numbers}:
                    label = next((label for keyword, label in (("memory", "Memory"), ("context window", "Context"), ("display", "Display"), ("credit", "Trial credit"), ("evaluation tasks", "Evaluation tasks")) if keyword in text.lower()), "Source-reported")
                    numbers.append(Number(value=value, label=label, source_ids=[item.id], context=text))
            if len(facts) >= 8:
                return facts, numbers[:3]
    return facts, numbers[:3]


def conflicts(items):
    limitations = []
    for index, left in enumerate(items):
        for right in items[index + 1:]:
            # Only compare the same metric sentence; differing release versions are clustered separately.
            for metric in ("throughput", "accuracy", "benchmark", "context window", "price"):
                left_sentences = [s for s in re.split(r"[.!?]\s", left.excerpt) if metric in s.lower()]
                right_sentences = [s for s in re.split(r"[.!?]\s", right.excerpt) if metric in s.lower()]
                if left_sentences and right_sentences:
                    a, b = numeric_tokens(" ".join(left_sentences)), numeric_tokens(" ".join(right_sentences))
                    if a and b and a != b:
                        limitations.append(f"{left.publisher} and {right.publisher} report different {metric} figures; measurement context may differ. Consult both sources.")
    return sorted(set(limitations))


def validate_summary(summary, items):
    sources = {item.id: item for item in items}
    evidence = " ".join(item.title + " " + item.excerpt for item in items)
    allowed_numbers = numeric_tokens(evidence)
    strings = [summary.headline, summary.why_it_matters, summary.broader_summary, *summary.summary_bullets,
               *summary.limitations, *[fact.text for fact in summary.key_facts], *[number.value + " " + number.context for number in summary.key_numbers]]
    for text in strings:
        if not numeric_tokens(text) <= allowed_numbers:
            raise ValueError("Unsupported numeric claim")
        if re.search(r"\b(best|unprecedented|revolutionary|guaranteed|confirmed)\b", text, re.I) and text.lower() not in evidence.lower():
            raise ValueError("Unsupported certainty or superlative")
    for fact in [*summary.key_facts, *summary.claim_map, *summary.key_numbers]:
        if not set(fact.source_ids) <= sources.keys():
            raise ValueError("Unknown claim source")
        if isinstance(fact, Fact) and fact.attribution not in {sources[key].source_class for key in fact.source_ids}:
            raise ValueError("Claim attribution does not match cited evidence")
        mapped = " ".join(sources[key].title + " " + sources[key].excerpt for key in fact.source_ids)
        text = fact.text if hasattr(fact, "text") else fact.value + " " + fact.context
        if not numeric_tokens(text) <= numeric_tokens(mapped):
            raise ValueError("Numeric claim not supported by cited source")
    claims = {fact.text for fact in summary.claim_map}
    if not set(summary.summary_bullets) <= claims:
        raise ValueError("Every summary bullet requires a claim mapping")
    for conflict in conflicts(items):
        if conflict not in summary.limitations:
            raise ValueError("Source conflict must be exposed")


def validate_story(story, sources, now):
    if not set(story.source_ids) <= sources.keys():
        raise ValueError("Story contains missing sources")
    items = [sources[key] for key in story.source_ids]
    if story.primary_source_id is not None and (story.primary_source_id not in story.source_ids or sources[story.primary_source_id].source_class != "primary"):
        raise ValueError("Invalid primary source attribution")
    for change in story.change_log:
        if not set(change.source_ids) <= sources.keys():
            raise ValueError("Correction history contains missing evidence")
    validate_summary(story, items)
    if story.evidence_state != evidence_state(items):
        raise ValueError("Inconsistent evidence state")
    if story.published_at > now + timedelta(minutes=10):
        raise ValueError("Future publication date")


def offer_status(offer, now):
    if offer.expires_at and offer.expires_at <= now:
        return "expired"
    if offer.starts_at and offer.starts_at > now:
        return "unverified"
    if now - offer.last_verified_at > timedelta(days=7) or offer.status == "unverified":
        return "unverified"
    if offer.expires_at and offer.expires_at <= now + timedelta(days=7):
        return "expiring"
    return "active"
