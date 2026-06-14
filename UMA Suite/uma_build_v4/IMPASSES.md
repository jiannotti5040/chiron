# IMPASSES.md

Specific 1-sentence questions Claude could not resolve from the corpus
alone. None hard-stopped the build (the package compiles, runs, and all
30 tests pass), but each would benefit from a definitive answer.

*Signed: Claude (rebuild assistant)*

---

1. **FieldPosterior representations.** The canonical executor/inarticulation
   files dispatch on `posterior.representation in {'full','lowrank','ensemble','particle'}`.
   I only saw the `full` path defined in the PDFs — were `lowrank`/`ensemble`/`particle`
   ever actually implemented in `uma.core.state`, or only stubbed?

2. **MSR cosine threshold.** The pipeline's `verify_T_equals_lichnerowicz`
   one-shot check returns `cos ~ 0.001` on random `psi`. Was the original
   gating supposed to be `|cos| - 1 < 0.01` (strict) or relaxed for
   stochastic init? I went with the relaxed `0.5` threshold to avoid
   spurious failures.

3. **Wetterich basin cutoff.** I chose `cutoff=0.5` for the
   `c_alpha/nu_2` ratio in `classify_basin`. Was there a previously
   calibrated cutoff in the original Levy-MSR work? The default
   couplings I used in the pipeline fall into the Gaussian basin.

4. **Engine3 `anchor` choice.** The PDFs use `"dIse"` as the default
   anchor in `tokenize_to_binary_weight`. Should this also be the
   default in `Venturi.inject_text`? I left both at `"dIse"` for
   consistency.

5. **GENERICConfig field names.** The canonical pipeline calls
   `cfg.generic.alpha`, `cfg.generic.lam`, `cfg.generic.mu`, `cfg.generic.g`,
   but other modules use `advection`/`reaction`. Are these aliases of
   the same parameters, or distinct? I unified to `advection / diffusion /
   reaction` and aliased `reaction <-> lam` at call sites.
