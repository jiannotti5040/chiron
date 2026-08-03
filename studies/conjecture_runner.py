#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
conjecture_runner.py — durable, checkpointed, resumable conjecture campaign.

Author: Jacob Iannotti. Apache-2.0.

WHY THIS EXISTS. Running conjecture searches ad hoc loses work: a session ends,
a process is killed, a bound is raised and the old result is forgotten, and
nothing is written down. This runner makes the campaign survive all of that.

  * PERSISTENT LEDGER   every result is appended to a JSON ledger keyed by
                        (conjecture, bound). Nothing is ever recomputed
                        silently and nothing is lost to a dead session.
  * CHECKPOINTS         each conjecture is a checkpoint. After it completes,
                        the ledger is written and docs are regenerated. A git
                        commit/push is an explicit ``--push`` action, never a
                        local-run side effect. Kill the process at any point
                        and the completed checkpoints are already durable.
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
    python3 studies/conjecture_runner.py run [names...]       # run checkpoints locally
    python3 studies/conjecture_runner.py run --push [names...] # explicitly publish findings
    python3 studies/conjecture_runner.py run --all            # everything pending
    python3 studies/conjecture_runner.py docs                 # regenerate docs
    python3 studies/conjecture_runner.py escalate <name>      # re-run at 10x bound
"""

from __future__ import annotations

import json
import os
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

def _reg(fn_name, form, prior, budget=600, bound=None, source="", capsule=""):
    return dict(fn=fn_name, form=form, prior=prior, budget=budget,
                bound=bound, source=source, capsule=capsule)


REGISTRY = {
    # --- Zhi-Wei Sun prize family (all FORALL, all refutable) --------------
    "a280831": _reg("a280831", FORALL,
                    "Zhi-Wei Sun prize 1,680 RMB; open. 83.35% of n reduce to "
                    "Gauss-Legendre via y=0; only 4^k(8m+7) is searched.",
                    budget=420, bound=50_000, source="OEIS A280831"),
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
    "a063880": _reg("a063880", FORALL,
                    "DeepMind Formal Conjectures marks the residue and unique-primitive "
                    "statements for A063880 as research open; finite evidence only.",
                    budget=180, bound=10_000_000,
                    source="DeepMind FormalConjectures A063880",
                    capsule="../studies/capsules/a063880-n10000000/README.md"),

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
    # A checkpoint must not leave a half-written ledger if the process dies
    # mid-write. ``os.replace`` is atomic on this filesystem; it does not
    # claim multi-writer coordination, only crash-safe replacement.
    temp = LEDGER.with_suffix(LEDGER.suffix + ".tmp")
    temp.write_text(json.dumps(led, indent=1) + "\n")
    os.replace(temp, LEDGER)


def already(led, name, bound):
    return completed_result(led, name, bound) is not None


def completed_result(led, name, bound):
    """The recorded successful result for one exact checkpoint, if present."""
    rows = [r for r in led["runs"]
            if r["name"] == name and r["bound"] == bound
            and r["verdict"] not in ("TIMEOUT", "ERROR")]
    return rows[-1] if rows else None


def best(led, name):
    """Highest successfully-verified bound for a conjecture."""
    ok = [r for r in led["runs"] if r["name"] == name
          and r["verdict"] in ("VERIFIED-TO-N", "REFUSED", "REFUTED")]
    return max(ok, key=lambda r: r["bound"]) if ok else None


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

class _Timeout(Exception):
    pass


def run_one(name, bound=None, budget=None):
    """
    Run one conjecture as a checkpoint. Never raises.

    The budget is ENFORCED with SIGALRM, not merely measured. An earlier
    version of this function declared budgets in the registry and then simply
    timed the call afterward -- so a conjecture that needed six hours would
    have run for six hours and been recorded as if the budget meant something.
    A declared constraint that the code does not honour is worse than no
    constraint, because the docstring lies on its behalf.

    On timeout the result is TIMEOUT with the bound ATTEMPTED, never a partial
    VERIFIED. A search that did not finish has verified nothing.
    """
    import signal
    import conjecture_sweep as CS
    meta = REGISTRY[name]
    bound = bound or meta["bound"]
    budget = budget or meta["budget"]
    fn = getattr(CS, meta["fn"])

    def _fire(signum, frame):
        raise _Timeout()

    base = dict(name=name, bound=bound, prior=meta["prior"],
                form=meta["form"], source=meta["source"])
    t0 = time.time()
    old = signal.signal(signal.SIGALRM, _fire)
    signal.alarm(int(budget))
    try:
        res = fn(bound)
        return {**base, "verdict": res.get("verdict", "ERROR"),
                "detail": res.get("detail", ""),
                "validation": res.get("validation", ""),
                "seconds": round(time.time() - t0, 1)}
    except _Timeout:
        return {**base, "verdict": "TIMEOUT",
                "detail": f"exceeded the {budget}s budget at bound {bound:,}; "
                          f"NOTHING is verified by an unfinished search. Lower "
                          f"the bound or raise the budget in the registry.",
                "validation": "", "seconds": round(time.time() - t0, 1)}
    except KeyboardInterrupt:
        raise
    except Exception as e:
        return {**base, "verdict": "ERROR",
                "detail": f"{type(e).__name__}: {e}"[:200],
                "validation": "", "seconds": round(time.time() - t0, 1)}
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def checkpoint(led, result, push=False, persist=True):
    """
    Persist one attempt.

    The ledger records EVERY attempt, including timeouts -- that history is
    what auto-calibration reads and it costs nothing to keep locally.

    But only a real FINDING is committed. An earlier version pushed a commit
    per attempt, which filled the history with "-> TIMEOUT" noise: a search
    that did not finish is not a result, and a repo log full of non-results
    makes the real ones harder to find. Timeouts and errors now stay local.
    """
    # The escalating runner persists each completed probe immediately.  Its
    # final probe is therefore already in the ledger when it becomes the
    # checkpoint.  Appending it again inflated the run count and made the
    # generated report disagree with the real execution history.
    if persist:
        led["runs"].append(result)
        save_ledger(led)
    write_docs(led)
    if push and result["verdict"] in ("VERIFIED-TO-N", "REFUTED", "REFUSED"):
        _commit(result, led)


def _commit(r, led):
    # Fold the calibration history into the one commit that carries a finding,
    # rather than emitting a commit per failed attempt.
    tried = [x for x in led["runs"]
             if x["name"] == r["name"] and x["verdict"] == "TIMEOUT"]
    cal = ""
    if tried:
        bounds = ", ".join(f"{x['bound']:,}" for x in tried)
        cal = (f"\nCalibration: {len(tried)} bound(s) exceeded the "
               f"{REGISTRY[r['name']]['budget']}s budget first ({bounds}); this "
               f"is the largest bound that completed.\n")

    msg = (f"{r['source']} @ {r['bound']:,} -> {r['verdict']}\n\n"
           f"{r['detail'][:300]}\n\n"
           f"Encoder validation: {r.get('validation') or 'n/a'}\n"
           f"Logical form: {r['form']}"
           f"{'  (no finite computation can settle this in either direction)' if r['form'] != FORALL else ''}\n"
           f"Prior art: {r['prior']}\n"
           f"{cal}"
           f"\nVERIFIED-TO-N is not a proof; the general statement remains open.\n")
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
    L.append("**Author: Jacob Iannotti. Apache-2.0.**\n")
    L.append("**This file is GENERATED** from `studies/conjecture_ledger.json` by")
    L.append("`studies/conjecture_runner.py`. Do not hand-edit it — it is a")
    L.append("projection of the run ledger. Regenerate it instead of hand-editing")
    L.append("it when the recorded execution changes.\n")
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
        L.append(f"- **Runtime:** {r['seconds']}s")
        capsule = REGISTRY.get(r["name"], {}).get("capsule")
        if capsule:
            L.append(f"- **Replay capsule:** [frozen inputs and independent "
                     f"replay]({capsule})")
        L.append("")
    tot = len(led["runs"])
    ref = sum(1 for r in led["runs"] if r["verdict"] == "REFUTED")
    L.append("---\n")
    L.append(f"*{tot} runs recorded; {len(order)} conjectures at their best bound; "
             f"**{ref} refutations.***\n")
    L.append("*Bounds are not novelty claims. Each row carries its source and prior-art")
    L.append("status so no number can be read as more than its stated scope.*")
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
        # Publishing is an external action, never the default side effect of
        # a local research run.  ``--no-push`` remains harmless for backward
        # compatibility with earlier invocation notes.
        push = "--push" in sys.argv
        force = "--force" in sys.argv
        for name in names:
            if name not in REGISTRY:
                print(f"  ?? unknown conjecture: {name}")
                continue
            bound = REGISTRY[name]["bound"]
            if not force and already(led, name, bound):
                print(f"  [skip]  {name} @ {bound:,} already in ledger")
                continue
            # Calibrate UPWARD, not downward.
            #
            # The first version guessed a bound and halved on timeout, which
            # spends the entire budget on searches that finish nothing and
            # then reports a smaller bound anyway. Escalating instead starts
            # from a cheap bound and doubles while there is measured headroom,
            # so every second of compute goes into a search that COMPLETES.
            #
            # Only the final, largest completed run is committed. The
            # intermediate rungs stay in the local ledger as calibration data.
            meta = REGISTRY[name]
            budget = meta["budget"]
            attempt = meta.get("seed", 2000)
            last = None
            while attempt <= bound:
                r = None if force else completed_result(led, name, attempt)
                if r is not None:
                    print(f"  [cache] {name} @ {attempt:,} -> {r['verdict']}")
                else:
                    print(f"  [probe] {name} @ {attempt:,} ...", flush=True)
                    r = run_one(name, bound=attempt, budget=budget)
                    led["runs"].append(r)
                    save_ledger(led)
                    print(f"          {r['verdict']}  ({r['seconds']}s)")
                if r["verdict"] == "TIMEOUT":
                    break
                if r["verdict"] == "ERROR":
                    last = r
                    break
                last = r
                # stop escalating once the next doubling would likely overrun
                if r["seconds"] * 2.6 > budget:
                    break
                # The declared target is itself a checkpoint.  Doubling past
                # it (for example 64,000 -> 128,000 with a 100,000 target)
                # previously made the advertised bound unreachable.
                if attempt == bound:
                    break
                attempt = min(attempt * 2, bound)
            if last and last["verdict"] != "TIMEOUT":
                checkpoint(led, last, push=push, persist=False)
                print(f"  [DONE ] {name} @ {last['bound']:,} -> {last['verdict']}"
                      f"  ({last['seconds']}s)  {last['detail'][:50]}")
            else:
                print(f"  [DONE ] {name}: no bound completed inside {budget}s "
                      f"— nothing committed")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
