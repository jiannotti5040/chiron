# Why Chiron refuses

Chiron is built to answer *or refuse* within an exact, stated boundary. That is
the design: a candidate is not accepted just because it looks plausible.

## The target property: no unsupported verifications

A change that makes an engine stamp something it cannot exactly prove is a
defect — even if every benchmark number improves. This is not a tuning
preference; it is the contract. The value of a `verified` stamp depends on
external tests that can catch false ones. The current published frozen
evaluation grades **22 stamped / 22 externally correct / 0 false stamps / 12
refusals**. An earlier 109-sequence sweep caught three false stamps; the misses
were published, repaired, and re-run with 44 verified and zero false. That
record is evidence of a process, not a claim of infallibility.

So Chiron would rather say **REFUSED** than issue an unsupported **VERIFIED**.
Refusal is a feature, not a failure, when the alternative is a result that
cannot carry its own evidence.

## What "exact" means here

On the path where a claim gets stamped, Chiron uses exact arithmetic —
fractions and exact integer equality, not floating-point "close enough."
Verification is by **held-out prediction**: the rule must reproduce evidence it
was never shown, exactly. If it can't, it doesn't get the stamp. Numbers too
large to represent exactly are refused rather than approximated.

This is why the primes example refuses. A model can be found that fits the given
terms perfectly; Chiron checks it against terms it withheld, sees the prediction
fail, and reports `recovered_unstamped` instead of pretending.

## Falsifiability is required, not optional

A certificate is **rejected at creation** unless it names the exact thing that
would prove it wrong. "I believe this" is not allowed to be recorded; "I believe
this, and here is precisely what would break it" is. This forces every claim the
system memorializes to be the kind of claim that could, in principle, be caught —
which is the only kind worth trusting.

## Why this matters for machine intelligence

As AI systems move into decisions that carry real consequences, the scarce thing
is not capability — it is **warranted confidence**. Plenty of systems will tell
you an answer. Almost none will tell you, precisely and honestly, when they
cannot stand behind one. Chiron's refusal is not a limitation to apologize for.
It is the product.
