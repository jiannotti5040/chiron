# Vault artifact system

The vault is a set of **independently-runnable, self-certifying scripts**. Each
one proves something on its own and now leaves a durable, signed, *falsifiable*
certificate behind instead of printing the result and losing it. This directory
holds the four pieces that turn 60-plus loose scripts into one auditable
intelligence system.

## The four pieces

| File | Job |
|---|---|
| `chiron_artifact.py` | One emit path every script calls. Builds a dual-view certificate (`machine_view` evidence + `human_view` plain-language claim) and writes it to `artifacts/<script>/`. **Refuses any claim with no stated falsifier.** |
| `build_manifest.py` | Walks every runnable script, records what it proves / deps / SPDX / last result, and ties each to its emitted certificate. Writes `manifest.json`. |
| `vault_dashboard.html` | Reads `manifest.json` + the artifact tree. One tile per script showing pass/fail, what it found, and **the one thing that would break the claim.** |
| `apply_license_headers.py` | Idempotently stamps the PolyForm SPDX header on every `.py`, after any shebang/coding line. |

## Workflow

```bash
# 1. stamp licenses (idempotent; safe to repeat)
python3 apply_license_headers.py --write --root ..

# 2. run the scripts you care about — each emits its certificate
python3 semic.py selftest
python3 density_emotion.py --json evolve 2 4 6 8 10

# 3. build the index (live mode runs every selftest and records the result)
python3 build_manifest.py --run

# 4. open the dashboard (serve so fetch() can read manifest.json)
python3 -m http.server 8000   # then open http://localhost:8000/vault_dashboard.html
```

## The discipline that keeps it honest

A certificate is **rejected at emit time** unless it carries a non-empty
`what_would_falsify`. This is deliberate. The hard scripts satisfy it trivially
(Primus/SEMIC: *"one wrong held-out term breaks it"*). The soft scripts are
forced to anchor their claim to a checkable invariant too — `density_emotion`
stands on the CPTP validity of its quantum channel and a deterministic
half-life, **not** on the readability of its interpretation sentence. That is
the line between applicable intelligence and authoritative-looking text.

## Propagating to the rest of the scripts

Four scripts are wired as proofs — `semic.py` (hard), `density_emotion.py` (soft),
`chiron.py` (the core, 12/12 gates), and `invariant_engine.py` (Primus). `build_manifest.py`
reports **4 emitting artifacts** across the Chiron tree (`chiron_artifact.py` self-emits too).
To wire another, drop this at the end of its `__main__`:

```python
try:
    from chiron_artifact import quick
    quick(script=__file__,
          purpose="<what this script proves>",
          verified=<bool from its own gate>,
          discovered="<what it found, plain language>",
          why="<the evidence>",
          falsify="<the concrete condition that would break it>",
          machine={<the exact, hashable evidence>})
except Exception:
    pass   # import-safe: the script still runs standalone if the module is absent
```

The `try/except` is required — it preserves the standalone-runnability that is
the whole point of the architecture.
