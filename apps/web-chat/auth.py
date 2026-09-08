import asyncio
from dataclasses import dataclass

import jwt
from fastapi import HTTPException
from jwt import PyJWKClient


@dataclass(frozen=True)
class Identity:
    tenant_id: str
    object_id: str


class PilotAuth:
    def __init__(self, tenant_id: str, client_id: str, group_id: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.group_id = group_id
        self.issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
        self.keys = PyJWKClient(
            f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
            timeout=10,
        )

    def verify(self, token: str) -> Identity:
        try:
            key = self.keys.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.issuer,
                options={"require": ["exp", "iat", "nbf", "iss", "aud", "tid", "oid"]},
                leeway=30,
            )
        except jwt.PyJWKClientConnectionError as exc:
            raise HTTPException(503, "Sign-in verification is temporarily unavailable.") from exc
        except jwt.PyJWTError as exc:
            raise HTTPException(401, "A valid access token is required.") from exc
        if claims.get("tid") != self.tenant_id or claims.get("azp") != self.client_id:
            raise HTTPException(403, "This application is not authorized.")
        if "Chat.Access" not in claims.get("scp", "").split():
            raise HTTPException(403, "Chat permission is required.")
        if self.group_id not in claims.get("groups", []):
            raise HTTPException(403, "Pilot membership is required. Contact the pilot administrator.")
        if not isinstance(claims["oid"], str) or not claims["oid"]:
            raise HTTPException(401, "A user identity is required.")
        return Identity(claims["tid"], claims["oid"])

    async def authorize(self, authorization: str | None) -> Identity:
        if not authorization or not authorization.startswith("Bearer ") or len(authorization) > 32768:
            raise HTTPException(401, "Sign in to continue.")
        return await asyncio.to_thread(self.verify, authorization[7:])