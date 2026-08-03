# Contributing

The code here is licensed under the **Apache License 2.0** (see [`LICENSE`](LICENSE))
and the prose works under **CC BY 4.0** (see [`LICENSES.md`](LICENSES.md) for the
map). Clone it, run it, modify it, ship it, sell it — experiment freely. There is no
commercial tier and nothing is held back.

This project has one inviolable property: **zero false verifications.** A change that
makes an engine stamp something it cannot exactly prove is wrong even if every
benchmark number goes up. Refusal is a feature; treat it as one.

## Run it / experiment

Everything runs offline. The one dependency is numpy — `pip install ./Primus` brings it, or `pip install numpy` directly (the engine imports it at load; there is no pure-Python fallback for the core today):

```bash
python3 bin/chiron test                # the whole gate battery (same gates as CI)
python3 bin/chiron parity              # prove spine and fold are one organism (138 identical gates)
python3 Chiron/chiron.py selftest      # just the embedded gate suite (prints GREEN)
python3 Chiron/benchmark.py            # the reproducible benchmark (VERDICT: PASS)
pip install ./Primus && primus selftest
```

Fork it, point the grower at your own sources, try the tools — that's encouraged.

## Before you open a PR — run the gates

All of them pass or the change isn't ready (CI runs the same stack on a
Python 3.9/3.13 × Ubuntu/Windows matrix):

```bash
pip install ./Primus
cd Primus
python3 test_invariant_engine.py     # 48 stress gates (via the compat shim)
python3 benchmark.py                 # internal proving run — zero false confidence
primus selftest                      # engine + certify gates
python3 test_mcp_server.py           # MCP protocol handshake
python3 test_certify_fuzz.py         # adversarial gates
python3 oeis_live.py                 # external validation (cached live corpus)
python3 drift_check.py               # seed vs Chiron differential test
cd .. && python3 Chiron/chiron.py selftest
```

## Ground rules

- **Sources of truth.** The seed engine is `Primus/src/primus/engine.py`
  (`invariant_engine.py` is a shim — never add code there). Chiron modules are
  canonical; `Chiron Monolith/chiron_monolith.py` is generated — edit the modules and
  run `build_monolith.py`. The package version lives in `Primus/pyproject.toml` only.
- **Exact means exact.** On integer surfaces, verification is exact integer equality —
  no tolerances, no "close enough," floats beyond 2⁵³ are refused. New hypothesis
  families follow the same contract: recover, predict held-out data exactly, or
  abstain.
- **If the seed and Chiron diverge on purpose,** ledger it in
  `Primus/drift_check.py` with a dated reason. Unledgered divergence fails the build
  by design.
- **Certificate schema changes** bump the schema string and get documented in
  `Primus/SCHEMA.md` + `Primus/CHANGELOG.md`. Consumers gate on that string.
- **New checkable claim kinds** need exact semantics (no probabilistic or approximate
  judgments — REFUSE instead), work bounds against hostile input, selftest gates for
  the true/false/refused cases, and a fuzz case if they add a new scan pattern.
- **State epistemic status plainly.** Implemented-and-tested, prototype, or theory —
  label it like the rest of the vault does. Overclaiming is the one style error that
  gets a PR closed on sight.

## Contributing back — the public grow

The most welcome place to contribute is the **public grow** (`Chiron/grow-public/`):
new **sources** or **profiles** (a website, a JSON API, an OEIS slice, a subject
configuration), or corrections to public-grow configuration and documentation. Open a
Pull Request.

Also high-value: external validation escalations (full OEIS, PySR), new exact claim
kinds, hypothesis-class extensions with proofs (order-2 P-recursion is the known open
edge), Windows/py-version compatibility, and documentation that removes a footgun.
Low-value: new layers, new dashboards, new folds — the vault grows outward now, not
inward.

## Attribution and licensing

Inbound equals outbound: contributions of **code** are accepted under Apache-2.0, and
contributions of **prose** under CC BY 4.0 — the same terms the repository already
carries. You keep the copyright in what you write; no CLA and no copyright assignment.
Apache-2.0 §5 makes this explicit, and its patent grant (§3) runs from contributors
too, which is the main reason this project uses Apache rather than MIT.

Grown content carries its sources' attribution — Wikipedia (CC BY-SA 4.0), OEIS, the
vendored DeepMind `formal-conjectures` file, and the public-domain Caramuel source;
see [`NOTICE`](NOTICE). Note that CC BY-SA is copyleft and **cannot** be relicensed
into this repository: a Congress grown over Wikipedia is not redistributable here,
which is why `Chiron/chiron_memory.json` is untracked. By opening a PR you confirm you
have the right to contribute the material and that it is attributed correctly.

## Conduct

Be precise, cite evidence, and prefer reproducible claims. The whole project rests on
the idea that a claim arrives with what would falsify it — contributions are held to
the same standard.
