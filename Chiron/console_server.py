#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
console_server.py — a read-only, allowlisted Chiron launcher for the dashboard.

A small local launcher (port 8768). It exposes a curated catalog of deterministic analysis and
status actions. The dashboard's "Run" tab renders that static allowlist and shows the output;
nothing here touches the signed chiron.py.

Safety: there is no shell, no module auto-discovery, and no generic "run a sibling script" path.
A request must exactly match a read-only (engine-facing) allowlisted module + verb. Known mutating
or process-control requests are escalated to a trusted local operator; unknown requests are refused.
Run growth, writes, builds, process control, or any other operator command from a reviewed local CLI.

    python3 console_server.py serve         # launcher at http://127.0.0.1:8768
    python3 console_server.py selftest

Status: implemented & tested.

Browser requests from the documented local dashboard are explicitly allowlisted;
this loopback service never uses a wildcard CORS policy.
"""
import os
import sys
import json
import time
import shlex
import argparse
import subprocess
import re

import local_cors

_HERE = os.path.dirname(os.path.abspath(__file__))


# Curated labels for the browser catalog. Every row still needs an exact entry in
# READ_ONLY_COMMANDS below before it is executable.
# Each item: (module, [fixed argv], label, args_placeholder_or_None).
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
    "Compose — build your own validation system": [
        ("pipeline", ["demo"], "chain · team · swarm — worked examples", None),
        ("pipeline", ["selftest"], "the composer's own gates (7/7)", None),
        ("pipeline", ["run"], "run a pipeline spec (JSON)",
         '{"mode":"chain","input":"1 1 2 3 5 8 13 21 34 55","stages":[{"component":"collapse"},{"component":"cross_examine"}]}'),
        ("planner", ["run"], "goal-directed campaign (gate arbitrates)", "1 1 2 3 5 8 13"),
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
        ("llm_certify", [], "certify an LLM output — audit + verify its claims", "obviously 2 4 8 16 32 64 continues, and 310 of 1,240 renewed, or 30 percent"),
        ("llm_certify", ["selftest"], "LLM-wrapper self-test", None),
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
        ("stress_test", [], "adversarial stress probes — try to break the vault", None),
        ("planner", ["run"], "compose a campaign — the gate arbitrates each step", "1 1 2 3 5 8 13"),
        ("planner", ["selftest"], "planner gates (compose / halt / escalate)", None),
        ("heartbeat", ["status"], "the vault's pulse — last beat + certificate", None),
    ],
}

# Browser-executable commands, named exactly. This is deliberately not derived from files on
# disk or from FEATURED: adding a script must never silently make it remotely invocable.
READ_ONLY_COMMANDS = frozenset((
    ("chiron", ("collapse",)),
    ("chiron", ("topk",)),
    ("chiron", ("explain",)),
    ("chiron", ("articulate",)),
    ("chiron", ("solve",)),
    ("chiron", ("same-origin",)),
    ("chiron", ("audit",)),
    ("chiron", ("twins",)),
    ("chiron", ("state",)),
    ("semic", ()),
    ("semic_energy", ("demo",)),
    ("epistemic", ("demo",)),
    ("bench_suite", ()),
    ("bench_symreg", ()),
    ("bench_proverbs", ()),
    ("bench_protocol", ()),
    ("bench_legal", ()),
    ("bench_compression", ()),
    ("bench_authorship", ()),
    ("compare", ()),
    ("govern", ("demo",)),
    ("llm_certify", ()),
    ("president_grow", ("status",)),
    ("grow_control", ("status",)),
    ("heartbeat", ("status",)),
))

# Only these allowlisted actions accept the dashboard's free-form payload. Option-looking
# tokens are refused before subprocess creation, so an input field cannot change the verb or
# activate a hidden file/network mode.
USER_INPUT_COMMANDS = frozenset((
    ("chiron", ("collapse",)),
    ("chiron", ("topk",)),
    ("chiron", ("explain",)),
    ("chiron", ("articulate",)),
    ("chiron", ("solve",)),
    ("chiron", ("same-origin",)),
    ("chiron", ("audit",)),
    ("llm_certify", ()),
))

# These known state-changing families never execute through this unauthenticated loopback
# launcher. They are reported as an escalation so a person can review and run the direct CLI.
OPERATOR_ONLY_MODULES = frozenset((
    "grow_clean", "chiron_grow", "grow_control", "president_grow", "heartbeat", "build",
    "apply_license_headers",
))
OPERATOR_ONLY_PREFIXES = frozenset((
    ("chiron", "run"), ("chiron", "ingest"), ("chiron", "seal"), ("chiron", "unseal"),
    ("chiron", "merge"), ("chiron", "checkpoint"), ("chiron", "compact"),
    ("chiron", "self-growth"), ("chiron", "grow-concepts"),
    ("chiron", "propose"), ("chiron", "apply-proposal"),
    ("chiron", "rollback-proposal"),
    ("pipeline", "run"), ("planner", "run"),
    ("president_grow", "cycle"),
    ("grow_control", "start"), ("grow_control", "stop"), ("grow_control", "serve"),
    ("heartbeat", "serve"),
))
_OPTION_TOKEN = re.compile(r"^--?[A-Za-z]")


def _command_key(module, argv):
    """Normalize one request, rejecting ambiguous shapes before policy lookup."""
    if not isinstance(module, str) or not module or any(c in module for c in "/\\."):
        return None
    if not module.replace("_", "").isalnum():
        return None
    if not isinstance(argv, (list, tuple)) or not all(isinstance(v, str) and v for v in argv):
        return None
    return module, tuple(argv)


def command_policy(module, argv):
    """Return the execution classification for one console request.

    This function is part of the testable trust boundary: callers must check it before
    constructing a subprocess command.
    """
    key = _command_key(module, argv)
    if key is None:
        return {"status": "refused", "reason": "module and argv must be a simple exact command"}
    if key in READ_ONLY_COMMANDS:
        return {"status": "allowed", "reason": "exact read-only command allowlisted"}
    if (key[0] in OPERATOR_ONLY_MODULES or
            (key[1] and (key[0], key[1][0]) in OPERATOR_ONLY_PREFIXES)):
        return {
            "status": "escalated",
            "reason": ("This command can change state or control a process. Review and run it "
                       "from the trusted local CLI; the dashboard launcher will not execute it."),
        }
    return {
        "status": "refused",
        "reason": "command is not in the console's explicit read-only allowlist",
    }


def _read_only_args(key, user_args):
    """Parse a payload only after exact command authorization."""
    if user_args in (None, ""):
        return [], None
    if key not in USER_INPUT_COMMANDS:
        return None, "this allowlisted command does not accept dashboard arguments"
    if not isinstance(user_args, str) or len(user_args) > 4096:
        return None, "arguments must be a short string"
    try:
        extra = shlex.split(user_args)
    except ValueError as e:
        return None, f"invalid quoted arguments: {e}"
    if any(_OPTION_TOKEN.match(token) for token in extra):
        return None, "option-like arguments are not permitted through the dashboard"
    return extra, None


def catalog():
    groups = []
    for title, items in FEATURED.items():
        rows = []
        for mod, argv, label, ph in items:
            key = _command_key(mod, argv)
            if key not in READ_ONLY_COMMANDS:
                continue
            rows.append({"module": mod, "argv": argv, "label": label, "args": ph,
                         "policy": "read-only"})
        if rows:
            groups.append({"title": title, "items": rows})
    return groups


def run(module, argv, user_args=""):
    key = _command_key(module, argv)
    policy = command_policy(module, argv)
    if policy["status"] != "allowed":
        return {"ok": False, "policy": policy["status"], "output": policy["reason"]}
    extra, arg_error = _read_only_args(key, user_args)
    if arg_error:
        return {"ok": False, "policy": "refused", "output": arg_error}
    path = os.path.join(_HERE, key[0] + ".py")
    # The static allowlist is source-of-truth, but retain this defense against an incomplete checkout.
    if not os.path.isfile(path):
        return {"ok": False, "policy": "refused", "output": f"allowlisted module is unavailable: {key[0]}.py"}
    cmd = [sys.executable, path] + list(key[1]) + extra
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=_HERE, capture_output=True, text=True, timeout=180)
        out = (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return {"ok": False, "policy": "allowed", "output": "timed out after 180s",
                "cmd": " ".join(cmd[1:])}
    res = {"ok": p.returncode == 0, "returncode": p.returncode,
           "output": out[-12000:], "seconds": round(time.time() - t0, 2),
           "cmd": "python3 " + " ".join(os.path.basename(c) if c == path else c for c in cmd[1:]),
           "policy": "allowed"}
    try:  # the witness never breaks the act it witnesses
        import run_ledger
        res["certificate"] = run_ledger.certificate_for(key[0])
        run_ledger.record(key[0], list(key[1]) + extra, ok=res["ok"],
                          # Console output can contain user-selected text; the ledger
                          # records only the operation outcome and redacted argument
                          # witnesses, never a tail of that output.
                          verdict=f"exit {p.returncode}",
                          seconds=res["seconds"], certificate=res["certificate"],
                          source="console", redact=True)
    except Exception:
        pass
    return res


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
<h2>Run read-only Chiron analysis</h2>
<div class=qs><b>Quick start:</b> <code>python3 chiron.py serve</code> (console :8765) ·
<code>python3 console_server.py serve</code> (this :8768). Growth, writes, builds, and process
control are operator-only: review and run those commands from the local CLI.</div>
<div id=out></div><div id=cat></div>
<script>const B='';
async function j(p,b){const o=b?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}:{};const r=await fetch(B+p,o);return r.json()}
async function go(m,argv,el){const a=el.querySelector('input');const args=a?a.value:'';document.getElementById('out').innerHTML='<pre>running '+m+' '+argv.join(' ')+' …</pre>';
const r=await j('/api/console/run',{module:m,argv:argv,args:args});
document.getElementById('out').innerHTML='<pre>'+(r.policy||'unknown policy')+' · $ '+(r.cmd||'')+'  ('+(r.seconds||0)+'s, '+(r.ok?'ok':'exit '+(r.returncode??'?'))+')\\n\\n'+(r.output||'').replace(/</g,'&lt;')+'</pre>';window.scrollTo(0,0)}
async function load(){const groups=await j('/api/console/catalog');let h='';
for(const g of groups){h+='<h3>'+g.title+'</h3><div class=grp>';
for(const it of g.items){const id='i'+Math.random().toString(36).slice(2);
h+='<div class=it id='+id+'><span class=lab>'+it.label+' <span class=mod>'+it.module+' '+it.argv.join(' ')+'</span></span>'+
(it.args!==null?'<input placeholder="'+it.args+'" size=22>':'')+
'<button onclick="go(\\''+it.module+'\\','+JSON.stringify(it.argv)+',document.getElementById(\\''+id+'\\'))">Run</button></div>'}
h+='</div>'}document.getElementById('cat').innerHTML=h}
load()</script></body></html>"""


def make_server(port=8768, cors_origins=None):
    """Create the loopback server without starting it (also used by HTTP contract tests)."""
    import http.server
    origins = (local_cors.configured_origins() if cors_origins is None
               else local_cors.normalize_origins(cors_origins))

    class H(http.server.BaseHTTPRequestHandler):
        def _send(self, code, body, ctype="application/json", *, preflight=False):
            data = body.encode() if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            for name, value in local_cors.headers_for(
                    self.headers.get("Origin"), preflight=preflight, origins=origins):
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

        def do_OPTIONS(self):
            origin = self.headers.get("Origin")
            if origin and not local_cors.allowed_origin(origin, origins):
                return self._send(403, json.dumps({"error": "CORS origin not allowed"}))
            self._send(204, b"", preflight=bool(origin))

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

    return http.server.ThreadingHTTPServer(("127.0.0.1", port), H)


def serve(port=8768):
    httpd = make_server(port)
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
    catalog_keys = {(it["module"], tuple(it["argv"])) for g in cat for it in g["items"]}
    ok("catalog has read-only featured groups", len(cat) >= 5)
    ok("every catalog row is an exact read-only allowlist entry",
       catalog_keys and catalog_keys <= READ_ONLY_COMMANDS
       and all(it.get("policy") == "read-only" for g in cat for it in g["items"]))
    ok("a normal analysis action is allowlisted",
       command_policy("chiron", ["collapse"])["status"] == "allowed")
    ok("known growth mutation is escalated",
       run("grow_clean", ["file"], "./notes.txt")["policy"] == "escalated")
    ok("unknown sibling script is refused, never auto-discovered",
       run("legal_corpus", ["selftest"])["policy"] == "refused")
    ok("rejects path-y module names", run("../etc/passwd", [])["policy"] == "refused")
    ok("rejects option injection into an allowlisted action",
       run("chiron", ["collapse"], "--memory /tmp/other.json")["policy"] == "refused")

    passed = sum(1 for _, c in checks if c)
    print("console_server self-test")
    for n, c in checks:
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"  {passed}/{len(checks)} checks")
    return passed == len(checks)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run exact read-only Chiron actions from one launcher.")
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
