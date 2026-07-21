# Manifest errata

`MANIFEST.sha256` is a chain-hashed provenance artifact and is preserved
byte-identical; corrections to the tree it describes are recorded here
instead of edited into it.

**2026-07-04 — Windows-compatibility renames (content unchanged).**
Two source-material filenames contained literal `*` characters, which
Windows forbids in filenames — `actions/checkout` failed on every Windows
CI runner before any code could run. Renamed:

| Manifest path | New path | SHA-256 |
|---|---|---|
| `./source_materials/Files/*current*.pages` | `./source_materials/Files/current.pages` | unchanged |
| `./source_materials/RSLS_source_PDFs/*current*.pages` | `./source_materials/RSLS_source_PDFs/current.pages` | unchanged |

The file *contents* are byte-identical to what the manifest hashes; only
the names changed. Verify either file against its manifest line by hashing
the renamed file.

**2026-07-21 — Post-manifest addition: `uma/jacobian/` (new files, nothing renamed).**
Three files added after the manifest was sealed; the manifest itself is
preserved byte-identical, and these additions are recorded here per the
convention above:

| New path | What it is |
|---|---|
| `uma_build_v4/uma/jacobian/__init__.py` | exact-arithmetic verification of the 2026 Jacobian-conjecture counterexample (Alpöge 2026-07-20, Knill transcription): det J ≡ −2 as a polynomial identity + exact two-point collision, plus positive/discrimination controls |
| `uma_build_v4/uma/jacobian/__main__.py` | `python3 -m uma.jacobian` certificate CLI |
| `uma_build_v4/tests/test_jacobian.py` | 12 pytest gates (suite: 104 → 136 with the v4-ext files; all green 2026-07-21) |
| `uma_build_v4/docs/JACOBIAN_COUNTEREXAMPLE.md` | honest write-up: what is verified (arithmetic), what is not (provenance, n = 2, peer review) |
