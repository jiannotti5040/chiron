# Chiron

Chiron is a local, macOS-first workspace for exact checks, bounded analysis,
and auditable records. Its Python core does not try to turn every input into an
answer. For the claim families it implements, it returns one of three
dispositions:

- **VERIFIED** — a defined exact check succeeded, with the supporting record.
- **REFUTED** — a defined exact check failed.
- **REFUSED** — the input is outside the checker's warranted scope.

That vocabulary is deliberately narrow. A certificate is not a general truth
judgment, a probability that prose was machine-written, legal advice, or a
replacement for review.

## Use it locally

The core runs with Python. The native interface is a local macOS SwiftUI app;
it invokes the same Python entry points and contains no second verifier.

```bash
git clone https://github.com/jiannotti5040/chiron.git
cd chiron
python3 -m pip install ./Primus

primus collapse "1 1 2 3 5 8 13 21 34 55"
printf '%s\n' '17 * 3 = 51 and 2^10 = 1025' | primus certify - --gate
```

For the macOS interface (macOS 14+, Swift 6, a local Python installation):

```bash
cd App
swift run chiron-app
swift test --scratch-path /tmp/chiron-build
./make_app.sh
```

The app locates a checkout by walking up from its working directory. A
double-clickable bundle records the checkout used to build it; set
`CHIRON_VAULT` to choose another checkout and `CHIRON_PYTHON` to choose a
specific interpreter. See [the macOS operator guide](App/README.md).

## What is here

| Surface | Role | Boundary |
|---|---|---|
| [Primus](Primus/) | Exact recovery and claim certification | It stamps only the claim families and holdout tests it can perform exactly. |
| [Chiron](Chiron/) | Local analysis, provenance, adjudication, and composition tools | Source modules are canonical; the monolith is generated from them. |
| [Chiron Monolith](Chiron%20Monolith/) | Offline, generated fold of Chiron modules | Regenerate after a Chiron-source change; never edit the fold directly. |
| [App](App/) | Local macOS SwiftUI interface | Uses `Foundation.Process` to call the canonical vault; it does not recalculate verdicts. |
| [JDICert](JDICert/) | Decision-certificate and court-analysis material | Auditable software artifacts, not a claim of legal admissibility. |
| [studies](studies/) | Reproducible research capsules and records | Each capsule states its finite scope and non-claims. |
| [UMA Suite](UMA%20Suite/) | Separate computational/theory work | Its empirical claims remain separate from the exact-verification core. |

MCP and local HTTP interfaces are available for local integration. They are not
a hosted service, a public gateway, or evidence of a configured third-party
deployment. The Foundry/AIP material is an unconfigured typed boundary only;
it does not deliver to an ontology or make a live Foundry claim.

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
