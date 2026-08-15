# Birch and Swinnerton-Dyer: the historical record, the live frontier, and what this vault can actually do about it

**Author: Jacob Iannotti. Licensed under Apache-2.0 (code) / CC BY 4.0 (prose).**

> ### ⚠ Corrections, 2026-08-11 — three claims withdrawn
>
> An independent audit found this report's originality claims false. They are
> corrected in place below; this notice is here because a reader of the
> rendered document would otherwise not know a correction had happened.
>
> 1. **"Every published `Sha_an`, LMFDB's included, is a rounded float
>    quotient"** and **"never once … a procedure capable of returning no"**
>    (§ *The flaw in the existing record*, § 7) — **false**. Rank-0/1 analytic
>    Sha is computed *exactly*. Demonstrated, not merely cited:
>    `studies/exact_rank0_sha/` reproduces this report's own battery in exact
>    rationals from modular symbols, with no float and no rounding anywhere
>    (11.a2→1, 15.a1→1, 37.b1→1, 571.b1→4). Sage's `L_ratio()` is exact for
>    semistable curves, and Miller (arXiv:1010.2431) proved the full BSD
>    formula for 16,714 specific curves in 2011. The float-rounding gap is
>    real but lives at **rank ≥ 2**.
>
> 2. **"Not one curve of analytic rank ≥ 2 has an unconditional proof that its
>    Mordell–Weil rank matches"** (§3.8) — **false**. It confuses the absence
>    of a general theorem with the absence of every instance. See
>    `studies/rank2_389a1/`, which certifies analytic rank exactly 2 for 103
>    curves of conductor 389–11467.
>
> 3. **"Zero floats, zero trust in anyone else's arithmetic"** (§7) — **false
>    as written**. The torsion bound called binary floating-point
>    exponentiation and π was enclosed by trusting a hard-coded decimal.
>
> Separately, the shared primality gate certified the composite
> `318665857834031151167461 = 399165290221 × 798330580441` as **prime** — a
> false VERIFIED under the vault's own zero-false-verification rule. Fixed
> 2026-08-11 by deriving the Miller–Rabin bound from the witness list;
> see `Primus/EXTERNAL_VALIDATION.md`.
>
> None of this affects the report's central honest claim: **nothing here
> proves BSD, and nothing here claims to.**

**Epistemic status, stated per vault convention and enforced throughout:**

| Part | Status |
| --- | --- |
| §1–§4 (history, results, obstructions) | **Reported.** Standard published mathematics, attributed. Not certified by this repository. |
| §5 (the proposed programme) | **Theory.** A strategy argument, not a result. |
| §6–§8 (`uma/bsd`) | **Implemented-and-tested.** 30/30 pytest gates, 4/4 validation battery, 6/6 controls, on this machine, today. |
| §9 (the oversight) | **Measured.** A count over `eval/triage.json`, reproducible. |

Nothing here proves BSD, and nothing here claims to. The claim that *is* made,
in §7, is narrow and exact.

---

## 1. The statement, and which parts are open

Let `E/Q` be an elliptic curve, `L(E, s)` its Hasse–Weil L-function.

**Rank conjecture (BSD I).** `ord_{s=1} L(E, s) = rank E(Q)`.

**Strong / refined conjecture (BSD II).** Writing `r` for that common value,

```
    L^(r)(1)          Omega_E * Reg_E * prod_p c_p * |Sha(E)|
    --------   =      ----------------------------------------
       r!                       |E(Q)_tors|^2
```

with `Omega_E` the real period, `Reg_E` the regulator of the Néron–Tate height
pairing, `c_p` the Tamagawa numbers, and `Sha(E)` the Tate–Shafarevich group —
whose **finiteness is not known** and is itself part of the conjecture.

Three separate things are open, and conflating them is the most common error in
informal accounts:

1. the rank equality (BSD I);
2. the finiteness of `Sha`;
3. the exact formula (BSD II), which presupposes (2).

`L(E, s)` even *having* an analytic continuation to `s = 1` was itself open
until modularity — so for thirty years the conjecture's own statement was
conditional.

## 2. Origin: the conjecture is computational in its DNA

Birch and Swinnerton-Dyer computed on the **EDSAC II** at Cambridge through the
early 1960s, tabulating `prod_{p<X} N_p/p` for curves of known rank and observing
growth like `C (log X)^r`. The conjecture was read off a plot. This matters for
what follows: BSD is the one Millennium Problem that was *discovered by
numerical experiment*, and it is the one whose statement still reduces, on any
single curve, to a checkable numerical assertion. That is not a coincidence and
it is the hook §6 hangs on.

Their published form (J. reine angew. Math., 1965) already contained the refined
constant, including the `Sha` factor, before anyone could compute `Sha`.

## 3. The proof record — what is actually theorem

### 3.1 Coates–Wiles (1977)
For `E/Q` with complex multiplication by an imaginary quadratic field of class
number 1: `L(E,1) != 0` implies `E(Q)` finite. The first crack — one direction,
one special class.

### 3.2 Gross–Zagier (1986)
For modular `E` and suitable imaginary quadratic `K`, the Néron–Tate height of a
**Heegner point** equals (a constant times) `L'(E/K, 1)`. Converts an analytic
derivative into a point of infinite order. This is the reason **rank ≤ 1 is
tractable and rank ≥ 2 is not**: there is exactly one Heegner point to spend.

### 3.3 Kolyvagin (1988–90)
The **Euler system** of Heegner points. If a Heegner point is non-torsion then
`rank E(Q) = 1` **and** `Sha(E)` is finite. Combined with Gross–Zagier:

> **Theorem (Gross–Zagier + Kolyvagin).** If `ord_{s=1} L(E,s) <= 1`, then
> `rank E(Q) = ord_{s=1} L(E,s)` **and `Sha(E)` is finite.**

This is the single strongest unconditional result and it has not been surpassed
in kind for thirty-five years. Note what it does *not* give: the exact formula,
and anything at all when the analytic rank is ≥ 2.

### 3.4 Wiles / Taylor–Wiles / BCDT (1994–2001)
Modularity of all `E/Q`, which supplies the analytic continuation the conjecture
needs to even be stated, and makes §3.2–§3.3 unconditional.

### 3.5 Kato (2004), Skinner–Urban (2014), and the Iwasawa route to BSD II
Kato's Euler system of zeta elements gives one divisibility in the Iwasawa Main
Conjecture; Skinner–Urban supply the converse under hypotheses. Together they
yield the **`p`-part of the exact formula in analytic rank 0 and 1**, for most
`p`. Later work (Castella, Burungale, Wan, Sprung, and others; see
[Burungale–Castella–Skinner, *Base change and Iwasawa Main Conjectures for GL₂*](https://arxiv.org/abs/2405.00270),
and Castella–Ciperiani–Skinner–Sprung at non-ordinary primes) removes
ramification hypotheses and covers supersingular `p`. This is how BSD II is
being proved: **one prime at a time.**

### 3.6 Zhang, and the converse
Wei Zhang's proof of Kolyvagin's conjecture, and the converse theorems
(Skinner; Zhang; Burungale–Tian), give `rank = 1 => ord L = 1` — closing the
loop in rank 1 rather than only one implication.

### 3.7 The statistical results
- Bhargava–Shankar: bounded average rank via geometry-of-numbers on Selmer groups.
- **[Bhargava–Skinner–Zhang (2014): a majority — over 66% — of elliptic curves over `Q`, ordered by height, satisfy BSD I.](https://arxiv.org/abs/1407.1826)**
- Alex Smith's `2^∞`-Selmer distribution work, which resolves Goldfeld-type
  statements about ranks of quadratic twists.
- Burungale–Skinner–Tian–Wan: first infinite families of quadratic twists of
  **non-CM** curves satisfying the **strong** conjecture.

**Read the 66% correctly.** It is a statement about density under a height
ordering, and it is achieved *precisely by showing most curves have analytic
rank ≤ 1* — i.e. by routing into §3.3. It is not partial progress on rank ≥ 2;
it is a proof that rank ≥ 2 is rare, which is a different thing.

### 3.8 Where the frontier sits, in one line

> **Everything unconditional flows through rank ≤ 1: there is no general
> theorem giving rank equality in analytic rank ≥ 2.**

<!-- CORRECTED 2026-08-11. This read "Not one curve of analytic rank >= 2 has
an unconditional proof that its Mordell-Weil rank matches", which confuses the
absence of a general theorem with the absence of any certified curve.
Individual rank-2 and rank-3 curves do have rigorously determined algebraic
and analytic ranks -- LMFDB documents rigorous analytic ranks through 3 across
its complete low-conductor range, and studies/rank2_389a1/ certifies 389.a1
here: 2-descent returns the unconditional interval [2,2], the modular symbol
gives L(E,1) = 0 exactly, and L''(E,1)/2 is enclosed in a ball excluding zero.
What is missing in rank >= 2 is the general theorem, not every instance. -->


## 4. Why rank ≥ 2 is hard — the actual obstruction

The Euler-system method needs a supply of algebraic classes whose behaviour is
governed by L-values. Heegner points provide **one**. To reach rank 2 you need
two independent classes controlled by `L''`, and the modular curve does not
supply them: the relevant Selmer group has rank 2 while the available Kolyvagin
classes span at most 1 dimension.

Candidate escapes, all partial:

- **Higher-rank Euler / Kolyvagin / Stark systems.** (Mazur–Rubin; Burns–Sakamoto–Sano.) The formalism exists and is elegant; the *inputs* — the actual higher-rank classes — largely do not.
- **Beilinson–Flach and diagonal-cycle classes** in `GL2 x GL2` and triple-product settings (Bertolini–Darmon–Rotger, Darmon–Rotger). These generate genuinely new classes, and they are the most promising line, but they attach to the rank-2 situation only under strong hypotheses.
- **Arithmetic of `Sha` directly** via `p`-descent and visibility (Cremona–Mazur). Constructs elements of `Sha`; does not bound it.
- **`p`-adic BSD** (Mazur–Tate–Teitelbaum). A parallel conjecture with its own exceptional-zero phenomena; progress there does not transfer directly.

There is no known mechanism that produces `r` independent classes for arbitrary
`r`. That is the wall, and it is structural, not technical.

## 5. What an overarching solution would have to look like

Stated as strategy, not result. Any complete proof must supply **four**
components; every historical attempt has supplied at most two.

**(A) A source of algebraic classes of arbitrary rank.** The single hardest
requirement. The honest candidate is the conjectural theory of higher
Gross–Zagier / Beilinson-type cycles on higher-dimensional Shimura varieties,
where `L^(r)(1)` should pair against an `r`-dimensional space of cycles. The
arithmetic intersection theory needed (Kudla's programme, Yuan–Zhang–Zhang's
work on arithmetic theta lifts) is exactly the machinery under construction.

**(B) A finiteness mechanism for `Sha` that does not presuppose rank ≤ 1.**
Kolyvagin's bound is the only unconditional route and it is rank-bounded by
construction. An alternative would be a global Euler characteristic / Iwasawa
Main Conjecture at *all* primes simultaneously — which is why the "one prime at
a time" programme in §3.5 matters more than its incrementality suggests: if the
`p`-part were known for all `p` with a uniform bound, `Sha` finiteness follows.

**(C) A descent that terminates.** Full `p`-descent terminates iff `Sha[p^∞]`
is finite — circular. Breaking the circle needs (B).

**(D) An exactness argument for the constant.** This is where the Tamagawa
number conjecture (Bloch–Kato) subsumes BSD II. Arguably the right frame is not
to prove BSD but to prove Bloch–Kato for `h^1` of an elliptic curve.

**The honest strategic assessment.** The realistic sequencing is
**(B) → (C) → (A) → (D)**, not the reverse: the `p`-adic Iwasawa programme is
the only component making steady unconditional progress, and it is the only one
that could plausibly deliver `Sha` finiteness in the next decade without a new
geometric idea. Component (A) requires mathematics that does not yet exist. Any
claim of an imminent full proof that does not say concretely how it produces
rank-`r` classes is not making a claim about BSD.

**And one structural point that shapes everything below:** BSD is not going to
be settled by computation. But BSD is *falsifiable* by computation, and the
falsification test has never been run exactly. That asymmetry is the opening.

---

## 6. The opening: BSD has finite refutable content, and no one checks it exactly

Fix a single curve `E` of analytic rank 0. Then `Reg_E = 1` and the strong
conjecture collapses to

```
    Sha_an(E)  :=  L(E,1) * |E(Q)_tors|^2 / (Omega_E * prod_p c_p).
```

BSD asserts this is `|Sha(E)|`. Two consequences are checkable on one curve:

- **(i) it is a positive integer**;
- **(ii) it is a perfect square**, because on a finite `Sha` the Cassels–Tate
  pairing is alternating and non-degenerate.

**Either failing on any single curve refutes BSD outright.** No asymptotics, no
quantifier over curves, no infinite search. One curve, finite time.

This is exactly the shape of obligation that `studies/famous_conjectures.py`
exists to find: *named open conjectures with finite refutable content*.

### The flaw in the existing record

`Sha_an` is a ratio of two transcendental-looking reals asserted to be a
rational integer. **In rank ≥ 2** that is how it is generally obtained:
dividing two floating-point numbers and rounding to the nearest integer.

Rounding-to-nearest is where the falsification test dies. It maps a lawful
`4.0000000` and a hypothetical `3.9999997` to the same reported `4`. **No amount
of extra precision repairs this**, because the defect is not precision — it is
that the procedure has no verdict other than "the nearest integer". A genuine
counterexample would be silently rounded into agreement and never seen.

So the gap is real, but it lives at **rank ≥ 2**, not everywhere.

<!-- CORRECTED 2026-08-11. This section previously claimed that EVERY published
Sha_an, LMFDB's included, is a rounded float quotient, and concluded that the
falsifiable content of a Millennium Problem had "never once" been evaluated by
a procedure capable of returning "no". Both are false, and the correction is
demonstrated rather than cited: studies/exact_rank0_sha/ computes Sha_an for
this report's own rank-0 battery entirely in exact rationals, from PARI's
modular symbols, with no float and no rounding anywhere --

    11.a2 -> 1     15.a1 -> 1     37.b1 -> 1     571.b1 -> 4

all matching the published values, and 389.a1 giving L(1)/Omega = 0 exactly.
A wrong value comes out non-integral there rather than rounding into
agreement, which is exactly the "no" this section said did not exist. LMFDB's
reviewed knowledge page states that rank-0/1 analytic Sha is rational and was
computed exactly for every curve in the database; Sage's L_ratio() is exact
and provably correct for semistable curves; and Miller (arXiv:1010.2431)
proved the full BSD formula for 16,714 specific low-rank curves in 2011.
Only rank >= 2 values are generally stored as rounded approximations. -->


## 7. `uma/bsd` — the exact gate

**Status: implemented-and-tested.** 30/30 pytest gates, 4/4 battery, 6/6
controls.

The module computes `Sha_an` as a **closed interval with dyadic rational
endpoints and outward rounding at every step**, so the interval provably
contains the true value. Nothing is ever rounded to a nearest value. Then:

| Outcome | Verdict |
| --- | --- |
| the enclosure contains **no positive integer** | **REFUTED** — `Sha_an` is provably not a positive integer |
| it contains integers but **no perfect square** | **REFUTED** — contradicts Cassels–Tate |
| it contains **exactly one integer, and it is `m^2`** | **CONSISTENT**, pinned to `m^2` |
| it contains **several** integers | **REFUSED** — insufficient precision, raise `rig.PREC` |

`CONSISTENT` is deliberately *not* called `VERIFIED`. Pinning `Sha_an` for one
curve is not a proof of BSD there; it is an exact statement of what BSD
predicts there. Writing it up as verification would be exactly the overclaim
this repository cannot afford.

### What is exact, and what is enclosed

Exact integer arithmetic, no approximation anywhere:
`b`- and `c`-invariants, discriminant, minimality proof, reduction types,
conductor, Tamagawa numbers, root number, `a_p` by point counting, `a_n` by
Hecke recursion, and `|E(Q)_tors|` by an **exhaustive** Nagell–Lutz search over
a range that is *computed and proven complete*, not assumed.

Rigorous enclosures, never point estimates: `pi`, `exp`, `sqrt`, `AGM`, the
largest real root of the 2-division cubic, `Omega_E`, `L(E,1)`.

### The period, done uniformly

The usual treatment splits on `sign(Delta)` and reaches for a complex AGM when
`Delta < 0`. Substituting `x = e1 + 1/u^2` on the unbounded branch and then
Gauss's `w = t - sqrt(Q)/t` gives, for **both** signs,

```
    Omega_inf = 2 pi / AGM( 2 Q^(1/4),  sqrt(2 sqrt(Q) + P) ),
    P = 3 e1 + b2/4,        Q = h'(e1)/4 = 3 e1^2 + (b2 e1 + b4)/2,
```

with `Omega = 2 * Omega_inf` exactly when `Delta > 0` (two real components).
`Q > 0` in both cases — it is `(e1-e2)(e1-e3)` when the roots are real and
`|e1-e2|^2` when they are conjugate — so **no complex arithmetic appears
anywhere**, and the only non-rational input is the root `e1`, which enters
solely as a bisection bracket whose every sign test is exact.

### Domain, and why the refusals are where they are

Semistable `E/Q`, minimal model, root number `+1`, `L(1)` enclosure provably
bounded away from `0`. Semistability makes three things exact at once: the
conductor is the radical of `Delta`; every `c_p` is `v_p(Delta)` or
`gcd(2, v_p(Delta))`; and the root number is `(-1)^(1 + #split)`. Outside it,
all three need the wild part of Tate's algorithm and local root numbers at 2
and 3 — not implemented, therefore refused. A smaller claim honestly made.

### The controls — the gate must be able to fail

A validation battery that only agrees proves nothing, so six controls try to
break it:

| Control | What it proves |
| --- | --- |
| `wrong_period_factor_detected` | Dropping the two-components doubling on `15.a1` yields `Sha_an = 2` — an integer (so an integrality test alone would pass it) but **not a square**, so Cassels catches it. |
| `largest_real_root_is_used` | Asserts the root used has exactly 2 distinct real roots below it. |
| `split_test_routes_agree` | The fast Euler-criterion split test agrees with slow point counting on every bad prime where both apply. |
| `additive_reduction_refused` | `27.a3` is refused, not estimated. |
| `rank_one_refused` | `37.a1` (rank 1, root number `-1`) is refused, not forced. |
| `perturbed_curve_moves` | Perturbing one coefficient changes the answer. |

**The first two controls earned their keep during construction.** The initial
`largest_real_root` used plain sign-change bisection, which on a cubic with
three real roots converges to the *smallest*. It returned a perfectly plausible
positive period, and it matched the published value on three of the four
battery curves by accident of the bisection path. Only the fourth curve, and
then the control, exposed it. It is now driven by an exact **Sturm-sequence
root count**. That is the entire argument for controls, observed live.

### Validation — the battery must contain, never equal

| curve | `Delta` | torsion | `prod c_p` | proven `Omega` | pinned `Sha_an` |
| --- | --- | --- | --- | --- | --- |
| `11.a2` | `-11^5` | 5 | 5 | `1.2692093042795534216887...` | **1** |
| `15.a1` | `+405` | 2 | 2 | `0.7003015211663010115900...` | **1** |
| `37.b1` | `+37` | 1 | 1 | `0.7256810619361527823362...` | **1** |
| `571.b1` | `-571` | 1 | 1 | `0.4323412562718609702353...` | **4** |

Every digit shown is *proven*: it is common to both endpoints of the interval,
truncated at the first disagreement. The battery spans both signs of `Delta`,
torsion 1/2/5, and `Sha = 1` and `Sha = 4` (`571.b1`, the smallest conductor
with non-trivial `Sha`) — a battery whose curves all had `Sha = 1` would not
discriminate at all.

One entry in my first draft of that table said `37.b1` had torsion 3. The module
said 1, and was right: `psi_3`'s only rational root is `x = -76/3`, whose
`y`-discriminant is `-1/27`, so the 3-division point is not even real. The
reduction bound stalls at 3 because `#E(F_p)` is an isogeny invariant and the
class contains a curve with `Z/3`. The exhaustive search was right and the
transcription was wrong — which is the intended direction of that failure.

### The sweep — measured, not asserted

`python3 -m uma.bsd.sweep 10` enumerates curves from small `a`-invariants with
**no external database**, lets the module decide for itself which are inside its
domain, and records every refusal reason:

```
distinct curves          5274
CONSISTENT (pinned)       472        REFUSED       4802
in-domain fraction       8.9 %
Sha distribution         {1: 472}
REFUTED                     0
widest enclosure         2.04e-59
elapsed                  105 s
```

Refusal reasons, in order: additive reduction (2041), conductor above the sweep
cap (1975), root number `-1` (648), and — the interesting one — **138 curves
where the `L(1)` enclosure is not provably nonzero.** Those are the even
analytic ranks `>= 2`: the gate refuses them rather than dividing by an
interval that straddles zero. Rank ≥ 2 is where BSD is genuinely open, and the
module's honest answer there is *nothing*, which is the correct answer.

The headline number is the **8.9% in-domain fraction**, reported as the headline
precisely because it is small. And the number that does not exist in any
floating-point account: the widest enclosure over 472 pinned curves is
`2.0e-59`, so the nearest wrong integer sits some `10^58` enclosure-widths
away — against a double-precision relative error of `~10^-16` that comes with a
heuristic estimate rather than a proof.

`REFUTED` is empty, which is expected and is **not** evidence for BSD. It is
evidence that the gate agrees with the existing numerical record while
computing it without a rounding step.

## 8. What this is and is not worth

**It is not** progress on proving BSD. Nothing in §7 touches rank ≥ 2, `Sha`
finiteness, or any component of §5.

**It is** three things that are real:

1. An **independent, audit-friendly reimplementation** of the rank-0 gate in a
   restricted domain, which can return "no". It is not the first such
   procedure: exact modular-symbol routines predate it (see
   `studies/exact_rank0_sha/`, Sage's `L_ratio()`, and Miller 2011). Its value
   is that the whole path is readable in one file with explicit refusals.
2. A re-derivation of published `Sha_an` values with **zero network and zero
   CAS**, conditional on its own arithmetic kernel — the same discipline as
   `uma/jacobian` and `uma/dgg`, applied to a standing open problem.

<!-- CORRECTED 2026-08-11. Claim 1 said "for the first time as far as I can
establish"; that is false, and studies/exact_rank0_sha/ exhibits a float-free
exact computation of this report's own battery. Claim 2 said "zero floats,
zero trust in anyone else's arithmetic"; also false as written. The torsion
bound called binary floating-point exponentiation (abs(n) ** (1.0/k)) in
uma/bsd/curve.py, and uma/bsd/rig.py encloses pi by trusting a hard-coded
decimal literal rather than proving it. Those are trusted inputs and should be
listed as such. Separately, the shared primality gate paired twelve
Miller-Rabin witnesses with the thirteen-witness bound and so certified the
composite 318665857834031151167461 = 399165290221 * 798330580441 as prime;
that was fixed on 2026-08-11 by deriving the bound from the witness list. -->

3. A named, defensible **domain boundary**. The module's refusals say exactly
   which curves it cannot reach and why.

**Where it would actually bite.** The rounding margin is thinnest where
`Sha_an` is large, because the float quotient's relative error is amplified by
the same factor. The published record of *exceptionally large* analytic `Sha`
(orders `10^8` and beyond) is precisely the region where a rounding artefact is
most plausible and least checked. Re-deriving those exactly is the natural next
target; it needs the L-series summation extended (`T ~ 22 sqrt(N)` terms), which
is engineering, not new mathematics.

## 9. The oversight this closes

`studies/conjecture_triage.py` ran the verify-or-refuse contract over
google-deepmind/formal-conjectures — 3,195 classified statements in
`eval/triage.json`:

```
REFUSED-NEEDS-LEAN    1545
REFUSED-INFINITARY     922
REFUSED-NO-ANSWER      426
FINITE-CHECKABLE       302
```

Occurrences of `Birch`, `Swinnerton`, `BSD`, or `Millennium` in all 3,195: **0.**

The only elliptic-curve entry that made it in at all is `EllipticCurveRank.lean`
— a statement about the *asymptotic distribution* of ranks — and it was
classified `REFUSED-INFINITARY` by a regex matching `∀ ... : ℕ`.

That is the same failure mode `famous_conjectures.py` already documented and
fixed once: a regex deciding what is reachable, and being wrong about famous
problems. It recovered Legendre, Oppermann, Brocard, Kurepa and Erdős base-3
from the discard pile. BSD belongs on that list and was never on it — it was
absent from the corpus entirely, so no re-triage could have found it.

**The general lesson, which is worth more than the module:** a conjecture's
finite content is not always visible in its formal statement. BSD's Lean
statement quantifies over curves and looks hopelessly infinitary. The finite
obligation only appears after you *instantiate* — one curve, rank 0 — and then
notice that the conjecture asserts a real number is a perfect-square integer.
No syntactic classifier finds that. The triage layer needs an
**instantiate-then-classify** pass, and BSD is its first worked example.

---

## Reproduce

```bash
cd "UMA Suite/uma_build_v4"
python3 -m pytest tests/test_bsd.py -v      # 30 gates
python3 -m uma.bsd                          # battery + controls, as JSON
python3 -m uma.bsd.sweep 10                 # self-generated family
```

## Sources consulted

Birch & Swinnerton-Dyer, *Notes on elliptic curves II*, J. reine angew. Math.
218 (1965) · Coates–Wiles (1977) · Gross–Zagier, Invent. Math. 84 (1986) ·
Kolyvagin (1988–90) · Wiles (1995), Taylor–Wiles (1995), BCDT (2001) · Kato
(2004) · Skinner–Urban, Invent. Math. 195 (2014) ·
[Bhargava–Skinner–Zhang, arXiv:1407.1826](https://arxiv.org/abs/1407.1826) ·
[Burungale–Castella–Skinner, arXiv:2405.00270](https://arxiv.org/abs/2405.00270) ·
Castella–Ciperiani–Skinner–Sprung, [arXiv:1804.10993](https://arxiv.org/pdf/1804.10993) ·
[Dąbrowski et al., *Elliptic curves with exceptionally large analytic order of Sha*, arXiv:2103.11001](https://arxiv.org/pdf/2103.11001) ·
LMFDB curve pages [11.a2](https://www.lmfdb.org/EllipticCurve/Q/11/a/2),
[15.a1](https://www.lmfdb.org/EllipticCurve/Q/15/a/1),
[37.b1](https://www.lmfdb.org/EllipticCurve/Q/37/b/1),
[571.b1](https://www.lmfdb.org/EllipticCurve/Q/571a1/) (values used only as
containment targets, never as inputs).
