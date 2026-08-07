"""Single-admin session auth. No users table — one credential from .env."""

import bcrypt
from fastapi import HTTPException, Request, status

from app.config import get_settings


def verify_password(plain_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))


def authenticate(username: str, password: str) -> bool:
    settings = get_settings()
    if username != settings.admin_username:
        return False
    return verify_password(password, settings.admin_password_hash)


def require_auth(request: Request) -> None:
    """FastAPI dependency: 401s unless the session cookie is authenticated."""
    if not request.session.get("authenticated"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated."
        )
