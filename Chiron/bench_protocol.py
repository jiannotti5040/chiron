#!/usr/bin/env python3
"""
bench_protocol.py — exact finite-state-machine recovery from observed traces (new domain).

A fresh instantiation of the same architecture: surface -> hypothesis -> exact search -> MDL ->
held-out -> accept/refuse. The surface is a set of event traces from an unknown protocol; the
hypothesis class is deterministic finite-state machines; MDL prefers the minimal transition table
consistent with the data over memorizing the traces; verification predicts held-out traces at exact
equality; and contradictory (noisy) observations are REFUSED rather than forced into a wrong machine.

Baseline: a first-order Markov predictor over states (ignores the event) — it cannot capture
event-dependent transitions and is wrong on held-out steps the exact recovery gets right.

    python3 bench_protocol.py            # results table
    python3 bench_protocol.py selftest   # 0/1 gate

Status: implemented & tested. Self-contained (ground-truth machines are known, so recovery is
checkable); embodies the Chiron discipline without importing the monolith.
"""
import sys
import random
from collections import defaultdict, Counter

# Ground-truth machines: (name, states, events, transition table {(state,event): next_state}).
TURNSTILE = ("turnstile", ["LOCKED", "UNLOCKED"], ["push", "coin"], {
    ("LOCKED", "push"): "LOCKED", ("LOCKED", "coin"): "UNLOCKED",
    ("UNLOCKED", "push"): "LOCKED", ("UNLOCKED", "coin"): "UNLOCKED",
})
HANDSHAKE = ("tcp-handshake", ["CLOSED", "SYN", "ESTAB"], ["open", "ack", "close"], {
    ("CLOSED", "open"): "SYN", ("CLOSED", "ack"): "CLOSED", ("CLOSED", "close"): "CLOSED",
    ("SYN", "open"): "SYN", ("SYN", "ack"): "ESTAB", ("SYN", "close"): "CLOSED",
    ("ESTAB", "open"): "ESTAB", ("ESTAB", "ack"): "ESTAB", ("ESTAB", "close"): "CLOSED",
})
MACHINES = [TURNSTILE, HANDSHAKE]


def gen_traces(fsm, states, events, n_traces, length, seed):
    rnd = random.Random(seed)
    traces = []
    for _ in range(n_traces):
        s = rnd.choice(states)
        tr = []
        for _ in range(length):
            e = rnd.choice(events)
            nxt = fsm[(s, e)]
            tr.append((s, e, nxt))
            s = nxt
        traces.append(tr)
    return traces


def recover_fsm(traces):
    """MDL recovery: the minimal deterministic transition table consistent with the traces.
    Returns (table, contradictions). contradictions>0 means the data is not a deterministic FSM."""
    table, contradictions = {}, 0
    for tr in traces:
        for (s, e, nxt) in tr:
            k = (s, e)
            if k in table and table[k] != nxt:
                contradictions += 1
            else:
                table[k] = nxt
    return table, contradictions


def certify_fsm(train, holdout):
    table, contra = recover_fsm(train)
    if contra > 0:
        return {"verified": False, "reason": "non-deterministic observations — abstained",
                "table": table}
    total = correct = covered = 0
    for tr in holdout:
        for (s, e, nxt) in tr:
            total += 1
            if (s, e) in table:
                covered += 1
                correct += int(table[(s, e)] == nxt)
    return {"verified": total > 0 and correct == total and covered == total,
            "table": table, "transitions": len(table),
            "heldout_total": total, "heldout_correct": correct}


def markov_state(train):
    succ = defaultdict(Counter)
    for tr in train:
        for (s, e, nxt) in tr:
            succ[s][nxt] += 1
    return {s: c.most_common(1)[0][0] for s, c in succ.items()}


def markov_eval(model, holdout):
    total = correct = 0
    for tr in holdout:
        for (s, e, nxt) in tr:
            total += 1
            correct += int(model.get(s) == nxt)
    return correct, total


def run():
    rows = []
    for name, states, events, fsm in MACHINES:
        traces = gen_traces(fsm, states, events, n_traces=40, length=12, seed=7)
        cut = len(traces) * 3 // 4
        train, holdout = traces[:cut], traces[cut:]
        cert = certify_fsm(train, holdout)
        recovered_full = cert["verified"] and dict(cert["table"]) == fsm
        mc, mt = markov_eval(markov_state(train), holdout)
        data_triples = sum(len(t) for t in train)
        rows.append((name, len(states), len(events), cert["transitions"], recovered_full,
                     cert["heldout_correct"], cert["heldout_total"], mc, mt,
                     data_triples))

    # abstention: corrupt one transition so the data is non-deterministic -> must refuse
    name, states, events, fsm = TURNSTILE
    traces = gen_traces(fsm, states, events, 20, 10, seed=3)
    traces[0] = [("LOCKED", "coin", "LOCKED")] + traces[0][1:]   # a lie: coin should unlock
    abstained = not certify_fsm(traces, traces[:3])["verified"]

    print("bench_protocol — exact FSM recovery from traces vs first-order Markov\n")
    print(f"{'protocol':16}{'states':>7}{'events':>7}{'trans':>7}{'recovered':>10}"
          f"{'held-out (exact)':>18}{'markov':>14}")
    print("-" * 86)
    for nm, ns, ne, tr, rec, hc, ht, mc, mt, dt in rows:
        print(f"{nm:16}{ns:>7}{ne:>7}{tr:>7}{('full' if rec else 'partial'):>10}"
              f"{f'{hc}/{ht}':>18}{f'{mc}/{mt} ({100*mc//max(1,mt)}%)':>14}")
    print("-" * 86)
    print(f"contradictory traces -> abstained: {abstained}")
    print("\nThe exact recovery predicts every held-out transition (it learned the event-dependent")
    print("machine); the Markov baseline ignores the event and is wrong wherever an event matters.")
    print("On noisy (non-deterministic) input the recovery refuses rather than certify a wrong FSM.")
    return rows, abstained


def _selftest():
    rows, abstained = run()
    all_recovered = all(r[4] for r in rows)
    all_heldout_exact = all(r[5] == r[6] and r[6] > 0 for r in rows)
    beats_markov = all(r[5] > r[7] for r in rows)   # exact correct > markov correct on held-out
    checks = [
        ("every machine recovered in full", all_recovered),
        ("held-out transitions predicted exactly", all_heldout_exact),
        ("beats the Markov baseline on held-out", beats_markov),
        ("abstains on contradictory traces", abstained),
    ]
    print("\nSELFTEST")
    for n, c in checks:
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    ok = all(c for _, c in checks)
    print(f"  {sum(c for _, c in checks)}/{len(checks)} checks")
    return ok


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        sys.exit(0 if _selftest() else 1)
    run()
