#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
test_engine_server.py — real HTTP against the real endpoint process.

Spawns `python -m primus.engine_server` and drives it over actual sockets:
verify/refuse round-trips for all three tools, the over-budget refusals,
rate limiting, concurrency budget, auth, the closed route table (404 / 405
with Allow), log hygiene, and the no-leak rule (no tracebacks, no source
paths, ever). Same discipline as test_mcp_server.py: exact expected
fields, no tolerance.

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
    code, _hdrs, obj = call_ex(base, path, body, method, headers, raw)
    return code, obj


def call_ex(base, path, body=None, method=None, headers=None, raw=None):
    """Same call, but the response headers come back too (for `Allow:`)."""
    data = raw if raw is not None else (
        json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(base + path, data=data,
                                 method=method or ("POST" if data else "GET"))
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, dict(r.headers), _decode(r.read())
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), _decode(e.read())


def _decode(payload):
    """JSON if it is JSON. A non-JSON body (e.g. the stdlib's HTML error
    page) is surfaced, not raised: the gate must FAIL, not explode — and the
    leak scanner needs to see that text."""
    text = payload.decode("utf-8", "replace")
    try:
        obj = json.loads(text)
    except Exception:
        return {"_not_json": text}
    return obj if isinstance(obj, dict) else {"_not_object": obj}


def raw_request(base, request_line, extra_headers=""):
    """Speak HTTP by hand — for request shapes urllib refuses to produce
    (unknown verbs, a POST with no Content-Length). Returns the raw bytes
    of the whole response, headers included."""
    host, port = base.split("//", 1)[1].split(":")
    s = socket.create_connection((host, int(port)), timeout=15)
    s.sendall((request_line + "\r\n" + extra_headers + "\r\n").encode())
    buf = b""
    while True:
        try:
            chunk = s.recv(65536)
        except socket.timeout:
            break
        if not chunk:
            break
        buf += chunk
    s.close()
    return buf.decode("utf-8", "replace")


# Every error body is scanned for these. "schema" is excluded from the scan
# before it runs: `primus.engine_server/1` is the deliberate, documented
# schema identifier carried by every response, not an internals leak.
LEAK_MARKERS = ["Traceback", "File \"", ".py", "src/primus", "site-packages",
                "/opt/", "/Users/", "primus.certify", "primus.engine",
                "json.decoder", "Unsupported method", "<html", "<!DOCTYPE",
                "Error response", "self.", "line "]


def leaks_in(obj):
    """Leak markers found in an error body, with `schema` set aside."""
    scanned = {k: v for k, v in obj.items() if k != "schema"} \
        if isinstance(obj, dict) else obj
    blob = json.dumps(scanned)
    return [m for m in LEAK_MARKERS if m in blob]


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

        # ---- closed route table: no catch-all -----------------------------
        # Production log evidence: an unmapped skill-ish path came back 200.
        # A path that is not in the table must be 404, and the body must name
        # the routes that do exist.
        bogus = "/cockroachdb:reviewing-cluster-health"
        code, r = call(base, bogus)
        gate("unmapped path -> 404 'not found' + valid_routes (no catch-all)",
             code == 404 and r.get("error") == "not found" and
             sorted(r.get("valid_routes") or []) == ["GET /", "GET /health",
                                           "POST /certify", "POST /collapse",
                                           "POST /conjecture"], f"{code} {r!r}")

        code, r = call(base, "/")
        gate("GET / -> 200 short banner listing the routes",
             code == 200 and len(r.get("routes") or []) == 5 and
             r.get("service") == "chiron-engine", f"{code} {repr(r)[:200]}")

        code, hdrs, r = call_ex(base, "/certify", method="GET")
        gate("GET /certify -> 405 + Allow: POST header + allow body",
             code == 405 and hdrs.get("Allow") == "POST" and
             r.get("error") == "method not allowed" and r.get("allow") == ["POST"],
             f"{code} allow_hdr={hdrs.get('Allow')!r} {r!r}")

        code, hdrs, r = call_ex(base, "/collapse", method="PUT",
                                raw=b'{"surface":[1,2,3]}')
        gate("PUT /collapse -> 405 JSON (not the stdlib 501 HTML page)",
             code == 405 and hdrs.get("Allow") == "POST" and
             r.get("allow") == ["POST"], f"{code} {r!r}")

        code, _ = call(base, "/health?probe=1")
        gate("query string cannot dodge the route table (/health?probe=1 -> 200)",
             code == 200, repr(code))

        # ---- hostile bodies: bounded refusal, never a dropped connection ---
        deep = b"[" * 60_000 + b"]" * 60_000          # under the 128 KiB cap
        try:
            code, r = call(base, "/certify", raw=deep)
        except Exception as exc:
            code, r = f"CONNECTION DROPPED ({type(exc).__name__})", {}
        gate("hostile 60k-deep nested JSON -> bounded 400, not a crash",
             code == 400 and r.get("error") == "bad request" and
             not leaks_in(r), f"{code} {r!r}")

        # A 2 MiB body is refused on the HEADER — the server answers 413 and
        # hangs up without pulling a single body byte into memory. Sent by
        # hand: urllib would block writing 2 MiB into an already-closed socket.
        huge = raw_request(base, "POST /collapse HTTP/1.0",
                           "Content-Length: 2097152\r\n")
        gate("declared 2 MiB body -> 413 refused on the header, body never read",
             " 413 " in huge.split("\r\n")[0] and "payload too large" in huge and
             "Traceback" not in huge, repr(huge[:200]))

        # ---- the stdlib error paths speak JSON, and echo nothing ----------
        unknown_verb = raw_request(base, "FOO /certify HTTP/1.0")
        gate("unknown verb -> JSON refusal, no HTML page, no echo of the verb",
             " 501 " in unknown_verb.split("\r\n")[0] and
             "application/json" in unknown_verb and
             "<html" not in unknown_verb.lower() and
             "FOO" not in unknown_verb.split("\r\n\r\n", 1)[-1],
             repr(unknown_verb[:200]))

        no_len = raw_request(base, "POST /certify HTTP/1.0")
        gate("POST with no Content-Length -> 411 JSON refusal",
             " 411 " in no_len.split("\r\n")[0] and
             "length required" in no_len, repr(no_len[:200]))

        # ---- no-leak across EVERY error path ------------------------------
        # 400 / 404 / 405 / 411 / 413 / 429 / 401 collected as real responses.
        error_bodies = {}
        error_bodies["404"] = call(base, "/no/such/thing")[1]
        error_bodies["405"] = call(base, "/conjecture", method="GET")[1]
        error_bodies["400-json"] = call(base, "/certify", raw=b"{{{")[1]
        error_bodies["400-field"] = call(base, "/certify", {"nope": 1})[1]
        error_bodies["413"] = call(base, "/certify", raw=b"z" * 140_000)[1]
        error_bodies["413-terms"] = call(base, "/conjecture",
                                         {"terms": list(range(400))})[1]
        # the stdlib error paths belong in the scan too — they are where the
        # HTML page that echoes the caller's method used to come out
        error_bodies["405-put"] = call(base, "/collapse", method="PUT",
                                       raw=b'{"surface":[1]}')[1]
        error_bodies["405-trace"] = call(base, "/health", method="TRACE")[1]
        error_bodies["501-verb"] = _decode(raw_request(
            base, "BREW /certify HTTP/1.0").split("\r\n\r\n", 1)[-1].encode())
        found = {k: leaks_in(v) for k, v in error_bodies.items() if leaks_in(v)}
        gate("no-leak scan: every error body is free of traceback/path/module",
             not found, repr(found))
        schemas = {k: v.get("schema") for k, v in error_bodies.items()}
        gate("every error body still carries the refusal envelope",
             all(v.get("status") == "REFUSED" for v in error_bodies.values()) and
             set(schemas.values()) == {"primus.engine_server/1"}, repr(schemas))
    finally:
        proc.kill()

    # rate limit, per tool: one server, three distinct forwarded client IPs so
    # each tool gets its own per-IP bucket. Budget 1/min -> the 2nd call trips.
    proc, base = start_server({"CHIRON_RATE_PER_MIN": "1",
                               "CHIRON_TRUST_FORWARDED": "1"})
    try:
        tools = [("/collapse", {"surface": "1 2 3 4 5 6 7 8"}, "203.0.113.11"),
                 ("/certify", {"text": "2+2=4"}, "203.0.113.12"),
                 ("/conjecture", {"terms": [1, 3, 6, 10, 15, 21, 28, 36]},
                  "203.0.113.13")]
        results, dirty = {}, {}
        for path, body, ip in tools:
            h = {"X-Forwarded-For": ip}
            first = call(base, path, body, headers=h)[0]
            code, r = call(base, path, body, headers=h)
            results[path] = (first, code)
            if code == 429 and (leaks_in(r) or r.get("status") != "REFUSED"):
                dirty[path] = r
        gate("per-IP rate limit trips on ALL THREE tools (429 + clean JSON)",
             all(v == (200, 429) for v in results.values()) and not dirty,
             f"{results!r} dirty={dirty!r}")
    finally:
        proc.kill()

    # log hygiene: /health must not bury the human traffic, and the caller's
    # input must never appear verbatim in the access log.
    proc, base = start_server({"CHIRON_RATE_PER_MIN": "1000"})
    try:
        for _ in range(5):
            call(base, "/health")
        call(base, "/certify", {"text": "CANARY7f3a9 says 2+2=4"})
        call(base, "/nope-not-here")
    finally:
        proc.kill()
        log = proc.stderr.read().decode("utf-8", "replace")
    gate("access log: /health suppressed, real routes logged, input never verbatim",
         "path=/health" not in log            # 5 probes, zero lines
         and "path=/certify" in log           # real traffic still visible
         and "path=/nope-not-here" in log     # and so are the 404 probers
         and "CANARY7f3a9" not in log         # never the input verbatim
         and "in_bytes=" in log and "in_sha256=" in log
         and "status=200" in log,
         repr(log[-400:]))

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
