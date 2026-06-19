# Example — primes

**Input (a surface):** `2 3 5 7 11 13 17 19 23 29`

**Reproduce:**

```bash
python3 chiron.py explain 2 3 5 7 11 13 17 19 23 29
```

## What Chiron recovered

| field | value |
|---|---|
| model class | `incompressible` |
| verified (held-out, exact) | **False** |
| description length | 108.9 bits (vs 108.9 bits to list the raw terms) |
| compression ratio | 1.0x |
| residual | [Fraction(2, 1), Fraction(3, 1), Fraction(5, 1), Fraction(7, 1), Fraction(11, 1), Fraction(13, 1), Fraction(17, 1), Fraction(19, 1)] |

## Why

> No exact model in the hypothesis class reproduces this sequence (honest negative).

## What this means

No closed-form generator exists in Chiron's hypothesis classes, so it ABSTAINS rather than fabricate one. This honest negative is the property the whole design is built around.

## Certificate

The engine's own certificate for this run is in [`certificates/primes.json`](certificates/primes.json) — *what was discovered, why it is believed, and what would falsify it.*
