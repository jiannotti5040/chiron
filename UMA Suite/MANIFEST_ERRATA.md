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
