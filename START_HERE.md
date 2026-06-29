# Start here

## Run everything — one command

```bash
cd Chiron
python3 vault.py
# then open  http://127.0.0.1:8765
```

That's it. One command, one page, `Ctrl-C` stops everything. You never need to remember the ports.

Everything runs **offline with no key**. The two LLM features (the **Chat** tab and **President**
grow) need a free key first — `export GROW_LLM_API_KEY=...` (get one at aistudio.google.com/apikey);
without it they simply stay disabled and nothing else is affected.

Just the engine, nothing else: `python3 vault.py --core`.

## The one page — http://127.0.0.1:8765

| Tab | What it does |
|---|---|
| **Analyze** | paste a number sequence, text, or ciphertext → it recovers the exact rule, speaks it back, and issues a certificate |
| **Run** | run any engine function from a menu, see the output |
| **Chat** | say what you want in plain language; it runs the real, deterministic functions (needs a key) |
| **Feed** | start / stop the grower and point it at any source (Wikipedia / a site / an API / OEIS) |
| **Growth** · **What it knows** | watch the Congress grow; browse what it has learned |

## Prefer the command line?

```bash
python3 chiron.py collapse 1 1 2 3 5 8 13     # recover + prove a rule
python3 chiron.py solve "WKLV LV D WHVW"      # crack a classical cipher
python3 bench_suite.py                         # six benchmarks vs established baselines
python3 chiron.py selftest                     # the engine's own gates
```

## What `vault.py` starts for you (so you don't have to)

| Service | Port | Powers the tab |
|---|---|---|
| `chiron.py serve` | 8765 | the console itself + the engine API |
| `console_server.py` | 8768 | **Run** |
| `assistant_server.py` | 8769 | **Chat** |
| `grow_control.py` | 8767 | **Feed** (start/stop/point the grower) |
| `president_grow.py` | 8766 | **President** (LLM-proposes → engine-verifies growth) |

## Going deeper (optional)

- **[Chiron/RUNNING.md](Chiron/RUNNING.md)** — the full run guide, service by service.
- **[Chiron/ARTIFACTS.md](Chiron/ARTIFACTS.md)** — the certificate + manifest system: every script can
  leave a signed, falsifiable artifact; `python3 build_manifest.py --run` indexes them.
- **[README.md](README.md)** — what the project is, and the measured proof.
- **Mathematical_Compendium.pdf** — every formal result, each tagged by its epistemic status.
