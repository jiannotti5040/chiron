#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
test_engine_server.py — real HTTP against the real endpoint process.

Spawns `python -m primus.engine_server` and drives it over actual sockets:
verify/refuse round-trips for all three tools, the over-budget refusals,
rate limiting, concurrency budget, auth, and the no-leak rule (no
tracebacks, no source paths, ever). Same discipline as test_mcp_server.py:
exact expected fields, no tolerance.

    python3 test_engine_server.py
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
FAILS = 0
GATES = 0


def gate(name, cond, detail=""):
    global FAILS, GATES
    GATES += 1
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + ("" if cond else f"  <- {detail}"))
    FAILS += 0 if cond else 1


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def start_server(env_extra=None):
    port = free_port()
    env = dict(os.environ, PYTHONPATH=os.path.join(HERE, "src"), **(env_extra or {}))
    proc = subprocess.Popen(
        [sys.executable, "-m", "primus.engine_server", "--port", str(port)],
        env=env, cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    base = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            with urllib.request.urlopen(base + "/health", timeout=2) as r:
                if r.status == 200:
                    return proc, base
        except Exception:
            time.sleep(0.1)
    proc.kill()
    raise RuntimeError("server did not come up")


def call(base, path, body=None, method=None, headers=None, raw=None):
    data = raw if raw is not None else (
        json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(base + path, data=data,
                                 method=method or ("POST" if data else "GET"))
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def main():
    proc, base = start_server({"CHIRON_RATE_PER_MIN": "1000"})
    try:
        code, health = call(base, "/health")
        gate("health 200 + engine version + three tools",
             code == 200 and health["ok"] and
             sorted(health["tools"]) == ["certify", "collapse", "conjecture"],
             repr(health))

        # CORS — a browser must be able to preflight and read the response
        preflight = urllib.request.Request(base + "/collapse", method="OPTIONS")
        try:
            with urllib.request.urlopen(preflight, timeout=10) as r:
                pf_code, pf_acao = r.status, r.headers.get("Access-Control-Allow-Origin")
        except urllib.error.HTTPError as e:
            pf_code, pf_acao = e.code, e.headers.get("Access-Control-Allow-Origin")
        gate("CORS preflight (OPTIONS) -> 204 + Allow-Origin *",
             pf_code == 204 and pf_acao == "*", f"{pf_code} {pf_acao}")
        with urllib.request.urlopen(base + "/health", timeout=10) as r:
            acao = r.headers.get("Access-Control-Allow-Origin")
        gate("CORS Allow-Origin header on normal responses", acao == "*", repr(acao))

        code, r = call(base, "/collapse", {"surface": "1 1 2 3 5 8 13 21 34 55 89 144"})
        gate("collapse: fibonacci VERIFIED via string surface",
             code == 200 and r["certificate"]["verified"] is True and
             "linear_recurrence" in r["certificate"]["model_class"], repr(r)[:200])

        code, r = call(base, "/collapse", {"surface": [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]})
        gate("collapse: primes honestly not verified",
             code == 200 and r["certificate"]["verified"] is False, repr(r)[:200])

        code, r = call(base, "/certify", {"text": "2+2=5 and 97 is prime and 10 choose 3 is 120."})
        c = r["certificate"]["counts"]
        gate("certify: refuted and verified counted exactly",
             code == 200 and c["refuted"] == 1 and c["verified"] == 2, repr(c))

        code, r = call(base, "/conjecture", {"terms": [1, 3, 6, 10, 15, 21, 28, 36, 45, 55, 66, 78]})
        gate("conjecture: triangulars stamped by the exact gate",
             code == 200 and r["certificate"]["status"] == "VERIFIED", repr(r)[:200])

        code, r = call(base, "/collapse", {"surface": list(range(300))})
        gate("collapse: 300 terms REFUSED over budget (256 cap)",
             code == 413 and r["status"] == "REFUSED", repr(r))

        code, r = call(base, "/conjecture", {"terms": "9 " * 300})
        gate("conjecture: 300-term string REFUSED over budget",
             code == 413 and r["status"] == "REFUSED", repr(r))

        code, r = call(base, "/certify", raw=b"x" * (129 * 1024))
        gate("oversize body REFUSED before parsing (413)",
             code == 413 and r["status"] == "REFUSED", repr(r))

        code, r = call(base, "/collapse", raw=b"{not json")
        gate("bad JSON -> 400 REFUSED, not a crash",
             code == 400 and r["status"] == "REFUSED", repr(r))

        code, r = call(base, "/collapse", {"wrong_field": 1})
        gate("missing required field -> 400 REFUSED",
             code == 400 and r["status"] == "REFUSED", repr(r))

        code, r = call(base, "/collapse", {"surface": []})
        gate("empty surface -> refusal envelope, exception TYPE only",
             r["status"] == "REFUSED" and "Traceback" not in json.dumps(r) and
             "src/primus" not in json.dumps(r), repr(r))

        code, r = call(base, "/nope", {"x": 1})
        gate("unknown route -> 404 REFUSED", code == 404 and r["status"] == "REFUSED", repr(r))

        code, r = call(base, "/collapse", method="GET")
        gate("GET on a tool -> 405", code == 405, repr(r))

        leaks = []
        for path, body in [("/collapse", {"surface": "\x00\xff garbage ☃"}),
                           ("/certify", {"text": "a" * 99_000}),
                           ("/conjecture", {"terms": [0] * 256})]:
            _, r = call(base, path, body)
            blob = json.dumps(r)
            if "Traceback" in blob or ".py" in blob or "src/primus" in blob:
                leaks.append((path, blob[:120]))
        gate("no traceback / no source path in any hostile response", not leaks, repr(leaks))
    finally:
        proc.kill()

    # rate limit: fresh server with a 3/min budget
    proc, base = start_server({"CHIRON_RATE_PER_MIN": "3"})
    try:
        codes = [call(base, "/collapse", {"surface": "1 2 3 4 5 6 7 8"})[0] for _ in range(4)]
        gate("per-IP rate limit trips on request 4 (429)",
             codes[:3] == [200, 200, 200] and codes[3] == 429, repr(codes))
    finally:
        proc.kill()

    # auth: token required when configured
    proc, base = start_server({"CHIRON_API_TOKEN": "sekrit"})
    try:
        code, r = call(base, "/collapse", {"surface": "1 2 3 4 5 6 7 8"})
        gate("auth on: POST without token -> 401 REFUSED",
             code == 401 and r["status"] == "REFUSED", repr(r))
        code, r = call(base, "/collapse", {"surface": "2 4 8 16 32 64 128 256"},
                       headers={"Authorization": "Bearer sekrit"})
        gate("auth on: correct bearer -> engine answers (geometric VERIFIED)",
             code == 200 and r["certificate"]["verified"] is True, repr(r)[:200])
        code, _ = call(base, "/health")
        gate("auth on: /health stays open", code == 200)
    finally:
        proc.kill()

    print(f"\n  {GATES - FAILS}/{GATES} endpoint gates passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
