# Changelog — primus-intelligence

All notable changes to the installable seed. Dates are UTC.

## 0.7.1 — 2026-08-08

- **A narrow `/v1` local mobile-safe HTTP contract now wraps the canonical
  engine routes.** `GET /v1/capabilities`, `POST /v1/collapse`, and `POST
  /v1/certify` use the stable `chiron.mobile_api/1` envelope with a
  server-generated request id, Primus version/certificate-schema metadata,
  and the unchanged `primus.engine_server/1` result nested inside. Request
  bodies are strict, inline, bounded JSON with no unknown fields, paths, or
  dynamic dispatch. `/v1/conjecture` is deliberately absent because its
  optional proposer may use stochastic search. The legacy routes are
  unchanged. `test_engine_server.py`: **48/48** real-HTTP gates, including
  success, schema, closed-route, no-leak, auth, and CORS checks.
- **Safe retry hints on every `429`.** Rate-limited responses now carry
  `Retry-After: 60`; a saturated concurrency gate carries `Retry-After: 1`.
  Both the legacy and v1 routes are live-HTTP gated, and v1 capabilities
  reports the same conservative integer hints for clients.
- **CORS is now default-deny and exact-origin opt-in.** The prior wildcard
  policy let arbitrary browser pages preflight a local endpoint. Set
  `CHIRON_CORS_ORIGIN` to one exact `http(s)` origin only when a browser UI
  needs it; native clients do not use CORS. This is not authentication.
- **Deployment posture corrected.** The versioned route is local and
  implemented-and-tested, not a public/mobile deployment. `CHIRON_API_TOKEN`
  remains an optional fixed development bearer, not mobile identity or
  production authorization. `MOBILE_API.md` and `DEPLOY_ENDPOINT.md` record
  the required external gateway, TLS, scoped short-lived credentials,
  rotation/revocation, and edge controls before any such claim is made.

- **`certify` now checks `product of ...` in prose.** `sum`, `total`,
  `average`, and `mean` were all matched in their written-out form;
  `product` was not, so "the product of 3 and 4 is 11" passed through
  uncertified while "the sum of 2 and 2 is 5" was refuted. The asymmetry was
  an oversight, not a policy. A product whose operands together exceed
  `MAX_INT_DIGITS` is REFUSED rather than computed — multiplication is the
  only aggregate here that grows faster than linearly in its operands, so it
  needs the bound stated. Gates: 4 added (verified, refuted, listed set,
  bound refusal).
- **The certify selftest stopped counting itself.** Its summary line
  hardcoded `31/31`, so every gate added after that line was written was
  invisible in the reported total — 35 gates were reporting as 31. The
  denominator is now derived. No verdict changed; the number that described
  them was wrong.

## 0.7.0 — 2026-08-03

**Relicensed to Apache-2.0. The paywall is gone and nothing is held back.**
No stamping path was touched; no verdict changed. The gate battery is
byte-identical to the pre-conversion run — 11/11 green, including
`oeis_live` at `n=29 · 20 verified · 0 false confidence · PASS`.

- **License: PolyForm Noncommercial 1.0.0 → Apache-2.0.** PolyForm
  Noncommercial is source-available, not open source: it discriminates
  against commercial use, so it fails the OSI definition. Apache-2.0 keeps
  the explicit patent grant the old license had and keeps attribution
  binding through NOTICE. Commercial use, modification, and redistribution
  are now all permitted. The project's prose and books are CC BY 4.0 —
  see `LICENSES.md` in the repository root.
- **No commercial tier.** The paid tiers, the Stripe checkout, and the
  private `chiron-vault` delivery repository are retired. The full engine,
  the flagship, the folded monolith, and every research capsule now live in
  one public repository.
- **Packaging fix that would have shipped a license-less wheel.**
  `license-files` still pointed at `LICENSE.md`, which the relicense
  deleted; the wheel would have carried no license text at all and
  `ci/check_wheel_license.py` would have failed the release. Now `LICENSE`,
  verified present inside the built wheel.
- **Project URLs** now point at the merged public repository. Nothing links
  to a private destination.
- **No managed endpoint.** The hosted demo instance is retired. `primus-serve`
  runs the same engine locally with the same contract (33/33 endpoint gates);
  `eval/remote.py` works against any instance you run.

## 0.6.3 — 2026-07-25

**The endpoint's front door is a closed table, and every error path is a
clean refusal.** Hardening only — no stamping path touched, no verdict
changed. Prompted by production log evidence (an unmapped skill-shaped path
being probed, and a platform health checker polling `/health` ~1×/sec).

- **Explicit route table, no catch-all.** `GET /`, `GET /health`,
  `POST /collapse|/certify|/conjecture` and nothing else. An unmapped path
  is `404 {"error":"not found","valid_routes":[…]}`; a mapped path with the
  wrong method is `405 {"error":"method not allowed","allow":["POST"]}` with
  a matching `Allow:` response header. `GET /` is a new short banner
  (routes + budgets, nothing about the box). Query strings no longer defeat
  routing — `/health?probe=1` is `/health` (it used to 404).
- **The stdlib's HTML error page is gone.** `PUT`/`TRACE`/unknown verbs used
  to fall through to `http.server`'s default page, which returns `501` with
  `Content-Type: text/html` and **echoes the caller's method back**
  (`Message: Unsupported method ('PUT').`). All error paths now emit
  fixed-string JSON; nothing derived from the request is ever reflected.
- **Adversarial JSON is now a bounded refusal, not a dropped connection.** A
  ~120 KB body of 60 000-deep nested arrays raised an uncaught
  `RecursionError` inside `json.loads`, killing the connection with no
  response and printing a traceback server-side. It is now a clean `400`.
- **Top-level handler.** Any unexpected exception returns
  `500 {"error":"internal error"}`; the detail and traceback go to the
  operator's stderr and nowhere else. Verified by fault injection.
- **Log hygiene.** `/health` is no longer access-logged (set
  `CHIRON_LOG_HEALTH=1` to restore), so a 1/sec platform probe cannot bury
  real traffic — the access log is a usable human-detector again. Real
  requests log one structured line: client IP, method, normalized path
  (never the query string), status, and the input **length + a truncated
  SHA-256** — never the caller's input verbatim. A trusted
  `X-Forwarded-For` is scrubbed to address characters so it cannot forge a
  log line.
- **Rate limit verified, not assumed.** The documented per-IP budget was
  already wired and enforcing; the battery now *proves* it trips with a
  clean JSON `429` on all three tools (`/collapse`, `/certify`,
  `/conjecture`) rather than on `/collapse` alone.
- CORS behaviour is unchanged and still gated: `Allow-Origin *` on every
  response class including errors, `OPTIONS` preflight → 204 on all five
  routed paths. The browser playground keeps working.
- `test_engine_server.py`: **33/33** (was 20/20 — 13 new gates). The new
  gates were checked against the pre-hardening server and 12 of them fail
  there, so they bite rather than decorate.
- Honest caveat: the reported "unmapped path returned 200" catch-all does
  **not** reproduce against this source — `/cockroachdb:reviewing-cluster-health`
  already returned 404 here. The closed route table and its regression gate
  were added anyway; if a 200 was really observed in production, it came
  from something in front of this process, not from it.

## 0.6.2 — 2026-07-21

**The endpoint speaks CORS — the browser playground can call the real engine
directly.** So a buyer can run the licensed engine on their own input from the
demo page, not just from a shell.

- `primus.engine_server` now sends a permissive CORS policy (`Allow-Origin *`,
  `GET/POST/OPTIONS`) and answers the browser preflight (`OPTIONS` → 204),
  exempt from auth and rate limits (it carries no body and does no work).
  Safe by construction: the API is read-only, cookieless, and grants no
  capability a `curl` couldn't already reach.
- `test_engine_server.py`: **20/20** (added the preflight + Allow-Origin gates).
- No stamping path touched; full battery re-run green under 0.6.2.

## 0.6.1 — 2026-07-21

**The engine as a live HTTP endpoint — request in, certificate out, source
never.** The verifier-that-refuses can now be served over HTTP for the
strongest possible eval (the real engine on caller-chosen input) without
shipping the engine.

- **New module `primus.engine_server`** (+ `primus-serve` console script).
  Stdlib `http.server` wrapper exposing `POST /collapse`, `POST /certify`,
  `POST /conjecture`, and `GET /health`. The engine source is never
  serialized: responses are certificate JSON only; engine exceptions become
  a REFUSED envelope carrying the exception TYPE NAME alone (no messages, no
  tracebacks, no source paths); `/health` is the only GET.
- **Everything hostile meets a refusal, not a crash.** 128 KiB body cap;
  sequence caps reuse the certify/conjecture bounds (`MAX_SEQ_TERMS = 256`);
  sliding-window per-IP + global rate limits (429 + REFUSED); bounded
  concurrency; optional bearer auth via `CHIRON_API_TOKEN`;
  `CHIRON_TRUST_FORWARDED` for correct client IPs behind a proxy.
- **`test_engine_server.py`** drives a real server process over real HTTP:
  18/18 gates — verify/refuse round-trips for all three tools, the
  over-budget refusals, rate limit, concurrency budget, auth on/off, and an
  explicit no-leak assertion (no traceback or source path in any hostile
  response). Added to the AGENTS.md battery.
- **Deploy notes** in `DEPLOY_ENDPOINT.md` (Fly.io / Render, Dockerfile,
  the env table). The public repo ships the client (`eval/remote.py`).
- No stamping path changed. Full battery re-run green before release.

## 0.6.0 — 2026-07-20

**Guess-and-prove: a stochastic proposer behind the exact gate.**
The benchmark adversary (gplearn GP, see SYMREG_RESULTS.md) becomes a
conjecture generator whose output must survive the same discipline it was
losing to. The stochastic search never touches a stamping path.

- **New module `primus.conjecture`** (+ `primus conjecture` CLI, MCP
  `conjecture` tool, optional install `pip install primus-intelligence[conjecture]`).
  Pipeline: the engine's `collapse` answers first; on refusal, gplearn
  proposes closed forms from a train split, float constants are snapped to
  exact integers/rationals, and a candidate is stamped ONLY if it
  reproduces every supplied term exactly in rational arithmetic —
  including a holdout suffix the search never saw (h ≥ p: candidates with
  more snapped constants than holdout terms are refused). No gplearn →
  honest REFUSED, never an error. The certificate carries the caveat that
  a stamp certifies fit to the given data, never the true generator.
- **New certify claim kind `closed_form`** (`a(n) = <expr> matches …`,
  schema string unchanged at primus.certificate/2, contract in SCHEMA.md):
  a pure exact checker — no gplearn on this path — so conjecture output
  round-trips through the gate. Anchor-windowed scan, depth/exponent/digit
  bounds, three fuzz gates added.
- **Chiron twin `Chiron/conjecture.py`**: line-identical exact core;
  stage 0 uses `chiron.collapse`. Honest capability note: with the
  add/sub/mul/div function set an integer-valued closed form is
  necessarily polynomial, so the layer adds stamping reach to the SEED
  (degree-6 poly cap → degree-7+ now reachable, gated in selftest) while
  Chiron's uncapped polynomial family subsumes it today — its gates prove
  pipeline integrity with the engine verdict disclosed alongside.
- **External validation** (SYMREG_RESULTS.md, cached live corpus, 29
  rows): raw GP 2 exact / 27 wrong; gated GP **3 exact / 0 stamped-wrong /
  26 refused** — every forced wrong answer became a refusal, and the gate
  rescued one row (cubes) the raw run missed. `collapse`, `oeis_live.py`,
  and `drift_check.py` are untouched; all published claims stand as-is.
- Battery after the change: 55 stress · 31 certify · 16 conjecture ·
  16 fuzz · 11 MCP · 12 twins · certify property grid · internal benchmark
  (zero false confidence) · live-OEIS 20 verified / 0 false · drift GREEN
  (42 surfaces agree) · Chiron 12/12 · Chiron reproducibility ·
  monolith sweep 49/49 selftest-bearing modules through the fold.

## 0.5.1 — 2026-07-07

**A live false stamp on the seed, caught by an extended external OEIS probe and
repaired at the root — the repunit story a third time.**

- **Fix (stamping path).** On an integer surface, when any candidate reproduces
  the data EXACTLY in integer arithmetic, the non-exact (float/SVD) holonomic
  path is no longer allowed to mask it. Found live on OEIS **A002203** (companion
  Pell): the seed scored a 6-parameter float `holonomic_r1_p2` overfit shorter
  than the true order-2 linear recurrence, cleared the prefix-holdout it happened
  to match, and stamped VERIFIED while predicting 551612 instead of 551614.
  Chiron was already correct (exact `linear_recurrence_order2`); the seed had
  silently drifted behind it.
- **Guard.** A002203 added to the seed/Chiron differential (`drift_check.py`) and
  to the external OEIS battery, closing the blind spot permanently.
- Full battery green after the fix: 48 stress · 27 certify · 13 fuzz · 10 MCP ·
  internal benchmark (zero false confidence) · live-OEIS extended 25 verified / 0
  false · drift GREEN (companion Pell now covered) · Chiron selftest.

## 0.5.0 — 2026-07-05

**The Apéry release: degree-3 P-recursion, the deep-evidence tier, and
three engine repairs the attempt forced.**

- Exact P-recursive solver extended to polynomial coefficients of degree 3
  (`max_pdeg` 2 → 3, seed and Chiron in step — no ledger debt). The Apéry
  numbers (A005259, the ζ(3) irrationality sequence) now verify with their
  classical recurrence; Franel numbers (A000172) verify as the blind probe
  that needed only deeper evidence, not the new degree.
- **Deep-evidence protocol tier** in `oeis_live.py`: sequences marked
  `protocol: "deep"` are graded at 24 shown / 4 held out. This is MDL's
  appetite made into protocol — a (2,3) rule has 12 unknowns and cannot
  even FORM a candidate on 12 terms, and its holdout refit needs 18-term
  prefixes to be unambiguous. Bell numbers ride the tier as the control:
  24 terms of evidence still buy a refusal, because Bell is not P-recursive.
- Repairs forced by the attempt (each a latent defect beyond Apéry):
  1. **Exact integers now ride past the float front door.**
     `collapse_numeric` floated every term on entry, silently corrupting
     integers beyond 2⁵³ — Apéry's 29-digit terms died before any exact
     solver saw them. Python-int inputs are preserved end-to-end
     (`_exact_int_view`), and integral-looking floats are trusted only
     below 2⁵³.
  2. **Nullspace uniqueness is now a refusal condition** (seed and Chiron).
     A solution space of dimension > 1 means the data admits multiple rules
     of the class; any basis vector is an arbitrary mixture that reproduces
     the shown terms yet predicts noise. Ambiguity refuses.
  3. **Holdout refits judge the prefix at the prefix's own scale.** Reusing
     full-surface precision let a tail-dominated tolerance (~10²⁶ for
     Apéry) quantize every prefix residual to zero, handing the refit to a
     one-parameter constant.
- Live-OEIS battery now 28 sequences: **20 verified, all externally
  correct; 0 false stamps; 7 honest refusals; 1 conservative unstamp.**

## 0.4.0 — 2026-07-04

**The capability edge the live-OEIS run identified is closed.** New exact
P-recursive solver (`_cand_holonomic_exact`): recurrences with polynomial
coefficients, order ≤ 2, degree ≤ 2, found by exact Fraction nullspace —
no SVD, no thresholds — with exact reproduction of every shown term
required before a candidate exists, and exact-arithmetic prediction after.

- Motzkin (A001006) now VERIFIED with the classical recurrence
  (n+4)M(n+2) = (2n+5)M(n+1) + 3(n+1)M(n), recovered from 12 terms.
- Large Schröder numbers (A006318), fetched live from OEIS *after* the
  solver was written, verified on first contact — a genuine out-of-
  development probe.
- Bell numbers still refuse (they are not P-recursive) — the control holds.
- Live-OEIS battery is now 18 / 25 verified, all externally correct,
  zero false stamps, 6 honest refusals.
- The rank-1 exclusion keeps canonical families canonical: a polynomial
  multiple of a constant-coefficient recurrence is rejected (without it,
  Fibonacci could be dressed up as holonomic — caught by the 48-gate
  stress suite before shipping).
- The drift detector did its first real job: the new capability turned the
  build RED as SEED-ONLY until ledgered with a dated reason. Later the same
  day the margin fix was ported into Chiron (whose holonomic solver was
  already exact — the original ledger text misdiagnosed it as float/SVD;
  only its rows ≥ unknowns+2 margin blocked holdout verification), Motzkin
  and Schröder verify in both engines, and the ledger is empty again. The
  full loop — RED, written reason, repair, cleared — took one afternoon.

## 0.3.0 — 2026-07-04

**Certificate layer (schema `primus.certificate/1` → `/2`; contract now
written down in [SCHEMA.md](SCHEMA.md)):**

- New checkable claim kinds: primality/compositeness (deterministic
  Miller–Rabin below the proven witness bound, REFUSED above it), binomial
  coefficients, gcd/lcm, modular arithmetic, date arithmetic (days
  after/before, days between; exact calendar math), sums/totals/averages of
  listed numbers, power claims (`2^10 = 1024`, bounded), and reversed
  arithmetic (`91 = 7 × 13`).
- New certificate fields: `coverage` (fraction of input actually checked —
  read it before trusting a pass), `claims_capped`, `input.truncated`,
  per-claim `span`, `attestation.kind`.
- Adversarial hardening, verified by a new 13-gate fuzz suite
  (`test_certify_fuzz.py`): input truncation at 100k chars, 200-claim cap,
  4,096-digit integer bound (refused, not computed), 256-term per-claim
  sequence bound (fixes a real DoS the fuzzer found: a 20k-integer flood
  became one giant collapse call), digit-run clamping + anchor-windowed
  regex scanning (fixes a second real finding: quadratic scan cost on
  '='-free operand soup).
- Honest attestation language: the certificate hash is labeled what it is —
  a tamper-evident hash, not an unforgeable signature.

**Engine (the float purge):**

- Polynomial recovery on integer surfaces now uses exact Newton
  finite-difference arithmetic (no `polyfit` on the stamping path);
  predictions are exact Python ints valid far beyond 2⁵³.
- Geometric recovery on integer surfaces now uses exact rational ratio
  detection (no log-space regression); handles negative ratios, which the
  float path structurally could not.
- These close the same defect class as 0.1.0's repunit fix (float drift
  passing a tolerance, then compounding).

**Differential testing:** `drift_check.py` runs a 33-surface battery
through both this seed and `../Chiron/chiron.py`; contradictions (both
stamp, different predictions) and unledgered seed-only stamps fail the
build. Wired into CI.

**Packaging:** LICENSE.md now ships inside every wheel/sdist (the PolyForm
notice must travel with the code); CI runs a 3.9/3.13 × Ubuntu/Windows
matrix; tag-triggered PyPI release workflow (trusted publishing) added.

## 0.2.0 — 2026-07-04

- `primus-mcp`: dependency-free MCP stdio server exposing `certify` and
  `collapse` as agent tools; 10-gate live-subprocess handshake test.
- `__version__` reads package metadata — pyproject is the single source of
  version truth.

## 0.1.0 — 2026-07-04

- First packaging of the seed: `primus.engine` (moved from
  `invariant_engine.py`, which remains as a full compatibility shim),
  `primus.certify`, `primus` CLI (`collapse`, `certify --gate`, `selftest`).
- Engine fix found by the first live-OEIS external validation run:
  recurrence coefficients snapped to exact rationals; held-out verification
  demands exact integer equality on integer surfaces (the repunit
  false-verification, A002275). Details in
  [EXTERNAL_VALIDATION.md](EXTERNAL_VALIDATION.md).
