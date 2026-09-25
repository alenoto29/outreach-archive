import hmac
import os
from functools import wraps
from flask import request, jsonify, g

ADMIN_NAMES = {n.strip().lower() for n in os.getenv("ADMIN_NAMES", "").split(",") if n.strip()}


def _parse_user_tokens():
    """Parse explicit per-user bearer tokens. An empty mapping disables protected routes."""
    out = {}
    for part in os.getenv("USER_TOKENS", "").split(","):
        part = part.strip()
        if ":" not in part:
            continue
        name, tok = part.split(":", 1)
        name = name.strip().lower()
        tok = tok.strip()
        if name and tok:
            out[name] = tok
    return out


USER_TOKENS = _parse_user_tokens()


def _extract_token():
    auth_hdr = request.headers.get("Authorization", "")
    if auth_hdr.startswith("Bearer "):
        return auth_hdr[7:].strip()
    return ""


def _authenticate():
    """Populate g._auth_user, g._auth_role. Returns True if request is authenticated."""
    token = _extract_token()
    if not token:
        return False

    if not USER_TOKENS:
        return False
    for user, expected in USER_TOKENS.items():
        if hmac.compare_digest(token, expected):
            claimed = (request.headers.get("X-User-Name") or "").strip().lower()
            if claimed and claimed != user:
                return False
            g._auth_user = user
            g._auth_role = "admin" if user in ADMIN_NAMES else "editor"
            return True
    return False


def _token_valid():
    """Back-compat helper for endpoints that accept token without user name (e.g. /api/meta)."""
    token = _extract_token()
    if not token:
        return False
    return any(hmac.compare_digest(token, expected) for expected in USER_TOKENS.values())


def get_user():
    return getattr(g, "_auth_user", None)


def get_role(user=None):
    return getattr(g, "_auth_role", None)


def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not _authenticate():
            return jsonify({"error": "unauthorized", "message": "invalid token"}), 401
        return f(*args, **kwargs)
    return wrapper


def require_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not _authenticate():
            return jsonify({"error": "unauthorized", "message": "invalid token"}), 401
        if g._auth_role != "admin":
            return jsonify({"error": "forbidden", "message": "admin only"}), 403
        return f(*args, **kwargs)
    return wrapper
