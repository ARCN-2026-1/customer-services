from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from internal.application.errors import (
    AuthenticationFailedError,
    AuthorizationDeniedError,
)
from internal.domain.services.token_generator import TokenGenerator

bearer_scheme = HTTPBearer(
    bearerFormat="JWT",
    description="Paste a Bearer token to access admin endpoints.",
    auto_error=False,
)
BearerCredentials = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(bearer_scheme),
]


@dataclass(frozen=True, slots=True)
class AuthenticatedActor:
    customer_id: str
    role: str


def require_authenticated_actor(
    token_generator: TokenGenerator,
    credentials: HTTPAuthorizationCredentials | None,
) -> AuthenticatedActor:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationFailedError("Missing bearer token")

    token = credentials.credentials.strip()
    try:
        payload = token_generator.validate(token)
    except jwt.PyJWTError as error:
        raise AuthenticationFailedError("Invalid bearer token") from error

    return AuthenticatedActor(customer_id=payload["sub"], role=payload["role"])


def require_admin_actor(
    token_generator: TokenGenerator,
    credentials: BearerCredentials,
) -> AuthenticatedActor:
    actor = require_authenticated_actor(token_generator, credentials)
    if actor.role != "admin":
        raise AuthorizationDeniedError("Admin role is required")
    return actor
