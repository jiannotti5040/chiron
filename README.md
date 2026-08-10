# Chiron

Chiron recovers the exact law underneath your data, proves it on evidence it
was never shown, and refuses when no such law exists.

That last clause is the product. Most systems that find patterns will always
find one. This one is built so that it cannot report a rule it has not proven,
and a refusal is a result rather than a failure.

```
$ chiron ingest ledger.csv

PARTIAL   total = 25*units + ship
          confirmed on 10 rows the solver never saw
          rows inconsistent with that law: 9
```

Nobody told it there was a pricing rule, which columns mattered, or that one
row was wrong. It recovered the rule from the data, held out ten rows to test
it against, and named the row that breaks it.

## Four dispositions, and what they cost

| | Meaning |
|---|---|
| **VERIFIED** | An exact check succeeded, or a recovered law held on every held-out case. No tolerance, no residual — rational arithmetic and `==`. |
| **REFUTED** | An exact check failed, or the law failed on evidence it had not seen. |
| **REFUSED** | Outside the warranted scope. Nothing is stamped in either direction. |
| **PARTIAL** | A law holds on all but a few cases, and those cases are named. Explicitly **not** a weaker VERIFIED — it is a finding about the data. |

The cost of that discipline is real and worth stating: measured data with
rounding usually REFUSES, because the honest answer to "is there an exact law
here" is usually no. A system that answered anyway would be easier to demo and
worth less.

## Try it in one minute

```bash
python3 -m pip install primus-intelligence

python3 - <<'EOF'
from primus.relate import relate
rows = [{"units": 3+i, "ship": 10+(i%3),
         "total": 25*(3+i) + 10+(i%3) + (50 if i == 9 else 0)} for i in range(14)]
print(relate(rows, "total", ["units", "ship"]))
EOF
```

Or from a checkout, with every surface available:

```bash
git clone https://github.com/jiannotti5040/chiron.git
cd chiron

python3 bin/chiron ingest "1 1 2 3 5 8 13 21"     # recover a generator
python3 bin/chiron ingest data.csv                # recover a law across columns
python3 bin/chiron falsify 1 1 2 3 5 8 13 21      # what would overturn it
python3 bin/chiron engines                        # everything it can be asked
```

## What it does

**Recovers laws.** Given a sequence, it recovers the generator under minimum
description length and proves it on held-out terms. Given a table, it recovers
an exact relation across columns and proves it on held-out rows.

**Localises anomalies.** A law that holds on all but a few rows names those
rows. That is how a pricing error, a transcription slip, or a fabricated line
surfaces — as the case inconsistent with the rule governing everything else.

**Runs backwards.** A law that VERIFIED can be inverted to recover a missing
value exactly. A law that did not verify cannot, because inverting an unproven
rule would launder it into a confident number.

**Says what would refute it.** Every result carries the observation that would
overturn it. A refusal carries the specific evidence that would resolve it,
which turns a dead end into a task.

**Attributes text.** `attest` reports which supplied source produced each span
of a document. It is not a detector and reports no probability that text is
machine-written; that measurement does not exist.

## The same core, every way in

Every surface below reaches one Python engine through one dispatch table
(`Chiron/mcp_server.py:_IMPL`). A verdict is produced in exactly one place, so
a terminal, an agent, and the app cannot disagree about what a tool does.

| Surface | Entry point | Status |
|---|---|---|
| CLI | `python3 bin/chiron …` | `ingest`, `relate`, `falsify`, `experiment`, `attest`, `verify`, `solve`, `explore`, `compare`, `engines`, `service`, `mcp` |
| MCP (stdio) | `Chiron/mcp_server.py` | 16 reviewed tools, no arbitrary dispatch. Verified live from Claude Code. |
| Local HTTP | `python3 Chiron/service.py` | All 16 operations over `/v1`, closed routes, bounded bodies |
| macOS app | `./run-chiron.command` | Builds, launches, runs |
| iOS app | `iOS/ChironMobile.xcodeproj` | Builds and runs in Simulator; same target as macOS |

Apple's on-device model is wired in as a **proposer only**: it points at spans
of your text and structurally cannot express a verdict, because the type it
returns has no status field. Anything it writes that is not verbatim in your
source is discarded before it reaches the engine. OpenAI and Anthropic adapters
work the same way, and require a credential *and* separate network
authorization — holding a key is not consent to use it.

## What is here

| Surface | Role | Boundary |
|---|---|---|
| [Primus](Primus/) | Exact recovery and claim certification | It stamps only the claim families and holdout tests it can perform exactly. |
| [Chiron](Chiron/) | Local analysis, provenance, adjudication, and composition tools | Source modules are canonical; the monolith is generated from them. |
| [Chiron Monolith](Chiron%20Monolith/) | Offline, generated fold of Chiron modules | Regenerate after a Chiron-source change; never edit the fold directly. |
| [App](App/) | macOS SwiftUI interface, and the Swift modules both apps share | `ChironKit` uses `Foundation.Process` to call the canonical vault; it does not recalculate verdicts. |
| [iOS](iOS/) | iOS SwiftUI app, plus a Siri/Shortcuts intent | Talks to the versioned `/v1` service. It cannot run Python or recompute a certificate on device. |
| [JDICert](JDICert/) | Decision-certificate and court-analysis material | Auditable software artifacts, not a claim of legal admissibility. |
| [studies](studies/) | Reproducible research capsules and records | Each capsule states its finite scope and non-claims. |
| [UMA Suite](UMA%20Suite/) | Separate computational/theory work | Its empirical claims remain separate from the exact-verification core. |

## The same core, five ways

Every surface below reaches the identical Python engine. A verdict is produced
in exactly one place.

| Surface | Entry point | Status |
|---|---|---|
| CLI | `python3 bin/chiron …` | Runs. `test`, `parity`, `verify`, `serve`, `benchmark`, `plan`. |
| MCP (stdio) | `Chiron/mcp_server.py` | Runs. Sixteen reviewed tools; no arbitrary module dispatch. Invoked live from Claude Code. |
| Local HTTP | `python3 -m primus.engine_server` | Runs. Versioned `/v1`, bounded bodies, closed routes. See [LOCAL_API.md](Primus/LOCAL_API.md). |
| macOS app | `cd App && ./make_app.sh` | Builds, launches, runs. |
| iOS app | `iOS/ChironMobile.xcodeproj` | Builds for the Simulator. No completed test-runner result — see below. |

Apple's on-device model is wired in as a **proposer only**: it points at spans
of your text and structurally cannot express a verdict, because the type it
returns has no status field. Anything it writes that is not verbatim in your
source is discarded before it can reach the engine.

MCP and local HTTP are for local integration. They are not a hosted service, a
public gateway, or evidence of a configured third-party deployment. The
Foundry/AIP material is an unconfigured typed boundary only; it does not
deliver to an ontology or make a live Foundry claim.

## What is not built

Stated here rather than buried, because the reading order below promises
evidence before narrative:

- No evidence graph or contradiction record as first-class objects.
- No web retrieval or persistent corpus index. PDF reads the text layer only
  and refuses by name when it cannot — see [FILE_SUPPORT.md](docs/FILE_SUPPORT.md).
- No signing, notarization, or App Store submission of any kind.
- The Foundry/AIP material is an unconfigured typed boundary. It does not
  deliver to an ontology or make a live Foundry claim.
- The iOS test runner stalls on the development host; that is an environment
  fault, and no iOS *test* result is claimed. The app itself builds and runs.

[docs/MANDATE_STATUS.md](docs/MANDATE_STATUS.md) tracks all of this against
observed evidence.

## Evidence before narrative

The useful reading order is:

1. [Research map](docs/RESEARCH_MAP.md) — separates executable evidence,
   bounded computation, and experimental theory.
2. [External validation record](Primus/EXTERNAL_VALIDATION.md) — including
   failures caught from external data and their repairs.
3. [Known limitations](Chiron/docs/KNOWN_LIMITATIONS.md) — where the engine
   abstains and what its stamps do not mean.
4. [Reconstruction record](docs/RECONSTRUCTION.md) — the present local
   implementation boundary and validation commands.

The paper draft, theory documents, benchmark results, and historical logs have
different evidentiary status. The repository does not treat a test suite,
bounded computation, or self-authored theory as interchangeable with an
independent result.

## Verify a checkout

Run the standard gate battery from the repository root:

```bash
python3 bin/chiron test --full
python3 bin/chiron parity
```

If a Chiron source module changes, regenerate its derived records before
claiming the fold is current:

```bash
cd "Chiron Monolith" && python3 build_monolith.py && python3 chiron_monolith.py --selftest
cd .. && python3 Chiron/build_manifest.py --run && python3 Chiron/build_encyclopedia.py
```

## License

Code is licensed under [Apache-2.0](LICENSE). Prose and books are licensed
under [CC BY 4.0](LICENSES.md). See [NOTICE](NOTICE) and
[CONTRIBUTING.md](CONTRIBUTING.md) for repository-specific notices and
contribution guidance.
