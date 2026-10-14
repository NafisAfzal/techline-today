import math
import re


def novelty(items, previous_sources):
    if any(item.id not in previous_sources for item in items):
        return 1
    return .65 if any(item.content_hash != previous_sources[item.id].content_hash for item in items) else 0


def rank(items, config, categories, now, novelty_score=1):
    latest = max(item.published_at for item in items)
    strength = max({"primary": 1, "independent": .8, "aggregator": .35, "community": .15}[item.source_class] for item in items)
    groups = {item.source_independence_group for item in items if item.source_class in ("primary", "independent")}
    signals = {
        "recency": math.exp(-max(0, (now - latest).total_seconds()) / 86400),
        "source_strength": strength, "cross_source_support": min(1, max(0, len(groups) - 1) / 2),
        "novelty": max(0, min(1, novelty_score)), "category_relevance": categories[items[0].category]["priority"],
        "community_signal": min(.5 if strength < .5 else 1, math.log1p(max(i.community_score for i in items)) / 8),
    }
    if all(item.missing_publication_time for item in items):
        signals["recency"] *= 1 - config["penalties"].get("missing_publication_time", .65)
    score = sum(config["weights"][key] * value for key, value in signals.items())
    release = any(item.source_class == "primary" and (item.source_type == "github_releases" or re.search(r"\b(releases?|introduc\w*|launch\w*|announc\w*|open[- ]sourc\w*)\b", item.title, re.I)) for item in items)
    if release:
        score += config["boosts"]["primary_product_release"]
    if items[0].category == "security" and strength >= .8:
        score += config["boosts"]["critical_security_update"]
    if strength < .5:
        score *= 1 - config["penalties"]["community_only_unverified"]
    if not any(item.source_class in ("primary", "independent") and len(item.excerpt.strip()) >= 80
               and item.excerpt.strip().casefold() != item.title.strip().casefold() for item in items):
        score *= 1 - config["penalties"].get("insufficient_prose", .65)
    return round(max(0, min(1, score)), 5)
