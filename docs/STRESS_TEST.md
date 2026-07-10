# Stress test — where are the holes

*Written 2026-07-10. The vault is being readied to sell, so it was handed to an
adversary whose only job was to break it — the way a buyer's technical diligence
will. This is the honest record: the probes, what held, the holes actually found,
how they were repaired, and — just as important — what has **not** yet been tested.
A repaired defect is worth more than an unblemished claim; this document is that
principle applied to the whole vault.*

The adversary is a committed gate: `Chiron/stress_test.py` (also `chiron test`
runs it, and it is in the manifest). It is not a story about testing — it is the
test, and it stays a regression gate forever. **21/21 probes hold today.**

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
| **P1** | parity has teeth | "spine and fold are one organism" isn't a rubber stamp | a real mutation to the engine's own gate suite makes its selftest **fail** (the gates aren't vacuous); the parity comparator flags a synthetic one-gate divergence and never calls an empty outcome-set "agreement" |
| **P2** | the certificate can't lie | the vault certificate never flatters | a beat with one failed movement can never report `all_movements_green`; the self-hash actually binds the content (tampering changes it); a corrupted certificate is caught, never fatal |
| **P3** | the ledger survives concurrency | operational memory is trustworthy under load | 8 writers × 40 records = 320 whole, valid JSON lines, zero torn or interleaved; the rolling window stays bounded under a 400-record flood and keeps the newest |
| **P4** | the launcher is not a shell | the "run any function" console can't be abused | 11 hostile module names (path traversal, dotted, slashed, `os`/`subprocess`, injection) all rejected; a real sibling still runs; no blocking `serve` verb is ever exposed |
| **P5** | zero false verification, adversarially | the one promise, under fuzz | 240 genuinely-recoverable surfaces verified, **0 false stamps**; 60 adversarial junk strings, **0 crashes** |
| **P6** | certify never blesses a lie | the product itself | false arithmetic → REFUTED (never VERIFIED); true → VERIFIED (never REFUTED); free prose → zero VERIFIED stamps; a false claim buried among true ones and prose is still caught |

---

## What has NOT been stress-tested (honest coverage gaps)

The probes above are real, but a sale deserves to know the edges too:

- **P1 is teeth-by-transitivity, not end-to-end.** It proves the spine's gates
  catch a mutation and the comparator catches a divergence; it does **not** yet
  mutate the 2.7 MB fold in place and run the real `chiron parity` against it.
  That end-to-end mutation test is the stronger version and is not written.
- **Outward growth needs the network.** Inward growth and every gate are fully
  offline, but the heartbeat's *outward* movement pulls from Wikipedia/OEIS. On an
  air-gapped machine, outward beats fail — the certificate reports them honestly as
  not-green, which is correct behavior, but a buyer running offline should expect
  partial beats by design.
- **`certify`'s claim extraction is scoped, not general NLP.** It reliably catches
  checkable arithmetic/structural claims; it does not attempt to parse every
  natural-language assertion. Its discipline is to *refuse* what it cannot check,
  never to bless it — so the failure mode is silence, not a false stamp.
- **The H2 layer does not exist to test.** The President-as-planner and
  certify-before-act for external agents are HORIZON theory; there is nothing to
  stress yet.
- **The certify kernel is battery-proven, not machine-checked.** Formal
  verification of the stamping path is a HORIZON dream, not a current guarantee.

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
