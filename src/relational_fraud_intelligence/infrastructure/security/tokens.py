from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt

from relational_fraud_intelligence.settings import AppSettings


class TokenService:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings

    def issue_access_token(self, *, user_id: str, username: str, role: str) -> str:
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=self._settings.jwt_access_token_ttl_minutes)
        payload = {
            "sub": user_id,
            "username": username,
            "role": role,
            "iss": self._settings.jwt_issuer,
            "aud": self._settings.jwt_audience,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(
            payload,
            self._settings.jwt_secret,
            algorithm=self._settings.jwt_algorithm,
        )

    def decode_access_token(self, token: str) -> dict[str, str]:
        payload = jwt.decode(
            token,
            self._settings.jwt_secret,
            algorithms=[self._settings.jwt_algorithm],
            audience=self._settings.jwt_audience,
            issuer=self._settings.jwt_issuer,
        )
        return {key: str(value) for key, value in payload.items()}
