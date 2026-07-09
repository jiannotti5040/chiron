# Known Limitations

A project that hides its failure modes asks you to take it on faith. This one
doesn't. Below is where Chiron stops working, where it works but shouldn't be
trusted blindly, and what its guarantees do and do not mean. Every claim here is
reproducible with the commands in [WHY_CHIRON.md](WHY_CHIRON.md).

## What "verified" means — and does not

`verified: true` means exactly one thing: the recovered generator predicted the
**held-out terms** of *this* surface exactly, in exact arithmetic. It does **not**
mean the rule is the "true" generator in any platonic sense, only that it is the
minimal one consistent with the evidence and that it survived a held-out test.
Two different rules can fit a short prefix; with more terms held out, spurious
fits fail verification. Short inputs are therefore weaker evidence than long ones.

## Where collapse fails or abstains

- **Natural-language prose.** Exact-recovery yield is low — single digits of
  percent — and that is by design, not a bug: prose rarely has an exact
  generator. Chiron mostly abstains on prose. If you need semantics, similarity,
  or summarization, this is the wrong tool; use an embedding/LLM approach.
- **Number-theoretic sequences without a closed form.** Primes, partitions,
  Euler totient, divisor counts and sums, Bell numbers, nⁿ — Chiron abstains.
  These are not in its hypothesis classes (constant, arithmetic, geometric,
  polynomial, linear-recurrence, holonomic, periodic, multiplicative,
  alternating, interleaved). Abstention is the correct behavior, but it *is* a
  ceiling: it will not discover a generator outside those classes.
- **Irrational / floating-point surfaces.** Recovery is built on exact rational
  arithmetic. Genuine floats (measured data with noise, transcendental
  constants) fall to a separate, weaker path; do not expect exact laws there.
- **Very short surfaces.** Fewer than ~3–4 terms cannot be collapsed with
  confidence; there isn't enough to hold out.

## Where it works but you should look twice

- **Ciphers: 42 of 44 in the benchmark, not 44.** The two misses are *decoder
  collisions*: a hex or base64 string can also be a plausible input to another
  decoder, and the English-likeness scorer occasionally ranks the wrong one
  first. The solver covers classical schemes only (Caesar/shift, Atbash, ROT13,
  A1Z26, Base64, hex, binary, Morse, reversal). It does **not** break modern
  cryptography, polyalphabetic ciphers (e.g. Vigenère), or anything keyed.
- **Held-out verification can still be fooled by very short inputs.** See above —
  more held-out terms is strictly stronger.

## Scaling and performance limits

- The engine is exact and single-threaded in its core search. Hypothesis fitting
  is cheap for the sequence lengths it targets (tens of terms); it is not built
  to collapse multi-megabyte inputs in one pass.
- The optional native hot-path (`bench-native`) accelerates polynomial-degree
  detection where a C compiler exists, but the pure-Python fallback is the
  always-available path — performance, not capability, differs.
- The growable memory ("Congress") compacts to stay value-dense, but it is a
  local content-addressed store, not a database; it is not designed for
  concurrent multi-writer use.

## Ambiguity limits

When two generators tie within the MDL margin, the engine breaks the tie toward
the canonically simpler class and reports the margin. A near-tie is reported, not
hidden, but it means the choice is less certain — read the margin in
`topk` / `trace` output rather than trusting the winner alone.

## Scope and provenance honesty

- The recovered rules are **rediscoveries of known structure**, not novel
  mathematics. On OEIS it re-derives what is already classified.
- The certification core (JDICert) is built to civilian regulatory standards but
  has **not** been through external legal or third-party audit; its certificates
  are auditable, not "court-admissible" in any tested sense.
- The theory layer (Holographic Continuity Theory, Projection Calculus, SoCPM,
  and related) is **self-developed and not peer-reviewed**. It is scaffolding and
  working theory, offered as exploration, not established result.
- Bounded self-growth applies source changes only behind a reversible backup and
  a full passing self-test, but it is **operator-initiated**, not autonomous
  emergence, and it is gated off by default.

## What would change these limits

Wider hypothesis classes would lift the number-theoretic ceiling; a keyed-cipher
module would extend decoding; external audit would change what can be claimed
about JDICert; peer review would change the status of the theory. None of that is
claimed today, and the benchmark measures only what is built.
