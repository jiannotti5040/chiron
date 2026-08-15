# studies

Reproducible research capsules. Each script states its own scope; none
of them is part of the verification path, and nothing here is imported
by `Primus/` or `Chiron/`.

## Scripts

| Script | Lines | Purpose |
|---|---:|---|
| `a063880_capsule.py` | 526 | Build and verify the frozen, bounded A063880 research capsule. |
| `a179210_extend.py` | 83 | A179210 — the shortest published verification range found: 69 terms. |
| `a179210_segmented.py` | 81 | A179210 with a SEGMENTED sieve — how far can validation actually reach? |
| `a261303_real.py` | 89 | A261303 / A261304 — testing the conjecture the entries ACTUALLY make. |
| `a300362_extend.py` | 118 | A300362 — extend a Zhi-Wei Sun conjecture BEYOND its published range. |
| `a302920_extend.py` | 104 | A302920 — extend past its published range. |
| `bfile_consistency.py` | 70 | bfile_consistency.py — do OEIS b-files agree with the `data` field of the same entry? |
| `bounded_search.py` | 275 | bounded_search.py — resolve the finite content of OPEN conjectures by exhaustive search, in exact integer arit |
| `certify_conjectures.py` | 245 | certify_conjectures.py — LEGACY / QUARANTINED math-artifact generator. |
| `claim_domain.py` | 168 | claim_domain.py — extract the DOMAIN of a natural-language conjecture, or refuse to test it. |
| `conjecture_runner.py` | 449 | conjecture_runner.py — durable, checkpointed, resumable conjecture campaign. |
| `conjecture_sweep.py` | 911 | conjecture_sweep.py — bounded exhaustive search over open conjectures, as a registry of independently-validate |
| `conjecture_triage.py` | 380 | conjecture_triage.py — run Chiron's verify-or-refuse contract over an external corpus of formalized open conje |
| `extend_batch.py` | 64 | extend_batch.py — push OEIS conjectures past their published b-files. |
| `famous_conjectures.py` | 264 | famous_conjectures.py — named open conjectures with finite refutable content. |
| `hunt.py` | 124 | hunt.py — hunt OEIS for a stated conjecture contradicted by published data. |
| `oeis_conjecture_miner.py` | 249 | oeis_conjecture_miner.py — cross-check OEIS's stated conjectures against OEIS's own published terms. |
| `oeis_novelty.py` | 636 | oeis_novelty.py — does Chiron recover an exact rule OEIS does not already state? |
| `oeis_offline_prefilter.py` | 158 | oeis_offline_prefilter.py — stage 1 of the novelty search. |
| `short_range_batch.py` | 86 | short_range_batch.py — conjectures with under ~80 published terms. |
| `signature_audit.py` | 159 | signature_audit.py — check OEIS's stated linear-recurrence signatures against the terms published in the same  |
| `systematic_sweep.py` | 345 | systematic_sweep.py — walk EVERY conjecture in the corpus, in order, and give each one a recorded status. No c |
| `witness_certificate.py` | 153 | witness_certificate.py — RETIRED generic counterexample issuer. |

## Directories

- `.oeis_cache/`
- `capsules/`
- `certificates/`

## Running one

```bash
python3 studies/<script>.py
```

Results that are kept live beside the script as JSON. An empty result
file means the study ran and found nothing, which is a result.
