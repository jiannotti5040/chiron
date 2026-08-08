#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""Real-HTTP regression gates for the assistant and console CORS boundary.

Run: python3 Chiron/tests/test_local_cors.py
"""
from contextlib import contextmanager
import http.client
import os
import sys
import threading


CHIRON = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, CHIRON)

import assistant_server
import console_server
import local_cors


DASHBOARD = "http://127.0.0.1:8765"
ARBITRARY_WEB = "https://example.invalid"


@contextmanager
def running(make_server):
    server = make_server(0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def request(port, method, path, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request(method, path, headers=headers or {})
    response = conn.getresponse()
    body = response.read()
    result = response.status, {k.lower(): v for k, v in response.getheaders()}, body
    conn.close()
    return result


def cors_headers(headers):
    return {k: v for k, v in headers.items() if k.startswith("access-control-")}


def assert_service_policy(make_server, path):
    with running(make_server) as port:
        own_origin = f"http://127.0.0.1:{port}"
        status, headers, _ = request(port, "GET", path, {"Origin": own_origin})
        assert status == 200
        # A panel served by this same service needs no CORS grant and remains usable.
        assert cors_headers(headers) == {}

        status, headers, _ = request(port, "GET", path, {"Origin": DASHBOARD})
        assert status == 200
        assert cors_headers(headers) == {"access-control-allow-origin": DASHBOARD}
        assert headers.get("vary") == "Origin"

        status, headers, _ = request(port, "OPTIONS", path, {
            "Origin": DASHBOARD,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        })
        assert status == 204
        assert cors_headers(headers) == {
            "access-control-allow-origin": DASHBOARD,
            "access-control-allow-methods": "GET, POST",
            "access-control-allow-headers": "Content-Type",
        }
        assert headers.get("vary") == "Origin"

        status, headers, _ = request(port, "GET", path, {"Origin": ARBITRARY_WEB})
        assert status == 200
        assert cors_headers(headers) == {}

        status, headers, _ = request(port, "OPTIONS", path, {
            "Origin": ARBITRARY_WEB,
            "Access-Control-Request-Method": "POST",
        })
        assert status == 403
        assert cors_headers(headers) == {}


def test_only_loopback_origins_can_be_configured():
    origins = local_cors.configured_origins({
        local_cors.ENV_VAR: "http://localhost:8765, https://example.invalid, http://127.0.0.1:80/"
    })
    assert origins == ("http://localhost:8765", "http://127.0.0.1")
    assert local_cors.configured_origins({local_cors.ENV_VAR: ""}) == ()


def test_custom_local_allowlist_changes_the_browser_grant():
    local_dashboard = "http://localhost:9876"
    with running(lambda port: console_server.make_server(
            port, cors_origins=(local_dashboard, ARBITRARY_WEB))) as port:
        status, headers, _ = request(port, "GET", "/api/console/catalog", {"Origin": local_dashboard})
        assert status == 200
        assert cors_headers(headers) == {"access-control-allow-origin": local_dashboard}

        status, headers, _ = request(port, "GET", "/api/console/catalog", {"Origin": DASHBOARD})
        assert status == 200
        assert cors_headers(headers) == {}


def test_assistant_cors_policy_is_strict_and_dashboard_compatible():
    assert_service_policy(assistant_server.make_server, "/api/assistant/status")


def test_console_cors_policy_is_strict_and_dashboard_compatible():
    assert_service_policy(console_server.make_server, "/api/console/catalog")


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok -", test.__name__)
    print("ALL PASSED (%d)" % len(tests))
