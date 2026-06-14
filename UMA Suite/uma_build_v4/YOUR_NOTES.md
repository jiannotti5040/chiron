# YOUR_NOTES.md

Technical reservations about the rebuild, kept separate from the user's
documents. None of this is editorial commentary on the framework
itself — these are mechanical notes on what changed during the
reconstruction and where the build deviates from what's strictly in
the corpus.

*Signed: Claude (rebuild assistant)*

---

## 1. FieldPosterior simplification (single representation)

The canonical executor and inarticulation modules dispatch on
`posterior.representation in {'full', 'lowrank', 'ensemble', 'particle'}`
and provide `FieldPosterior.full(mu, Sigma)`, `FieldPosterior.lowrank(...)`,
`FieldPosterior.ensemble(...)`, `FieldPosterior.particle(...)`
factories. The PDFs I had access to only define the `full` path
operationally; the other representations are referenced but their
implementation is not present in the corpus.

The rebuild's `FieldPosterior` is a plain `(mean, cov)` dataclass with
a `FieldPosterior.full(mu, Sigma)` classmethod and `Sigma` /
`representation = 'full'` aliases for compat. The inarticulation
scaling-coefficient computation was reduced to the `full` branch only.

If the multi-rep version exists in code I didn't have, dropping it into
`uma/core/state.py` should require no changes elsewhere — the rest of
the package only touches `mean`, `cov`, `dim`, and the `Sigma` alias.

## 2. pdftotext page-break repair

`pdftotext` injects a form-feed (`\f`) at every PDF page boundary and
in several places strips leading whitespace from the first line of the
next page. This destroyed Python indentation across page boundaries
in roughly every fifth method.

I wrote `/home/claude/build/clean_pdf_text.py` to normalize this:
it detects orphaned `def` / `class` continuations and re-indents them
based on the surrounding context. Every module under `Uma_clean/*.txt`
is the post-repair output. The repair is documented inline in
`clean_pdf_text.py`.

Two consequences:
- A handful of lines (mid-line comments split across pages) were
  manually reassembled. Mechanical-only repair never altered any
  symbol name, expression, or numeric constant.
- A few comments lost their original line breaks. Code semantics are
  unchanged.

## 3. UMAClient API surface

The canonical executor calls `client.dynamics.step(psi, dt, rng=rng)`,
`client.posterior_state`, and `client.projection.lift / project`.
The rebuild's `UMAClient` exposes a slightly higher-level surface:
`client.evolve(dt)`, `client.observe(obs, y)`, with `posterior_state`
as a `@property` alias to `client.filter.posterior`.

Both APIs coexist:
- The pipeline (`uma/pipeline.py`) drives the lower-level surface
  directly (manual `psi -> step -> project -> filter.update`) because
  it needs fine-grained control over the per-step Venturi injection.
- The executor (`uma/semantic/executor.py`) uses the high-level
  `client.evolve` / `client.observe` API because IR nodes are coarse.

Net: the canonical pipeline file imported from `from uma.venturi.operator
import VenturiOperator, VenturiConfig` — `VenturiConfig` was not defined
anywhere in the corpus I had. I dropped that import; `Venturi` and
`VenturiOperator` are now aliases of the same class.

## 4. MSR `verify_T_equals_lichnerowicz` was missing

The pipeline imports `verify_T_equals_lichnerowicz` from
`uma.msr.stress_energy` but the PDF for `stress_energy` did not contain
it. I wrote it as a self-contained one-shot check: it computes the
Noether `T_munu` on a fixed massive-scalar test field and compares its
cosine similarity to the trace-reversed linearized Einstein form on a
constant `h_pert`. With random initialization the cosine is generally
low; the *per-step* TensorBridge residual is what actually monitors GR
consistency during the run.

## 5. semantic/engine.py adapted

The canonical `engine.run()` checks `if client.posterior_state is None:
raise RuntimeError(...)` and demands an explicit `client.initialize(psi0)`
call. The rebuild's `UMAClient.__init__` already creates an empty
posterior with the right shape, so this check would always pass. I
left the engine's `run()` as a thin orchestrator that wires the
`hamiltonian_fn` callback into `SemanticFriction` and dispatches to
`UMAExecutor`. The semantic-engine test suite still passes the
canonical 6 tests.

## 6. Silver Ratio retraction

`uma/semantic/constants.py` contains the retraction note verbatim:
"Across 50 independent trajectories, E_DC/kT ranges from 0.08 to 1.93
with mean 0.77 and std 0.65. The value 0.1713 matched Silver to 0.16%
only for seed=42. It was a coincidence, not a derived constant."

The Silver Ratio constants (`DELTA_S`, `INV_DELTA_S_SQ`, `SQRT_E`,
`C1_SILVER`, `SILVER_ANGLE`) and the Engine3 complex state seed are
preserved exactly because they are real algebraic properties of the
text-encoding design, regardless of any claim about their physics
status.

## 7. wetterich_flow.py was compact

The PDF for `wetterich_flow.py` was the shortest of the MSR modules and
its full RG-flow derivation is not present. The rebuild ships a
working `LevyMSRCouplings` dataclass plus `classify_basin` /
`dynamic_exponent` functions — enough for the pipeline's classification
step. If a fuller Wetterich-flow implementation exists, it would slot
in here.

## 8. Test additions beyond the corpus

`tests/test_sanity.py` has eleven sanity checks I wrote — they cover
geometry self-lock, projection round-trip, Kalman innovation decrease,
GENERIC step shape, Wirtinger finiteness, Dykstra convergence, friction
closure on steady H, TensorBridge finiteness, full-pipeline closure,
and seed determinism. These are not in the corpus. They exist to catch
regressions during this rebuild and any future modification.

`tests/test_semantic.py` mirrors the canonical PDF test file but is
adapted to single-rep FieldPosterior; the friction summary test checks
both `dH_dt_final` and the canonical `dz_dt_final` alias.
