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

`arithmetic` (`a op b = c` and `c = a op b`; ops `+ - * / x × ^ **`, powers
bounded), `percentage`, `primality` (deterministic Miller–Rabin below
3.3×10²⁴; refused above), `binomial` (`C(n,k)`, `n choose k`, n ≤ 100000),
`gcd` / `lcm`, `modular` (`a mod m = c`, `a ≡ c (mod m)`),
`date_arithmetic` (`N days after/before DATE is DATE`, `days between A and
B is N`; unambiguous formats only, no year → refused), `aggregate`
(sum/total/average/mean of a listed number set, exact rationals),
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

The `schema` string bumps on any field addition, removal, or semantic
change (`/1` → `/2` added: coverage, claims_capped, input.truncated, span,
attestation.kind, and the v2 claim kinds). Consumers should tolerate
unknown extra fields and hard-fail on an unknown schema major.
