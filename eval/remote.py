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

No public endpoint URL is promised by this file's existence. When one is
live, it will be listed in this folder's README. Until then, this client
works against any deployment of the licensed endpoint (or a licensee's own:
`PYTHONPATH=src python3 -m primus.engine_server` in the vault).

    python3 remote.py --url http://127.0.0.1:8790 health
    python3 remote.py --url http://127.0.0.1:8790 collapse "1 1 2 3 5 8 13 21"
    python3 remote.py --url http://127.0.0.1:8790 certify "97 is prime and 2+2=5"
    python3 remote.py --url http://127.0.0.1:8790 conjecture "1 3 6 10 15 21 28 36"

Auth: if the endpoint requires a bearer token, set CHIRON_API_TOKEN.
Exit codes: 0 on any honest answer (including refusals — refusal is a
result), 2 on transport/HTTP-level failure.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def call(url: str, path: str, body=None, timeout: int = 120):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url.rstrip("/") + path, data=data,
                                 method="POST" if data else "GET")
    req.add_header("Content-Type", "application/json")
    token = os.environ.get("CHIRON_API_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"status": "TRANSPORT_ERROR", "reason": f"HTTP {e.code}"}


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
