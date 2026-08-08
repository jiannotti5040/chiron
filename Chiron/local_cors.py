#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""Small, strict CORS policy for Chiron's loopback browser surfaces.

The dashboard lives at ``http://127.0.0.1:8765`` and is the only cross-origin
browser caller enabled by default.  A user may replace that allowlist through
``CHIRON_CORS_ORIGINS`` (a comma-separated list), but only HTTP(S) loopback
origins are accepted.  An empty value deliberately disables cross-origin
browser access.

CORS is a browser policy, not authentication.  These services remain bound to
loopback and must not be treated as remotely exposed APIs.
"""
import ipaddress
import os
from urllib.parse import urlsplit


DEFAULT_ORIGINS = ("http://127.0.0.1:8765",)
ENV_VAR = "CHIRON_CORS_ORIGINS"
_METHODS = "GET, POST"
_HEADERS = "Content-Type"


def _normalize_origin(value):
    """Return one canonical loopback origin, or ``None`` for a disallowed value."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = urlsplit(value.strip())
        host = parsed.hostname
        port = parsed.port
    except (TypeError, ValueError):
        return None
    if (parsed.scheme.lower() not in ("http", "https") or not host
            or parsed.username is not None or parsed.password is not None
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment):
        return None
    host = host.lower()
    if host != "localhost":
        try:
            if not ipaddress.ip_address(host).is_loopback:
                return None
        except ValueError:
            return None
    scheme = parsed.scheme.lower()
    # Browsers serialize default ports out of Origin, so do the same here.
    if port == (80 if scheme == "http" else 443):
        port = None
    rendered_host = f"[{host}]" if ":" in host else host
    return f"{scheme}://{rendered_host}" + (f":{port}" if port is not None else "")


def normalize_origins(values):
    """Canonicalize a sequence of configured local origins, dropping invalid entries."""
    if isinstance(values, str):
        values = values.split(",")
    out = []
    for value in values or ():
        origin = _normalize_origin(value)
        if origin and origin not in out:
            out.append(origin)
    return tuple(out)


def configured_origins(environ=None):
    """Load the strict local allowlist; absent configuration preserves the dashboard default."""
    environ = os.environ if environ is None else environ
    raw = environ.get(ENV_VAR)
    return normalize_origins(DEFAULT_ORIGINS if raw is None else raw)


def allowed_origin(origin, origins=None):
    """Return the approved canonical origin, never an unvalidated request value."""
    normalized = _normalize_origin(origin)
    approved = configured_origins() if origins is None else normalize_origins(origins)
    return normalized if normalized in approved else None


def headers_for(origin, *, preflight=False, origins=None):
    """Headers for an approved browser origin; no wildcard or arbitrary reflection."""
    approved = allowed_origin(origin, origins)
    if not approved:
        return ()
    headers = [("Access-Control-Allow-Origin", approved), ("Vary", "Origin")]
    if preflight:
        headers.extend((("Access-Control-Allow-Methods", _METHODS),
                        ("Access-Control-Allow-Headers", _HEADERS)))
    return tuple(headers)
