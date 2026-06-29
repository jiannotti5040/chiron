#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
grow_clean.py — one clean growth interface over any source, LLM-aided.

Unifies every way the Congress can grow while keeping the deterministic discipline intact: structure
is recovered and VERIFIED by chiron (exact, held-out) before anything is grown; the LLM only
proposes candidates and steers what to read next — it never writes a fact.

Growth sources
  file <path>        grow from any file or folder (offline, deterministic)
  wikipedia <topic>  the preset general-Wikipedia growth (reuses the existing fetchers)
  ingest <path>      grow from the material AND use that material as the search parameters:
                     derive topics from what you fed it, then fetch and grow from related sources

LLM (optional; free key via president_grow / GROW_LLM_API_KEY)
  derive_topics      extract search topics from ingested material (offline keyword fallback if no key)
  propose            propose candidate structures; chiron verifies; only the verified are grown

    python3 grow_clean.py file ./notes.txt
    python3 grow_clean.py wikipedia "prime numbers"
    python3 grow_clean.py ingest ./paper.txt --llm
    python3 grow_clean.py llm                       # LLM proposes, chiron verifies, grows the verified
    python3 grow_clean.py selftest                 # offline (mock fetchers + mock LLM)

Status: implemented & tested offline. Network growth (wikipedia/ingest-fetch) needs connectivity;
LLM features need a free key. Both degrade gracefully to the deterministic, offline path.
"""
import os
import re
import sys
import json
import argparse
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import chiron                     # noqa: E402  the engine (verifier)
import chiron_grow as cg         # noqa: E402  reuse the existing Wikipedia/web/OEIS fetchers
import president_grow as pg      # noqa: E402  reuse the free-LLM client + propose->verify

WIKI_API = "https://en.wikipedia.org/w/api.php"
UA = "Chiron-GrowClean/1.0 (operator-directed; offline-first)"
DEFAULT_STORE = os.path.join(_HERE, "grow-public", "chiron_memory.json")

_STOP = set(("the a an of to and in is are was were for on with as by from at this that it its their "
             "his her be or not but they you we he she him them then than into over under can will "
             "which who whom whose what when where why how all any each more most other some such no "
             "nor only own same so too very").split())


# ---------------------------------------------------------------------
# topic derivation — "ingested material AS the search parameters"
# ---------------------------------------------------------------------
def keyword_topics(text, n=6):
    """Offline fallback: salient capitalized phrases + frequent content words."""
    caps = re.findall(r"\b([A-Z][a-z]{3,}(?:\s+[A-Z][a-z]{3,})*)\b", text)
    words = [w.lower() for w in re.findall(r"[A-Za-z]{4,}", text) if w.lower() not in _STOP]
    freq = [w for w, _ in Counter(words).most_common(n * 2)]
    out, seen = [], set()
    for t in [c.strip() for c in caps] + freq:
        k = t.lower()
        if k and k not in seen:
            seen.add(k)
            out.append(t)
        if len(out) >= n:
            break
    return out


def llm_topics(text, cfg, transport=None, n=6):
    prompt = ("Extract up to %d concise search topics (2-4 words each) from the material below, one "
              "per line, no numbering, no prose:\n\n%s" % (n, text[:4000]))
    return pg.parse_lines(pg.llm_generate(prompt, cfg, transport), n)


# ---------------------------------------------------------------------
# the clean grower
# ---------------------------------------------------------------------
class GrowClean:
    def __init__(self, store=DEFAULT_STORE):
        self.store = store
        self.org = chiron.Chiron.load_memory(store) if os.path.exists(store) else chiron.Chiron()
        self.cong = None

    def save(self):
        d = os.path.dirname(self.store)
        if d:
            os.makedirs(d, exist_ok=True)
        self.org.save_memory(self.store)
        return self.store

    def grow_text(self, text, source, domain=None):
        if not text or len(text) < 12:
            return None
        res = self.org.assimilate(text, source=source, domain_hint=domain)
        self.cong = res.get("congress", self.cong)
        return res

    def grow_file(self, path):
        if os.path.isfile(path):
            files = [path]
        else:
            files = [os.path.join(r, f) for r, _, fs in os.walk(path) for f in fs]
        grown = []
        for fp in files:
            try:
                txt = open(fp, encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            r = self.grow_text(txt, source="file:" + os.path.basename(fp))
            if r:
                grown.append((os.path.basename(fp), r.get("classification"), r.get("domain")))
        return grown

    def grow_wikipedia(self, topics, per=3, titles_fn=None, fetch=None):
        """Preset Wikipedia growth. titles_fn/fetch are injectable (default = the real fetchers)."""
        titles_fn = titles_fn or (lambda topic: cg.wiki_titles(WIKI_API, topic, per, 0, UA))
        fetch = fetch or (lambda title: cg.wiki_text(WIKI_API, title, UA))
        grown = []
        for topic in topics:
            try:
                titles = titles_fn(topic) or [topic]
            except Exception:
                titles = [topic]
            for t in titles[:per]:
                try:
                    txt = fetch(t)
                except Exception:
                    continue
                r = self.grow_text(txt, source="wikipedia:" + str(t))
                if r:
                    grown.append((str(t), r.get("classification")))
        return grown

    def grow_from_ingestion(self, path_or_text, use_llm=False, transport=None,
                            titles_fn=None, fetch=None, cfg=None):
        """Grow from the material, then use it AS the search parameters to grow from related sources."""
        if os.path.isfile(path_or_text):
            text = open(path_or_text, encoding="utf-8", errors="ignore").read()
            src = "ingest:" + os.path.basename(path_or_text)
        else:
            text, src = path_or_text, "ingest:text"
        first = self.grow_text(text, source=src)
        cfg = cfg or pg.LLMConfig.from_env()
        if use_llm and (cfg.enabled or transport is not None):
            topics = llm_topics(text, cfg, transport)
        else:
            topics = keyword_topics(text)
        related = self.grow_wikipedia(topics, titles_fn=titles_fn, fetch=fetch) if topics else []
        return {"ingested": bool(first), "topics": topics, "related_grown": related}

    def llm_propose_and_grow(self, transport=None, cfg=None):
        """LLM proposes candidate structures; chiron verifies; only the verified are grown."""
        cfg = cfg or pg.LLMConfig.from_env()
        cyc = pg.grow_cycle(cfg, transport=transport)
        grown = []
        for a in cyc.get("accepted", []):
            r = self.grow_text(" ".join(map(str, a["surface"])), source="llm-proposed")
            if r:
                grown.append((a["surface"], r.get("classification")))
        return {"enabled": cyc.get("enabled", False), "proposed": cyc.get("n_proposed", 0),
                "accepted": len(cyc.get("accepted", [])), "grown": grown}


# ---------------------------------------------------------------------
# self-test (offline: mock fetchers + mock LLM; real chiron verification)
# ---------------------------------------------------------------------
def _selftest():
    import tempfile
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    tmp = tempfile.mkdtemp()
    g = GrowClean(store=os.path.join(tmp, "mem.json"))

    fp = os.path.join(tmp, "notes.txt")
    open(fp, "w").write("Field notes from the run: 3 6 9 12 15 18 21 24, then later 2 4 8 16 32 64 128.")
    grown = g.grow_file(fp)
    ok("grows from any file (verified law)", any(c == "integral" for _, c, _ in grown))

    topics = keyword_topics("Prime Numbers and the Riemann Hypothesis anchor Analytic Number Theory.")
    ok("derives search topics from material (offline)", len(topics) >= 2)

    mock_titles = lambda topic: ["Article_" + re.sub(r"\W+", "_", topic)]
    mock_fetch = lambda title: "The page lists the values 5 10 15 20 25 30 35 in a table."
    wg = g.grow_wikipedia(["prime numbers"], titles_fn=mock_titles, fetch=mock_fetch)
    ok("wikipedia preset grows via injected fetchers", len(wg) >= 1)

    ing = g.grow_from_ingestion(
        "Study of Catalan Numbers and Fibonacci Sequences. Sample run: 1 2 4 8 16 32 64.",
        titles_fn=mock_titles, fetch=mock_fetch)
    ok("ingestion -> topics -> related growth", ing["ingested"] and len(ing["topics"]) >= 1
       and len(ing["related_grown"]) >= 1)

    keyed = pg.LLMConfig(provider="gemini", api_key="TEST", model="gemini-3.5-flash",
                         base_url=pg.DEFAULTS["gemini"][0])
    mock_llm = pg._mock_gemini("3 6 9 12 15 18 21\n9 2 7 4 1 8\n4 8 12 16 20 24")
    lp = g.llm_propose_and_grow(transport=mock_llm, cfg=keyed)
    ok("LLM proposes, chiron verifies, verified grown", lp["accepted"] >= 2 and len(lp["grown"]) >= 2)

    g.save()
    g2 = GrowClean(store=g.store)
    ok("store round-trips (grown Congress persists)", os.path.exists(g.store) and g2.org is not None)

    passed = sum(1 for _, c in checks if c)
    print("grow_clean self-test")
    for n_, c in checks:
        print(f"  [{'PASS' if c else 'FAIL'}] {n_}")
    print(f"  {passed}/{len(checks)} checks")
    return passed == len(checks)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Unified clean growth over any source, LLM-aided.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("selftest")
    for name in ("file", "wikipedia", "ingest"):
        sp = sub.add_parser(name); sp.add_argument("target"); sp.add_argument("--store", default=DEFAULT_STORE)
        sp.add_argument("--llm", action="store_true")
    lp = sub.add_parser("llm"); lp.add_argument("--store", default=DEFAULT_STORE)
    args = ap.parse_args(argv)

    if args.cmd in (None, "selftest"):
        return 0 if _selftest() else 1

    g = GrowClean(store=args.store)
    if args.cmd == "file":
        out = g.grow_file(args.target)
        print(json.dumps({"grown": out, "congress": g.cong}, indent=2, default=str))
    elif args.cmd == "wikipedia":
        out = g.grow_wikipedia([args.target])
        print(json.dumps({"grown": out, "congress": g.cong}, indent=2, default=str))
    elif args.cmd == "ingest":
        out = g.grow_from_ingestion(args.target, use_llm=args.llm)
        print(json.dumps({**out, "congress": g.cong}, indent=2, default=str))
    elif args.cmd == "llm":
        out = g.llm_propose_and_grow()
        print(json.dumps({**out, "congress": g.cong}, indent=2, default=str))
    g.save()
    print(f"[saved to {g.store}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
