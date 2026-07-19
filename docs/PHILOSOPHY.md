# Why Chiron refuses

Every other tool in this space is built to answer. Chiron is built to answer
*or refuse*, and to know the difference exactly. That single inversion is the
whole design.

## The one inviolable property: zero false verifications

A change to Chiron that makes any engine stamp something it cannot exactly prove
is wrong — even if every benchmark number improves. This is not a tuning
preference; it is the contract. The entire value of a `verified` stamp is that a
lie is never allowed to stand: the stamp is policed by live external testing,
and on the occasions that testing has caught a false stamp, the miss was
published the same night and fixed at the root — never quietly absorbed. The
current external battery grades 44 verified, all correct, zero false. A stamp
whose failures are hunted, published, and repaired in the open is the only kind
whose true stamps you can tell from luck.

So Chiron would rather say **REFUSED** than risk a false **VERIFIED**. Refusal is
a feature, not a failure. A calculator that is right 99% of the time is useless
for anything that matters, because you never know which 1% you're holding.

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
