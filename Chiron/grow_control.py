#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
grow_control.py — start / stop / point the continuous grower, from the dashboard.

`chiron_grow.py` is the pointable, continuous grower (Wikipedia / website / API / OEIS), and it
already picks up a live source redirect from `chiron_control.json` each pass. What it lacked was a
way to start and stop it without a terminal. This service adds exactly that: a small, local
control plane that launches the grower as a background process, stops it, reports its status, and
points it at any source --- so the dashboard can run it, halt it, and redirect it whenever you want.

It is its own process on its own port (8767), so it never touches the signed `chiron.py`. The
dashboard's Feed tab calls it. `grow_clean.py` stays separate --- that is for anyone who wants to
start their own grow from a file; this is the operator's live control of the main grower.

    python3 grow_control.py serve            # control plane on http://127.0.0.1:8767
    python3 grow_control.py start            # start the grower (default source)
    python3 grow_control.py stop             # stop it
    python3 grow_control.py status
    python3 grow_control.py selftest         # offline lifecycle test (dummy process)

Status: implemented & tested (offline lifecycle). Runs the real grower on your machine.
"""
import os
import sys
import json
import time
import signal
import argparse
import subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))
GROW_DIR = os.path.join(_HERE, "grow-public")
DEFAULT_PARAMS = os.path.join(GROW_DIR, "parameters.json")
CONTROL = os.path.join(GROW_DIR, "chiron_control.json")     # the live source redirect the grower reads
STATE = os.path.join(GROW_DIR, "grow_control_state.json")   # our pid/meta tracking
LOG = os.path.join(_HERE, "grow.log")
WIKI_API = "https://en.wikipedia.org/w/api.php"
UA = "Chiron-Grow/1.0 (operator-directed; dashboard)"


# ---------------------------------------------------------------------
# source: turn a simple (kind, value) into the dict the grower understands
# ---------------------------------------------------------------------
def source_from(kind, value=""):
    kind = (kind or "wikipedia").strip().lower()
    value = (value or "").strip()
    if kind == "web":
        return {"name": "web", "seeds": value.split(), "user_agent": UA,
                "domain_label": "web"}
    if kind == "api":
        return {"name": "api", "list_url": value, "user_agent": UA, "domain_label": "api"}
    if kind == "oeis":
        return {"name": "oeis", "query": value or "keyword:core",
                "search_url": "https://oeis.org/search", "user_agent": UA}
    return {"name": "wikipedia", "api_url": WIKI_API, "user_agent": UA}  # value -> topics live in params


def set_source(kind, value=""):
    os.makedirs(GROW_DIR, exist_ok=True)
    src = source_from(kind, value)
    with open(CONTROL, "w") as f:
        json.dump({"source": src}, f, indent=2)
    return src


# ---------------------------------------------------------------------
# process lifecycle
# ---------------------------------------------------------------------
def _save(pid, meta):
    with open(STATE, "w") as f:
        json.dump({"pid": pid, "started": time.time(), **meta}, f)


def _load():
    try:
        return json.load(open(STATE))
    except Exception:
        return {}


def _alive(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def is_running():
    return _alive(_load().get("pid"))


def _mb(path):
    try:
        return round(os.path.getsize(path) / 1e6, 3)
    except OSError:
        return 0.0


def status():
    st = _load()
    running = _alive(st.get("pid"))
    src = None
    try:
        src = json.load(open(CONTROL)).get("source", {}).get("name") if os.path.exists(CONTROL) else None
    except Exception:
        src = None
    passes = None
    try:
        rs = os.path.join(GROW_DIR, "chiron_grow_state.json")
        passes = json.load(open(rs)).get("passes") if os.path.exists(rs) else None
    except Exception:
        passes = None
    return {"running": running, "pid": st.get("pid") if running else None,
            "source": src or "default (from parameters.json)",
            "congress_mb": _mb(os.path.join(GROW_DIR, "chiron_memory.json")),
            "passes": passes,
            "uptime_s": round(time.time() - st["started"]) if running and st.get("started") else 0}


def start(kind=None, value="", once=False, cmd=None):
    if is_running():
        return {**status(), "note": "already running"}
    if kind:
        set_source(kind, value)
    if cmd is None:
        cmd = [sys.executable, os.path.join(_HERE, "chiron_grow.py"), "--params", DEFAULT_PARAMS]
        if once:
            cmd.append("--once")
    logf = open(LOG, "a")
    p = subprocess.Popen(cmd, cwd=_HERE, stdout=logf, stderr=logf, start_new_session=True)
    _save(p.pid, {"cmd": " ".join(cmd), "source": kind or "default"})
    time.sleep(0.3)
    return {**status(), "note": "started"}


def stop():
    st = _load()
    pid = st.get("pid")
    if _alive(pid):
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
            for _ in range(20):
                if not _alive(pid):
                    break
                time.sleep(0.1)
            if _alive(pid):
                os.killpg(os.getpgid(pid), signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass
    try:
        os.remove(STATE)
    except OSError:
        pass
    return {**status(), "note": "stopped"}


# ---------------------------------------------------------------------
# control-plane server (own port; CORS so the dashboard can call it)
# ---------------------------------------------------------------------
def _panel():
    return """<!doctype html><html><head><meta charset=utf-8><title>Grow control</title>
<style>body{font:14px system-ui;background:#0b0f17;color:#e6edf6;margin:0;padding:18px}
button{background:#1d6feb;color:#fff;border:0;border-radius:8px;padding:9px 14px;font-weight:600;cursor:pointer;margin-right:8px}
button.stop{background:#b4453a}.pill{border:1px solid #2a3a52;border-radius:999px;padding:2px 10px;color:#9fb0c6}
select,input{background:#0a0e16;color:#e6edf6;border:1px solid #2c3850;border-radius:8px;padding:8px}</style></head><body>
<h3>Grower control</h3><p id=st class=pill>...</p>
<p><select id=k><option value=wikipedia>Wikipedia (topics from config)</option>
<option value=web>Website (seed URLs)</option><option value=api>JSON API (list endpoint)</option>
<option value=oeis>OEIS (sequences)</option></select> <input id=v placeholder="value (optional)" size=40></p>
<p><button onclick=go('start')>Start</button><button class=stop onclick=go('stop')>Stop</button>
<button onclick=load()>Refresh</button></p>
<script>const B='';
async function j(p,b){const r=await fetch(B+p,b?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}:{});return r.json()}
async function load(){try{const s=await j('/api/control/status');document.getElementById('st').textContent=(s.running?'RUNNING':'stopped')+' · source: '+s.source+' · congress '+s.congress_mb+' MB'+(s.passes?(' · pass '+s.passes):'')}catch(e){document.getElementById('st').textContent='control offline'}}
async function go(a){const k=document.getElementById('k').value,v=document.getElementById('v').value;await j('/api/control/'+a,a==='start'?{kind:k,value:v}:{});load()}
load();setInterval(load,4000)</script></body></html>"""


def serve(port=8767):
    import http.server
    class H(http.server.BaseHTTPRequestHandler):
        def _send(self, code, body, ctype="application/json"):
            data = body.encode() if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

        def do_OPTIONS(self):
            self._send(204, b"")

        def do_GET(self):
            if self.path in ("/", "/grow-control"):
                return self._send(200, _panel(), "text/html; charset=utf-8")
            if self.path == "/api/control/status":
                return self._send(200, json.dumps(status()))
            self._send(404, json.dumps({"error": "not found"}))

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0) or 0)
            body = json.loads(self.rfile.read(n) or b"{}") if n else {}
            if self.path == "/api/control/start":
                return self._send(200, json.dumps(start(body.get("kind"), body.get("value", ""))))
            if self.path == "/api/control/stop":
                return self._send(200, json.dumps(stop()))
            if self.path == "/api/control/source":
                return self._send(200, json.dumps({"source": set_source(body.get("kind"), body.get("value", ""))}))
            self._send(404, json.dumps({"error": "not found"}))

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), H)
    print(f"grow control on http://127.0.0.1:{port}/grow-control")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    # source conversion
    ok("web source -> seeds list", source_from("web", "http://a http://b")["seeds"] == ["http://a", "http://b"])
    ok("oeis source -> query", source_from("oeis", "keyword:nice")["query"] == "keyword:nice")
    ok("default is wikipedia", source_from("")["name"] == "wikipedia")

    # set_source writes the control file the grower reads
    set_source("oeis", "keyword:core")
    ok("control file written", json.load(open(CONTROL))["source"]["name"] == "oeis")

    # lifecycle with a harmless dummy process (no network, no real grower)
    stop()  # clean slate
    ok("starts a process", start(cmd=[sys.executable, "-c", "import time;time.sleep(30)"])["running"] is True)
    ok("status reports running", is_running() is True)
    ok("stops the process", stop()["running"] is False)
    ok("status reports stopped", is_running() is False)

    passed = sum(1 for _, c in checks if c)
    print("grow_control self-test")
    for n, c in checks:
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"  {passed}/{len(checks)} checks")
    return passed == len(checks)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Start/stop/point the continuous grower.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("selftest")
    sub.add_parser("status")
    sub.add_parser("stop")
    sv = sub.add_parser("serve"); sv.add_argument("--port", type=int, default=8767)
    st = sub.add_parser("start"); st.add_argument("--kind", default=None); st.add_argument("--value", default="")
    st.add_argument("--once", action="store_true")
    args = ap.parse_args(argv)
    if args.cmd == "serve":
        serve(args.port); return 0
    if args.cmd == "status":
        print(json.dumps(status(), indent=2)); return 0
    if args.cmd == "stop":
        print(json.dumps(stop(), indent=2)); return 0
    if args.cmd == "start":
        print(json.dumps(start(args.kind, args.value, args.once), indent=2)); return 0
    return 0 if _selftest() else 1


if __name__ == "__main__":
    sys.exit(main())
