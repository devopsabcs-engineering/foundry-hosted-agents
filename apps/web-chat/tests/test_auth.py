import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from auth import PilotAuth


@pytest.fixture
def auth_fixture():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    auth = PilotAuth("tenant", "client", "pilot")
    auth.keys = SimpleNamespace(
        get_signing_key_from_jwt=lambda token: SimpleNamespace(key=private_key.public_key())
    )
    now = int(time.time())
    claims = {
        "iss": auth.issuer, "aud": "client", "tid": "tenant", "oid": "user",
        "azp": "client", "scp": "Chat.Access", "groups": ["pilot"],
        "iat": now, "nbf": now, "exp": now + 300,
    }
    return auth, private_key, claims


def test_pilot_access(auth_fixture):
    auth, key, claims = auth_fixture
    identity = auth.verify(jwt.encode(claims, key, algorithm="RS256"))
    assert identity.object_id == "user"
    assert identity.tenant_id == "tenant"


@pytest.mark.parametrize("field,value", [
    ("aud", "other"), ("iss", "https://other.example"), ("tid", "other"),
    ("azp", "other"), ("scp", "Other.Scope"), ("groups", []),
    ("groups", ["other"]), ("exp", 1), ("oid", ""),
])
def test_invalid_claims_denied(auth_fixture, field, value):
    auth, key, claims = auth_fixture
    claims[field] = value
    with pytest.raises(HTTPException) as failure:
        auth.verify(jwt.encode(claims, key, algorithm="RS256"))
    assert failure.value.status_code in (401, 403)


def test_group_overage_fails_closed(auth_fixture):
    auth, key, claims = auth_fixture
    del claims["groups"]
    claims["_claim_names"] = {"groups": "src1"}
    with pytest.raises(HTTPException, match="Pilot membership"):
        auth.verify(jwt.encode(claims, key, algorithm="RS256"))


def test_forged_signature_denied(auth_fixture):
    auth, _, claims = auth_fixture
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(HTTPException) as failure:
        auth.verify(jwt.encode(claims, other_key, algorithm="RS256"))
    assert failure.value.status_code == 401