# Example — catalan

**Input (a surface):** `1 1 2 5 14 42 132 429 1430 4862 16796 58786 208012 742900`

**Reproduce:**

```bash
python3 chiron.py explain 1 1 2 5 14 42 132 429 1430 4862 16796 58786 208012 742900
```

## What Chiron recovered

| field | value |
|---|---|
| model class | `holonomic_r1_p1` |
| verified (held-out, exact) | **True** |
| description length | 30.52 bits (vs 249.74 bits to list the raw terms) |
| compression ratio | 8.182x |
| residual | none — fully explained |
| next terms (predicted, unseen) | 2674440, 9694845, 35357670 |

## Why

> VERIFIED generator 'holonomic_r1_p1'. Recovered in EXACT arithmetic from the first 11 terms, this rule reproduces every term and predicts all 3 held-out terms exactly (== , not a tolerance). Compresses 250 bits to 31; MDL margin to the next model is 999 bits.

## What this means

A holonomic (P-recursive) rule, the kind behind the Catalan numbers. These are not polynomials or simple recurrences, yet the exact generator is still pinned and verified on held-out terms.

## Certificate

The engine's own certificate for this run is in [`certificates/catalan.json`](certificates/catalan.json) — *what was discovered, why it is believed, and what would falsify it.*
