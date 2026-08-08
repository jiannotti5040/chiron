#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
test_engine_server.py — real HTTP against the real endpoint process.

Spawns `python -m primus.engine_server` and drives it over actual sockets:
verify/refuse round-trips for legacy and versioned routes, the over-budget
refusals, rate limiting, concurrency budget, auth, the closed route table
(404 / 405 with Allow), strict v1 schema behavior, CORS opt-in, log hygiene,
and the no-leak rule (no tracebacks, no source paths, ever). Same discipline
as test_mcp_server.py: exact expected fields, no tolerance.

    python3 test_engine_server.py
"""
import json
import os
import re
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
    env = dict(os.environ)
    # Test each server's security posture explicitly, rather than inheriting a
    # developer shell's token, origin, or rate-limit configuration.
    for name in ("CHIRON_API_TOKEN", "CHIRON_RATE_PER_MIN",
                 "CHIRON_RATE_GLOBAL_PER_MIN", "CHIRON_MAX_CONCURRENCY",
                 "CHIRON_LOG_HEALTH", "CHIRON_CORS_ORIGIN",
                 "CHIRON_TRUST_FORWARDED"):
        env.pop(name, None)
    env["PYTHONPATH"] = os.path.join(HERE, "src")
    env.update(env_extra or {})
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
MOBILE_SCHEMA = "chiron.mobile_api/1"
ENGINE_SCHEMA = "primus.engine_server/1"
CERTIFICATE_SCHEMA = "primus.certificate/2"


def leaks_in(obj):
    """Leak markers found in an error body, with `schema` set aside."""
    scanned = {k: v for k, v in obj.items() if k != "schema"} \
        if isinstance(obj, dict) else obj
    blob = json.dumps(scanned)
    return [m for m in LEAK_MARKERS if m in blob]


def is_mobile_envelope(obj, operation):
    """The v1 response contract, independent of the underlying result."""
    engine = obj.get("engine") if isinstance(obj, dict) else None
    return (isinstance(obj, dict) and obj.get("schema") == MOBILE_SCHEMA and
            obj.get("operation") == operation and
            isinstance(obj.get("request_id"), str) and
            re.fullmatch(r"[0-9a-f]{32}", obj["request_id"]) is not None and
            isinstance(engine, dict) and
            isinstance(engine.get("primus_version"), str) and
            engine.get("certificate_schema") == CERTIFICATE_SCHEMA and
            isinstance(obj.get("result"), dict))


def main():
    proc, base = start_server({"CHIRON_RATE_PER_MIN": "1000"})
    try:
        code, health = call(base, "/health")
        gate("health 200 + engine version + three tools",
             code == 200 and health["ok"] and
             sorted(health["tools"]) == ["certify", "collapse", "conjecture"],
             repr(health))

        # CORS is deliberately off by default. Native clients do not need it;
        # an arbitrary web origin must not be able to preflight local POSTs.
        preflight = urllib.request.Request(base + "/collapse", method="OPTIONS")
        preflight.add_header("Origin", "https://untrusted.example")
        try:
            with urllib.request.urlopen(preflight, timeout=10) as r:
                pf_code, pf_acao, pf_body = (r.status,
                    r.headers.get("Access-Control-Allow-Origin"), _decode(r.read()))
        except urllib.error.HTTPError as e:
            pf_code, pf_acao, pf_body = (e.code,
                e.headers.get("Access-Control-Allow-Origin"), _decode(e.read()))
        gate("CORS default denies an unconfigured browser origin",
             pf_code == 403 and pf_acao is None and
             pf_body.get("status") == "REFUSED", f"{pf_code} {pf_acao} {pf_body!r}")
        health_request = urllib.request.Request(base + "/health")
        health_request.add_header("Origin", "https://untrusted.example")
        with urllib.request.urlopen(health_request, timeout=10) as r:
            acao = r.headers.get("Access-Control-Allow-Origin")
        gate("normal responses never emit wildcard CORS", acao is None, repr(acao))

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

        # ---- v1 mobile-safe contract: only canonical inline operations ---
        code, caps = call(base, "/v1/capabilities")
        capability_ops = caps.get("result", {}).get("operations", [])
        gate("v1 capabilities has the stable envelope and only two operations",
             code == 200 and is_mobile_envelope(caps, "capabilities") and
             [item.get("operation") for item in capability_ops] ==
             ["collapse", "certify"] and
             caps["result"].get("content_type") == "application/json" and
             caps["result"].get("retry_after_seconds") ==
             {"rate_limited": 60, "busy": 1} and
             caps["result"].get("request_fields") == "unknown fields are refused",
             repr(caps)[:500])

        code, mobile_collapse = call(
            base, "/v1/collapse",
            {"surface": "1 1 2 3 5 8 13 21 34 55 89 144"})
        gate("v1 collapse wraps the canonical collapse result without a new engine",
             code == 200 and is_mobile_envelope(mobile_collapse, "collapse") and
             mobile_collapse["result"].get("schema") == ENGINE_SCHEMA and
             mobile_collapse["result"].get("tool") == "collapse" and
             mobile_collapse["result"].get("certificate", {}).get("verified") is True,
             repr(mobile_collapse)[:500])

        code, mobile_certify = call(base, "/v1/certify", {"text": "2+2=5"})
        gate("v1 certify wraps the canonical certificate schema",
             code == 200 and is_mobile_envelope(mobile_certify, "certify") and
             mobile_certify["request_id"] != mobile_collapse["request_id"] and
             mobile_certify["result"].get("schema") == ENGINE_SCHEMA and
             mobile_certify["result"].get("tool") == "certify" and
             mobile_certify["result"].get("certificate", {}).get("schema") ==
             CERTIFICATE_SCHEMA and
             mobile_certify["result"]["certificate"]["counts"]["refuted"] == 1,
             repr(mobile_certify)[:500])

        canary = "v1-raw-input-canary-71a4"
        code, mobile_bad_fields = call(
            base, "/v1/certify", {"text": canary, "unrecognized": canary})
        mobile_bad_blob = json.dumps(mobile_bad_fields)
        gate("v1 rejects unknown request fields without reflecting caller input",
             code == 400 and is_mobile_envelope(mobile_bad_fields, "certify") and
             mobile_bad_fields["result"].get("status") == "REFUSED" and
             canary not in mobile_bad_blob and "Traceback" not in mobile_bad_blob and
             "src/primus" not in mobile_bad_blob,
             repr(mobile_bad_fields)[:500])

        code, mobile_bad_shape = call(base, "/v1/collapse", {"surface": [1, True, 3]})
        gate("v1 rejects non-integer surface arrays before the engine",
             code == 400 and is_mobile_envelope(mobile_bad_shape, "collapse") and
             mobile_bad_shape["result"].get("status") == "REFUSED",
             repr(mobile_bad_shape)[:500])

        code, mobile_bad_media = call(
            base, "/v1/certify", {"text": "2+2=4"},
            headers={"Content-Type": "text/plain"})
        gate("v1 rejects a non-JSON Content-Type before parsing the body",
             code == 415 and is_mobile_envelope(mobile_bad_media, "certify") and
             mobile_bad_media["result"].get("status") == "REFUSED" and
             mobile_bad_media["result"].get("error") == "unsupported media type",
             repr(mobile_bad_media)[:500])

        code, mobile_bad_json = call(
            base, "/v1/certify", raw=(b'{"text":"' +
                                         canary.encode() + b'"'))
        mobile_bad_json_blob = json.dumps(mobile_bad_json)
        gate("v1 malformed JSON remains a versioned no-leak refusal",
             code == 400 and is_mobile_envelope(mobile_bad_json, "certify") and
             mobile_bad_json["result"].get("status") == "REFUSED" and
             canary not in mobile_bad_json_blob and
             "Traceback" not in mobile_bad_json_blob and
             "src/primus" not in mobile_bad_json_blob,
             repr(mobile_bad_json)[:500])

        code, mobile_unknown = call(base, "/v1/conjecture", {"terms": [1, 2, 3]})
        gate("v1 keeps conjecture closed and returns a versioned 404 refusal",
             code == 404 and is_mobile_envelope(mobile_unknown, "unknown") and
             mobile_unknown["result"].get("error") == "not found",
             repr(mobile_unknown)[:500])

        code, hdrs, mobile_wrong_method = call_ex(base, "/v1/collapse", method="GET")
        gate("v1 wrong method is a versioned 405 with Allow: POST",
             code == 405 and hdrs.get("Allow") == "POST" and
             is_mobile_envelope(mobile_wrong_method, "collapse") and
             mobile_wrong_method["result"].get("allow") == ["POST"],
             repr(mobile_wrong_method)[:500])

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
                                           "GET /v1/capabilities",
                                           "POST /certify", "POST /collapse",
                                           "POST /conjecture", "POST /v1/certify",
                                           "POST /v1/collapse"], f"{code} {r!r}")

        code, r = call(base, "/")
        gate("GET / -> 200 short banner listing the routes",
             code == 200 and len(r.get("routes") or []) == 8 and
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

    bad_cors_env = dict(os.environ)
    bad_cors_env["PYTHONPATH"] = os.path.join(HERE, "src")
    bad_cors_env["CHIRON_CORS_ORIGIN"] = "*"
    bad_cors = subprocess.run(
        [sys.executable, "-m", "primus.engine_server", "--port", str(free_port())],
        env=bad_cors_env, cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=15)
    gate("CORS configuration rejects a wildcard rather than echoing it",
         bad_cors.returncode != 0 and
         "one exact http(s) origin" in bad_cors.stderr.decode("utf-8", "replace"),
         repr(bad_cors.stderr.decode("utf-8", "replace")[-300:]))

    # An owner can opt a single browser UI into CORS, but no wildcard or
    # reflective origin is ever emitted. This is deliberately separate from
    # authentication: browser access is not a mobile auth system.
    origin = "https://app.example.test"
    proc, base = start_server({"CHIRON_RATE_PER_MIN": "1000",
                               "CHIRON_CORS_ORIGIN": origin})
    try:
        allowed = urllib.request.Request(base + "/v1/capabilities")
        allowed.add_header("Origin", origin)
        with urllib.request.urlopen(allowed, timeout=10) as response:
            allowed_code = response.status
            allowed_origin = response.headers.get("Access-Control-Allow-Origin")
            allowed_vary = response.headers.get("Vary")
        denied = urllib.request.Request(base + "/v1/capabilities")
        denied.add_header("Origin", "https://other.example.test")
        with urllib.request.urlopen(denied, timeout=10) as response:
            denied_code = response.status
            denied_origin = response.headers.get("Access-Control-Allow-Origin")
        preflight = urllib.request.Request(base + "/v1/certify", method="OPTIONS")
        preflight.add_header("Origin", origin)
        with urllib.request.urlopen(preflight, timeout=10) as response:
            preflight_code = response.status
            preflight_origin = response.headers.get("Access-Control-Allow-Origin")
        gate("CORS opt-in emits only the configured exact origin",
             allowed_code == 200 and allowed_origin == origin and allowed_vary == "Origin" and
             denied_code == 200 and denied_origin is None and
             preflight_code == 204 and preflight_origin == origin,
             f"allowed={allowed_code}/{allowed_origin}/{allowed_vary} "
             f"denied={denied_code}/{denied_origin} preflight={preflight_code}/{preflight_origin}")
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
            code, hdrs, r = call_ex(base, path, body, headers=h)
            results[path] = (first, code, hdrs.get("Retry-After"))
            if code == 429 and (leaks_in(r) or r.get("status") != "REFUSED"):
                dirty[path] = r
        gate("per-IP rate limit trips on ALL THREE tools (429 + Retry-After)",
             all(v == (200, 429, "60") for v in results.values()) and not dirty,
             f"{results!r} dirty={dirty!r}")
        v1_headers = {"X-Forwarded-For": "203.0.113.20"}
        first = call(base, "/v1/certify", {"text": "2+2=4"},
                     headers=v1_headers)[0]
        code, hdrs, v1_limited = call_ex(base, "/v1/certify", {"text": "2+2=4"},
                                         headers=v1_headers)
        gate("v1 rate limit keeps its envelope and Retry-After: 60",
             first == 200 and code == 429 and hdrs.get("Retry-After") == "60" and
             is_mobile_envelope(v1_limited, "certify") and
             v1_limited["result"].get("status") == "REFUSED" and
             not leaks_in({k: v for k, v in v1_limited.items() if k != "result"}) and
             "Traceback" not in json.dumps(v1_limited), repr(v1_limited)[:500])
    finally:
        proc.kill()

    # A zero-sized gate gives a deterministic real-HTTP exercise of the busy
    # path. It does not change engine semantics; it verifies both contracts
    # tell a client to retry quickly when no execution slot is available.
    proc, base = start_server({"CHIRON_RATE_PER_MIN": "1000",
                               "CHIRON_MAX_CONCURRENCY": "0"})
    try:
        code, legacy_hdrs, legacy_busy = call_ex(
            base, "/collapse", {"surface": "1 1 2 3 5 8 13 21"})
        code_v1, v1_hdrs, v1_busy = call_ex(
            base, "/v1/collapse", {"surface": "1 1 2 3 5 8 13 21"})
        gate("busy 429 gives Retry-After: 1 on legacy and v1 routes",
             code == 429 and legacy_hdrs.get("Retry-After") == "1" and
             legacy_busy.get("status") == "REFUSED" and
             code_v1 == 429 and v1_hdrs.get("Retry-After") == "1" and
             is_mobile_envelope(v1_busy, "collapse") and
             v1_busy["result"].get("status") == "REFUSED",
             f"legacy={code}/{legacy_hdrs.get('Retry-After')}/{legacy_busy!r} "
             f"v1={code_v1}/{v1_hdrs.get('Retry-After')}/{v1_busy!r}")
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
        code, r = call(base, "/v1/certify", {"text": "2+2=4"})
        gate("auth on: v1 POST without token is a versioned 401 refusal",
             code == 401 and is_mobile_envelope(r, "certify") and
             r["result"].get("status") == "REFUSED", repr(r)[:500])
        code, r = call(base, "/v1/certify", {"text": "2+2=4"},
                       headers={"Authorization": "Bearer sekrit"})
        gate("auth on: v1 POST with the static development bearer answers",
             code == 200 and is_mobile_envelope(r, "certify") and
             r["result"].get("certificate", {}).get("counts", {}).get("verified") == 1,
             repr(r)[:500])
        code, _ = call(base, "/health")
        gate("auth on: /health stays open", code == 200)
    finally:
        proc.kill()

    print(f"\n  {GATES - FAILS}/{GATES} endpoint gates passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
