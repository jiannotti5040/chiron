#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See ../LICENSE.md.
"""
remote.py — talk to a live Chiron engine endpoint. Certificates come back;
the engine's source never does.

The licensed engine can be served as a minimal HTTP endpoint (request in,
certificate out, hard rate limits, everything over budget REFUSED). This
stdlib client is the public half: point it at a running endpoint and get
the real engine's verify-or-refuse on input YOU choose — the strongest
possible pre-purchase eval when an endpoint URL is published.

A live demo instance runs at https://chiron-engine.onrender.com (free tier:
rate-limited, refuses over budget, ~30 s cold start after idle). This client
also works against any other deployment (or a licensee's own:
`PYTHONPATH=src python3 -m primus.engine_server` in the vault).

    python3 remote.py --url https://chiron-engine.onrender.com collapse "1 1 2 3 5 8 13 21 34 55 89 144"
    python3 remote.py --url https://chiron-engine.onrender.com certify "97 is prime and 2+2=5"
    python3 remote.py --url http://127.0.0.1:8790 conjecture "1 3 6 10 15 21 28 36"   # local instance

Auth: if the endpoint requires a bearer token, set CHIRON_API_TOKEN.
Exit codes: 0 on any honest answer (including refusals — refusal is a
result), 2 on transport/HTTP-level failure.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request


#: the public demo runs on a free tier that suspends when idle. The first
#: request after a nap has to wait for a container to boot, which can look
#: like a hang or an empty reply. Retry politely and SAY SO, rather than
#: leaving the caller staring at nothing.
COLD_START_TRIES = 3
COLD_START_BACKOFF_S = 15


def _once(url: str, path: str, body, timeout: int):
    """One attempt. Returns (status, obj) or raises for a transport failure."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url.rstrip("/") + path, data=data,
                                 method="POST" if data else "GET")
    req.add_header("Content-Type", "application/json")
    token = os.environ.get("CHIRON_API_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode()
            if not raw.strip():
                raise ValueError("empty body")           # cold start: retry
            return r.status, json.loads(raw)
    except urllib.error.HTTPError as e:
        # An HTTP error carrying a JSON refusal envelope is a RESULT, not a
        # failure — the endpoint answered. Return it; do not retry.
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            if e.code in (502, 503, 504):               # gateway still waking
                raise
            return e.code, {"status": "TRANSPORT_ERROR", "reason": f"HTTP {e.code}"}


def call(url: str, path: str, body=None, timeout: int = 120):
    """Call the endpoint, tolerating a free-tier cold start.

    Never hangs silently and never dumps a traceback: on repeated failure it
    returns a plain refusal-shaped object naming the transport problem only.
    """
    last = None
    for attempt in range(1, COLD_START_TRIES + 1):
        try:
            return _once(url, path, body, timeout)
        except Exception as exc:                         # transport-level only
            last = type(exc).__name__
            if attempt < COLD_START_TRIES:
                print(f"waking the free-tier demo instance (~30s)… "
                      f"attempt {attempt}/{COLD_START_TRIES}", file=sys.stderr)
                time.sleep(COLD_START_BACKOFF_S)
    return 0, {"status": "TRANSPORT_ERROR",
               "reason": (f"no response after {COLD_START_TRIES} attempts "
                          f"({last}). The demo instance may be down; the "
                          f"endpoint is a free-tier convenience, not an SLA.")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--url", required=True, help="endpoint base URL")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("health")
    p = sub.add_parser("collapse")
    p.add_argument("surface", help="integer sequence like '1 1 2 3 5 8', or any string surface")
    p = sub.add_parser("certify")
    p.add_argument("text", help="text whose checkable claims to certify")
    p = sub.add_parser("conjecture")
    p.add_argument("terms", help="integer sequence")
    p.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)

    if args.cmd == "health":
        code, obj = call(args.url, "/health")
    elif args.cmd == "collapse":
        code, obj = call(args.url, "/collapse", {"surface": args.surface})
    elif args.cmd == "certify":
        code, obj = call(args.url, "/certify", {"text": args.text})
    else:
        code, obj = call(args.url, "/conjecture",
                         {"terms": args.terms, "seed": args.seed})

    print(json.dumps(obj, indent=2))
    if code in (200,):
        return 0
    if code in (401, 404, 405, 411, 429, 413, 400):
        # the endpoint answered with an honest refusal envelope
        print(f"(HTTP {code} — the endpoint refused, it did not fail)", file=sys.stderr)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
