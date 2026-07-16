# Examples — real output, reproducible today

These three files are **actual output from the Chiron engine**, not illustrations.
Regenerate them yourself from the licensed engine (or see the runnable
[`../prototype/`](../prototype/) for a taste that needs no license).

### `verified.json` — a claim it can prove
Input: `2 4 8 16 32 64`. Chiron recovers a geometric generator from the first
four terms and **confirms it against the last two, which it was not given**, in
exact arithmetic. `verified: true` is earned by held-out prediction, not by
fitting. It also reports the MDL compression (69 bits of surface → 14 bits of
rule) — the measure of *why* this rule and not a more complicated one.

### `refused.json` — a claim it will not fake
Input: `2 3 5 7 11 13 17` (the primes). Chiron finds a model that reproduces
every term you gave it — and then **refuses to stamp it** because its prediction
of the held-out terms failed (0/2). Status: `recovered_unstamped`,
`verified: false`. This is the whole product in one file: a system that fits the
data but tells you it cannot prove the rule. Nothing else in the market
volunteers "I don't know" this precisely.

### `certificate.json` — the artifact you keep
Every run can emit a signed certificate: a **machine view** (the exact evidence),
a **human view** (what was found, why it's believed, and the confidence), and —
required on every certificate — **`what_would_falsify`**, the specific thing that
would prove the claim wrong. A claim you cannot state a refutation for is not
allowed to be certified. This is the object an auditor, a regulator, or your own
future engineer can check.

---

*These certify integer-sequence recovery — the cleanest way to *show* exact
verification and refusal. The licensed engine applies the same
recover → prove-on-held-out → refuse-or-certify discipline to code, structured
claims, policy checks, and governed decisions.*
