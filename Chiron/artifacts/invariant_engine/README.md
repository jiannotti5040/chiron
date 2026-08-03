# Why this artifact still says PolyForm

`latest.json` here is a **dated historical record**, not a live artifact.

It was stamped on 2026-06-29 at commit `e0e45c0a`, when the seed engine still
had its own entry point. That entry point is now `Primus/invariant_engine.py`,
a pure module-alias shim over `primus.engine` with no artifact emitter — so
nothing regenerates this file, and it has not moved since.

Its `license` field reads `PolyForm-Noncommercial-1.0.0` because that is what
the license actually was at that commit. The repository relicensed to
Apache-2.0 in August 2026.

**It is deliberately not hand-edited.** These artifacts are stamped evidence of
a run; rewriting a field inside one to match today's repository would make it
assert something that was not true when it was generated. A certificate that
gets quietly updated is not a certificate. The live artifacts in the sibling
directories carry `Apache-2.0` because they were genuinely regenerated after
the change.

Note also `"verified": false` — this record never claimed a verification.
