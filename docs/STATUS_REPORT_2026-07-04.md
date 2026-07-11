# Project Status Report — Jacob's Portfolio Vault
**Date:** 2026-07-04, end of day · **Repo:** github.com/jiannotti5040/Jacob-s-Portfolio-Vault (public) · **Package:** primus-intelligence v0.4.0

---

## 1. Current state, one paragraph

The vault is public on GitHub. 21 of 22 session commits are pushed; 1 commit (the Windows-filename fix, `3d51e4d`) is committed locally and **waiting for you to double-click PUSH_TO_GITHUB.command**. The latest CI run passed every functional gate on all three Linux jobs (155+ gates green on GitHub's machines); the two Windows jobs failed only at file checkout because two filenames contained `*`, which the waiting commit fixes. Nothing is broken. Nothing is urgent.

## 2. CI / external validation status

| Job (run #41) | Result | Detail |
|---|---|---|
| chiron (ubuntu) | ✅ pass | selftest, grower, unit tests, drift detector, monolith smoke |
| primus (ubuntu, py3.13) | ✅ pass | all 8 gate steps incl. OEIS external + wheel/license check |
| primus (ubuntu, py3.9) | ✅ pass | same |
| primus (windows, both) | ❌ fail at checkout | `*` in two UMA filenames; **fixed in local commit 3d51e4d** |

## 3. Verification totals (all reproducible by command)

| Suite | Result |
|---|---|
| Engine stress tests | 48 / 48 |
| Internal benchmark (110 seqs) | PASS — 98% recovery, 100% precision, 0 false confidence |
| Certify gates | 27 / 27 |
| Adversarial fuzz | 13 / 13 (found + fixed 2 real bugs pre-release) |
| MCP protocol handshake | 10 / 10 |
| **Live-OEIS external (25 seqs)** | **18 verified — all externally correct · 0 false stamps · 6 honest refusals · 1 conservative unstamp** |
| vs gplearn symbolic regression | Primus 16-exact / 0-wrong / 8-refused; gplearn 2 / 22 |
| Drift (seed vs Chiron, 34 surfaces) | 34 / 34 agree, ledger empty |
| Chiron selftest + unit tests | GREEN · 6/6 |
| Monolith fold | 41 / 41 modules |
| Wheel build | 0.4.0 builds, LICENSE embedded |

## 4. What was built (v0.1.0 → v0.4.0, 22 commits, one day)

- **primus package** — `pip install ./Primus`: `collapse` (exact recovery, held-out proof), `certify` (VERIFIED/REFUTED/REFUSED over LLM output, 10 claim kinds, coverage signal, schema/2, SCHEMA.md contract), CLI incl. `--gate` and hash-chained `--jsonl` pipeline mode.
- **primus-mcp** — dependency-free MCP server; any agent can call the gate (`claude mcp add primus -- primus-mcp`).
- **Engine, all-exact stamping path** — rational recurrence snapping; exact Newton polynomials; exact geometric ratios (incl. negative); exact order-2 P-recursion (Motzkin recovered with its classical recurrence; Schröder verified on first contact as a post-development probe; Bell correctly refuses). Same capability ported into chiron.py; monolith regenerated.
- **Bug found by external data and fixed:** repunit false verification (float drift + tolerance hole) — the zero-false-stamp claim was falsified externally, repaired at root, and now holds.
- **Infrastructure** — drift detector with capability ledger (in CI), CI matrix (3.9/3.13 × Ubuntu/Windows), tag-triggered PyPI release workflow, CHANGELOG, CONTRIBUTING, CITATION.cff, CI badge, README repositioned around the certify gate.
- **Artifacts** — `Paper/abstain_or_prove.pdf` (6 pp, compiles clean, real numbers, TODO markers where only you can act), `playground.html` (browser demo of the real engine, needs one open-in-browser check), `PUSH_TO_GITHUB.command` (double-click pusher), `primus-vault-workflow` skill (installable card), Verified Ink art (in your outputs, personal, not in git).

## 5. Decisions on record

- **License: PolyForm Noncommercial — decided, done, no action.** Revisit only if a commercial request arrives.
- **Direction: contact before capability** (your call). Parked builds, in order: Apéry-class recursion → Candor as second product → full-OEIS atlas pipeline.

## 6. Your action list (total ~25 min, none urgent)

| # | Action | Time | When |
|---|---|---|---|
| 1 | Double-click `PUSH_TO_GITHUB.command` | 2 min | whenever |
| 2 | Tell me; I verify CI goes fully green | — | after 1 |
| 3 | GitHub → Settings → Pages → deploy `main` / root; open `…github.io/Jacob-s-Portfolio-Vault/playground.html` | 20 min | weekend |
| 4 | Show HN draft (I write it with you, repunit story) | later | next week |
| 5 | PyPI registration + `git tag v0.4.0` | later | optional, after 4 |
| 6 | PySR run + full-OEIS sweep (your machine, background) | later | optional |

## 7. Risk register

No open defects. No failing gates. No deadlines. Worst live issue is the un-pushed Windows fix (item 1). *Published working record — a point-in-time status report, tracked as part of the project's paper trail.*
