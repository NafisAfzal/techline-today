"""Bounded, unambiguous JSON for untrusted structured source responses."""

import json
import math
import re


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Nonfinite JSON number")
    return number


def reject_constant(value):
    raise ValueError("Nonfinite JSON constant")


def preflight(text, *, max_depth, max_tokens, max_container_items, max_string_chars):
    """Bound allocation before decoding, without replacing JSON syntax validation.

    Tokens include strings, scalar runs and punctuation. String length counts
    encoded characters (escapes conservatively count in full). Each container
    has its own comma budget; the global token budget bounds many small ones.
    """
    quoted = escaped = scalar = False
    stack = []
    tokens = string_chars = number_chars = 0
    for char in text:
        if quoted:
            if char == '"' and not escaped:
                quoted = False
                continue
            string_chars += 1
            if string_chars > max_string_chars:
                raise ValueError("JSON string limit exceeded")
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            continue
        if char.isspace():
            scalar = False
            continue
        if char == '"':
            quoted, escaped, scalar = True, False, False
            string_chars = 0
            tokens += 1
        elif char in "[{":
            stack.append(1)
            if len(stack) > max_depth:
                raise ValueError("JSON nesting limit exceeded")
            tokens += 1
            scalar = False
        elif char in "]},:":
            if char in "]}" and stack:
                stack.pop()
            elif char == "," and stack:
                stack[-1] += 1
                if stack[-1] > max_container_items:
                    raise ValueError("JSON container item limit exceeded")
            tokens += 1
            scalar = False
        else:
            if not scalar:
                tokens += 1
                number_chars = 0
            scalar = True
            number_chars += 1
            if number_chars > 128:
                raise ValueError("JSON scalar number limit exceeded")
        if tokens > max_tokens:
            raise ValueError("JSON token limit exceeded")


def strict_json(data: bytes, *, max_bytes=3_000_000, max_depth=32, max_tokens=200_000,
                max_container_items=20_000, max_string_chars=500_000):
    limits = (max_bytes, max_depth, max_tokens, max_container_items, max_string_chars)
    if any(type(limit) is not int or limit < 1 for limit in limits):
        raise ValueError("JSON limits must be positive integers")
    if not isinstance(data, bytes) or len(data) > max_bytes:
        raise ValueError("JSON byte limit exceeded or invalid input")
    # Bound nesting BEFORE the decoder allocates containers or recurses.
    # detect_encoding handles JSON's UTF-8/16/32 encodings, including BOMs.
    text = data.decode(json.detect_encoding(data))
    preflight(text, max_depth=max_depth, max_tokens=max_tokens,
              max_container_items=max_container_items, max_string_chars=max_string_chars)
    value = json.loads(text, object_pairs_hook=unique_keys, parse_constant=reject_constant,
                       parse_float=finite_float)
    # CPython accepts escaped lone surrogates, which cannot be safely encoded
    # as UTF-8 downstream. Valid JSON surrogate pairs have already been joined.
    pending = [value]
    while pending:
        current = pending.pop()
        if isinstance(current, str) and re.search(r"[\ud800-\udfff]", current):
            raise ValueError("Invalid JSON Unicode surrogate")
        if isinstance(current, dict):
            pending.extend(current.keys())
            pending.extend(current.values())
        elif isinstance(current, list):
            pending.extend(current)
    return value
