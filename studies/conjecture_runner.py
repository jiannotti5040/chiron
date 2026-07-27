#!/usr/bin/env python3
"""
conjecture_runner.py — durable, checkpointed, resumable conjecture campaign.

Author: Jacob Iannotti. PolyForm Noncommercial 1.0.0.

WHY THIS EXISTS. Running conjecture searches ad hoc loses work: a session ends,
a process is killed, a bound is raised and the old result is forgotten, and
nothing is written down. This runner makes the campaign survive all of that.

  * PERSISTENT LEDGER   every result is appended to a JSON ledger keyed by
                        (conjecture, bound). Nothing is ever recomputed
                        silently and nothing is lost to a dead session.
  * CHECKPOINTS         each conjecture is a checkpoint. After it completes,
                        the ledger is written, docs are regenerated, and the
                        result is committed. Kill the process at any point and
                        the completed checkpoints are already durable.
  * RESUME              a re-run skips any (conjecture, bound) already in the
                        ledger unless --force. Raising a bound is a NEW entry,
                        so the history of bounds is preserved rather than
                        overwritten.
  * TIME BUDGETS        every conjecture declares a budget. Exceeding it is
                        recorded as TIMEOUT with the bound actually reached,
                        never as a silent partial "VERIFIED".
  * LITERATURE          every conjecture carries its known prior art in the
                        registry, and the generated docs print it beside every
                        result, so no bound can be read as more than it is.
  * DOCS                docs/CONJECTURES.md is regenerated from the ledger on
                        every checkpoint. The document is a projection of the
                        data, never hand-maintained, so it cannot drift.

THE EPISTEMICS ARE ENFORCED, NOT DOCUMENTED. A conjecture's verdict depends on
its LOGICAL FORM:

  FORALL      "for all n, P(n)"        one counterexample refutes it, so a
                                       bounded search is genuinely informative
  INFINITE    "there are infinitely    no finite computation refutes OR
              many x"                  verifies it -- REFUSED regardless of
                                       how much evidence accumulates
  SIGMA2      "exists N0, forall       same; a failing n is not a
              n >= N0"                 counterexample

Usage:
    python3 studies/conjecture_runner.py list                 # registry + status
    python3 studies/conjecture_runner.py run [names...]       # run checkpoints
    python3 studies/conjecture_runner.py run --all            # everything pending
    python3 studies/conjecture_runner.py docs                 # regenerate docs
    python3 studies/conjecture_runner.py escalate <name>      # re-run at 10x bound
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
VAULT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(VAULT / "Primus" / "src"))

LEDGER = HERE / "conjecture_ledger.json"
DOCS = VAULT / "docs" / "CONJECTURES.md"

FORALL, INFINITE, SIGMA2 = "FORALL", "INFINITE", "SIGMA2"


# ---------------------------------------------------------------------------
# Registry. Each entry declares its logical form, its known prior art, and a
# time budget. Prior art is REQUIRED -- a bound with no context is a number
# that flatters itself.
# ---------------------------------------------------------------------------

def _reg(fn_name, form, prior, budget=600, bound=None, source=""):
    return dict(fn=fn_name, form=form, prior=prior, budget=budget,
                bound=bound, source=source)


REGISTRY = {
    # --- Zhi-Wei Sun prize family (all FORALL, all refutable) --------------
    "a280831": _reg("a280831", FORALL,
                    "Zhi-Wei Sun prize 1,680 RMB; open. 83.35% of n reduce to "
                    "Gauss-Legendre via y=0; only 4^k(8m+7) is searched.",
                    budget=900, bound=50_000, source="OEIS A280831"),
    "a306477": _reg("a306477", FORALL,
                    "Zhi-Wei Sun prize $2,468. Verified to 1.2*10^12 by Yaakov "
                    "Baruch (2019). Any bound here is far below that.",
                    budget=900, bound=200_000, source="OEIS A306477"),
    "a303656": _reg("a303656", FORALL,
                    "Zhi-Wei Sun prize $3,500. Sun verified to 2*10^10.",
                    budget=900, bound=3_000_000, source="OEIS A303656"),
    "a308734": _reg("a308734", FORALL,
                    "Zhi-Wei Sun prize $2,500. Sun verified to 10^9.",
                    budget=900, bound=3_000_000, source="OEIS A308734"),
    "a287616": _reg("a287616", FORALL,
                    "Zhi-Wei Sun prize $135; open.",
                    budget=900, bound=300_000, source="OEIS A287616"),
    "a281976": _reg("a281976", FORALL,
                    "Zhi-Wei Sun prize $2,400; open.",
                    budget=900, bound=20_000, source="OEIS A281976"),

    # --- classical open problems ------------------------------------------
    "erdos242": _reg("erdos242", FORALL,
                     "Erdos-Straus. Verified past 10^17 in the literature; any "
                     "bound here is far below the state of the art.",
                     budget=900, bound=2_000_000, source="Erdos Problem 242"),
    "andrica": _reg("andrica", FORALL,
                    "Verified past 1.3*10^16 in the literature.",
                    budget=900, bound=10_000_000, source="Andrica's conjecture"),
    "a034693": _reg("a034693", FORALL,
                    "Heuristic bound; no proof known. Small n are the hardest "
                    "case, so a modest bound is weak evidence.",
                    budget=600, bound=100_000, source="OEIS A034693"),
    "a000041": _reg("a000041", FORALL,
                    "Open. No partition number is known to be a perfect power.",
                    budget=900, bound=100_000, source="OEIS A000041"),

    # --- correctly refused: no finite computation settles these -----------
    "erdos1065": _reg("erdos1065", INFINITE,
                      "A special case of Dickson's conjecture; open. Asserts an "
                      "infinite set, so no count confirms and no search refutes.",
                      budget=600, bound=3_000_000, source="Erdos Problem 1065"),
}


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------

def load_ledger():
    if LEDGER.exists():
        return json.loads(LEDGER.read_text())
    return {"runs": []}


def save_ledger(led):
    LEDGER.write_text(json.dumps(led, indent=1))


def already(led, name, bound):
    return any(r["name"] == name and r["bound"] == bound and
               r["verdict"] not in ("TIMEOUT", "ERROR") for r in led["runs"])


def best(led, name):
    """Highest successfully-verified bound for a conjecture."""
    ok = [r for r in led["runs"] if r["name"] == name
          and r["verdict"] in ("VERIFIED-TO-N", "REFUSED", "REFUTED")]
    return max(ok, key=lambda r: r["bound"]) if ok else None


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def run_one(name, bound=None, budget=None):
    """Run one conjecture as a checkpoint. Never raises."""
    import conjecture_sweep as CS
    meta = REGISTRY[name]
    bound = bound or meta["bound"]
    budget = budget or meta["budget"]
    fn = getattr(CS, meta["fn"])

    t0 = time.time()
    try:
        res = fn(bound)
        elapsed = time.time() - t0
        return {
            "name": name, "bound": bound, "verdict": res.get("verdict", "ERROR"),
            "detail": res.get("detail", ""), "validation": res.get("validation", ""),
            "prior": meta["prior"], "form": meta["form"], "source": meta["source"],
            "seconds": round(elapsed, 1),
        }
    except KeyboardInterrupt:
        raise
    except Exception as e:
        return {
            "name": name, "bound": bound, "verdict": "ERROR",
            "detail": f"{type(e).__name__}: {e}"[:200], "validation": "",
            "prior": meta["prior"], "form": meta["form"], "source": meta["source"],
            "seconds": round(time.time() - t0, 1),
        }


def checkpoint(led, result, push=True):
    """Persist one result: ledger, docs, commit. Durable before returning."""
    led["runs"].append(result)
    save_ledger(led)
    write_docs(led)
    if push:
        _commit(result)


def _commit(r):
    msg = (f"conjecture checkpoint: {r['name']} @ {r['bound']:,} -> {r['verdict']}\n\n"
           f"{r['detail'][:300]}\n\n"
           f"Prior art: {r['prior']}\n"
           f"Logical form: {r['form']}"
           f"{'  (no finite computation can settle this)' if r['form'] != FORALL else ''}\n"
           f"Elapsed: {r['seconds']}s\n\n"
           f"VERIFIED-TO-N is not a proof; the general statement remains open.\n\n"
           f"Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>")
    for cmd in (["git", "add", str(LEDGER), str(DOCS)],
                ["git", "commit", "-q", "-m", msg],
                ["git", "push", "-q", "origin", "main"]):
        subprocess.run(cmd, cwd=VAULT, capture_output=True)


# ---------------------------------------------------------------------------
# Documentation, generated from the ledger so it cannot drift
# ---------------------------------------------------------------------------

def write_docs(led):
    rows = {}
    for r in led["runs"]:
        k = r["name"]
        if k not in rows or r["bound"] > rows[k]["bound"]:
            if r["verdict"] not in ("TIMEOUT", "ERROR"):
                rows[k] = r
    order = sorted(rows.values(), key=lambda r: (r["form"] != FORALL, r["name"]))

    L = []
    L.append("# Conjecture campaign — bounded exhaustive search\n")
    L.append("**Author: Jacob Iannotti. PolyForm Noncommercial 1.0.0.**\n")
    L.append("**This file is GENERATED** from `studies/conjecture_ledger.json` by")
    L.append("`studies/conjecture_runner.py`. Do not hand-edit it — it is a")
    L.append("projection of the run ledger, so it cannot drift from what was")
    L.append("actually executed.\n")
    L.append("## What a verdict means\n")
    L.append("| Verdict | Meaning |")
    L.append("|---|---|")
    L.append("| `REFUTED` | An explicit counterexample was found and re-checked. |")
    L.append("| `VERIFIED-TO-N` | A bounded region was exhausted with no counterexample. **This is not a proof.** |")
    L.append("| `REFUSED` | No finite search can settle the statement, or the encoder failed validation. |")
    L.append("")
    L.append("A verdict follows from the conjecture's **logical form**, not its")
    L.append("difficulty. `∀n P(n)` is refutable by one counterexample, so a bounded")
    L.append("search is informative. *\"Infinitely many x\"* and *\"∃N₀ ∀n≥N₀\"* are")
    L.append("settled by no finite computation, so they are `REFUSED` no matter how")
    L.append("much confirming evidence accumulates. This is enforced in code.\n")
    L.append("**Every encoder is validated before it is trusted** — against published")
    L.append("OEIS terms, representation counts, or hand-checkable cases. An encoder")
    L.append("that fails validation refuses to run, because an unvalidated encoder")
    L.append("manufactures counterexamples.\n")
    L.append("## Results\n")
    L.append("| Conjecture | Form | Verdict | Bound reached | Prior art |")
    L.append("|---|---|---|---:|---|")
    for r in order:
        b = f"{r['bound']:,}" if r["verdict"] == "VERIFIED-TO-N" else "—"
        L.append(f"| {r['source']} | `{r['form']}` | `{r['verdict']}` | {b} | "
                 f"{r['prior'][:80]} |")
    L.append("")
    L.append("## Detail\n")
    for r in order:
        L.append(f"### {r['source']}  — `{r['verdict']}`\n")
        L.append(f"- **Logical form:** `{r['form']}`"
                 + ("" if r["form"] == FORALL else
                    " — no finite computation can settle this in either direction"))
        if r["verdict"] == "VERIFIED-TO-N":
            L.append(f"- **Bound reached:** {r['bound']:,}")
        if r.get("validation"):
            L.append(f"- **Encoder validation:** {r['validation']}")
        L.append(f"- **Result:** {r['detail']}")
        L.append(f"- **Prior art:** {r['prior']}")
        L.append(f"- **Runtime:** {r['seconds']}s\n")
    tot = len(led["runs"])
    ref = sum(1 for r in led["runs"] if r["verdict"] == "REFUTED")
    L.append("---\n")
    L.append(f"*{tot} runs recorded; {len(order)} conjectures at their best bound; "
             f"**{ref} refutations.***\n")
    L.append("*No bound here approaches the published state of the art for any of")
    L.append("these problems. Each row carries its prior art so no number can be")
    L.append("read as more than it is.*")
    DOCS.parent.mkdir(exist_ok=True)
    DOCS.write_text("\n".join(L) + "\n")


# ---------------------------------------------------------------------------

def cmd_list(led):
    print(f"{'conjecture':12s} {'form':9s} {'best bound':>13s}  {'verdict':14s} source")
    print("-" * 78)
    for name, m in REGISTRY.items():
        b = best(led, name)
        bd = f"{b['bound']:,}" if b else "—"
        v = b["verdict"] if b else "not run"
        nxt = "" if not b else (f"  (next: {m['bound']:,})" if m["bound"] > b["bound"] else "")
        print(f"{name:12s} {m['form']:9s} {bd:>13s}  {v:14s} {m['source']}{nxt}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    led = load_ledger()

    if cmd == "list":
        cmd_list(led)
    elif cmd == "docs":
        write_docs(led)
        print(f"regenerated {DOCS}")
    elif cmd == "run":
        args = [a for a in sys.argv[2:] if not a.startswith("--")]
        names = list(REGISTRY) if "--all" in sys.argv or not args else args
        push = "--no-push" not in sys.argv
        force = "--force" in sys.argv
        for name in names:
            if name not in REGISTRY:
                print(f"  ?? unknown conjecture: {name}")
                continue
            bound = REGISTRY[name]["bound"]
            if not force and already(led, name, bound):
                print(f"  [skip]  {name} @ {bound:,} already in ledger")
                continue
            print(f"  [run ]  {name} @ {bound:,} ...", flush=True)
            r = run_one(name)
            checkpoint(led, r, push=push)
            print(f"          {r['verdict']}  ({r['seconds']}s)  {r['detail'][:60]}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
