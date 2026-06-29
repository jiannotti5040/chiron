# Chiron Monolith

**All of Chiron, folded into one file.**

`chiron_monolith.py` embeds the byte-identical source of every Chiron module (63 of them,
~1.9 MB of code) inside a single Python file, with a small loader so the whole spine runs
out of that one file — no `Chiron/*.py` siblings required for the *code*.

This is the answer to a simple question: *can the entire engine live in one file and still
run?* Yes — and it is proven by running the same selftests through the fold.

## Run it

```bash
python3 chiron_monolith.py --list                 # every embedded module
python3 chiron_monolith.py <module> [args...]      # run any module's command line
python3 chiron_monolith.py semic selftest          # -> 56/56 gates passing
python3 chiron_monolith.py chiron selftest         # -> CHIRON GREEN
python3 chiron_monolith.py trace "1 1 2 3 5 8 13"  # -> ranked candidates -> verified rule
python3 chiron_monolith.py --selftest              # battery across the core engines
python3 chiron_monolith.py chiron serve            # the operator console on :8765, from the one file
```

There is **no separate dashboard** for the monolith: it serves the same operator console as the
spine. `chiron_monolith.py chiron serve` opens it at <http://127.0.0.1:8765>, and the aux services
behind the other tabs run the same way (`chiron_monolith.py console_server serve`, etc.).

`python3 chiron_monolith.py --selftest` runs the core engines each in a fresh subprocess of
the monolith and reports pass/fail:

```
  [PASS] semic            56/56 gates passing
  [PASS] chiron           CHIRON GREEN — exact knowledge, honest wisdom, bounded agency
  [PASS] density_emotion  density_emotion.py self-test: 8/8 passed
  [PASS] semic_energy     8/8 checks
  [PASS] epistemic        13/13 checks
  5/5 engines green through the monolith
```

A broad sweep of all 45 selftest-bearing modules passes 43/43 through the fold; the two
that don't (`build_manifest`, `infectatrum_bridge`) are tools without a `selftest`
subcommand and fail identically whether folded or run standalone — i.e. the fold is faithful.

## How it works

- **Embedded source.** Every `Chiron/*.py` is base64-encoded into the dict `_SOURCES`. At
  build time each embedding is asserted byte-identical to its origin, so the monolith is a
  *lossless fold of the spine, not a rewrite.*
- **Internal imports.** A `sys.meta_path` finder makes `import chiron`, `import semic`,
  `import legal_corpus`, … resolve to the embedded copies. The cross-imports between
  modules therefore work with no source files alongside.
- **Running as `__main__`.** `run_module` registers the executing module in `sys.modules`
  as both `__main__` and its own name, because the spine self-references through
  `sys.modules[__name__]` (e.g. `veritas = sys.modules[__name__]`) and scans its own source
  via `inspect.getsource(...)`. Both must resolve to the running module.
- **Data + self-source.** Each module's `__file__` points at the real `../Chiron/<name>.py`
  when that directory is present (the normal in-repo case), so `_HERE`-relative data files
  (`parameters.json`, the Congress memory, `artifacts/`) and the self-source scan resolve
  exactly as they do for the standalone scripts. Behaviour is therefore identical to running
  the originals. Ship the monolith alongside the repo's `Chiron/` directory.

## Regenerate

The generator lives at the **repo root** (`build_monolith.py`) — a monolith is one file, so the
folder holds only `chiron_monolith.py` and this README. From the repo root:

```bash
python3 build_monolith.py            # rebuild "Chiron Monolith/chiron_monolith.py" from Chiron/*.py
python3 build_monolith.py --verify   # rebuild, then run the engine battery through it
```

Re-run after changing any Chiron module so the fold stays byte-identical to the spine.

## Scope

The monolith is a faithful single-file embodiment of Chiron's code. It is not a separate
engine and adds no logic — every behaviour, gate, and certificate is the spine's own,
reached through one file instead of sixty-three. Licensed under PolyForm Noncommercial 1.0.0
(see `../LICENSE.md`).
