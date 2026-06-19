# Principles of Operation

*A companion document for serious readers of the certification engine. Read this between the README and the theory artifact. The README tells you how to run the engine; the theory tells you what's underneath it; this document tells you how to think about what comes out.*

---

## What you are looking at

You are looking at a system that turns a high-stakes decision into a cryptographically-bound artifact. The artifact is structured. It is signed. It is replayable. It carries its own legal admissibility analysis. It records its own governance state. It says, in plain operational language, what it concluded and why.

The artifact is called a **certificate**. The system is called **the engine**. The engine is a Python file you ingest into a frontier LLM. When the LLM ingests the file, the LLM becomes the engine. The engine takes a `DecisionContext` and produces a `Certificate`. That is what it does.

It does this in approximately 175 milliseconds of computation against a 5-second aspirational target and an 86-second contractual ceiling.

Everything else is detail.

---

## How to read a certificate

A certificate has eighteen sections. Read them in order. Each section answers a specific question.

**Section 1 — Context Inventory** answers: *What did the engine know at the moment of decision, and what did it explicitly not know?* The K/U/Ω partition is here, with the Truth Horizon Θ_pre value. If Θ_pre is below the threshold (3.0), the engine should have escalated immediately on grounds of insufficient context. If it proceeded anyway, that is a load-bearing finding.

**Section 2 — Resolution Trail** answers: *What did the engine do with the unknowns?* Every U-element is listed with the reduction operator applied (Measure, Reframe, Invent, Model, Dialogue, Explore) and the outcome (RESOLVED, ESCALATED, DEFERRED). This section is the trail of due diligence. An engine that silently passed through unknowns without acting them would have an empty trail; that itself would be a finding.

**Section 3 — Simulated Sequence** answers: *What would happen if the proposed action proceeded?* Per-world-model trajectories under the UMA/RSLS dynamics. Each surviving model's λ_max, cone aperture, final epistemic energy, and counterfactual pressure are reported. Models that died during propagation are reported with the reason (Lyapunov divergence, cone collapse under frame-dragging, free-energy boil-off from ungrounded claims).

**Section 3b — UMA Generative Physics** answers: *What did the physics layer compute?* The complex-field Hamiltonian H[ψ], the MSR response field, the Noether stress-energy tensor T_μν, the Einstein consistency residual (does the cognitive substrate satisfy the linearized Einstein equation, or does it contradict itself?), semantic friction dH/dt with closure detection, the CPTP density-matrix superposition over surviving world-models with von Neumann entropy and validated PSD/Hermitian/trace conditions.

**Section 4 — Counterfactual Robustness** answers: *Does the verdict survive perturbation?* Eight perturbation types per surviving trajectory: intent misreading, missing-fact worst-case, NIST AI 100-2 adversarial categories, sensor spoofing, intel lag, bystander-mask suppression. Each is run; each produces a robustness band. A verdict that depends on a single sensor reading or a single source is fragile and will show as such here.

**Section 5 — Regulatory Compliance Matrix** answers: *What rules apply, and is the proposed action compliant?* 90+ constraints walked, with jurisdiction, instrument, citation, applicability finding, compliance finding, severity class, proposed remediation, source URI. This is the layer that makes the certificate court-admissible. Every constraint cites authoritative external sources (EU AI Act, GDPR, NIST AI RMF, ISO/IEC 42001, IEEE 7000-series, FRE, FRCP).

**Section 6 — Emotive Substrate Analysis** answers: *What's the decision gravity, and does the engine recognize it?* Gravity (heaviest weight for high-stakes autonomy), Valence (negative if affected-party exposure exists), Legitimacy (jurisdictional authority chain), Dignity (hazard/bystander distinction). Augmentations: irreducible_baseline, transcendence_margin, novelty_aesthetic_resonance, value_capture_with_recognition. The Holographic Continuity Theory projection stack output is here (significance geometry, holographic encoding, isometric projection, Cattaneo dynamics, sentiment).

**Section 7 — Hallucination Cross-Check** answers: *Are the engine's load-bearing claims grounded?* Six defense mechanisms per claim: grounding check against K-facts, metamorphic formulation (three independent rewordings), coherence score (must be ≥ 0.95), semantic entropy (must be ≤ 0.7), RAG-against-file, Friston KL divergence injection. A claim that fails any mechanism is removed from the load-bearing set or escalated.

**Section 8 — Reasoning Chain** answers: *In narrative form, what happened?* A composed paragraph threading through the Belief Delta. Citations into the preceding sections. Lean 4 proof sketches for the load-bearing mathematical claims (Lyapunov bound, cone aperture positivity). This section is what an attorney reads when the certificate is challenged in court.

**Sections 9-11** are the verdict, the Belief Delta, the escalation packets, and the Merkle root.

**Section 12 — Legal Admissibility Analysis** is the explicit Daubert / FRE 702 / FRCP 26 walk-through. Each of the five Daubert factors gets a finding (satisfied / challenged / unsatisfied), a basis statement, a citation, an opposing-counsel attack vector, and the documented defense on record. Same for the four FRE 702 prongs and the three FRCP 26(a)(2)(B) disclosure requirements. The section concludes with an `overall_assessment` (`ADMISSIBLE_AS_EXPERT_TESTIMONY`, `ADMISSIBLE_WITH_LIMITATIONS`, `ADMISSIBLE_AS_BUSINESS_RECORD`, or `INADMISSIBLE_AS_PROFFERED`).

**Section 13 — Governance Audit** is the report on the governance timeline: did the LexGuard policy remain constant across all phases? did the Fixed-Invariant partition remain read-only? what SoCPM phases were exercised? did the SBOM gate pass? did the runtime guard abort?

**Section 14 — Attestation Token** is the cryptographic identity binding. HMAC-SHA256-signed claim that binds the engine identity, input hash, output hash, timestamp, nonce, certificate ID, and verdict. Any verifier with the engine file and the shared secret can re-derive the engine identity hash and verify the HMAC. This is the equivalent of a remote attestation in confidential-computing contexts.

**Section 15 — Adversarial Probe** is the engine's self-report of its weak points. For each attack vector an opposing party would credibly attempt, the section names the attack, the evidence supporting it, the engine's on-record defense, and a severity rating. Reading this section is faster than reading the certificate cold.

**Section 16 — Cohort-Decomposed Valence** is V broken down by per-cohort contribution. Bystander, hazard, children, elderly, medical-staff cohorts each carry their own V_cohort component. The aggregate cannot hide a catastrophic per-cohort outcome.

**Section 17 — PAC-Bounded Confidence Intervals** is the Hoeffding-style interval around ΔΘ, ΔE, CP at 95% confidence level. The certificate's claim is "with 95% confidence, ΔΘ ∈ [a, b]", not a point estimate.

---

## How to read the verdict

There are three possible verdicts, and they mean three different things.

**`CERTIFIED_GO`** means: the engine cleared every gate. The proposed action is consistent with the regulatory corpus, the world-model set is reduced to a single surviving hazard-class hypothesis, counterfactual pressure exceeds the minimum for the high-consequence domain, the Belief Delta is in-envelope relative to the doctrine ledger, and the authority policy mode is appropriate for the decision class. The operator is the named countersignatory. The certificate is the action.

**`ESCALATE_HUMAN`** means: the engine could not clear every gate, AND it has identified the specific question(s) a human must answer. The escalation packets are typed (Domain Expert, Operator, Regulator, Adversarial Reviewer, Executive) and each carries a precise question, available options, and the consequence projection per option. The human picks from options; the human does not figure out from scratch what to do.

**`REJECT_INPUT`** means: Phase A validation failed. The input is malformed, adversarial, missing required fields, or violates a security predicate (sensor entropy above threshold, broken pedigree chain, expired time budget, invalid authority policy). The certificate is a refusal, and it identifies the specific gate that failed.

There is no fourth verdict. There is no `NO-GO`. The engine does not refuse a decision without giving the operator a question.

---

## How to read the Belief Delta

ΔΘ, ΔE, CP, surviving_models, λ_max envelope, cone_min envelope.

**ΔΘ (change in Truth Horizon)**: positive means the engine reduced ambiguity. Negative means the engine surfaced more unknowns than it resolved. Zero means the engine deferred (escalation typically yields ΔΘ ≈ 0; the engine did not claim resolution).

**ΔE (epistemic energy resolved)**: positive means contradictions were resolved. Negative means the engine surfaced contradictions that the input had concealed. A large negative ΔE on an ESCALATE_HUMAN verdict means "the engine looked into your context, found contradictions you did not see, and is asking you to resolve them before proceeding."

**CP (counterfactual pressure)**: the total adversarial-survival mass accumulated across surviving world-models. A high CP means the surviving models have been challenged extensively and survived; a low CP means they have not been challenged enough yet. CP < CP_MIN forces an escalation regardless of other gates.

**surviving_models**: the tuple of world-model roles that are still alive at the end of propagation. A `CERTIFIED_GO` must have exactly `("Hazard_Confirmed",)` (or equivalent for the proposed-target model only). An `ESCALATE_HUMAN` will have multiple survivors, each named.

**λ_max envelope**: the maximum across surviving trajectories of the chaotic divergence rate. Above `LYAPUNOV_CRITICAL = 19.4`, the trajectory bundle is runaway-chaotic and the verdict is escalated.

**cone_min envelope**: the minimum across surviving trajectories of the frame-dragging cone aperture. Below zero, the trajectory is ill-posed (the decision is genuinely undecidable on the current evidence); escalation is forced.

The six-tuple Belief Delta is what gets Merkle-chained across certificates. Doctrine is the time-series of Belief Deltas.

---

## What the engine is *not*

It is not a model. The model is the LLM that ingests the engine file. The engine constrains and structures what the model does.

It is not a chatbot. It does not act in dialogue. It accepts a `DecisionContext` and emits a `Certificate`. That is the entire interface.

It is not a moral authority. It checks against the regulatory corpus and the LexGuard gates. The corpus encodes what humans have decided counts as compliance. The engine evaluates the proposed action against that corpus. It does not invent ethics.

It is not a substitute for human judgment. It is an instrument for sharpening human judgment under time pressure. The operator countersignature is what completes the certification cycle.

It is not a verification of the upstream system's correctness. It is a validation of the upstream system's output against an independent regulatory and counterfactual standard. If the upstream system is right, the engine confirms it. If the upstream system is wrong, the engine flags it. If the engine cannot determine which, it escalates.

---

## How to challenge a certificate

If you are an attorney, regulator, auditor, or adversarial reviewer challenging a certificate, the path is:

1. **Verify the attestation token** (Section 14). Re-compute the HMAC with the shared secret. If the signature doesn't match, the certificate has been tampered with and is inadmissible.

2. **Replay the certificate** (`replay_seed` in the certificate header). Re-execute `cert_engine.certify()` on the same `DecisionContext` and verify the Merkle root matches. If it doesn't, either the engine version has changed or the input has been altered.

3. **Read Section 15 — Adversarial Probe** first. The engine has already identified its own weak points. Your job is to argue whether those weak points are dispositive in the specific case.

4. **Read Section 12 — Legal Admissibility Analysis**. The engine has already done the Daubert / FRE 702 walk-through. If you are challenging admissibility, the `challenged_prongs` list is the one to attack. The `documented_defense` list is what the engine has already prepared in response.

5. **Read Section 7 — Hallucination Cross-Check**. Identify any load-bearing claim that the defeat layer barely passed (coherence near 0.95, semantic entropy near 0.7). These are the weakest claims.

6. **Cross-reference Section 5 — Regulatory Compliance Matrix**. If a relevant regulation is missing from the corpus, file a motion to add it; the corpus is data, not code, and the engine accepts new constraints at instantiation.

7. **Examine the governance timeline** (Section 13). If the LexGuard policy hash changed across phases, the Resolution Engine wrote to LexGuard policy memory — that is a structural breach and is dispositive.

---

## What the engine does well

It produces a structured, signed, replayable artifact in approximately 175 milliseconds. It cites every regulatory standard it consults. It surfaces the weak points an opposing party would attack. It tracks belief evolution across decisions in a doctrine ledger. It runs on any frontier LLM. It is vendor-agnostic. It is portable. It is auditable.

---

## What the engine does not yet do well

It uses a regex-based fallback parser in `primer.py` Mode B when no LLM is available; a quantized local NER model would lift production fidelity, and is documented as future work.

It has not yet been stress-tested against a real-world adversarial red team in a non-synthetic context. The internal red-team pass is principled but not exhaustive.

It assumes the upstream system has produced a data fusion / decision proposal that is itself well-formed. It validates outputs, not inputs to the upstream system.

It is calibrated against synthetic data. The PAC bounds and confidence intervals will tighten as operational data accumulates via the doctrine ledger.

---

## The strategic posture

The engine is independent oversight. It does not need access to the upstream system's source code to validate its output. It sits downstream of any proprietary stack — the upstream analytics pipeline, third-party analytics platforms — and either authorizes, conditions, or aborts. It becomes the definitive authority on whether the upstream system is currently meeting its constraints.

The Merkle ledger is the moat. The engine is free; the chain is the strategic asset. Successive certificates accumulate institutional memory. Whoever runs the longest chain has the sharpest doctrine. Allies can ingest the ledger and inherit calibrated envelopes. Adversaries technically could plug in, but the first-mover strategic advantage is the depth of the chain.

That is what is being built. That is what the certificate is for.

---

*This document is part of the certification engine deliverable. It is intended for serious readers who need to understand the engine's outputs without reading the formal theory artifact. The README is for operators. The theory artifact is for technical reviewers. This is for everyone in between.*
