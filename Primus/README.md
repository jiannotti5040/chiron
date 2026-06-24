# Primus — folder map

**Author: Jacob Iannotti. Licensed under PolyForm Noncommercial 1.0.0 — free to use, modify, and share for any noncommercial purpose; commercial rights reserved (see the repository-root [LICENSE.md](../LICENSE.md)).**

What each file is, in plain terms. Nothing here is junk. This is the origin:
the lean engine and its proof. The full integrated program it grew into has
ascended into **Chiron** — see `../Chiron/chiron.py`.

---

## The code

**`invariant_engine.py`** — *the seed.* The clean, lean engine (~1,000 lines).
This is the novel part, by itself, easy to read and audit. One operation,
`collapse`, that takes anything codified (numbers, text, ciphers, graphs,
schemas, code, the twin spaces) and recovers the rule beneath it — with
held-out proof, honest residuals, and an owner-bound fingerprint. Start here.

```bash
python3 -c "from invariant_engine import collapse; print(collapse([1,1,2,3,5,8,13,21]).explanation)"
```

> The complete integrated system — certification core, intake standardizer,
> ambiguity crucible, field substrate, organism layer, and this engine as its
> invariant operation — is now the single file `../Chiron/chiron.py`. There is
> one program, Chiron; this folder is where its engine began.

---

## The proof

**`test_invariant_engine.py`** — the stress tests (currently 48/48). Run it to
confirm everything works on your machine.

```bash
python3 test_invariant_engine.py
```

**`benchmark.py`** — the proving run: feeds the engine known-generator
sequences, shows it part of each, and grades whether the rule it recovered
predicts terms it never saw. Prints recovery rate, precision, and false-positive
count.

```bash
python3 benchmark.py
```

**`BENCHMARK_RESULTS.md`** — the written-up results of that run (recovery 98%,
precision 100%, zero false confidence) plus a capability summary. Read this to
see, in words, what the engine can and cannot do.

---

## The background

**`Primus Flow Chart.svg`** — the system diagram: the cells and every level of
the organism the engine grew into, laid out visually.

The Caramuel *Primus Calamus* (1663) source material — the book with the twin
labyrinths the engine uses as built-in ground truth — lives with the
ambiguity work in `../Infectatrum`.

---

## Requirements

`invariant_engine.py` needs Python 3 with `numpy`. Everything runs offline; no
network, no API keys. `__pycache__` folders are auto-generated when you run
things and are safe to delete anytime. The full Chiron program in `../Chiron`
runs on bare Python 3 with no required dependencies.
