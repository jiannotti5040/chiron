#!/usr/bin/env python3
"""
assistant_server.py — a natural-language assistant over the Chiron engine and the Congress.

Tell it what you want in plain language; it figures out the intent, runs the REAL deterministic
functions (recover a rule, speak it back, search or summarize the Congress, run any engine), and
replies. The discipline is the portfolio's: the LLM *directs*, the engine *does the work* — every
factual result comes from exact, verifiable code, not from the model. The LLM is the front door,
never the source of truth.

It reuses the free-LLM client from president_grow (Gemini by default; Groq/OpenRouter via env), so
it needs a free key (GROW_LLM_API_KEY). Without a key it says so and stays out of the way.

    # get a free key at https://aistudio.google.com/apikey
    export GROW_LLM_API_KEY=your_key
    python3 assistant_server.py serve      # chat at http://127.0.0.1:8769/chat ; also the console's Chat tab
    python3 assistant_server.py selftest   # offline (mock LLM, real engine)

Status: implemented & tested offline (mock LLM + real engine actions).
"""
import os
import re
import sys
import json
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import president_grow as pg          # noqa: E402  the free-LLM client
import console_server as cs          # noqa: E402  the allowlisted function runner

CONGRESS = os.path.join(_HERE, "chiron_memory.json")


# ---------------------------------------------------------------------
# actions — each runs real engine/Congress code; the LLM only chooses one
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


def act_run(args):
    module = args.get("module", "")
    argv = args.get("argv", [])
    if isinstance(argv, str):
        argv = argv.split()
    return cs.run(module, argv, args.get("args", ""))


def act_answer(args):
    return None


ACTIONS = {"collapse": act_collapse, "congress": act_congress, "search": act_search,
           "run": act_run, "answer": act_answer}

SYSTEM = """You are the assistant for Chiron, a deterministic invariant-recovery engine with a
memory called the Congress. Decide what the user wants and reply with ONE JSON object only:
{"action": <one of collapse|articulate|congress|search|run|answer>, "args": {...}, "say": <a short
natural-language reply to the user>}.
- collapse: recover + verify the rule behind a sequence/string. args: {"surface": "1 1 2 3 5 8"}.
  (Use this for "what's the rule", "speak it back", "predict the next terms".)
- congress: summarize the Congress (domains, laws, size). args: {}.
- search: find something in the Congress. args: {"term": "fibonacci"}.
- run: run a named engine function. args: {"module": "bench_suite", "argv": [], "args": ""} or
  {"module":"semic","argv":["selftest"]}. Allowed modules are the engine files (chiron, semic,
  epistemic, bench_*, govern, build, ...).
- answer: just answer in words (capabilities, explanations). args: {}.
Always include a friendly "say". Output the JSON and nothing else."""


def _extract_json(text):
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return {"action": "answer", "args": {}, "say": text.strip()[:500]}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {"action": "answer", "args": {}, "say": text.strip()[:500]}


def chat(message, history=None, cfg=None, transport=None):
    cfg = cfg or pg.LLMConfig.from_env()
    if not cfg.enabled and transport is None:
        return {"enabled": False,
                "reply": "The assistant needs a free LLM key. Get one at "
                         "https://aistudio.google.com/apikey, then `export GROW_LLM_API_KEY=...` and "
                         "restart `assistant_server.py`. (The Run tab works without a key.)",
                "action": None, "result": None}
    convo = ""
    for turn in (history or [])[-6:]:
        convo += f"\n{turn.get('role', 'user')}: {turn.get('content', '')}"
    prompt = f"{SYSTEM}\n\nConversation so far:{convo}\n\nuser: {message}\n\nJSON:"
    plan = _extract_json(pg.llm_generate(prompt, cfg, transport))
    action = (plan.get("action") or "answer").strip()
    args = plan.get("args") or {}
    say = plan.get("say") or ""
    result = None
    if action in ACTIONS and action != "answer":
        try:
            result = ACTIONS[action](args)
        except Exception as e:
            result = {"error": str(e)}
    return {"enabled": True, "reply": say, "action": action, "args": args, "result": result}


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


def serve(port=8769):
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
            if self.path in ("/", "/chat"):
                return self._send(200, _panel(), "text/html; charset=utf-8")
            if self.path == "/api/assistant/status":
                cfg = pg.LLMConfig.from_env()
                return self._send(200, json.dumps({"enabled": cfg.enabled, "provider": cfg.provider,
                                                    "model": cfg.model}))
            self._send(404, json.dumps({"error": "not found"}))

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0) or 0)
            body = json.loads(self.rfile.read(n) or b"{}") if n else {}
            if self.path == "/api/assistant/chat":
                return self._send(200, json.dumps(chat(body.get("message", ""), body.get("history", []))))
            self._send(404, json.dumps({"error": "not found"}))

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), H)
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

    # 4. intent -> run an allowlisted function
    r3 = chat("run the semic gates", cfg=keyed,
              transport=pg._mock_gemini(json.dumps({"action": "run",
                                                    "args": {"module": "legal_corpus", "argv": ["selftest"]},
                                                    "say": "Running it."})))
    ok("routes to run and executes a real module", r3["action"] == "run" and r3["result"]["ok"] is True)

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
