#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
president_grow.py — the LLM-assisted grow function, fully compartmentalized.

This is the ONE deliberately non-deterministic, network-capable component, quarantined in its own
module and its own server process so the deterministic core (chiron.py) stays pure and offline.
It implements the only safe way to let a probabilistic model touch an exact engine:

        the LLM PROPOSES        ->        Chiron DISPOSES
        (brainstorms candidates)          (exact MDL + held-out verification)

A free LLM suggests candidate structures; every candidate is then run through chiron.collapse and is
KEPT only if it is verified by exact prediction of held-out terms. An LLM hallucination is therefore
structurally incapable of becoming a "grown" fact — the zero-false-positive discipline is preserved
with a model in the loop. Concept proposals that are not exactly verifiable are escalated to a human,
never auto-applied (the President "escalates anything irreversible to a human").

Best free LLM API (June 2026): Google Gemini / AI Studio — 1,500 requests/day on Gemini Flash, no
credit card, no expiry. The client is provider-pluggable: Groq, OpenRouter, Cerebras, or any
OpenAI-compatible endpoint work by setting GROW_LLM_PROVIDER=openai + GROW_LLM_BASE_URL + model.
The API key lives ONLY in the server environment, never in the dashboard.

    Enable (free):
      1) get a key at https://aistudio.google.com/apikey
      2) export GROW_LLM_API_KEY=...        # Gemini by default
      3) python3 president_grow.py serve    # http://127.0.0.1:8766/grow

    python3 president_grow.py selftest       # offline, mock LLM — proves the propose/verify gate
    python3 president_grow.py status         # show provider/model/enabled
    python3 president_grow.py cycle          # one grow cycle (live if a key is set)

Status: implemented & tested offline (mock transport). Live generation requires a user-supplied
free key. Proof of Concept for the concept-escalation mode; the sequence-verification gate is exact.
"""
from __future__ import annotations
import os
import re
import ssl
import sys
import json
import argparse
import urllib.request
from dataclasses import dataclass

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

DEFAULTS = {
    "gemini": ("https://generativelanguage.googleapis.com", "gemini-3.5-flash"),
    "openai": ("https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),  # Groq is OpenAI-compatible
}


# =====================================================================
# 1. PROVIDER-PLUGGABLE LLM CLIENT  (key is read from the environment only)
# =====================================================================
@dataclass
class LLMConfig:
    provider: str = "gemini"
    api_key: str = ""
    model: str = ""
    base_url: str = ""

    @classmethod
    def from_env(cls) -> "LLMConfig":
        provider = os.environ.get("GROW_LLM_PROVIDER", "gemini").strip().lower()
        if provider not in DEFAULTS:
            provider = "openai"  # treat any unknown provider as OpenAI-compatible
        base, model = DEFAULTS[provider]
        return cls(
            provider=provider,
            api_key=os.environ.get("GROW_LLM_API_KEY", "").strip(),
            model=os.environ.get("GROW_LLM_MODEL", "").strip() or model,
            base_url=os.environ.get("GROW_LLM_BASE_URL", "").strip() or base,
        )

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)


def _default_transport(url, headers, body):
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
        return r.status, r.read().decode("utf-8")


def llm_generate(prompt, cfg: LLMConfig, transport=None) -> str:
    """One text completion. `transport(url, headers, body)->(status,text)` is injectable so the
    whole pipeline is testable offline with a mock (no network, no key)."""
    transport = transport or _default_transport
    if cfg.provider == "gemini":
        url = f"{cfg.base_url}/v1beta/models/{cfg.model}:generateContent"
        headers = {"Content-Type": "application/json", "x-goog-api-key": cfg.api_key}
        body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
        status, text = transport(url, headers, body)
        if status != 200:
            raise RuntimeError(f"gemini HTTP {status}: {text[:200]}")
        data = json.loads(text)
        return data["candidates"][0]["content"]["parts"][0]["text"]
    # OpenAI-compatible (Groq / OpenRouter / Cerebras / NVIDIA NIM / ...)
    url = f"{cfg.base_url}/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {cfg.api_key}"}
    body = json.dumps({"model": cfg.model,
                       "messages": [{"role": "user", "content": prompt}]}).encode("utf-8")
    status, text = transport(url, headers, body)
    if status != 200:
        raise RuntimeError(f"openai-compatible HTTP {status}: {text[:200]}")
    data = json.loads(text)
    return data["choices"][0]["message"]["content"]


# =====================================================================
# 2. PROPOSE  ->  VERIFY  ->  GROW   (LLM proposes, Chiron disposes)
# =====================================================================
DEFAULT_SEEDS = [
    "arithmetic: 2 4 6 8 10 12",
    "geometric: 1 2 4 8 16 32",
    "linear recurrence (Fibonacci): 1 1 2 3 5 8 13",
    "polynomial (squares): 1 4 9 16 25 36",
]

SEQ_PROMPT = (
    "You are a proposal generator feeding an EXACT integer-sequence recovery engine that will "
    "verify every sequence you give it and discard any it cannot recover by exact prediction.\n"
    "Known verified laws:\n{seeds}\n\n"
    "Propose {n} NEW integer sequences (8 to 12 terms each) that follow a simple EXACT rule "
    "(arithmetic, geometric, polynomial, or linear recurrence). Be diverse.\n"
    "Output ONLY the sequences, one per line, integers separated by single spaces. "
    "No prose, no labels, no numbering."
)

CONCEPT_PROMPT = (
    "Given these verified knowledge areas:\n{seeds}\n\n"
    "Suggest {n} ADJACENT concepts or domains worth investigating next, one per line, a few words "
    "each. These are research leads for a human to approve — not facts. No numbering, no prose."
)


def parse_sequences(text: str):
    out = []
    for line in text.splitlines():
        nums = re.findall(r"-?\d+", line)
        if len(nums) >= 4:
            out.append([int(x) for x in nums])
    return out


def parse_lines(text: str, limit=12):
    out = []
    for line in text.splitlines():
        s = re.sub(r"^[\s\-\*\d\.\)]+", "", line).strip()
        if s:
            out.append(s)
    return out[:limit]


def verify_surface(surface):
    """The gate: run a proposed integer sequence through the real engine. Accept iff verified."""
    import chiron
    return chiron.collapse(list(surface))


def grow_cycle(cfg: LLMConfig, transport=None, n=6, seeds=None):
    """One LLM-assisted grow cycle. Returns accepted (exactly verified) vs rejected (refused)."""
    seeds = seeds or DEFAULT_SEEDS
    if not cfg.enabled and transport is None:
        return {"enabled": False, "accepted": [], "rejected": [], "n_proposed": 0,
                "note": "LLM disabled — set GROW_LLM_API_KEY (free Gemini key at "
                        "https://aistudio.google.com/apikey) and restart the grow service."}
    seed_text = "\n".join(seeds)
    raw = llm_generate(SEQ_PROMPT.format(seeds=seed_text, n=n), cfg, transport)
    proposals = parse_sequences(raw)
    accepted, rejected = [], []
    for surf in proposals:
        inv = verify_surface(surf)
        if inv.verified:
            nxt = inv.predict(len(surf) + 3)
            accepted.append({
                "surface": surf,
                "model_class": inv.model_class,
                "explanation": inv.explanation,
                "predict_next": [int(x) for x in nxt[len(surf):]],
                "generator_fingerprint": inv.generator_fingerprint,
            })
        else:
            rejected.append({"surface": surf,
                             "reason": f"refused ({inv.model_class}) — no held-out-exact rule"})
    return {"enabled": True, "accepted": accepted, "rejected": rejected,
            "n_proposed": len(proposals), "n_accepted": len(accepted),
            "discipline": "LLM proposed; Chiron verified; only exactly-recovered sequences kept"}


def propose_concepts(cfg: LLMConfig, transport=None, n=6, seeds=None):
    """Concept leads for HUMAN approval (not auto-grown — not exactly verifiable)."""
    seeds = seeds or DEFAULT_SEEDS
    if not cfg.enabled and transport is None:
        return {"enabled": False, "leads": [], "note": "LLM disabled — set GROW_LLM_API_KEY."}
    raw = llm_generate(CONCEPT_PROMPT.format(seeds="\n".join(seeds), n=n), cfg, transport)
    return {"enabled": True, "leads": parse_lines(raw, n),
            "escalation": "research leads only — require human approval before anything is grown"}


def status(cfg: LLMConfig) -> dict:
    return {"enabled": cfg.enabled, "provider": cfg.provider, "model": cfg.model,
            "base_url": cfg.base_url, "key_present": bool(cfg.api_key),
            "discipline": "LLM proposes, Chiron verifies; nothing enters unverified",
            "enable_hint": "export GROW_LLM_API_KEY=...  (free Gemini key: "
                           "https://aistudio.google.com/apikey)"}


# =====================================================================
# 3. COMPARTMENTALIZED SERVER  (own port; CORS so the dashboard can call it)
# =====================================================================
def _panel_html() -> str:
    return """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Grow — President</title>
<style>
:root{color-scheme:dark}body{margin:0;font:14px system-ui;background:#0b0f17;color:#e6edf6;padding:18px}
.warn{border:1px solid #b9892f;background:#211a0d;color:#f0d79a;border-radius:10px;padding:10px 12px;margin-bottom:14px}
.card{border:1px solid #1e2a3b;background:#0f1622;border-radius:12px;padding:14px;margin:10px 0}
h2{margin:.2em 0;font-size:16px}.muted{color:#8a98ad}button{background:#1d6feb;color:#fff;border:0;border-radius:8px;padding:9px 14px;font-weight:600;cursor:pointer}
.ok{color:#5bd17b}.no{color:#e0796f}.seq{font-family:ui-monospace,Menlo,monospace}
.pill{display:inline-block;border:1px solid #2a3a52;border-radius:999px;padding:1px 8px;font-size:12px;color:#9fb0c6}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.item{border-top:1px solid #16202e;padding:8px 0}
</style></head><body>
<div class="warn"><b>Grow function — compartmentalized.</b> Non-deterministic &middot; sandboxed &middot;
network-gated &middot; LLM-assisted. The LLM only <b>proposes</b>; the deterministic engine
<b>verifies</b>. Nothing enters the Congress without exact held-out verification.</div>
<div class="card"><div class="row"><span class="pill" id="prov">…</span>
<span class="pill" id="enabled">…</span><button onclick="run()">Run grow cycle</button></div>
<p class="muted" id="hint"></p></div>
<div class="card"><h2 class="ok">Accepted <span class="muted">— LLM proposed, Chiron verified</span></h2>
<div id="acc" class="muted">—</div></div>
<div class="card"><h2 class="no">Rejected <span class="muted">— refused by the gate (hallucination-safe)</span></h2>
<div id="rej" class="muted">—</div></div>
<script>
const B="";
async function j(p,m,b){const o=m==="POST"?{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(b||{})}:{};const r=await fetch(B+p,o);return r.json();}
async function load(){try{const s=await j("/api/grow/status");document.getElementById("prov").textContent=s.provider+" · "+s.model;document.getElementById("enabled").textContent=s.enabled?"ENABLED":"disabled (no key)";document.getElementById("enabled").className="pill "+(s.enabled?"ok":"no");document.getElementById("hint").textContent=s.enabled?"":s.enable_hint;}catch(e){document.getElementById("prov").textContent="grow service offline";}}
async function run(){document.getElementById("acc").textContent="proposing + verifying…";document.getElementById("rej").textContent="";try{const r=await j("/api/grow/cycle","POST",{});if(!r.enabled){document.getElementById("acc").innerHTML='<span class=no>'+(r.note||"disabled")+'</span>';return;}
document.getElementById("acc").innerHTML=r.accepted.length?r.accepted.map(a=>`<div class=item><span class=seq>${a.surface.join(" ")}</span> <span class=pill>${a.model_class}</span><br><span class=muted>→ next: ${a.predict_next.join(", ")}</span></div>`).join(""):"<span class=muted>none verified this cycle</span>";
document.getElementById("rej").innerHTML=r.rejected.length?r.rejected.map(a=>`<div class=item><span class=seq>${a.surface.join(" ")}</span><br><span class=muted>${a.reason}</span></div>`).join(""):"<span class=muted>none</span>";}catch(e){document.getElementById("acc").innerHTML='<span class=no>error: '+e.message+'</span>';}}
load();
</script></body></html>"""


def serve(port=8766):
    import http.server
    cfg_holder = {"cfg": LLMConfig.from_env()}

    class H(http.server.BaseHTTPRequestHandler):
        def _send(self, code, body, ctype="application/json"):
            data = body.encode("utf-8") if isinstance(body, str) else body
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
            if self.path in ("/", "/grow", "/index.html"):
                return self._send(200, _panel_html(), "text/html; charset=utf-8")
            if self.path == "/api/grow/status":
                return self._send(200, json.dumps(status(cfg_holder["cfg"])))
            self._send(404, json.dumps({"error": "not found"}))

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0) or 0)
            try:
                payload = json.loads(self.rfile.read(n) or b"{}") if n else {}
            except Exception:
                payload = {}
            if self.path == "/api/grow/cycle":
                out = grow_cycle(cfg_holder["cfg"], n=int(payload.get("n", 6)))
                return self._send(200, json.dumps(out))
            if self.path == "/api/grow/concepts":
                return self._send(200, json.dumps(propose_concepts(cfg_holder["cfg"],
                                                                    n=int(payload.get("n", 6)))))
            self._send(404, json.dumps({"error": "not found"}))

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), H)
    cfg = cfg_holder["cfg"]
    print(f"grow service on http://127.0.0.1:{port}/grow  "
          f"(provider={cfg.provider} model={cfg.model} enabled={cfg.enabled})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


# =====================================================================
# 4. SELF-TEST  (offline; mock transport; proves the propose/verify gate)
# =====================================================================
def _mock_gemini(reply):
    def t(url, headers, body):
        assert "generativelanguage" in url and "generateContent" in url, url
        assert headers.get("x-goog-api-key"), "missing gemini key header"
        return 200, json.dumps({"candidates": [{"content": {"parts": [{"text": reply}]}}]})
    return t


def _mock_openai(reply):
    def t(url, headers, body):
        assert url.endswith("/chat/completions"), url
        assert headers.get("Authorization", "").startswith("Bearer "), "missing bearer"
        return 200, json.dumps({"choices": [{"message": {"content": reply}}]})
    return t


def _selftest() -> bool:
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    # G1 disabled without a key
    cfg_none = LLMConfig(provider="gemini", api_key="")
    ok("disabled without an API key", not cfg_none.enabled and not grow_cycle(cfg_none)["enabled"])

    # G2 gemini request shape + parse
    cfg_g = LLMConfig(provider="gemini", api_key="TEST", model="gemini-3.5-flash",
                      base_url=DEFAULTS["gemini"][0])
    ok("gemini request shape + response parse",
       llm_generate("hi", cfg_g, _mock_gemini("hello")) == "hello")

    # G3 openai-compatible request shape + parse
    cfg_o = LLMConfig(provider="openai", api_key="TEST", model="llama-3.3-70b-versatile",
                      base_url=DEFAULTS["openai"][0])
    ok("openai-compatible request shape + response parse",
       llm_generate("hi", cfg_o, _mock_openai("hello")) == "hello")

    # G4 parse multi-line sequences
    seqs = parse_sequences("2 4 6 8 10 12\nnot a seq\n3 6 9 12 15 18")
    ok("parses sequences, ignores prose", len(seqs) == 2 and seqs[0] == [2, 4, 6, 8, 10, 12])

    # G5 a structured proposal is ACCEPTED (real chiron verification)
    acc = verify_surface([2, 4, 6, 8, 10, 12]).verified
    ok("structured proposal verified (accepted)", acc)

    # G6 a hallucinated proposal is REJECTED
    rej = not verify_surface([3, 1, 4, 1, 5, 9, 2, 6]).verified
    ok("hallucinated proposal refused (rejected)", rej)

    # G7 HEADLINE: LLM in the loop, zero false positives preserved
    mock = _mock_gemini("2 4 6 8 10 12 14\n3 1 4 1 5 9 2 6 5 3\n5 10 15 20 25 30")
    cyc = grow_cycle(cfg_g, transport=mock, n=3)
    ok("grow cycle keeps only verified (1+ accepted, hallucination rejected)",
       cyc["n_accepted"] >= 2 and any("refused" in r["reason"] for r in cyc["rejected"]))
    ok("every accepted item is exactly verified",
       all(verify_surface(a["surface"]).verified for a in cyc["accepted"]))

    # G8 status shape
    st = status(cfg_g)
    ok("status reports provider/model/enabled", st["provider"] == "gemini" and st["enabled"])

    passed = sum(1 for _, c in checks if c)
    for n_, c in checks:
        if not c:
            print(f"  FAIL: {n_}")
    print(f"  president_grow.py self-test: {passed}/{len(checks)} passed")
    return passed == len(checks)


def main(argv=None):
    ap = argparse.ArgumentParser(description="LLM-assisted grow function (propose -> verify).")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("selftest")
    sub.add_parser("status")
    cy = sub.add_parser("cycle"); cy.add_argument("-n", type=int, default=6)
    sv = sub.add_parser("serve"); sv.add_argument("--port", type=int, default=8766)
    args = ap.parse_args(argv)

    if args.cmd == "selftest" or args.cmd is None:
        return 0 if _selftest() else 1
    if args.cmd == "status":
        print(json.dumps(status(LLMConfig.from_env()), indent=2)); return 0
    if args.cmd == "cycle":
        print(json.dumps(grow_cycle(LLMConfig.from_env(), n=args.n), indent=2)); return 0
    if args.cmd == "serve":
        serve(args.port); return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
