# Chiron

Exact law recovery with held-out proof.

Chiron recovers the rule underlying a sequence or a table, verifies it against
data the solver never saw, and refuses when no exact rule exists. All
arithmetic on the deciding path is rational; there is no tolerance parameter
and no residual threshold.

[![Chiron CI](https://github.com/jiannotti5040/chiron/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/jiannotti5040/chiron/actions/workflows/ci.yml)
[![Swift](https://github.com/jiannotti5040/chiron/actions/workflows/swift.yml/badge.svg?branch=main)](https://github.com/jiannotti5040/chiron/actions/workflows/swift.yml)
[![proof](https://github.com/jiannotti5040/chiron/actions/workflows/proof.yml/badge.svg?branch=main)](https://github.com/jiannotti5040/chiron/actions/workflows/proof.yml)
[![PyPI](https://img.shields.io/pypi/v/primus-intelligence)](https://pypi.org/project/primus-intelligence/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

## Install

```bash
pip install primus-intelligence
```

## Example

Recover a relation across the columns of a table:

```python
from primus.relate import relate

rows = [
    {"units": 3, "ship": 10, "total": 85},
    {"units": 4, "ship": 11, "total": 111},
    {"units": 5, "ship": 12, "total": 137},
    {"units": 6, "ship": 10, "total": 160},
    {"units": 7, "ship": 11, "total": 186},
    {"units": 8, "ship": 12, "total": 212},
    {"units": 9, "ship": 10, "total": 235},
    {"units": 10, "ship": 11, "total": 261},
]

result = relate(rows, target="total", inputs=["units", "ship"])
print(result["status"])  # VERIFIED
print(result["law"])     # total = 25*units + ship
```

The law is solved on the first *k* rows and then required to hold exactly on
every remaining row. If one row disagrees, the status is `PARTIAL` and that
row is identified:

```python
rows[5]["total"] = 999
relate(rows, target="total", inputs=["units", "ship"])["anomalous_rows"]  # [5]
```

Recover a generator from a sequence:

```python
from primus.engine import collapse

inv = collapse([1, 1, 2, 3, 5, 8, 13, 21])
inv.verified     # True
inv.model_class  # 'linear_recurrence_order2'
inv.predict(11)[8:]  # [34, 55, 89]
```

## Dispositions

| Status | Meaning |
|---|---|
| `VERIFIED` | The rule held exactly on every held-out case. |
| `REFUTED` | The rule failed on data it had not seen. |
| `REFUSED` | No rule in the hypothesis class could be proven. Nothing is stamped in either direction. |
| `PARTIAL` | The rule held on all held-out cases but a named few. Not a weaker `VERIFIED`. |

Data with rounding or measurement error normally returns `REFUSED`. The
hypothesis classes are deliberately small: a class large enough to fit
arbitrary data cannot support a proof.

## Reading a document

`certify` extracts the claims in a text that can be checked exactly, and
refuses the rest. It reads figures the way reports write them — thousands
separators, operators in words, unit prices, appositive percentages:

```python
from primus.certify import certify

report = ("Q3 close. We shipped 1,240 units at 25 dollars each is 31,000 in "
          "product revenue. 31,000 plus 2,180 is 33,180 invoiced. "
          "Returns ran at 3 percent of 1,240, or 38 units.")

for claim in certify(report)["claims"]:
    print(claim["status"], claim["text"])
```

```
VERIFIED 1,240 units at 25 dollars each is 31,000
VERIFIED 31,000 plus 2,180 is 33,180
REFUTED  3 percent of 1,240, or 38
```

Three percent of 1,240 is 37.2. The free text around the claims is reported as
unverifiable rather than blessed, and `coverage` says how much of the document
was checkable at all.

A claim that is only part of a longer chain is `REFUSED` rather than judged,
because the kernel evaluates one binary operation and cannot know the
precedence of the rest.

## Capabilities

| Module | Function |
|---|---|
| `primus.engine` | Generator recovery from sequences, strings, graphs, and code, under minimum description length with held-out verification. |
| `primus.relate` | Exact relations across table columns; anomaly localisation. |
| `primus.invert` | Inversion of a verified law; recovery of the mapping between two tables. |
| `primus.certify` | Claim-level gating of text against ten exactly checkable claim kinds. |
| `primus.conjecture` | Candidate generation behind the exact gate. |

The `Chiron/` tree adds analysis, source provenance, span-level attestation,
adjudication, and composition over these engines.

## Interfaces

Every interface dispatches through `Chiron/mcp_server.py:_IMPL`. Results are
produced in one place.

| Interface | Entry point |
|---|---|
| Python API | `pip install primus-intelligence` |
| CLI | `python3 bin/chiron <verb>` |
| MCP (stdio) | `python3 Chiron/mcp_server.py` — 16 tools |
| HTTP | `python3 Chiron/service.py` — `/v1/<operation>` |

```bash
python3 bin/chiron ingest data.csv        # detect structure, certify it
python3 bin/chiron falsify 1 1 2 3 5 8    # what observation would refute this
python3 bin/chiron engines                # list available operations
```

MCP registration for Claude Code:

```bash
claude mcp add chiron -- python3 /absolute/path/to/Chiron/mcp_server.py
```

## Scope

Chiron does not evaluate general truth, estimate the probability that text was
machine-generated, or provide legal or professional advice. A certificate
records that a specific, defined check succeeded under stated inputs.

`attest` attributes spans of text to sources supplied by the caller. With no
sources supplied, every span returns `REFUSED`.

## Development

```bash
git clone https://github.com/jiannotti5040/chiron.git
cd chiron

python3 bin/chiron test --full   # gate battery
python3 bin/chiron parity        # 138 gates through both incarnations
python3 ci/state.py --check      # verify docs/STATE.json matches the checkout
```

After changing a module under `Chiron/`, regenerate the derived artifacts:

```bash
python3 Chiron/build_manifest.py
cd "Chiron Monolith" && python3 build_monolith.py && python3 chiron_monolith.py --selftest
```

Contributor guidance is in [CONTRIBUTING.md](CONTRIBUTING.md); repository
state and open work are in [HANDOFF.md](HANDOFF.md) and [STATUS.md](STATUS.md).

## Repository layout

| Path | Contents |
|---|---|
| [`Primus/`](Primus/) | The published package: engines, certification, packaging. |
| [`Chiron/`](Chiron/) | Analysis, provenance, adjudication, MCP server, HTTP service. |
| [`Chiron Monolith/`](Chiron%20Monolith/) | Generated single-file fold of `Chiron/`. Never edited directly. |
| [`App/`](App/), [`iOS/`](iOS/) | SwiftUI clients for macOS and iOS. |
| [`JDICert/`](JDICert/) | Decision-certificate analysis. |
| [`studies/`](studies/), [`eval/`](eval/) | Reproducible research capsules and evaluation records. |
| [`docs/`](docs/) | Architecture, security model, file support, MCP client setup. |

## License

Code is Apache-2.0 ([LICENSE](LICENSE)). Prose and books are CC BY 4.0
([LICENSES.md](LICENSES.md)). See [NOTICE](NOTICE).
