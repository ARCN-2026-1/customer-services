from datetime import UTC, datetime, timedelta

import jwt

from internal.infrastructure.config.settings import CustomerServiceSettings


class JWTTokenGenerator:
    def __init__(self, settings: CustomerServiceSettings) -> None:
        self._settings = settings

    def generate(self, *, customer_id: str, role: str) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": customer_id,
            "role": role,
            "exp": now + timedelta(seconds=self._settings.jwt_expiration_seconds),
            "iat": now,
        }
        return jwt.encode(
            payload,
            self._settings.jwt_secret,
            algorithm=self._settings.jwt_algorithm,
        )

    def validate(self, token: str) -> dict[str, str]:
        return jwt.decode(
            token,
            self._settings.jwt_secret,
            algorithms=[self._settings.jwt_algorithm],
        )
