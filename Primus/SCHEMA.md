# primus.certificate/2 — the certificate contract

**Author: Jacob Iannotti. Licensed under Apache-2.0 (see the repository-root [LICENSE](../LICENSE)).**

This is the written contract for consumers of `primus.certify` output —
agents, CI gates, and pipelines. Read the first section even if you read
nothing else.

## What a passing gate means — and does not

`counts.refuted == 0` means exactly one thing: **nothing checkable was
refuted.** It does NOT mean the output is true, safe, or complete. A wrong
claim phrased outside the extractor's patterns is not extracted, not
checked, and not caught. That blind spot is structural to any claim
extractor; this one differs only in admitting it. Before trusting a pass:

- read `coverage` — the fraction of input characters consumed by checked
  claims. A pass at coverage 0.02 certifies almost nothing.
- read `unverifiable_remainder` — `true` whenever meaningful free text
  remains outside the checked spans. It almost always is.
- treat everything unverified as exactly that: unverified.

## Statuses (per claim)

| Status | Meaning |
|---|---|
| `VERIFIED` | Exactly checked and holds (exact rational arithmetic, or held-out prediction for sequences). |
| `REFUTED` | Exactly checked and false. The exact value is included where meaningful (`expected` / `predicted`). |
| `REFUSED` | No exact proof either way: outside the engine's hypothesis classes, beyond exact-arithmetic bounds, beyond the deterministic Miller–Rabin bound, unparseable dates, or over a work cap. Refusal is a first-class outcome, never an error. |

## Claim kinds (v2)

`arithmetic` — `a op b = c` and `c = a op b`, with the operator written
either symbolically (`+ - * / x × ^ **`, powers bounded) or in words (`plus`,
`minus`, `less`, `times`, `multiplied by`, `divided by`), and the equality as
`=`, `is`, `equals`, `totals`, `comes to` or `leaves`. Also the unit-price
form `N units at P each is T`, which is read as a product. A match that is
only part of a longer chain is REFUSED rather than judged, in either notation:
the kernel evaluates one binary operation and cannot know the precedence of
the rest.

Numerals may carry thousands separators (`1,240`, `12,345,678`). A group is
exactly three digits and must not be followed by another digit, so `1,24` is
not read as grouped, and a separator is stripped only after the pattern has
decided the token is one number — `sum of 3, 4 and 5` remains three values.

`percentage` (`P percent of B is V`, the appositive `P percent of B, or V`,
and the share form `A of B, or P percent`), `difference` (`from A to B, an
increase of D` / `a decrease of D`; the endpoints and the delta all lie
inside the match, so the claim is closed. A stated direction that
contradicts the endpoints is a genuine refutation. A *percentage* change is
a rate, not a difference, and is not extracted at all),
`primality` (deterministic Miller–Rabin below
3.3×10²⁴; refused above), `binomial` (`C(n,k)`, `n choose k`, n ≤ 100000),
`modular` (`a mod m = c`, `a ≡ c (mod m)`),
`date_arithmetic` (`N days after/before DATE is DATE`, `days between A and
B is N`; unambiguous formats only, no year → refused), `aggregate`
(sum/total/average/mean/product of a listed number set, exact rationals; a
product whose operands together exceed the exact-arithmetic digit bound is
REFUSED rather than computed),
`sequence_continuation` (generator recovered from the stated prefix with
held-out proof, continuation compared exactly), `closed_form`
(`a(n) = <expr> matches t0, t1, ...`, optional `(n from k)` offset; the
expression — integers, `n`, `+ - * / ^` with constant exponents ≤ 64 —
is evaluated in exact rational arithmetic at EVERY index and must equal
every listed term; a pole or non-integer value at a required index is a
refutation; parse failures and bound violations are refusals. This is the
claim shape `primus.conjecture` emits, so guess-and-prove output
round-trips through the gate), `sequence` (bare integer runs, structural
recovery or refusal).

**Rounded percentages refuse rather than refute.** A percentage that is not
exact, but *is* the correct rounding of the exact value at the precision
written, is REFUSED: `1 of 3, or 33 percent` has no exact proof either way,
because the document does not state its rounding convention. Precision comes
from the figure as written (`33` to the unit, `66.7` to a tenth), and both
round-half-up and round-half-even are accepted. A figure that is not even a
correct rounding — `1 of 3, or 40 percent` — is REFUTED normally. Rounding is
a reporting convention, not a falsehood, and a gate that refutes conventions
invents errors; that costs exactly as much as missing them.

`gcd` / `lcm` — `gcd(a, b) = c` and `lcm(a, b) = c`, in symbolic or worded
form, checked by exact integer computation. Operands beyond the
exact-arithmetic digit bound are REFUSED rather than computed. These are
emitted under the operator's own name, so the claim kind is literally `gcd`
or `lcm`.

`grounded_fact` — a claim whose truth lives *outside* the sentence, checked
against facts the caller supplies alongside the text (see
[`grounded.py`](src/primus/grounded.py), schema `primus.grounded/1`). VERIFIED
requires that the subject resolve to exactly one supplied fact **and** that the
semantic units be equal, where "no unit" is a unit matching only "no unit"; a
magnitude (`M`, `thousand`) scales the number and is not a unit. Absent,
ambiguous, or unit-mismatched subjects are REFUSED, never guessed. Subjects
are matched exactly after normalisation — nothing is stemmed, so a singular
claim against a plural fact refuses and names the nearest supplied subject.
This kind appears only when the caller passes `facts`.

**Deliberately not judged:** approximations (`sqrt(2) = 1.414` is neither
verified nor refuted — it is not extracted; the gate refuses to grade
"approximately true" claims as exact ones), multi-operation expressions,
unit conversions (planned), and anything requiring outside knowledge.

## Adversarial bounds (all recorded in the certificate)

Input truncated at 100,000 chars (`input.truncated`); at most 200 claims
checked (`claims_capped`); integers beyond 4,096 digits refused, not
computed; sequence claims beyond 256 terms refused, not collapsed; power
claims bounded (exponent ≤ 64, base < 10⁹); digit runs are clamped and
pattern scanning is anchor-windowed so pathological input bounds work
instead of multiplying it. Same input → same certificate (minus timestamp
and attestation).

## Fields

```
schema                  "primus.certificate/2"
engine                  {name, version}
owner                   author attribution string
created_utc             ISO-8601 UTC timestamp
input                   {sha256 (over the ORIGINAL, untruncated text), chars, truncated}
claims[]                {kind, text (≤100 chars), status, span, ...kind-specific detail}
counts                  {checkable, verified, refuted, refused}
grounding               present ONLY when the caller supplied `facts`:
                        {schema: "primus.grounded/1", claims[], counts,
                         facts_supplied, facts_rejected, note}
coverage                checked-span chars / analyzed chars, 0..1
claims_capped           true if MAX_CLAIMS was hit
unverifiable_remainder  true if meaningful text remains outside checked spans
verdict                 one honest sentence; never a blanket blessing
meta                    caller-supplied passthrough (optional)
attestation             {sha256, kind: "tamper-evident-hash"}
```

## Attestation honesty

`attestation.sha256` is a hash over input digest + certificate body. It is
**tamper-evident, not unforgeable** — anyone can recompute it after
modifying a certificate. It detects accidental corruption and casual
tampering; it does not prove who issued the certificate. For cryptographic
provenance, sign certificates externally (the Merkle-chained machinery in
[`../JDICert`](../JDICert) is the in-vault path).

## Versioning

The `schema` string is a **major** version. It bumps on any change that could
break a consumer reading the previous contract: a field removed or renamed, a
field's meaning changed, or a status gaining new semantics (`/1` → `/2`
removed nothing but redefined enough to warrant it, and added: coverage,
claims_capped, input.truncated, span, attestation.kind, and the v2 claim
kinds). Consumers should tolerate unknown extra fields and hard-fail on an
unknown schema major.

**Additive-only changes do not bump the major**, precisely because consumers
are told above to tolerate unknown extra fields — a bump for a purely additive
change would hard-fail every consumer for something it was instructed to
ignore. New claim kinds and new optional top-level blocks are additive: a
consumer that has never heard of `grounded_fact` still reads every other claim
correctly.

Disclosed rather than papered over: an earlier wording of this section said the
string bumps on *any* field addition. Under that wording, adding the optional
`grounding` block in 0.8.0 and the `gcd` / `lcm` / `grounded_fact` kinds should
each have bumped the major, and none did. The rule as written contradicted the
consumer guidance three lines above it; the rule is now stated in the form the
code has actually followed. Nothing about an existing field changed, so no
consumer of `/2` was ever broken — but the contract said something it did not
do, and that is worth naming.
