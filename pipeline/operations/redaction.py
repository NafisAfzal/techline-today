"""Output boundary for operator reports.

Operator reports are assembled from operator-held files, so a credential that
is pasted into one of those files would otherwise be reproduced verbatim on
stdout. This module decides whether a report may be printed.

The credential markers are the ones this repository already applies to source
files, build output and recovery packs, so the operator CLI is governed by the
same rule as the rest of the project. Nothing here inspects a value's content
beyond matching a marker; a detection records only a category and a positional
path. Neither field names nor values from the input enter the diagnostic path.
"""

import math
import re

# Private key markers already used by pipeline/recovery/verify.py.
PRIVATE_KEY_MARKERS = (
    "PRIVATE KEY-----", "BEGIN ENCRYPTED PRIVATE KEY", "-----BEGIN RSA",
    "-----BEGIN EC", "-----BEGIN OPENSSH",
)

# Provider credential markers already used by scripts/security.mjs.
PROVIDER_CREDENTIAL_MARKERS = (
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{40,}"),
    re.compile(r"AIza[A-Za-z0-9_-]{30,}"),
    re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{25,}"),
)
AUTHORIZATION_MARKER = re.compile(r"\b(?:bearer|basic)\s+[A-Za-z0-9._+/=-]+", re.IGNORECASE)

# A key whose string value is a credential. Public material is deliberately
# excluded: public keys, fingerprints, key ids and signatures are not secrets
# and refusing them would break the operator tools.
SENSITIVE_KEY = re.compile(
    r"(?i)(?:^|[_-])(?:private[_-]?key|client[_-]?secret|secret[_-]?key|session[_-]?key|"
    r"access[_-]?key|api[_-]?key|apikey|secret|password|passwd|passphrase|token|"
    r"credential|credentials|authorization|seed|mnemonic)(?:$|[_-])")
MAX_OUTPUT_DEPTH = 64


def _string_category(value: str) -> str | None:
    if any(marker in value for marker in PRIVATE_KEY_MARKERS):
        return "private_key_material"
    if any(pattern.search(value) for pattern in PROVIDER_CREDENTIAL_MARKERS):
        return "provider_credential"
    if AUTHORIZATION_MARKER.search(value):
        return "authorization_material"
    return None


def _walk(value, path: str, found: list[dict], depth: int = 0) -> None:
    if depth > MAX_OUTPUT_DEPTH:
        raise ValueError("Output nesting exceeds the inspection limit")
    if type(value) is dict:
        for index, (key, child) in enumerate(value.items()):
            if type(key) is not str:
                raise ValueError("Output object keys must be strings")
            if re.search(r"[\ud800-\udfff]", key):
                raise ValueError("Output contains an invalid Unicode surrogate")
            # Field names can themselves contain credentials. Keep diagnostics
            # independent of input text, including opaque names we cannot classify.
            child_path = f"{path}[field:{index}]"
            category = _string_category(key)
            if category is not None:
                found.append({"category": category, "path": child_path + ".key"})
            sensitive = SENSITIVE_KEY.search(key)
            # Numeric metadata such as credential_count is not a credential.
            # A numeric api_key/password still ends with the sensitive name.
            if sensitive and ((type(child) in (int, float) and sensitive.end() == len(key))
                    or (type(child) in (str, list, dict) and bool(child))):
                found.append({"category": "credential_value", "path": child_path})
            _walk(child, child_path, found, depth + 1)
    elif type(value) is list:
        for index, child in enumerate(value):
            _walk(child, f"{path}[{index}]", found, depth + 1)
    elif type(value) is str:
        if re.search(r"[\ud800-\udfff]", value):
            raise ValueError("Output contains an invalid Unicode surrogate")
        category = _string_category(value)
        if category is not None:
            found.append({"category": category, "path": path or "$"})
    elif type(value) is float:
        if not math.isfinite(value):
            raise ValueError("Output contains a nonfinite number")
    elif value is not None and type(value) not in (bool, int):
        raise ValueError("Output contains an unsupported JSON type")


def scan_payload(payload) -> list[dict]:
    """Report credential-shaped material in a report.

    Returns ``{"category": ..., "path": ...}`` entries without input names or
    values. Paths start at ``$``; ``[field:N]`` identifies a zero-based object
    entry in input order and ``[N]`` identifies a list entry.
    """
    found: list[dict] = []
    _walk(payload, "$", found)
    return found


def refusal(detections: list[dict]) -> dict:
    """The minimal report printed instead of a report that carries a credential."""
    return {
        "version": 1,
        "status": "REFUSED",
        "code": "sensitive_output_refused",
        "detections": detections,
        "publication_allowed": False,
        "ai_submission_allowed": False,
        "note": "The report contained credential-shaped material and was not printed. "
                "Inspect the input privately; no authority was granted and nothing was published.",
    }
