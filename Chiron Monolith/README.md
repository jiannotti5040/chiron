# Chiron Monolith

**All of Chiron, folded into one file.**

`chiron_monolith.py` embeds the byte-identical source of every Chiron module (63 of them,
~1.9 MB of code) inside a single Python file, with a small loader so the whole spine runs
out of that one file — no `Chiron/*.py` siblings required for the *code*.

This is the answer to a simple question: *can the entire engine live in one file and still
run?* Yes — and it is proven by running the same selftests through the fold.

## Source-of-truth policy

**The `Chiron/*.py` modules are the single source of truth. `chiron_monolith.py`
is a build artifact — never hand-edit it.** The generated file carries an
`@generated … DO NOT EDIT` banner, and `build_monolith.py` asserts every embedded
module is byte-identical to its original at build time, so any drift between the
fold and the spine is a build error, not a fork. After changing any Chiron
module:

```bash
python3 build_monolith.py            # regenerate the fold
python3 chiron_monolith.py --selftest  # prove the fold (41/41 modules green)
```

(The same policy holds vault-wide: the packaged seed engine lives at
`../Primus/src/primus/engine.py`, and `../Primus/invariant_engine.py` is a thin
compatibility shim over it — one implementation per idea, everything else
generated or aliased.)

## Run it

```bash
python3 chiron_monolith.py serve                   # OPEN THE DASHBOARD — operator console on :8765
python3 chiron_monolith.py --list                 # every embedded module
python3 chiron_monolith.py <module> [args...]      # run any module's command line
python3 chiron_monolith.py semic selftest          # -> 56/56 gates passing
python3 chiron_monolith.py chiron selftest         # -> CHIRON GREEN
python3 chiron_monolith.py trace "1 1 2 3 5 8 13"  # -> ranked candidates -> verified rule
python3 chiron_monolith.py --selftest              # FULL sweep: every selftest-bearing module
python3 chiron_monolith.py --smoke                 # quick: just the core-engine battery
```

**The dashboard.** `python3 chiron_monolith.py serve` opens the full operator console at
<http://127.0.0.1:8765> — Analyze, Run, Chat (with the *Add your own API key* panel), Feed. It is
the same console as the spine; there is no second dashboard to maintain. This folder is
**self-contained**: `build_monolith.py` bundles `dashboard.html` (whose Verify stage is the certificate browser) and the
data it needs (`manifest.json`, `lexicon.json`, `parameters.json`, a clean Congress seed) right here,
so the console works whether or not a sibling `Chiron/` directory is present. The aux services behind
the other tabs run the same way (`chiron_monolith.py console_server serve`, etc.).

`python3 chiron_monolith.py --selftest` runs **every** selftest-bearing module through the fold —
the same set the full build's `build_manifest --run` executes (servers and corpus mutators excluded
identically) — and reports the count:

```
  [PASS] aesthetics           ...
  [PASS] chiron               CHIRON GREEN — exact knowledge, honest wisdom, bounded agency
  [PASS] semic                56/56 gates passing
  ...
  41/41 modules green through the fold (same coverage as the full build's manifest)
```

This is the proof that **Chiron-full and Chiron-monolith are identical in function**: the embedded
sources are byte-identical to `Chiron/*.py` (asserted at build), so the fold passes exactly the gates
the spine passes. `--smoke` is the quick five-engine check.

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

The generator (`build_monolith.py`) lives here in the folder. From this directory:

```bash
python3 build_monolith.py            # rebuild chiron_monolith.py from ../Chiron/*.py + bundle the dashboard
python3 build_monolith.py --verify   # rebuild, then run the engine battery through it
```

Re-run after changing any Chiron module so the fold stays byte-identical to the spine.

## Scope

The monolith is a faithful single-file embodiment of Chiron's code. It is not a separate
engine and adds no logic — every behaviour, gate, and certificate is the spine's own,
reached through one file instead of sixty-three. Licensed under PolyForm Noncommercial 1.0.0
(see `../LICENSE.md`).
