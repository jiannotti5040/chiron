#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
llm_providers.py — one multi-provider LLM client with a fallback chain.

The discipline is unchanged: the model only PROPOSES; chiron's exact engine DISPOSES. This module
just lets the proposer be any of several providers, tried in order until one answers — each keyed
from its OWN environment variable. No key ever lives in the repo; the code only reads the env.

  provider     key env var (first set wins)                    what it unlocks
  --------     ----------------------------                    ---------------
  gemini       GEMINI_API_KEY | GOOGLE_API_KEY | GROW_LLM_API_KEY   Google Gemini (free tier)
  openrouter   OPENROUTER_API_KEY                                   OpenRouter (Llama, Qwen, GPT, …)
  groq         GROQ_API_KEY                                         Groq (free, fast Llama)
  openai       OPENAI_API_KEY                                       OpenAI
  anthropic    ANTHROPIC_API_KEY                                    Anthropic Claude
  perplexity   PERPLEXITY_API_KEY                                   Perplexity (online models)
  cerebras     CEREBRAS_API_KEY                                     Cerebras
  llama, qwen  OPENROUTER_API_KEY                                   named OpenRouter models

Chain order (override with CHIRON_LLM_CHAIN="gemini,openrouter,groq"):
  gemini, openrouter, groq, openai, anthropic, perplexity

    python3 llm_providers.py check            # which providers have a key (add --live to ping each)
    python3 llm_providers.py ask "..."        # run the chain, print which provider answered
    python3 llm_providers.py providers        # the registry
    python3 llm_providers.py selftest         # offline (mock transport, no key, no network)

Status: implemented & tested (offline, mock transport). Live calls happen only on your machine.
"""
import os
import sys
import json
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import president_grow as pg  # noqa: E402  reuse its LLMConfig + llm_generate (gemini + openai styles)

# name -> (env-var candidates, base_url, default_model, api_style)
REGISTRY = {
    "gemini":     (("GEMINI_API_KEY", "GOOGLE_API_KEY", "GROW_LLM_API_KEY"),
                   "https://generativelanguage.googleapis.com", "gemini-3.5-flash", "gemini"),
    "openrouter": (("OPENROUTER_API_KEY",),
                   "https://openrouter.ai/api/v1", "meta-llama/llama-3.3-70b-instruct", "openai"),
    "llama":      (("OPENROUTER_API_KEY",),
                   "https://openrouter.ai/api/v1", "meta-llama/llama-3.3-70b-instruct", "openai"),
    "qwen":       (("OPENROUTER_API_KEY",),
                   "https://openrouter.ai/api/v1", "qwen/qwen-2.5-72b-instruct", "openai"),
    "groq":       (("GROQ_API_KEY",),
                   "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile", "openai"),
    "openai":     (("OPENAI_API_KEY",),
                   "https://api.openai.com/v1", "gpt-4o-mini", "openai"),
    "anthropic":  (("ANTHROPIC_API_KEY",),
                   "https://api.anthropic.com", "claude-3-5-haiku-latest", "anthropic"),
    "perplexity": (("PERPLEXITY_API_KEY",),
                   "https://api.perplexity.ai", "llama-3.1-sonar-large-128k-online", "openai"),
    "cerebras":   (("CEREBRAS_API_KEY",),
                   "https://api.cerebras.ai/v1", "llama-3.3-70b", "openai"),
}

DEFAULT_CHAIN = ["gemini", "openrouter", "groq", "openai", "anthropic", "perplexity"]


# ---------------------------------------------------------------------
# keys + chain (read only from the environment)
# ---------------------------------------------------------------------
def _key_for(env_vars):
    for e in env_vars:
        v = os.environ.get(e, "").strip()
        if v:
            return v, e
    return "", None


def _model_for(name):
    base_model = REGISTRY[name][2]
    return os.environ.get("CHIRON_LLM_MODEL_" + name.upper(), "").strip() or base_model


def chain():
    raw = os.environ.get("CHIRON_LLM_CHAIN", "").strip()
    names = ([s.strip().lower() for s in raw.split(",") if s.strip()]
             if raw else list(DEFAULT_CHAIN))
    return [n for n in names if n in REGISTRY]


def available():
    """[(name, env_var_used, model)] for every provider that currently has a key."""
    out = []
    for name, (envs, _base, _model, _style) in REGISTRY.items():
        key, src = _key_for(envs)
        if key:
            out.append((name, src, _model_for(name)))
    return out


# ---------------------------------------------------------------------
# one call to one provider
# ---------------------------------------------------------------------
def _anthropic_generate(prompt, base, key, model, transport):
    transport = transport or pg._default_transport
    url = base + "/v1/messages"
    headers = {"content-type": "application/json", "x-api-key": key,
               "anthropic-version": "2023-06-01"}
    body = json.dumps({"model": model, "max_tokens": 1024,
                       "messages": [{"role": "user", "content": prompt}]}).encode("utf-8")
    status, text = transport(url, headers, body)
    if status != 200:
        raise RuntimeError(f"anthropic HTTP {status}: {text[:200]}")
    return json.loads(text)["content"][0]["text"]


def call_one(name, prompt, transport=None):
    """Call a single named provider. Raises on no-key or HTTP error."""
    if name not in REGISTRY:
        raise RuntimeError(f"unknown provider: {name}")
    envs, base, _model, style = REGISTRY[name]
    key, _src = _key_for(envs)
    if not key:
        raise RuntimeError(f"{name}: no key (set {envs[0]})")
    model = _model_for(name)
    if style == "gemini":
        cfg = pg.LLMConfig(provider="gemini", api_key=key, model=model, base_url=base)
        return pg.llm_generate(prompt, cfg, transport)
    if style == "anthropic":
        return _anthropic_generate(prompt, base, key, model, transport)
    cfg = pg.LLMConfig(provider="openai", api_key=key, model=model, base_url=base)
    return pg.llm_generate(prompt, cfg, transport)


# ---------------------------------------------------------------------
# the chain (fallback) and the fan-out (use them together)
# ---------------------------------------------------------------------
def generate(prompt, chain_names=None, transport=None):
    """Try providers in order; return the first non-empty answer. Result is a dict with the
    answering provider so the caller knows who spoke."""
    names = chain_names or chain()
    tried, errors = [], []
    for name in names:
        key, _ = _key_for(REGISTRY[name][0])
        if not key:
            continue
        tried.append(name)
        try:
            text = call_one(name, prompt, transport)
            if text and text.strip():
                return {"text": text, "provider": name, "model": _model_for(name),
                        "tried": tried, "errors": errors}
        except Exception as e:  # noqa: BLE001 — a failed provider must not stop the chain
            errors.append(f"{name}: {e}")
    return {"text": "", "provider": None, "tried": tried, "errors": errors,
            "note": "no provider answered — set at least one key (run `check`)"}


def propose_all(prompt, transport=None):
    """Fan out to EVERY keyed provider at once — the natural 'use them all together' mode: many
    proposers, then chiron's exact engine verifies each proposal. Returns one row per provider."""
    rows = []
    for name, _src, model in available():
        try:
            rows.append({"provider": name, "model": model,
                         "text": call_one(name, prompt, transport)})
        except Exception as e:  # noqa: BLE001
            rows.append({"provider": name, "model": model, "error": str(e)})
    return rows


def enabled():
    return len(available()) > 0


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------
def _cmd_check(live):
    rows = []
    for name, (envs, base, _model, style) in REGISTRY.items():
        key, src = _key_for(envs)
        status = "—"
        if key and live:
            try:
                call_one(name, "Reply with the single word: ok", None)
                status = "live OK"
            except Exception as e:  # noqa: BLE001
                status = "live FAIL: " + str(e)[:60]
        rows.append((name, "yes" if key else "no", src or envs[0], _model_for(name), status))
    print("provider     key   via                       model                              "
          + ("ping" if live else ""))
    for name, has, src, model, status in rows:
        print("  %-10s %-4s %-24s %-34s %s" % (name, has, src, model[:34], status))
    n = len(available())
    print(f"\n{n} provider(s) keyed. Chain: {', '.join(chain())}")
    return 0 if n else 1


def _cmd_ask(prompt):
    r = generate(prompt)
    if not r["text"]:
        print("no provider answered.")
        if r.get("errors"):
            print("  " + "\n  ".join(r["errors"]))
        print("  set a key, e.g.  export OPENROUTER_API_KEY=...   (then `check`)")
        return 1
    print(f"[{r['provider']} · {r['model']}]\n{r['text']}")
    return 0


def _cmd_providers():
    for name, (envs, base, model, style) in REGISTRY.items():
        print("  %-10s style=%-9s key=%-18s model=%s" % (name, style, envs[0], model))
    return 0


def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    GEM = json.dumps({"candidates": [{"content": {"parts": [{"text": "GEMINI-SAYS"}]}}]})
    OAI = json.dumps({"choices": [{"message": {"content": "OPENAI-SAYS"}}]})
    ANT = json.dumps({"content": [{"text": "ANTHROPIC-SAYS"}]})

    def mock(url, headers, body):
        if "generateContent" in url:
            return 200, GEM
        if "/v1/messages" in url:
            return 200, ANT
        if "/chat/completions" in url:
            return 200, OAI
        return 404, "no route"

    def mock_fail_gemini(url, headers, body):
        if "generateContent" in url:
            return 500, "gemini down"
        return mock(url, headers, body)

    saved = {k: os.environ.get(k) for k in
             ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GROW_LLM_API_KEY", "OPENROUTER_API_KEY",
              "GROQ_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "PERPLEXITY_API_KEY",
              "CEREBRAS_API_KEY", "CHIRON_LLM_CHAIN")}
    for k in saved:
        os.environ.pop(k, None)
    try:
        # 1. no keys -> no provider
        ok("no keys -> disabled", not enabled() and generate("hi", transport=mock)["provider"] is None)

        # 2. only openrouter keyed -> chain answers via openrouter (openai style)
        os.environ["OPENROUTER_API_KEY"] = "k"
        r = generate("hi", transport=mock)
        ok("single keyed provider answers", r["provider"] == "openrouter" and r["text"] == "OPENAI-SAYS")

        # 3. gemini preferred when both keyed
        os.environ["GEMINI_API_KEY"] = "k"
        r = generate("hi", transport=mock)
        ok("gemini wins the default chain", r["provider"] == "gemini" and r["text"] == "GEMINI-SAYS")

        # 4. gemini fails -> falls back to the next keyed provider
        r = generate("hi", transport=mock_fail_gemini)
        ok("falls back past a failing provider", r["provider"] == "openrouter" and "openrouter" in r["tried"])
        ok("failure recorded honestly", any("gemini" in e for e in r["errors"]))

        # 5. anthropic style parses its own shape
        os.environ["ANTHROPIC_API_KEY"] = "k"
        ok("anthropic shape parsed", call_one("anthropic", "hi", mock) == "ANTHROPIC-SAYS")

        # 6. chain override is honored
        os.environ["CHIRON_LLM_CHAIN"] = "anthropic,gemini"
        r = generate("hi", transport=mock)
        ok("CHIRON_LLM_CHAIN override respected", r["provider"] == "anthropic")
        os.environ.pop("CHIRON_LLM_CHAIN", None)

        # 7. fan-out reaches every keyed provider
        rows = propose_all("hi", transport=mock)
        provs = {row["provider"] for row in rows}
        ok("propose_all fans out to all keyed", {"gemini", "openrouter", "anthropic"} <= provs)
        ok("propose_all returns text per provider", all(("text" in r or "error" in r) for r in rows))

        # 8. llama/qwen are OpenRouter models, reachable with the OpenRouter key
        ok("llama via openrouter key", call_one("llama", "hi", mock) == "OPENAI-SAYS")
        ok("qwen via openrouter key", call_one("qwen", "hi", mock) == "OPENAI-SAYS")
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    passed = sum(1 for _, c in checks if c)
    print("llm_providers self-test")
    for n, c in checks:
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"  {passed}/{len(checks)} checks")
    return passed == len(checks)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Multi-provider LLM client with a fallback chain.")
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("check", help="which providers have a key")
    c.add_argument("--live", action="store_true", help="also ping each keyed provider")
    a = sub.add_parser("ask", help="run the chain on a prompt")
    a.add_argument("text", nargs="*")
    sub.add_parser("providers", help="show the registry")
    sub.add_parser("selftest")
    args = ap.parse_args(argv)
    if args.cmd == "check":
        return _cmd_check(args.live)
    if args.cmd == "ask":
        return _cmd_ask(" ".join(args.text) or "Say hello in one short sentence.")
    if args.cmd == "providers":
        return _cmd_providers()
    return 0 if _selftest() else 1


if __name__ == "__main__":
    sys.exit(main())
