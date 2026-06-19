# Example — caesar cipher

**Input (ciphertext only, no key):** `WKLV LV D VHFUHW PHVVDJH`

**Reproduce:**

```bash
python3 chiron.py solve "WKLV LV D VHFUHW PHVVDJH"
```

## What the solver recovered

| field | value |
|---|---|
| method | **caesar_shift_3** |
| plaintext | **THIS IS A SECRET MESSAGE** |
| confidence | 1.32 |
| schemes tried | 29 |

Runners-up it ranked below the winner:

| method | decoding |
|---|---|
| caesar_shift_7 | `PDEO EO W OAYNAP IAOOWCA` |
| rot13 | `JXYI YI Q IUSHUJ CUIIQWU` |
| caesar_shift_21 | `BPQA QA I AMKZMB UMAAIOM` |

## What this means

Given only ciphertext and no key, the solver recovers the plaintext and names the method, ranked against every classical scheme by English-likeness.
