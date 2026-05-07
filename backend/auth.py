"""Simple two-user JWT auth. Users configured via env vars."""
from __future__ import annotations
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Header, HTTPException

SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "legalrag-dev-secret-change-in-production")
ALGORITHM = "HS256"
EXPIRE_HOURS = 24 * 7  # 7-day tokens

# Users configurable via env vars — defaults match the two users requested
USERS: dict[str, dict] = {
    os.getenv("USER1_NAME", "hiren"): {
        "password": os.getenv("USER1_PASSWORD", "1234"),
        "role": "user",
    },
    os.getenv("ADMIN_NAME", "admin"): {
        "password": os.getenv("ADMIN_PASSWORD", "1234"),
        "role": "admin",
    },
}


def authenticate(username: str, password: str) -> dict:
    user = USERS.get(username.lower().strip())
    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = jwt.encode(
        {
            "sub": username.lower().strip(),
            "role": user["role"],
            "exp": datetime.now(timezone.utc) + timedelta(hours=EXPIRE_HOURS),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return {"token": token, "username": username.lower().strip(), "role": user["role"]}


def get_current_user(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(
            authorization.split(" ")[1], SECRET_KEY, algorithms=[ALGORITHM]
        )
        return {"username": payload["sub"], "role": payload["role"]}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired — please log in again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
