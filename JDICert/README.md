# CERT_ENGINE

**Experimental research prototype for structured decision review.**

> **Status and limits.** This is a self-developed prototype, not a deployed safety system, legal product, regulatory certification, or independently validated scientific result. Its output is a record produced by this implementation. It does not establish legal admissibility, regulatory compliance, factual truth, or fitness for autonomous action. Any real-world use requires domain-specific validation, qualified human review, and the operator's own legal, safety, and security assessment.

Scope: a detect–decide–act research workflow with a `CERTIFY` phase between Detection and Action. The engine produces a cryptographically bound structured record intended for inspection and experimentation; it is not an authoritative decision artifact.

---

## License

Licensed under the **Apache License 2.0**. You may use, modify, distribute, and commercialise this work, including inside proprietary products; attribution and the NOTICE are the conditions. Full text in the repository-root `LICENSE`.

---

## Architecture

Three files, single domain (autonomous high-stakes decisions):

| File | Role | Approx. lines |
|---|---|---|
| `cert_engine.py` | The monolithic engine. Activation protocol, UMA/RSLS dynamics, LexGuard four-gate, K/U/Ω partition, Mystery Taxonomy + reduction operators, emotive substrate, world-model set, hallucination defeat (Friston-aligned), 14+ section certificate format, Merkle ledger, Belief Delta, the `certify()` furnace, embedded 256-test suite, holographic continuity theory primitives, governance-as-invariant tracking, Daubert/FRE 702/FRCP 26 admissibility analyzer, attestation tokens, doctrine ledger, cross-institution merge, Kuramoto consensus, adversarial probe. | ~11,200 |
| `primer.py` | Loader / preprocessor / adapter. Three modes: LLM-assisted, local-deterministic, direct-JSON. Pre-clusters K/U/Ω, deduplicates K-facts, runs Mystery Taxonomy classification, computes content hashes, invokes `cert_engine.certify()`. | ~800 |
| `intel_standardizer.txt` | LLM prompt that ingests raw data feeds (multi-source structured JSON, signal feeds, human reports, sensor descriptors, geospatial coordinates, free-text) and emits DecisionContext JSON. Provider-agnostic. | ~280 |

---

## Install / dependencies

Standard library + `numpy` + `scipy`. `numba` is detected and used for JIT acceleration if available; the engine works without it.

```bash
pip install numpy scipy
# optional: pip install numba
```

No network access required for the engine itself. Only `primer.py --mode llm` requires an outbound API call to the configured LLM.

---

## Operator workflow

Three modes, all run from the command line.

### Mode A — LLM-assisted ingestion (highest fidelity)

```bash
export CERT_ENGINE_LLM_ENDPOINT="https://api.openai.com/v1/chat/completions"
export CERT_ENGINE_LLM_API_KEY="sk-..."
export CERT_ENGINE_LLM_MODEL="gpt-4o"
export CERT_ENGINE_LLM_PROVIDER="openai_compatible"
python primer.py --mode llm --intel-file raw_intel.txt > certificate.json
```

### Mode B — Local-deterministic ingestion (no LLM needed)

```bash
python primer.py --mode local --intel-file raw_intel.txt > certificate.json
```

Lower fidelity than Mode A. Emits more `XI_IGNORANCE` U-elements. Useful for disconnected / edge environments.

### Mode C — Direct-input ingestion (already standardized)

```bash
python primer.py --mode direct --json-file target.json > certificate.json
```

Used when an upstream system (the upstream analytics pipeline / third-party analytics platforms / any platform) has already produced standardized output.

### Direct engine invocation (Python)

```python
import cert_engine
ctx = cert_engine.build_validation_context()  # or your own DecisionContext
cert = cert_engine.certify(ctx)
print(cert.verdict)                # CERTIFIED_GO | ESCALATE_HUMAN | REJECT_INPUT
print(cert.merkle_root())          # 64-char SHA-256 hex
print(cert.to_dict())              # full structured certificate
```

---

## What the engine does

The `certify()` function is the **epistemic furnace**. It accepts a `DecisionContext`, propagates competing world-models (`Hazard_Confirmed`, `Bystander_Present`, `Sensor_Spoof`, `Data_Lag`, `Null_Action`) through the UMA/RSLS dynamics, applies the LexGuard four-gate, defeats hallucinations through Friston-style free-energy injection, computes the Belief Delta (ΔΘ, ΔE, CP), and emits a Merkle-bound `Certificate`.

The certificate carries 18 sections by default, including:

- Context Inventory (K/U/Ω partition, Truth Horizon, provenance)
- Resolution Trail (every U-element addressed)
- Simulated Sequence (per-world-model propagation, λ_max, cone aperture)
- UMA Generative Physics (Hamiltonian, MSR response, Einstein residual, Lindblad density matrix)
- Counterfactual Robustness (eight perturbation types per trajectory)
- Regulatory Compliance Matrix (90+ articles checked: EU AI Act, GDPR, NIST AI RMF, ISO/IEC 42001, IEEE 7000-series, FRE, FRCP)
- Emotive Substrate Analysis (G, V, L, D + augmentations + cohort decomposition)
- Hallucination Cross-Check (six mechanisms, Friston KL divergence)
- Reasoning Chain (narrative + Lean 4 proof sketches)
- Verdict + Belief Delta + Merkle Root
- Legal Admissibility Analysis (Daubert + FRE 702 + FRCP 26)
- Governance Audit (Map/Measure/Manage/Govern phase coverage)
- **Attestation Token** (HMAC-signed, deterministically verifiable)
- Adversarial Probe (programmatic weak-point report)
- Cohort-Decomposed Valence
- PAC-Bounded Confidence Intervals

---

## Verdicts

One of three structured outcomes, never anything else:

- **CERTIFIED_GO**: All gates clear. Hazard_Confirmed alive with R ≥ R_MIN and CP ≥ CP_MIN. All non-target world-models eliminated by evidence. Lyapunov λ_max < critical. All regulatory constraints satisfied. Doctrine envelope in-band.

- **ESCALATE_HUMAN**: Structured questions emitted (typically 3-4 typed packets) each carrying a precise question, the available options, and the consequence projection per option. Types: Domain Expert, Operator, Regulator, Adversarial Reviewer, Executive. The human picks from options; the human does not figure out from scratch.

- **REJECT_INPUT**: Phase A validation failed (entropy gate, pedigree integrity, time budget, authority policy). The input is malformed or adversarial.

There is no `NO-GO`. A decision that cannot be certified is escalated with the specific question the human must answer.

---

## Performance

Median `certify()` time is ~175 ms on a single modern CPU. The aspirational hard target is 5 s; the contractual ceiling is the the upstream analytics pipeline 86 s window. The full 256-test embedded suite runs in approximately 35 s.

Benchmark from inside the engine: `bench_certify()` is available as a Python entry point.

---

## Testing and verification

```bash
python cert_engine.py
```

Runs the embedded 256-test suite and the validation pillar (synthetic high-stakes context). Tests cover: primitives, state machine, K/U/Ω partition, Mystery Taxonomy, reduction operators, world-models, counterfactual pressure, epistemic energy, simulation per-world-model propagation, regulatory walk (90+ articles), emotive substrate, hallucination defeat, certificate format, Merkle reproducibility, doctrine envelope, holographic continuity theory primitives (axioms A1-A10, theorems T1-T8), governance frame emission, LexGuard policy immutability, legal admissibility (Daubert 5 factors, FRE 702 four prongs, FRCP 26), and god-mode tier (attestation tokens, anytime certificate, inverse certification, doctrine envelope Mahalanobis, cross-institution merge, Kuramoto consensus, adversarial probe, cohort-decomposed V, PAC intervals).

The validation pillar exercises the engine end-to-end on a synthetic high-stakes autonomy-class context and asserts `verdict == ESCALATE_HUMAN` with required escalation packet types present.

---

## Research use and boundaries

- **Validator pattern.** The prototype can be explored downstream of an upstream system that emits a `DecisionContext`. It evaluates the supplied context against policies, a bundled regulatory corpus, counterfactual pressure, and implementation-defined invariants. It does not itself authorize, condition, or abort real-world actions.

- **Legal-analysis prototype.** The certificate can format a Daubert / FRE 702 / FRCP 26 analysis section. That feature is not legal advice, expert testimony, a business-record determination, judicial notice, or evidence that a court will admit any output. Consult qualified counsel and independent experts before relying on it in any proceeding.

- **Ledger experiments.** Successive certificates can be Merkle-chained into a `DoctrineLedger` for reproducibility experiments. A chain demonstrates only the records retained by this implementation; it does not create institutional authority, calibrated policy, or a basis for transferring conclusions between organizations.

The Apache-2.0 license governs permission to use the code. Safety boundaries remain: do not use this prototype to weaken oversight, as a substitute for qualified human judgment, or as the sole basis for high-stakes or autonomous action. The certificate is an implementation-generated deliberation record, not the action itself.

---

## What's in `intel_standardizer.txt`

A standalone LLM prompt that any frontier model can execute. It ingests arbitrary raw data feeds (multi-source structured JSON, signal feeds, human reports, sensor descriptors, geospatial coordinates in DMS/DD/MGRS/UTM, time stamps, track histories, identification probability distributions, operating-policy annotations, authority citations, free-text operator notes, partial structured data, contradictory fields, sensor confidence scores, pedigree chains, raw image classifier outputs) and emits a single strictly-formatted JSON object conforming to the `DecisionContext` schema. The output is fed into `primer.py` (Mode A) or directly into `cert_engine.certify()` (Mode C).

---

## Companion documents

- `PRINCIPLES_OF_OPERATION.md` — explanatory companion describing how a serious reader should understand the engine's outputs. Between this README and the theory artifact.
- `HOLOGRAPHIC_CONTINUITY_THEORY.md` — the formal theory artifact underlying the engine's substrate dynamics. Holographic Continuity Theory (HCT) as the scientific theory, the Projection Calculus as its formal apparatus.
- `MANIFEST.md` — file hashes, line counts, test counts, bench timings, regulatory corpus inventory, build state markers.

---

## Author

J. Iannotti, 2026. Licensed under Apache-2.0.

---

## Final notes

The engine is an experimental certification-layer design. Its Merkle ledger is useful for checking the internal continuity of records generated by the same implementation; it does not confer truth, authority, or institutional acceptance.

The certificate records one implementation's evaluation of a decision context. It is not a substitute for the decision process, evidence review, or accountable human judgment.
