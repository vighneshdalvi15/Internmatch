from __future__ import annotations

from typing import Literal

from werkzeug.security import check_password_hash, generate_password_hash

Role = Literal["student", "company", "admin"]


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return check_password_hash(password_hash, password)

