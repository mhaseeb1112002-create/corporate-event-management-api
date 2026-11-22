"""JWT creation and authentication dependencies."""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from services import find_user


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def hash_password(password: str) -> str:
    """Hash a password with scrypt and a new cryptographic salt."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Verify a password without comparing hashes with ordinary equality."""
    try:
        salt_hex, expected = stored.split("$", 1)
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=16384, r=8, p=1)
        return hmac.compare_digest(digest.hex(), expected)
    except (ValueError, TypeError):
        return False


def secret_key() -> str:
    """Require a configured secret rather than shipping a default key."""
    key = os.environ.get("JWT_SECRET", "")
    if len(key) < 32:
        raise RuntimeError("Set JWT_SECRET to a random value of at least 32 characters")
    return key


def create_token(username: str) -> str:
    """Issue a 30-minute signed access token."""
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": username, "iat": now, "exp": now + timedelta(minutes=30)}, secret_key(), algorithm="HS256")


async def current_user(token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_session)) -> str:
    """Validate a token and confirm its account still exists."""
    error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, secret_key(), algorithms=["HS256"], options={"require": ["sub", "exp", "iat"]})
        username = payload.get("sub")
        if not isinstance(username, str):
            raise error
    except jwt.InvalidTokenError as exc:
        raise error from exc
    if await find_user(session, username) is None:
        raise error
    return username
