# Primus — the installable seed

**Author: Jacob Iannotti. Licensed under Apache-2.0 — free to use, modify, distribute, and use commercially, with attribution (see the repository-root [LICENSE](https://github.com/jiannotti5040/chiron/blob/main/LICENSE)).**

Primus is the clean, auditable core of the whole vault, now shipped as a
Python package: **exact invariant recovery with held-out verification and
refusal** — plus that discipline turned into an accountability certificate
for LLM/agent output. One idea: never certify what you cannot exactly verify.

```bash
pip install primus-intelligence
```

(From a checkout of the vault, `pip install ./Primus` installs the same
package from source.)

## Two operations

**`collapse`** — recover the minimal generator beneath a codified surface
(numbers, text, ciphers, graphs, schemas, code) under a two-part MDL
criterion in exact arithmetic. *Verified* means one thing only: the rule
exactly predicted held-out data it never saw. Anything else is an honest
residual, never a confident guess.

```python
from primus import collapse
inv = collapse([1, 1, 2, 3, 5, 8, 13, 21])
inv.verified        # True — held-out terms predicted exactly
inv.explanation     # what was recovered, why it is believed
```

**`certify`** — the front door for the agent era: feed it a model's output,
and every checkable claim comes back **VERIFIED**, **REFUTED**, or
**REFUSED**; the free-text remainder is reported as unverifiable, never
blessed. Checkable kinds (schema `primus.certificate/2`, contract in
[`SCHEMA.md`](https://github.com/jiannotti5040/chiron/blob/main/Primus/SCHEMA.md)): exact arithmetic incl. powers, percentages,
primality, binomials, gcd/lcm, modular and date arithmetic, sums/averages,
sequence continuations, and integer runs. Gate an agent on `refuted == 0`,
then read `coverage` before trusting the pass — a passing gate means
*nothing checkable was refuted*, never *the output is true*.

```python
from primus import certify
cert = certify(
    "We shipped 1,240 units at 25 dollars each for a total of 31,000, "
    "and headcount grew from 84 to 96, an increase of 14."
)
cert["counts"]      # {'checkable': 2, 'verified': 1, 'refuted': 1, 'refused': 0}
cert["claims"][1]   # the increase is 12, not 14 — REFUTED, with the span
```

The second line exits 1 on any refuted claim — pipe your model's output in
place of the example text:

```bash
primus collapse "1 1 2 3 5 8 13 21"
echo "310 of 1,240 renewed, or 25 percent" | primus certify - --json --gate
primus selftest
```

## Guess-and-prove — `primus.conjecture` (optional)

The symbolic-regression baseline this project benchmarks against
(SYMREG_RESULTS.md) can also serve it: `primus conjecture "0 1 128 2187 …"`
lets a gplearn genetic-programming proposer suggest closed forms for an
input the engine refuses — and stamps a candidate ONLY if, after snapping
its float constants to exact integers/rationals, it reproduces every
supplied term exactly in rational arithmetic, including a holdout suffix
the search never saw. The stochastic proposer never stamps; the exact
verifier does, and the certificate says exactly what was proven (fit to
the given data — never the true generator). Without `pip install
primus-intelligence[conjecture]` the stage degrades to an honest REFUSED.
A verified conjecture emits the claim `a(n) = <expr> matches <terms>`,
which the certify gate checks independently as the `closed_form` claim
kind — guess-and-prove output round-trips through the gate. On the live
OEIS corpus the gate converted the raw regressor's 27 wrong answers into
26 refusals + 3 exact stamps, with zero stamped-wrong (SYMREG_RESULTS.md).

## The MCP server — the gate as agent infrastructure

`primus-mcp` serves both operations over the Model Context Protocol (stdio,
dependency-free), so any MCP-speaking agent can call the verifier natively —
certify its own draft answer, gate on `counts.refuted == 0`, and treat the
unverifiable remainder as exactly that.

`primus-mcp` speaks newline-delimited JSON-RPC on stdio; the second line
registers it with Claude Code:

```bash
primus-mcp
claude mcp add primus -- primus-mcp
```

Claude Desktop / Cowork (`claude_desktop_config.json` → `mcpServers`):

```json
{ "primus": { "command": "primus-mcp" } }
```

Tools exposed: `certify(text)` → the full certificate as structured content;
`collapse(surface)` → the invariant (or an honest refusal). A refuted claim
is a *result*, not a tool error — `isError` is reserved for real failures.
Protocol conformance is gated by `python3 test_mcp_server.py` (10 handshake
gates against the live subprocess).

## Local HTTP boundary

`primus-serve` / `python3 -m primus.engine_server` exposes the same canonical
engine on local HTTP. The legacy routes remain available for local tooling;
the narrower versioned contract is `GET /v1/capabilities`, `POST
/v1/collapse`, and `POST /v1/certify`. Its envelope is
`chiron.local_api/1`, and its `result` preserves the existing
`primus.engine_server/1` output so it does not create another engine or
certificate format.

Read [LOCAL_API.md](https://github.com/jiannotti5040/chiron/blob/main/Primus/LOCAL_API.md) before building a client. This is an
implemented-and-tested local wire contract, **not** a public endpoint, cloud
integration, or production authentication service. The optional
`CHIRON_API_TOKEN` is a fixed local/development bearer, not something to
embed in an app. The default service binding is loopback; production gateway,
TLS, short-lived scoped credentials, rotation/revocation, and edge abuse
controls remain external work. `python3 test_engine_server.py` drives the
local routes over real HTTP.

## The code

**`src/primus/engine.py`** — *the seed, and the single source of truth*
(~1,700 lines). The novel part by itself, easy to read and audit in one
sitting: `collapse`, `same_generator`, `cast`, `transcode`, the twin spaces.
`invariant_engine.py` at this folder's root is a compatibility shim so every
historical entry point still works.

**`src/primus/certify.py`** — the certificate layer: claim extraction
(arithmetic, percentages, sequence continuations, integer runs), exact
checking through the engine, four-way honesty (verified / refuted / refused /
unverifiable), SHA-256 attestation.

**`src/primus/relate.py`** — exact laws across the columns of a table.
Coefficients are solved in rational arithmetic and the law must then hold on
rows the solver never saw. `PARTIAL` names the rows that break an otherwise
exact law, which is anomaly localisation rather than a weaker verification.

**`src/primus/invert.py`** — runs a `VERIFIED` law backwards to recover a
missing value, and recovers the exact per-column map between two tables. A law
that did not verify is not inverted; irrational roots are refused rather than
rounded.

**`src/primus/grounded.py`** — claims whose truth lives outside the sentence,
checked against a caller-supplied fact table. A subject nobody supplied is
`REFUSED` by name rather than guessed at.

**`src/primus/conjecture.py`** — candidate generation behind the exact gate.

**`src/primus/mcp_server.py`**, **`src/primus/engine_server.py`** — the stdio
MCP surface and the versioned local HTTP service.

**`src/primus/cli.py`** — the `primus` command.

> The full integrated system — certification core, intake standardizer,
> ambiguity crucible, field substrate, organism layer, and this engine as its
> invariant operation — is **Chiron**: `../Chiron/chiron.py`. There is one
> program, Chiron; this folder is where its engine began and the clearest
> place to read the idea in isolation.

## The proof

**`test_invariant_engine.py`** — the stress tests (60/60). Run it to confirm
everything works on your machine.

```bash
python3 test_invariant_engine.py
```

**`benchmark.py`** — the proving run: feeds the engine known-generator
sequences, shows it part of each, and grades whether the rule it recovered
predicts terms it never saw. Results in
[the reconciled battery map](https://github.com/jiannotti5040/chiron/blob/main/docs/BATTERIES.md): recovery 98%, precision 100%,
zero false confidence.

**`oeis_live.py`** — the *external* proving run: the same held-out discipline
against sequences fetched live from OEIS rather than a self-generated bank.
Results and the honest miss list in
[the public external eval](https://github.com/jiannotti5040/chiron/tree/main/eval).

**`bench_symreg_external.py` / `bench_pysr.py`** — head-to-head against
established symbolic-regression baselines (gplearn results in
[docs/SYMREG.md](https://github.com/jiannotti5040/chiron/blob/main/docs/SYMREG.md); PySR harness included, runs wherever
PySR is installed).

**`test_certify_fuzz.py`** — adversarial gates: hostile input must crash
nothing, respect every work bound, and never flip a planted verdict. The
fuzzer has already earned its keep twice (a sequence-flood DoS and a
quadratic scan cost, both found and fixed — see [`CHANGELOG.md`](https://github.com/jiannotti5040/chiron/blob/main/Primus/CHANGELOG.md)).

**`test_mcp_server.py`** — the MCP protocol handshake against the live
subprocess.

**`drift_check.py`** — differential testing against `../Chiron/chiron.py`:
contradictions between the seed and the monolith fail the build; deliberate
capability differences must be ledgered with a dated reason.

## The background

**`Primus Flow Chart.svg`** — the system diagram: the cells and every level of
the organism the engine grew into, laid out visually.

The Caramuel *Primus Calamus* (1663) source material — the book with the twin
labyrinths the engine uses as built-in ground truth — lives with the
ambiguity work in `../Infectatrum`.

## Requirements

Python 3.9+ with `numpy`. Everything runs offline; no network, no API keys
(`oeis_live.py` is the one deliberate exception — it exists to fetch external
ground truth). `__pycache__` folders are auto-generated and safe to delete.
The guess-and-prove stage (`primus.conjecture`) optionally uses
`gplearn` + `scikit-learn` (`pip install primus-intelligence[conjecture]`);
absent, it refuses honestly and everything else is unaffected.
