from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def require_fields(payload: dict[str, Any], fields: list[str]) -> list[str]:
    missing: list[str] = []
    for f in fields:
        v = payload.get(f)
        if v is None or (isinstance(v, str) and not v.strip()):
            missing.append(f)
    return missing


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email or ""))


def normalize_skill(skill: str) -> str:
    return re.sub(r"\s+", " ", (skill or "").strip()).lower()


def split_skills(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw = value
    else:
        raw = str(value).split(",")
    out: list[str] = []
    for s in raw:
        ns = normalize_skill(str(s))
        if ns and ns not in out:
            out.append(ns)
    return out


# Public email domains — cannot be used for company website↔email verification.
_PUBLIC_EMAIL_DOMAINS = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "yahoo.com",
        "yahoo.co.in",
        "outlook.com",
        "hotmail.com",
        "live.com",
        "icloud.com",
        "protonmail.com",
        "proton.me",
        "aol.com",
        "rediffmail.com",
    }
)


def domain_from_email(email: str) -> str:
    e = (email or "").strip().lower()
    if "@" not in e:
        return ""
    return e.split("@", 1)[1].strip()


def domain_from_website(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    if not u.lower().startswith(("http://", "https://")):
        u = "https://" + u
    try:
        parsed = urlparse(u)
        host = (parsed.netloc or parsed.path or "").lower()
        if host.startswith("www."):
            host = host[4:]
        if "/" in host:
            host = host.split("/")[0]
        if ":" in host:
            host = host.split(":")[0]
        return host
    except Exception:
        return ""


def company_email_matches_website(login_email: str, company_website: str) -> bool:
    """
    True if the user's work email domain matches the company website host
    (e.g. user@acme.com vs https://careers.acme.com).
    """
    ed = domain_from_email(login_email)
    wd = domain_from_website(company_website)
    if not ed or not wd:
        return False
    if ed in _PUBLIC_EMAIL_DOMAINS:
        return False
    if ed == wd:
        return True
    # Subdomain: jobs.acme.com vs acme.com
    if ed.endswith("." + wd) or wd.endswith("." + ed):
        return True
    return False

