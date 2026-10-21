"""Output boundary for operator reports.

Operator reports are assembled from operator-held files, so a credential that
is pasted into one of those files would otherwise be reproduced verbatim on
stdout. This module decides whether a report may be printed.

The credential markers are the ones this repository already applies to source
files, build output and recovery packs, so the operator CLI is governed by the
same rule as the rest of the project. Nothing here inspects a value's content
beyond matching a marker; a detection records only a category and the JSON path
where the marker was found, never the value itself.
"""

import re

# Private key markers already used by pipeline/recovery/verify.py.
PRIVATE_KEY_MARKERS = (
    "PRIVATE KEY-----", "BEGIN ENCRYPTED PRIVATE KEY", "-----BEGIN RSA",
    "-----BEGIN EC", "-----BEGIN OPENSSH", "ssh-ed25519", "id_ed25519",
)

# Provider credential markers already used by scripts/security.mjs.
PROVIDER_CREDENTIAL_MARKERS = (
    re.compile(r"\bghp_[A-Za-z0-9]{30,}"),
    re.compile(r"\bAIza[A-Za-z0-9_-]{30,}"),
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{25,}"),
)
AUTHORIZATION_MARKER = re.compile(r"\b(?:bearer|basic)\s+[A-Za-z0-9._+/=-]{16,}", re.IGNORECASE)

# A key whose string value is a credential. Public material is deliberately
# excluded: public keys, fingerprints, key ids and signatures are not secrets
# and refusing them would break the operator tools.
SENSITIVE_KEY = re.compile(
    r"(?i)(?:^|[_-])(?:private[_-]?key|client[_-]?secret|secret[_-]?key|session[_-]?key|"
    r"access[_-]?key|api[_-]?key|apikey|secret|password|passwd|passphrase|token|"
    r"credential|credentials|seed|mnemonic)(?:$|[_-])")
MIN_CREDENTIAL_LENGTH = 12


def _string_category(value: str) -> str | None:
    if any(marker in value for marker in PRIVATE_KEY_MARKERS):
        return "private_key_material"
    if any(pattern.search(value) for pattern in PROVIDER_CREDENTIAL_MARKERS):
        return "provider_credential"
    if AUTHORIZATION_MARKER.search(value):
        return "authorization_material"
    return None


def _walk(value, path: str, found: list[dict]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if (isinstance(child, str) and len(child) >= MIN_CREDENTIAL_LENGTH
                    and SENSITIVE_KEY.search(str(key))):
                found.append({"category": "credential_value", "path": child_path})
            _walk(child, child_path, found)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk(child, f"{path}[{index}]", found)
    elif isinstance(value, str):
        category = _string_category(value)
        if category is not None:
            found.append({"category": category, "path": path or "$"})


def scan_payload(payload) -> list[dict]:
    """Report credential-shaped material in a report.

    Returns a list of ``{"category": ..., "path": ...}`` entries. The detected
    value is never included in the result.
    """
    found: list[dict] = []
    _walk(payload, "", found)
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
