"""Explainable local intake triage; neither rights nor editorial approval."""

import re


def intake_assessment(item, now):
    kind = ("SECURITY_ADVISORY" if item.editorial_kind == "security-advisory" else
            "RESEARCH" if item.source_type == "arxiv" else
            "OFFICIAL_RELEASE" if item.source_type == "github_releases" else
            "EVERGREEN" if item.source_type == "github_document" else "NEWS")
    dated = item.published_at is not None and not item.missing_publication_time
    age = (now - item.published_at).total_seconds() / 3600 if dated else None
    corpus = item.title + " " + item.excerpt
    signals = {
        "timeliness": 2 if age is not None and 0 <= age <= 24 else 1 if age is not None and 0 <= age <= 72 else 0,
        "originality": 0,  # Origin/authorship cannot be proved by feed fields.
        "primary_source": 2 if item.source_class == "primary" else 0,
        "reader_usefulness": int(bool(re.search(r"\b(fix\w*|migrat\w*|support\w*|secur\w*|API|compatib\w*)\b", corpus, re.I))),
        "technical_specificity": int(bool(re.search(r"\b(?:v?\d+\.\d+|CVE-\d{4}-\d+|API)\b", corpus))),
        "technical_significance_signal": int(bool(re.search(r"\b(breaking|security|vulnerability|stable)\b", corpus, re.I))),
        "substantive_evidence": int(len(item.excerpt) >= 120),
        "origin_evidence": 0,
        "duplicate_clearance": 0,  # Not measured across unseen pages/sources.
    }
    return {"kind_candidate": kind, "classification_status": "EDITORIAL_PENDING",
            "utility_score": sum(signals.values()), "utility_max": 8, "signals": signals,
            "unknowns": ["originality", "origin_evidence", "cross_source_duplicates", "claim_accuracy"],
            "publication_allowed": False}
