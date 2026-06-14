# Governance

**Architect & sole owner: Jacob Iannotti. Proprietary — all rights reserved.**

The governance frameworks that bound how an automated system is allowed to reason
and recommend. They are specifications, not runtime code: the certification
pipeline (JDICert) implements them as gates, and Chiron carries them as live
laws, but they stand on their own as the doctrine.

### Contents

- **LexGuard** (`LexGuard.pdf`) — a mathematically-derived four-point gate check
  that tests a decision's logic against system and safety parameters before it is
  allowed to ship. The four gates (entropy, standard-of-care, regulatory, and
  counterfactual pressure) collapse complex compliance into a single, auditable
  pass/fail with an escalation path to a human when the model is uncertain.

- **A Standard of Care for Persuasive Machines (SoCPM)** (`A Standard of Care
  for Persuasive Machines .pdf`) — the standard governing AI that makes
  high-stakes recommendations to people, organized across **Map / Measure /
  Manage / Govern**. It defines the duty of care a persuasive system owes the
  human reading it: legibility of reasoning, bounded confidence, and accountable
  provenance.

### How it is used

LexGuard and SoCPM are the governance layer of the certification program. They
are referenced directly by JDICert's gate matrix and are enforced at runtime
inside Chiron (laws L1–L8, the candor discipline, and the escalate-to-human
rule). Read them as the "rules of admissibility" for any decision the systems
produce.
