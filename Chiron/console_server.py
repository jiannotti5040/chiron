#!/usr/bin/env python3
"""
console_server.py — run any Chiron function, and reach every engine, from the dashboard.

A small local launcher (port 8768). It exposes a curated catalog of the engines' functions — the
chiron CLI verbs, the semantic calculus, the framework interface, the governance and certification
layer, the growth tools, the build verifier, and the six-task benchmark suite — plus an
auto-discovered self-test for every module in the folder. The dashboard's "Run" tab renders the
catalog and shows the output; nothing here touches the signed chiron.py.

Safety: there is no shell. A request names a module (which must be an existing `.py` in this folder)
and a verb; the launcher runs `python3 <module>.py <verb> <args>` with arguments passed as argv, so
there is no shell interpolation. Long-running servers (anything `serve`) are intentionally not in the
catalog.

    python3 console_server.py serve         # launcher at http://127.0.0.1:8768
    python3 console_server.py selftest

Status: implemented & tested.
"""
import os
import sys
import glob
import json
import time
import shlex
import argparse
import subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))


# Curated, featured catalog. Each item: (module, [fixed argv], label, args_placeholder_or_None).
FEATURED = {
    "Engine — recover & prove": [
        ("chiron", ["collapse"], "collapse a sequence", "1 1 2 3 5 8 13"),
        ("chiron", ["topk"], "ranked competing hypotheses", "1 4 9 16 25"),
        ("chiron", ["explain"], "machine + human view", "2 4 8 16 32"),
        ("chiron", ["articulate"], "speak a rule back up (codec)", "1 1 2 3 5 8 13"),
        ("chiron", ["solve"], "crack a classical cipher", "WKLV LV D WHVW"),
        ("chiron", ["same-origin"], "provable twins (a :: b)", "1 2 3 :: 9 18 27"),
        ("chiron", ["audit"], "candor / anti-patronization audit", "Obviously it just works."),
        ("chiron", ["ingest"], "ingest + certify a string", "SATOR AREPO TENET OPERA ROTAS"),
        ("chiron", ["twins"], "the quintillion-scale twin proof", None),
        ("chiron", ["gauntlet"], "labeled benchmark: recovery + 0 false-verify", None),
        ("chiron", ["state"], "the Congress' current state", None),
        ("chiron", ["selftest"], "the engine's full gate suite", None),
        ("chiron", ["demo"], "self-contained demonstration", None),
    ],
    "Meaning — the semantic calculus": [
        ("semic", ["selftest"], "semic gates (56/56)", None),
        ("semic", [], "semic full report", None),
        ("semic_energy", ["demo"], "three-level stack (exact then energy)", None),
        ("semic_energy", ["selftest"], "energy-stack gates", None),
        ("semic_bridge", ["selftest"], "semic↔chiron bridge", None),
    ],
    "Framework & benchmarks": [
        ("epistemic", ["demo"], "one contract, four instances", None),
        ("epistemic", ["selftest"], "framework gates", None),
        ("bench_suite", [], "six external tasks vs baselines", None),
        ("bench_symreg", [], "symbolic regression vs polyfit", None),
        ("bench_proverbs", [], "proverb invariants vs bag-of-words", None),
        ("bench_protocol", [], "FSM recovery vs Markov", None),
        ("bench_legal", [], "provision recovery vs keyword", None),
        ("bench_compression", [], "vs gzip / bz2 / lzma", None),
        ("bench_authorship", [], "Burrows Δ vs content baseline", None),
        ("compare", [], "compression head-to-head", None),
    ],
    "Governance & certification": [
        ("govern", ["selftest"], "SoCPM / LexGuard gate", None),
        ("govern", ["demo"], "governance demo", None),
        ("certify_finding", ["selftest"], "Daubert / attestation certificate", None),
        ("legal_corpus", ["selftest"], "67-provision corpus", None),
        ("judgment", ["selftest"], "Chief Justice / earned finality", None),
        ("cross_examine", ["selftest"], "adversarial reasonable-doubt", None),
    ],
    "Growth": [
        ("grow_clean", ["file"], "grow from any file", "./notes.txt"),
        ("grow_clean", ["wikipedia"], "grow from a Wikipedia topic", "prime numbers"),
        ("grow_clean", ["selftest"], "grower gates", None),
        ("president_grow", ["status"], "LLM grow status", None),
        ("grow_control", ["status"], "grower run-state", None),
    ],
    "Build & verify": [
        ("build", ["verify-all"], "chiron.py + semic.py recompile byte-identical", None),
        ("formal_check", [], "property-based soundness check", None),
    ],
}

# Verbs we never offer (they block / serve forever).
_BLOCK = {"serve"}


def _modules_with_selftest():
    """Auto-discover every module in the folder that declares a self-test — 'the entirety'."""
    found = []
    for path in sorted(glob.glob(os.path.join(_HERE, "*.py"))):
        name = os.path.basename(path)[:-3]
        if name in ("console_server",):
            continue
        try:
            text = open(path, encoding="utf-8", errors="ignore").read(8000)
        except OSError:
            continue
        if "selftest" in text:
            verb = "--selftest" if "--selftest" in text and "add_parser(\"selftest\"" not in text else "selftest"
            found.append({"module": name, "verb": verb})
    return found


def catalog():
    groups = []
    for title, items in FEATURED.items():
        rows = []
        for mod, argv, label, ph in items:
            if any(v in _BLOCK for v in argv):
                continue
            rows.append({"module": mod, "argv": argv, "label": label, "args": ph})
        groups.append({"title": title, "items": rows})
    groups.append({"title": "Every module — self-test",
                   "items": [{"module": m["module"], "argv": [m["verb"]],
                              "label": f"{m['module']} self-test", "args": None}
                             for m in _modules_with_selftest()]})
    return groups


def run(module, argv, user_args=""):
    if not module or any(c in module for c in "/\\.") or not module.replace("_", "").isalnum():
        return {"ok": False, "output": f"rejected module name: {module!r}"}
    path = os.path.join(_HERE, module + ".py")
    if not os.path.isfile(path):
        return {"ok": False, "output": f"no such module: {module}.py"}
    extra = shlex.split(user_args) if user_args else []
    cmd = [sys.executable, path] + list(argv) + extra
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=_HERE, capture_output=True, text=True, timeout=180)
        out = (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": "timed out after 180s", "cmd": " ".join(cmd[1:])}
    return {"ok": p.returncode == 0, "returncode": p.returncode,
            "output": out[-12000:], "seconds": round(time.time() - t0, 2),
            "cmd": "python3 " + " ".join(os.path.basename(c) if c == path else c for c in cmd[1:])}


# ---------------------------------------------------------------------
def _panel():
    return """<!doctype html><html><head><meta charset=utf-8><title>Chiron — Run</title>
<style>body{font:14px system-ui;background:#0b0f17;color:#e6edf6;margin:0;padding:18px;max-width:1000px}
h3{margin:18px 0 6px}.grp{border:1px solid #1e2a3b;border-radius:12px;padding:10px 14px;margin:10px 0;background:#0f1622}
.it{display:flex;gap:8px;align-items:center;padding:6px 0;border-top:1px solid #16202e;flex-wrap:wrap}.it:first-child{border:0}
.lab{flex:1;min-width:200px}.mod{font-family:ui-monospace,monospace;color:#9fb0c6;font-size:12px}
button{background:#1d6feb;color:#fff;border:0;border-radius:8px;padding:7px 12px;font-weight:600;cursor:pointer}
input{background:#0a0e16;color:#e6edf6;border:1px solid #2c3850;border-radius:8px;padding:7px;font-family:ui-monospace,monospace;font-size:12px}
pre{background:#0a0e16;border:1px solid #1e2a3b;border-radius:10px;padding:12px;white-space:pre-wrap;max-height:380px;overflow:auto;font-size:12px}
.qs{background:#0e1a16;border:1px solid #2b5444;border-radius:10px;padding:10px 14px}</style></head><body>
<h2>Run anything in Chiron</h2>
<div class=qs><b>Quick start:</b> <code>python3 chiron.py serve</code> (console :8765) ·
<code>python3 console_server.py serve</code> (this :8768) — full guide in RUNNING.md.</div>
<div id=out></div><div id=cat></div>
<script>const B='';
async function j(p,b){const o=b?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}:{};const r=await fetch(B+p,o);return r.json()}
async function go(m,argv,el){const a=el.querySelector('input');const args=a?a.value:'';document.getElementById('out').innerHTML='<pre>running '+m+' '+argv.join(' ')+' …</pre>';
const r=await j('/api/console/run',{module:m,argv:argv,args:args});
document.getElementById('out').innerHTML='<pre>$ '+(r.cmd||'')+'  ('+(r.seconds||0)+'s, '+(r.ok?'ok':'exit '+(r.returncode??'?'))+')\\n\\n'+(r.output||'').replace(/</g,'&lt;')+'</pre>';window.scrollTo(0,0)}
async function load(){const groups=await j('/api/console/catalog');let h='';
for(const g of groups){h+='<h3>'+g.title+'</h3><div class=grp>';
for(const it of g.items){const id='i'+Math.random().toString(36).slice(2);
h+='<div class=it id='+id+'><span class=lab>'+it.label+' <span class=mod>'+it.module+' '+it.argv.join(' ')+'</span></span>'+
(it.args!==null?'<input placeholder="'+it.args+'" size=22>':'')+
'<button onclick="go(\\''+it.module+'\\','+JSON.stringify(it.argv)+',document.getElementById(\\''+id+'\\'))">Run</button></div>'}
h+='</div>'}document.getElementById('cat').innerHTML=h}
load()</script></body></html>"""


def serve(port=8768):
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
            if self.path in ("/", "/run", "/console"):
                return self._send(200, _panel(), "text/html; charset=utf-8")
            if self.path == "/api/console/catalog":
                return self._send(200, json.dumps(catalog()))
            self._send(404, json.dumps({"error": "not found"}))

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0) or 0)
            body = json.loads(self.rfile.read(n) or b"{}") if n else {}
            if self.path == "/api/console/run":
                return self._send(200, json.dumps(run(body.get("module"), body.get("argv", []),
                                                       body.get("args", ""))))
            self._send(404, json.dumps({"error": "not found"}))

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), H)
    print(f"console on http://127.0.0.1:{port}/run")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    cat = catalog()
    ok("catalog has featured groups + the auto self-test group", len(cat) >= 6)
    ok("auto-discovery found many modules", len(cat[-1]["items"]) >= 15)
    ok("no blocked (serve) verbs in the catalog",
       not any("serve" in it["argv"] for g in cat for it in g["items"]))
    ok("rejects path-y module names", run("../etc/passwd", [])["ok"] is False)
    ok("rejects unknown module", run("nope_not_real", ["selftest"])["ok"] is False)

    r = run("legal_corpus", ["selftest"])      # fast, no chiron import
    ok("runs a real module and captures output", r["ok"] and "PASS" in r["output"].upper())

    rc = run("chiron", ["collapse", "2", "4", "6", "8", "10"])
    ok("runs a chiron verb with args", "arithmetic" in rc["output"].lower())

    passed = sum(1 for _, c in checks if c)
    print("console_server self-test")
    for n, c in checks:
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"  {passed}/{len(checks)} checks")
    return passed == len(checks)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run any Chiron function from one launcher.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("selftest")
    sub.add_parser("catalog")
    sv = sub.add_parser("serve"); sv.add_argument("--port", type=int, default=8768)
    args = ap.parse_args(argv)
    if args.cmd == "serve":
        serve(args.port); return 0
    if args.cmd == "catalog":
        print(json.dumps(catalog(), indent=2)); return 0
    return 0 if _selftest() else 1


if __name__ == "__main__":
    sys.exit(main())
