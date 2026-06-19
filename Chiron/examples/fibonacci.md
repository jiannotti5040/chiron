# Example — fibonacci

**Input (a surface):** `0 1 1 2 3 5 8 13 21 34`

**Reproduce:**

```bash
python3 chiron.py explain 0 1 1 2 3 5 8 13 21 34
```

## What Chiron recovered

| field | value |
|---|---|
| model class | `linear_recurrence_order2` |
| verified (held-out, exact) | **True** |
| description length | 24.02 bits (vs 88.43 bits to list the raw terms) |
| compression ratio | 3.682x |
| residual | none — fully explained |
| next terms (predicted, unseen) | 55, 89, 144 |

## Why

> VERIFIED generator 'linear_recurrence_order2'. Recovered in EXACT arithmetic from the first 8 terms, this rule reproduces every term and predicts all 2 held-out terms exactly (== , not a tolerance). Compresses 88 bits to 24; MDL margin to the next model is 999 bits.

## What this means

Two seeds and one rule — each term is the sum of the previous two — regenerate the whole sequence and every future term. Chiron proves it by predicting terms it was never shown.

## Certificate

The engine's own certificate for this run is in [`certificates/fibonacci.json`](certificates/fibonacci.json) — *what was discovered, why it is believed, and what would falsify it.*
