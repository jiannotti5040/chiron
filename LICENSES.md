# Which license covers what

This repository holds two kinds of work, and they carry different licenses.

| | License | Full text |
|---|---|---|
| **Code** — engines, gates, tests, schemas, certificates, tooling, and the technical documentation that describes them | **Apache License 2.0** | [`LICENSE`](LICENSE) |
| **Prose** — the books, the paper, and the standalone essays | **CC BY 4.0** | [`LICENSE-CC-BY-4.0.txt`](LICENSE-CC-BY-4.0.txt) |

Both are genuinely open. Apache-2.0 is an OSI-approved open-source license and
CC BY 4.0 is an approved free-culture license. Neither restricts commercial use.

If a file carries an `SPDX-License-Identifier` header, that header wins.

## Prose paths — CC BY 4.0

These directories are prose in their entirety:

- `Ontological & Philosophical Books/` — Books I–V and the Compendium
- `Quack System Constructs/` — the Resonant Manifold, the white paper, the epilogue
- `Paper/` — *Abstain or Prove* (`.tex` and `.pdf`)
- `Governance/` — *A Standard of Care for Persuasive Machines*, *LexGuard*

These directories are mixed. The prose files listed carry CC BY 4.0; everything
else in them is code under Apache-2.0:

- `notes/` — `Mathematical_Compendium.tex` and `Mathematical_Compendium.pdf`
- `UMA Suite/` — `docs/THEORY_*.md`, `docs/URF_*.md`, and `source_materials/`
- `Individual Programs/` — `PIH_*.md`, `Thruput_Compiled.txt`
- `Infectatrum/` — `HONEST_ARTICULATION.md`

Each prose directory also carries its own `LICENSE.md` stating the same thing,
because PDFs and `.docx` files cannot carry an SPDX header.

## Third-party material

Some material here belongs to other people, and their terms survive this
project's relicensing untouched. [`NOTICE`](NOTICE) records each one in full:

- **Google DeepMind's `formal-conjectures`** — one vendored Lean file,
  Apache-2.0, hash-pinned as a capsule input. Do not edit or restamp it.
- **OEIS sequence data** — © The OEIS Foundation Inc., frozen snapshots
  included for reproducibility, not relicensed.
- **Wikipedia** — a Congress grown over Wikipedia carries verbatim article
  prose under CC BY-SA 4.0, which is one-way incompatible with both licenses
  above. That is why `Chiron/chiron_memory.json` is untracked and regenerable
  rather than shipped. See `NOTICE` for the full reasoning.
- **Caramuel (1663)** — public domain; the transcriptions derived from it are
  original work.

## Why this changed

This project was previously PolyForm Noncommercial 1.0.0 with a paid commercial
tier. PolyForm Noncommercial is *source-available*, not open source — it
discriminates against commercial use, which fails the OSI definition. The
commercial tier is retired and the whole repository is now open under licenses
that actually mean it.

The one thing that has not changed is the property the project exists to
defend: **zero false verifications.** The gates that enforce it are unchanged
and still run on every commit.

---

Copyright © 2026 Jacob Iannotti
