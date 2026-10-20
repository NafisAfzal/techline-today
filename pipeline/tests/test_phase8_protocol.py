import hashlib
import json

import pytest
from pydantic import ValidationError

from pipeline.authority.protocol import (
    Admin,
    AuthorityError,
    canonical,
    decode64,
    encode64,
    envelope_bytes,
    instant,
    read_envelope,
    sign,
    verify_signature,
)
from pipeline.authority.registry import Registry
from pipeline.tests.authority_support import common, enrollment, grant, key, pin, private


def signed():
    return sign(enrollment(), private("owner"), possession_key=private("editor"))


def test_ed25519_independent_roundtrip():
    envelope = read_envelope(envelope_bytes(signed()) + b"\n")
    verify_signature(envelope, key("owner").public_key)
    verify_signature(envelope, key("editor").public_key, proof=True)
    registry = Registry(pin())
    registry.apply(envelope)
    assert registry.revision == 1 and "editor" in registry.reviewers


@pytest.mark.parametrize("mutation", [
    lambda d: d.update(algorithm="HS256"),
    lambda d: d["payload"].update(version=True),
    lambda d: d["payload"].update(version=2),
    lambda d: d["payload"].update(unknown="ambiguous"),
    lambda d: d["payload"].pop("previous_sha256"),
    lambda d: d.update(signature="A" * 86),
    lambda d: d["payload"].update(environment="production"),
    lambda d: d["payload"].update(issued_at="2026-10-20"),
    lambda d: d["payload"].update(issued_at="2026-02-30T00:00:00Z"),
    lambda d: d["payload"].update(sequence=True),
    lambda d: d["payload"].update(sequence=1.0),
    lambda d: d["payload"].update(target_id="test-owner"),
    lambda d: d["payload"]["key"].update(public_key=key("attacker").public_key),
    lambda d: d.update(proof=None),
])
def test_malformed_or_forged_records_are_rejected(mutation):
    data = signed().model_dump(mode="json")
    mutation(data)
    with pytest.raises((ValueError, AuthorityError)):
        envelope = read_envelope(canonical(data))
        Registry(pin()).apply(envelope)


@pytest.mark.parametrize("wire", [
    lambda b: b"\xef\xbb\xbf" + b,
    lambda b: b.decode().encode("utf-16"),
    lambda b: b" " + b,
    lambda b: b + b"\n\n",
    lambda b: b.replace(b'"algorithm":"Ed25519"', b'"algorithm":"Ed25519","algorithm":"Ed25519"'),
    lambda b: b.replace(b"enroll-editor", b"enroll-\\u0065ditor"),
    lambda b: b.replace(b"enroll-editor", b"enroll-\\ud800"),
    lambda b: b"[" * 40 + b"0" + b"]" * 40,
    lambda b: b + b" " * 64000,
])
def test_ambiguous_and_oversized_wire_rejected(wire):
    with pytest.raises((ValueError, UnicodeError)):
        read_envelope(wire(envelope_bytes(signed())))


@pytest.mark.parametrize("value", [1.0, float("nan"), -1, 2**53, {1: "bad"}, "বাংলা", "bad\ncontrol"])
def test_canonical_profile_rejects_ambiguous_types(value):
    with pytest.raises(AuthorityError):
        canonical(value)


def test_exact_canonical_encoding_and_base64():
    assert canonical({"z": [True, None, 0], "a": "x"}) == b'{"a":"x","z":[true,null,0]}'
    assert decode64(encode64(b"x" * 32), 32) == b"x" * 32
    for value in ["abc=", "a+bc", "a/bc", "", "A" * 42]:
        with pytest.raises(AuthorityError):
            decode64(value, 32)


def test_fake_owner_cannot_self_enroll():
    forged = sign(enrollment(), private("attacker"), possession_key=private("editor"))
    with pytest.raises(AuthorityError, match="verification failed"):
        Registry(pin()).apply(forged)


def test_reviewer_cannot_change_root_or_grant_role():
    registry = Registry(pin())
    registry.apply(signed())
    payload = Admin(**common("grant-forged", signer="editor", key_name="editor", sequence=2), kind="admin",
                    role="owner-admin", operation="grant", target_id="editor", key=None, grant=grant())
    with pytest.raises(AuthorityError, match="pinned current owner"):
        registry.apply(sign(payload, private("editor")))


def test_role_escalation_is_not_a_registry_option():
    with pytest.raises(ValidationError):
        grant(role="english-editor", decisions=["RIGHTS_APPROVED"])


def test_json_property_order_is_not_signature_order():
    data = signed().model_dump(mode="json")
    wire = json.dumps(data, sort_keys=False).encode()
    with pytest.raises(AuthorityError, match="canonical wire"):
        read_envelope(wire)


@pytest.mark.parametrize("timestamp", ["2026-10-20T00:00:00+00:00", "2026-10-20T00:00:00.0Z", "2026-13-20T00:00:00Z"])
def test_noncanonical_times(timestamp):
    with pytest.raises(AuthorityError):
        instant(timestamp)


@pytest.mark.parametrize("raw", [bytes(32), bytes([1]) + bytes(31), bytes([255]) * 32,
                                  bytes([237]) + bytes([255]) * 30 + bytes([127]),
                                  bytes([238]) + bytes([255]) * 30 + bytes([127])])
def test_weak_or_noncanonical_public_points_cannot_be_trust_roots_or_reviewers(raw):
    from pipeline.authority.protocol import Key, fingerprint
    with pytest.raises(AuthorityError, match="prime-order"):
        fingerprint(raw)
    valid = key("owner").model_dump(mode="json")
    valid.update(public_key=encode64(raw), key_id=hashlib.sha256(raw).hexdigest())
    with pytest.raises(ValueError):
        Key.model_validate(valid)
    bootstrap = pin().model_dump(mode="json")
    bootstrap["root_key"] = valid
    from pipeline.authority.registry import TrustPin
    with pytest.raises(ValueError):
        TrustPin.model_validate(bootstrap)


def test_neutral_point_forgery_is_rejected_by_the_actual_verifier():
    forged = signed().model_copy(update={"signature": encode64(bytes([1]) + bytes(63))})
    with pytest.raises(AuthorityError, match="prime-order"):
        verify_signature(forged, encode64(bytes([1]) + bytes(31)))
