#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
assistant_server.py — a natural-language assistant over the Chiron engine and the Congress.

Tell it what you want in plain language; it figures out the intent, runs the REAL deterministic
read-only functions (recover a rule, speak it back, search or summarize the Congress), and replies.
The discipline is the portfolio's: the LLM can select only this bounded read-only tool surface;
every factual result comes from exact, verifiable code, not from the model. The LLM is the front
door, never the source of truth or a command dispatcher.

It reuses the free-LLM client from president_grow (Gemini by default; Groq/OpenRouter via env), so
it needs a free key (GROW_LLM_API_KEY). Without a key it says so and stays out of the way.

    # get a free key at https://aistudio.google.com/apikey
    export GROW_LLM_API_KEY=your_key
    python3 assistant_server.py serve      # chat at http://127.0.0.1:8769/chat ; also the console's Chat tab
    python3 assistant_server.py selftest   # offline (mock LLM, real engine)

Status: implemented & tested offline (mock LLM + real engine actions).

Browser requests from the documented local dashboard are explicitly allowlisted;
this loopback service never uses a wildcard CORS policy.
"""
import os
import re
import sys
import json
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import president_grow as pg          # noqa: E402  the free-LLM client
import local_cors                    # noqa: E402  strict browser-origin policy

CONGRESS = os.path.join(_HERE, "chiron_memory.json")


# ---------------------------------------------------------------------
# actions — each is a deterministic, read-only engine/Congress operation.
# The LLM is untrusted planner input, never a command dispatcher.
# ---------------------------------------------------------------------
def _seq(s):
    return [int(x) for x in re.findall(r"-?\d+", str(s))]


def act_collapse(args):
    import chiron
    surface = args.get("surface", "")
    seq = _seq(surface)
    inv = chiron.collapse(seq if len(seq) >= 2 else str(surface))
    out = {"verified": bool(inv.verified), "model_class": inv.model_class,
           "explanation": (getattr(inv, "explanation", "") or "")[:300]}
    if inv.verified:
        try:
            nxt = [int(x) for x in inv.predict(len(seq) + 4)]
            out["spoken_back"] = nxt              # regenerated + extended in its own language
            out["predict_next"] = nxt[len(seq):]  # the continuation it forecasts
        except Exception:
            pass
    return out


def act_congress(args):
    try:
        data = json.load(open(CONGRESS))
    except Exception:
        return {"note": "no Congress file found"}
    def _count(d, key):
        v = d.get(key)
        return len(v) if isinstance(v, (list, dict)) else v
    summary = {"size_mb": round(os.path.getsize(CONGRESS) / 1e6, 3)}
    for k in ("domains", "laws", "vault", "items", "organisms", "concepts", "ledger"):
        if k in data:
            summary[k] = _count(data, k)
    return summary


def act_search(args):
    term = str(args.get("term", "")).lower().strip()
    if not term:
        return {"matches": []}
    try:
        text = open(CONGRESS, encoding="utf-8", errors="ignore").read()
    except Exception:
        return {"matches": []}
    hits = []
    for m in re.finditer(re.escape(term), text.lower()):
        s = max(0, m.start() - 50)
        hits.append(text[s:m.start() + 60].replace("\n", " "))
        if len(hits) >= 6:
            break
    return {"term": term, "match_count": text.lower().count(term), "samples": hits}


def act_answer(args):
    return None


ACTIONS = {"collapse": act_collapse, "congress": act_congress, "search": act_search,
           "answer": act_answer}

# These names are intentionally explicit instead of attempting to infer whether an
# LLM-proposed command mutates state. The assistant has no command-execution tool at
# all: a human can review an operator action and invoke the local CLI directly.
MODEL_READ_ONLY_ACTIONS = frozenset(("collapse", "congress", "search", "answer"))
MODEL_ESCALATED_ACTIONS = frozenset((
    "run", "exec", "execute", "shell", "script", "grow", "grow_clean", "grow_control",
    "ingest", "write", "edit",
    "delete", "mutate", "build", "install", "serve", "start", "stop", "publish", "deploy",
    "commit", "push", "key", "set_key", "beat", "heartbeat", "upload", "release",
))


def model_action_policy(action):
    """Classify untrusted model output before it reaches a real operation.

    Read-only engine actions are the complete assistant tool surface. Known mutation or
    execution requests are escalated to the trusted local operator; unknown requests are
    refused rather than being interpreted as a command.
    """
    normalized = str(action or "answer").strip().lower()
    if normalized in MODEL_READ_ONLY_ACTIONS:
        return {"status": "allowed", "action": normalized}
    if normalized in MODEL_ESCALATED_ACTIONS:
        return {
            "status": "escalated",
            "action": normalized,
            "reason": ("Model-directed execution and mutation are disabled. Review this "
                       "operation and run it from the trusted local CLI if appropriate."),
        }
    return {
        "status": "refused",
        "action": normalized,
        "reason": "The assistant only exposes deterministic read-only engine actions.",
    }

SYSTEM = """You are the assistant for Chiron, a deterministic invariant-recovery engine with a
memory called the Congress. Decide what the user wants and reply with ONE JSON object only:
{"action": <one of collapse|congress|search|answer>, "args": {...}, "say": <a short
natural-language reply to the user>}.
- collapse: recover + verify the rule behind a sequence/string. args: {"surface": "1 1 2 3 5 8"}.
  (Use this for "what's the rule", "speak it back", "predict the next terms".)
- congress: summarize the Congress (domains, laws, size). args: {}.
- search: find something in the Congress. args: {"term": "fibonacci"}.
- answer: just answer in words (capabilities, explanations). args: {}.
Never request command execution, growth, writes, credentials, network operations, or deployment.
Always include a friendly "say". Output the JSON and nothing else."""


def _extract_json(text):
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return {"action": "answer", "args": {}, "say": text.strip()[:500]}
    try:
        parsed = json.loads(m.group(0))
        return parsed if isinstance(parsed, dict) else {"action": "answer", "args": {}, "say": ""}
    except Exception:
        return {"action": "answer", "args": {}, "say": text.strip()[:500]}


def _need_key():
    return {"enabled": False, "action": None, "result": None,
            "reply": "The assistant needs at least one LLM key. Set any of GEMINI_API_KEY, "
            "OPENROUTER_API_KEY, GROQ_API_KEY, CEREBRAS_API_KEY, OPENAI_API_KEY, "
            "ANTHROPIC_API_KEY, or PERPLEXITY_API_KEY "
            "(e.g. `export OPENROUTER_API_KEY=...`) and restart this service. Run "
            "`python3 llm_providers.py check` to see what's keyed. (The Run tab works "
            "without a key.)"}


def chat(message, history=None, cfg=None, transport=None):
    """Plan an action with the LLM, then execute it on the real engine. The real path uses the
    multi-provider chain (any keyed provider); passing an explicit cfg/transport forces the
    single-provider path (used by the offline self-test)."""
    import llm_providers as llm
    explicit = cfg is not None or transport is not None
    if explicit:
        eff = cfg or pg.LLMConfig.from_env()
        if not eff.enabled and transport is None:
            return _need_key()
    elif not llm.enabled():
        return _need_key()
    convo = ""
    for turn in (history or [])[-6:]:
        convo += f"\n{turn.get('role', 'user')}: {turn.get('content', '')}"
    prompt = f"{SYSTEM}\n\nConversation so far:{convo}\n\nuser: {message}\n\nJSON:"
    if explicit:
        raw, provider = pg.llm_generate(prompt, eff, transport), eff.provider
    else:
        res = llm.generate(prompt)
        raw, provider = res.get("text", ""), res.get("provider")
        if not raw:
            return {"enabled": False, "action": None, "result": None,
                    "reply": "No LLM provider answered — run `python3 llm_providers.py check`."}
    plan = _extract_json(raw)
    action = str(plan.get("action") or "answer").strip().lower()
    args = plan.get("args") if isinstance(plan.get("args"), dict) else {}
    say = str(plan.get("say") or "")[:500]
    result = None
    policy = model_action_policy(action)
    if policy["status"] == "allowed" and action != "answer":
        try:
            result = ACTIONS[action](args)
        except Exception as e:
            result = {"error": str(e)}
    elif policy["status"] != "allowed":
        result = policy
        # Do not display a model-authored claim that an operator action ran when the
        # policy blocked it. The policy result is the authoritative user-facing reply.
        say = policy["reason"]
    return {"enabled": True, "reply": say, "action": action, "args": args,
            "result": result, "provider": provider, "policy": policy["status"]}


# ---------------------------------------------------------------------
def _panel():
    return """<!doctype html><html><head><meta charset=utf-8><title>Chiron — Chat</title>
<style>body{font:14px system-ui;background:#0b0f17;color:#e6edf6;margin:0;padding:18px;max-width:860px}
#log{min-height:300px;margin-bottom:12px}.msg{padding:10px 12px;border-radius:10px;margin:8px 0;max-width:85%}
.u{background:#15233a;margin-left:auto}.a{background:#0f1622;border:1px solid #1e2a3b}
pre{background:#0a0e16;border:1px solid #1e2a3b;border-radius:8px;padding:10px;white-space:pre-wrap;font-size:12px;overflow:auto}
.row{display:flex;gap:8px}input{flex:1;background:#0a0e16;color:#e6edf6;border:1px solid #2c3850;border-radius:10px;padding:11px}
button{background:#1d6feb;color:#fff;border:0;border-radius:10px;padding:11px 16px;font-weight:600;cursor:pointer}</style></head><body>
<h3>Chiron assistant</h3><div id=log></div>
<div class=row><input id=m placeholder="Tell it what you want — e.g. 'what rule is behind 1 1 2 3 5 8?'" onkeydown="if(event.key==='Enter')send()"><button onclick=send()>Send</button></div>
<script>const B='';let hist=[];
function add(role,html){const d=document.createElement('div');d.className='msg '+(role==='user'?'u':'a');d.innerHTML=html;document.getElementById('log').appendChild(d);window.scrollTo(0,9e9)}
async function send(){const i=document.getElementById('m');const t=i.value.trim();if(!t)return;i.value='';add('user',t);hist.push({role:'user',content:t});
add('assistant','…');const log=document.getElementById('log');const ph=log.lastChild;
try{const r=await fetch(B+'/api/assistant/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:t,history:hist})}).then(x=>x.json());
let h=(r.reply||'').replace(/</g,'&lt;');if(r.result)h+='<pre>'+JSON.stringify(r.result,null,2).replace(/</g,'&lt;')+'</pre>';if(r.action&&r.action!=='answer')h+='<div style=\"color:#8593a8;font-size:11px\">action: '+r.action+'</div>';
ph.innerHTML=h;hist.push({role:'assistant',content:r.reply||''})}catch(e){ph.innerHTML='<span style=color:#ff8090>'+e.message+'</span>'}}
</script></body></html>"""


def make_server(port=8769, cors_origins=None):
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
            if self.path in ("/", "/chat"):
                return self._send(200, _panel(), "text/html; charset=utf-8")
            if self.path == "/api/assistant/status":
                import llm_providers as llm
                avail = llm.available()  # [(name, env_var, model)]
                provs = [a[0] for a in avail]
                return self._send(200, json.dumps({
                    "enabled": bool(avail),
                    "provider": (provs[0] if provs else "none"),
                    "providers": provs,
                    "chain": llm.chain(),
                    "model": (avail[0][2] if avail else "")}))
            if self.path == "/api/assistant/manifest":
                # The vault manifest (build_manifest.py output) — feeds the dashboard's
                # Verify stage (certificate browser). Read fresh from disk on every call.
                p = os.path.join(_HERE, "manifest.json")
                if not os.path.isfile(p):
                    return self._send(404, json.dumps(
                        {"error": "no manifest.json — run `chiron build` first"}))
                return self._send(200, open(p, "rb").read())
            if self.path == "/api/assistant/ledger":
                import run_ledger
                return self._send(200, json.dumps({"records": run_ledger.read(40)}))
            if self.path == "/api/assistant/vault":
                out = {"certificate": None, "heart": None}
                vc = os.path.join(_HERE, "artifacts", "vault", "latest.json")
                if os.path.isfile(vc):
                    try:
                        out["certificate"] = json.load(open(vc, encoding="utf-8"))
                    except Exception:
                        pass
                hs = os.path.join(_HERE, "artifacts", "heart_state.json")
                if os.path.isfile(hs):
                    try:
                        out["heart"] = json.load(open(hs, encoding="utf-8"))
                    except Exception:
                        pass
                return self._send(200, json.dumps(out))
            if self.path == "/api/assistant/artifacts":
                # Every engine's latest signed certificate from the artifact ledger.
                out = {}
                arts = os.path.join(_HERE, "artifacts")
                if os.path.isdir(arts):
                    for d in sorted(os.listdir(arts)):
                        latest = os.path.join(arts, d, "latest.json")
                        if os.path.isfile(latest):
                            try:
                                out[d] = json.load(open(latest, encoding="utf-8"))
                            except Exception as e:
                                out[d] = {"error": str(e)}
                return self._send(200, json.dumps(out))
            self._send(404, json.dumps({"error": "not found"}))

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0) or 0)
            body = json.loads(self.rfile.read(n) or b"{}") if n else {}
            if self.path == "/api/assistant/chat":
                return self._send(200, json.dumps(chat(body.get("message", ""), body.get("history", []))))
            if self.path == "/api/assistant/beat":
                # One beat of the heart, on demand from the Pulse stage. The beat
                # obeys every gate the autonomous loop obeys — this only changes WHEN.
                try:
                    import heartbeat
                    cert = heartbeat.beat_once(quiet=True)
                    return self._send(200, json.dumps({"ok": True, "certificate": cert}))
                except Exception as e:
                    return self._send(500, json.dumps({"ok": False, "error": str(e)}))
            if self.path == "/api/assistant/key":
                # Set a provider's key for THIS running process only — session-scoped, held in
                # memory, never written to disk or the repo. Restarting the service forgets it;
                # use environment variables for anything you want to persist.
                import llm_providers as llm
                provider = (body.get("provider") or "").strip().lower()
                key = (body.get("key") or "").strip()
                if provider not in llm.REGISTRY:
                    return self._send(400, json.dumps({"error": f"unknown provider: {provider}"}))
                env_var = llm.REGISTRY[provider][0][0]
                if key:
                    os.environ[env_var] = key
                    note = f"{provider} key set for this session (in memory only)"
                else:
                    os.environ.pop(env_var, None)
                    note = f"{provider} key cleared"
                avail = [a[0] for a in llm.available()]
                return self._send(200, json.dumps({"ok": True, "note": note,
                                                    "providers": avail, "chain": llm.chain()}))
            self._send(404, json.dumps({"error": "not found"}))

    return http.server.ThreadingHTTPServer(("127.0.0.1", port), H)


def serve(port=8769):
    httpd = make_server(port)
    cfg = pg.LLMConfig.from_env()
    print(f"assistant on http://127.0.0.1:{port}/chat  (enabled={cfg.enabled} provider={cfg.provider})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    keyed = pg.LLMConfig(provider="gemini", api_key="TEST", model="gemini-3.5-flash",
                         base_url=pg.DEFAULTS["gemini"][0])

    # 1. disabled without a key
    ok("disabled without a key", chat("hi", cfg=pg.LLMConfig(provider="gemini", api_key=""))["enabled"] is False)

    # 2. intent -> collapse action runs the REAL engine
    plan = json.dumps({"action": "collapse", "args": {"surface": "1 1 2 3 5 8 13"},
                       "say": "Recovering the rule…"})
    r = chat("what's the rule behind 1 1 2 3 5 8 13?", cfg=keyed, transport=pg._mock_gemini(plan))
    ok("routes to collapse and runs the engine", r["action"] == "collapse" and r["result"]["verified"] is True)
    ok("collapse forecasts the continuation", r["result"].get("predict_next", [])[:3] == [21, 34, 55])

    # 3. intent -> congress summary (real read)
    r2 = chat("how big is the memory?", cfg=keyed,
              transport=pg._mock_gemini(json.dumps({"action": "congress", "args": {}, "say": "Here it is."})))
    ok("routes to congress summary", r2["action"] == "congress" and isinstance(r2["result"], dict))

    # 4. The model cannot turn Chat into a generic command or mutation surface.
    r3 = chat("run this arbitrary script", cfg=keyed,
              transport=pg._mock_gemini(json.dumps({"action": "run",
                                                    "args": {"module": "arbitrary_script", "argv": ["now"]},
                                                    "say": "Running it."})))
    ok("model-directed arbitrary script is escalated, never executed",
       "run" not in ACTIONS and r3["policy"] == "escalated"
       and r3["result"]["status"] == "escalated")

    r_grow = chat("grow from this file", cfg=keyed,
                  transport=pg._mock_gemini(json.dumps({"action": "grow",
                                                        "args": {"target": "/tmp/never-run"},
                                                        "say": "Growing it."})))
    ok("model-directed growth is escalated, never invoked",
       r_grow["policy"] == "escalated" and r_grow["result"]["action"] == "grow")

    r_unknown = chat("do a novel tool action", cfg=keyed,
                     transport=pg._mock_gemini(json.dumps({"action": "arbitrary_script",
                                                           "args": {}, "say": "Done."})))
    ok("unknown model action is refused, never interpreted", r_unknown["policy"] == "refused")

    # 5. plain answer needs no action
    r4 = chat("what are you?", cfg=keyed,
              transport=pg._mock_gemini(json.dumps({"action": "answer", "args": {},
                                                    "say": "I'm the Chiron assistant."})))
    ok("plain answer returns no engine result", r4["action"] == "answer" and r4["result"] is None)

    # 6. the LLM can never be the source of a fact — results come from code
    ok("collapse result is the engine's, not the model's text",
       isinstance(r["result"], dict) and "model_class" in r["result"])

    passed = sum(1 for _, c in checks if c)
    print("assistant_server self-test")
    for n, c in checks:
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"  {passed}/{len(checks)} checks")
    return passed == len(checks)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Natural-language assistant over the Chiron engine.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("selftest")
    sv = sub.add_parser("serve"); sv.add_argument("--port", type=int, default=8769)
    args = ap.parse_args(argv)
    if args.cmd == "serve":
        serve(args.port); return 0
    return 0 if _selftest() else 1


if __name__ == "__main__":
    sys.exit(main())
