# Stress test — where are the holes

*Written 2026-07-10. The vault is being readied to sell, so it was handed to an
adversary whose only job was to break it — the way a buyer's technical diligence
will. This is the honest record: the probes, what held, the holes actually found,
how they were repaired, and — just as important — what has **not** yet been tested.
A repaired defect is worth more than an unblemished claim; this document is that
principle applied to the whole vault.*

The adversary is a committed gate: `Chiron/stress_test.py` (also `chiron test`
runs it, and it is in the manifest). It is not a story about testing — it is the
test, and it stays a regression gate forever. **23/23 probes hold today.**

---

## The holes that were found and fixed

Three real findings. Two were defects; one was the adversary catching *itself*
being too weak — which is the discipline working on its own tools.

### HOLE 1 — the headline "no dependencies" claim was false *(fixed: literature)*

The README said the core is *"a single self-contained file with no third-party
dependencies"*; ARCHITECTURE said numpy has *"pure-Python fallbacks"*; CONTRIBUTING
said *"Chiron runs on bare Python."* All three were **untrue**: `Chiron/chiron.py`
(and `Primus/src/primus/engine.py`) import numpy at load, and hiding numpy makes
`import chiron` fail immediately. A buyer's very first `pip install` + run catches
this — in fact Jacob's own first boot did, when the heartbeat's first beat recorded
honest `FAIL` movements for "No module named numpy."

This is exactly the overclaim the project says it *cannot afford*. The honest fix
was not to fake a fallback but to tell the truth: **numpy is the one dependency**,
declared in `Primus/pyproject.toml` (`numpy>=1.22`), installed by `pip install
./Primus`. README, ARCHITECTURE, CONTRIBUTING, and RUNNING were all corrected;
`chiron doctor` checks for numpy; RUNNING carries a first-boot note. Making the
bare `collapse` path genuinely numpy-free is now a tracked item in HORIZON, labeled
as unbuilt rather than pretended-done.

### HOLE 2 — the run ledger grew without bound *(fixed: rolling window)*

The heartbeat appends to `artifacts/run_ledger.jsonl` on every beat, forever. On
an always-on pulse that is a slow disk-exhaustion hole — months of beats, an
unbounded file. Fixed in `run_ledger.py` with a bounded rolling window: past
`MAX_LINES` (20 000) it atomically rewrites the newest `KEEP_LINES` (10 000) via a
temp file + `os.replace`, so a crash mid-rotate leaves the old ledger intact.
History that must survive lives in git and the per-run certificates, not in the
ledger. Probe **P3** now floods the ledger past its cap and asserts it stays
bounded *and* keeps the newest record.

### HOLE 3 — the adversary's own zero-false-verification probe was vacuous *(fixed: stronger adversary)*

P5's first version fed 250 random integer sequences and reported "0 verified, 0
false stamps — PASS." But **0 verified** means the VERIFIED path never fired: random
noise almost never has exact structure, so the probe proved nothing about the one
promise it existed to defend. The fix seeds genuinely-recoverable surfaces
(arithmetic, geometric, Fibonacci-like) alongside the noise, so the VERIFIED path
is exercised **240 times over 510 surfaces** — and *then* asserts zero false stamps.
A test that never triggers the behavior it guards is a hole too.

---

## The probes (what each defends, why it has teeth)

| # | Probe | The claim it attacks | Result |
|---|---|---|---|
| **P1** | parity has teeth | "spine and fold are one organism" isn't a rubber stamp | a real mutation to the engine's own gate suite makes its selftest **fail** (the gates aren't vacuous); **end-to-end**, the real fold's 138 named gate outcomes are run and a real injected divergence is caught by the exact comparator; an empty outcome-set is never called "agreement" |
| **P2** | the certificate can't lie | the vault certificate never flatters | a beat with one failed movement can never report `all_movements_green`; the self-hash actually binds the content (tampering changes it); a corrupted certificate is caught, never fatal |
| **P3** | the ledger survives concurrency | operational memory is trustworthy under load | 8 writers × 40 records = 320 whole, valid JSON lines, zero torn or interleaved; the rolling window stays bounded under a 400-record flood and keeps the newest |
| **P4** | the launcher is not a shell | the read-only console can't be abused | hostile module names, unlisted siblings, option injection, and known growth mutations are refused or escalated; only exact static read-only commands can run |
| **P5** | zero false verification, adversarially | the one promise, under fuzz | 240 genuinely-recoverable surfaces verified, **0 false stamps**; 60 adversarial junk strings, **0 crashes** |
| **P6** | certify never blesses a lie | the product itself | false arithmetic → REFUTED (never VERIFIED); true → VERIFIED (never REFUTED); free prose → zero VERIFIED stamps; a false claim buried among true ones and prose is still caught |

---

## What has NOT been stress-tested (honest coverage gaps)

The probes above are real, but a sale deserves to know the edges too:

- ~~P1 is teeth-by-transitivity, not end-to-end.~~ **Closed 2026-07-10.** P1 now runs the
  real fold's `chiron selftest` (138 named gate outcomes), injects a real divergence into a
  live engine copy, and confirms the exact parity comparison catches it — end-to-end, two
  real runs and the real comparator.
- **Outward growth needs the network — now handled honestly.** The heartbeat probes
  connectivity first; offline, the outward movement records `skipped: offline` as a **neutral**
  event (not a failure), so an air-gapped vault still beats **green** on inward + reflex while
  disclosing the skip. Only a real attempted failure marks a beat red.
- **`certify`'s claim extraction is scoped, not general NLP.** It reliably catches
  checkable arithmetic/structural claims; it does not attempt to parse every
  natural-language assertion. Its discipline is to *refuse* what it cannot check,
  never to bless it — so the failure mode is silence, not a false stamp.
- **The H2 layer is now a testable prototype.** `Chiron/planner.py` composes engines toward
  a goal (observe→analyze→verify→remember→escalate) with the exact gate arbitrating every
  step; 11/11 gates prove an unverifiable surface **halts** at the gate and an irreversible
  step **escalates** rather than executing. Certify-before-act for *external* agents is still
  HORIZON theory.
- **The certify kernel is now property-proven over a bounded grid**, the honest step before a
  proof assistant: `Primus/test_certify_property.py` checks every `a∘b=c` for a,b∈[-10,10],
  ∘∈{+,−,×}, in true and wrong forms — **2646 claims, 0 false VERIFIED, 0 true REFUTED**. Full
  machine-checking of the stamping path remains a HORIZON dream.

---

## How to re-run the adversary

```bash
python3 Chiron/stress_test.py         # the full report
python3 Chiron/stress_test.py selftest  # as a gate (exit 1 on any hole)
python3 bin/chiron test               # runs it inside the whole battery
```

If a future change opens a hole, one of these turns red. That is the point: the
vault's value is not that it has never had a hole — it is that every hole it has
ever had became a gate.
