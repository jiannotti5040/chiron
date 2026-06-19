# Example — squares

**Input (a surface):** `0 1 4 9 16 25 36 49 64 81`

**Reproduce:**

```bash
python3 chiron.py explain 0 1 4 9 16 25 36 49 64 81
```

## What Chiron recovered

| field | value |
|---|---|
| model class | `polynomial_deg2` |
| verified (held-out, exact) | **True** |
| description length | 20.51 bits (vs 116.91 bits to list the raw terms) |
| compression ratio | 5.699x |
| residual | none — fully explained |
| next terms (predicted, unseen) | 100, 121, 144 |

## Why

> VERIFIED generator 'polynomial_deg2'. Recovered in EXACT arithmetic from the first 8 terms, this rule reproduces every term and predicts all 2 held-out terms exactly (== , not a tolerance). Compresses 117 bits to 21; MDL margin to the next model is 21 bits.

## What this means

A degree-2 polynomial, recovered exactly in rational arithmetic. A naive curve-fit would also get this one — but only this kind.

## Certificate

The engine's own certificate for this run is in [`certificates/squares.json`](certificates/squares.json) — *what was discovered, why it is believed, and what would falsify it.*
