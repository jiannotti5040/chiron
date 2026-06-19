# Example — powers of two

**Input (a surface):** `1 2 4 8 16 32 64 128 256`

**Reproduce:**

```bash
python3 chiron.py explain 1 2 4 8 16 32 64 128 256
```

## What Chiron recovered

| field | value |
|---|---|
| model class | `geometric` |
| verified (held-out, exact) | **True** |
| description length | 13.01 bits (vs 108.96 bits to list the raw terms) |
| compression ratio | 8.376x |
| residual | none — fully explained |
| next terms (predicted, unseen) | 512, 1024, 2048 |

## Why

> VERIFIED generator 'geometric'. Recovered in EXACT arithmetic from the first 7 terms, this rule reproduces every term and predicts all 2 held-out terms exactly (== , not a tolerance). Compresses 109 bits to 13; MDL margin to the next model is 4 bits.

## What this means

A geometric law (ratio 2): constant-size to store, infinite to extend.

## Certificate

The engine's own certificate for this run is in [`certificates/powers_of_two.json`](certificates/powers_of_two.json) — *what was discovered, why it is believed, and what would falsify it.*
