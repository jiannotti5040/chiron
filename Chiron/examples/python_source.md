# Example — python source

**Input (Python source):**

```python
def f(x):
    total = 0
    for i in range(x):
        total = total + i
    return total
```

## What Chiron recovered

| field | value |
|---|---|
| model class | `ast_skeleton` |
| verified | **True** |
| structure fingerprint | `be1a1517801d50d8` |

## Why

> Structure-only AST skeleton: 28 nodes (identifiers/literals abstracted). Same skeleton => clone through renaming/reformatting.

## What this means

Source collapses to a relabel-invariant structural skeleton: rename every variable or reformat the file and the skeleton — and therefore the fingerprint — is unchanged. A clone detector by construction.
