# Chiron Vault — Standard Operating Procedures

The instruction manual. If the [DICTIONARY](DICTIONARY.md) is what the words
mean and the [ENCYCLOPEDIA](ENCYCLOPEDIA.md) is what each module is, this is
**how to operate the vault** — as its owner, a maintainer, or an agent
working inside it. Every procedure here has been executed for real; several
were forged by the incidents they now prevent.

---

## 0 · The one law

**Zero false verifications.** A change that makes any engine stamp something
it cannot exactly prove is wrong even if every benchmark number improves.
Refusal is a feature. When recall and honesty conflict, choose honesty.
Everything below exists to serve this law.

## 1 · Sources of truth (edit these; never their copies)

| Idea | Source of truth | Generated / aliased copy — never hand-edit |
|---|---|---|
| Seed engine | `Primus/src/primus/engine.py` | `Primus/invariant_engine.py` (module-alias shim) |
| Certify gate | `Primus/src/primus/certify.py` | — |
| Flagship | `Chiron/*.py` modules | `Chiron Monolith/chiron_monolith.py` (regenerate) |
| Version | `Primus/pyproject.toml` | `__init__.py` reads package metadata |
| Certificate contract | `Primus/SCHEMA.md` + schema string | consumers gate on the string |
| Module index | `Chiron/manifest.json` (via `build_manifest.py`) | `docs/ENCYCLOPEDIA.md` (via `build_encyclopedia.py`) |

After changing any Chiron module:

```bash
cd "Chiron Monolith" && python3 build_monolith.py && python3 chiron_monolith.py --selftest
```

After the module set or gates change:

```bash
python3 Chiron/build_manifest.py --run && python3 Chiron/build_encyclopedia.py
```

## 2 · Daily operation

```bash
# The whole organism, one command (or double-click SERVE_VAULT.command):
python3 bin/chiron serve          # → http://127.0.0.1:8765
```

The dashboard opens on **Pulse** (live vault certificate + run ledger) and
flows through Analyze, Run, Chat, Verify → Certificates, Feed. **Opening
`Chiron/dashboard.html` as a plain file shows dead panels** — it needs the
local services; always serve.

No install at all: the [playground](https://jiannotti5040.github.io/chiron-vault/playground.html)
runs the real engine in the browser.

CLI essentials:

```bash
pip install ./Primus                                # one dependency: numpy
primus collapse "1 1 2 3 5 8 13 21"                 # recover + prove a rule
echo "<model output>" | primus certify - --gate     # exit 1 on any REFUTED claim
primus certify - --jsonl                            # hash-chained pipeline mode
claude mcp add primus -- primus-mcp                 # the gate, callable by agents
python3 Chiron/chiron.py plan "1 1 2 3 5 8"         # a planner campaign (prototype)
```

## 3 · The gate battery

Run the relevant gates BEFORE claiming a change works; run the standard
battery before any commit that touches an engine or a gate. **A failing gate
is information, not an obstacle** — investigate the root cause; never widen a
tolerance to get green.

```bash
python3 bin/chiron test        # THE standard battery (spine, primus, twins,
                               # units, grow dry-run, drift, stress, monolith smoke)
python3 bin/chiron test --full # adds benchmark, fuzz, MCP, cached OEIS, full sweep
```

Individual suites, from `Primus/` unless noted:

| Suite | Command | Green looks like |
|---|---|---|
| Engine stress | `python3 test_invariant_engine.py` | 55/55 |
| Internal benchmark | `python3 benchmark.py` | PASS, zero false confidence |
| Certify + engine | `primus selftest` | PRIMUS GREEN (27/27 certify) |
| Adversarial fuzz | `python3 test_certify_fuzz.py` | 13/13 |
| Certify property grid | `python3 test_certify_property.py` | 2646 claims, 0 false / 0 missed |
| MCP handshake | `python3 test_mcp_server.py` | 10/10 |
| Twins cross-lock | `python3 test_twins_exact.py` | green |
| Drift (seed vs Chiron) | `python3 drift_check.py` | 42/42, ledger empty |
| Live OEIS (cached) | `python3 oeis_live.py` | zero false verifications |
| Spine | `python3 Chiron/chiron.py selftest` (repo root) | CHIRON GREEN 12/12 |
| Fold sweep | `python3 chiron_monolith.py --selftest` (Monolith dir) | 46/46 through the fold |
| Stress probes | `python3 Chiron/stress_test.py` | 23/23, no holes |
| Parity | via `bin/chiron parity` | 138/138 both incarnations |

## 4 · Change playbooks

**Any engine change (any hypothesis family).** Exact arithmetic only on the
stamping path — Fractions, exact integer equality, floats ≥ 2⁵³ refused. New
families must recover, predict held-out terms exactly, or abstain. Then the
full battery INCLUDING `oeis_live.py` and `drift_check.py`. If seed and
Chiron now disagree on purpose, add a dated `SEED_AHEAD_LEDGER` entry saying
why and what clears it — then port promptly so the ledger empties.

**New certify claim kind.** Exact semantics only (REFUSE rather than judge
approximations); deterministic work bounds against hostile input; selftest
gates for VERIFIED / REFUTED / REFUSED; a fuzz case if it adds a scan
pattern; document in `SCHEMA.md`; bump the schema string if fields change;
anchor-window any new regex scan.

**Docs / dashboard / tooling change.** Battery still runs before push (it is
cheap insurance and CI reruns it anyway), but no drift/oeis obligations.

**Commit style.** One logical change per commit; the message states what
changed, what got proven (gate counts), and any honest caveat — the log is
the lab notebook. **Never `git add -A` at the vault root** (the untracked
Xcode app `Jacob Dylan Iannotti/` contains an embedded git repo and becomes a
broken gitlink). Fresh certificates after battery runs are normal — commit
them as "fresh green certificates" or fold them into the change commit.

**Session discipline.** `git fetch && git status -sb` is the FIRST command of
any working session — this folder has lagged origin by 12 commits before,
and a day's work had to be re-applied.

## 5 · Defect-response protocol (the important one)

When external data catches a false verification — it has, three times — the
procedure, with the 2026-07-11→12 night as the worked example:

1. **Publish the miss the same night.** A dated OPEN-DEFECTS section in
   `Primus/EXTERNAL_VALIDATION.md` with the exact predicted-vs-expected
   values and the raw log tracked in git. De-overclaim every public surface
   (README headline, repo About) *before* fixing. The miss list is the
   product.
2. **File the defect issue** with one suspected root cause per miss.
3. **Reproduce fail-first** in a scratch harness before touching the engine.
4. **Root-cause each miss separately** — three misses were three different
   defects (a verification hole, a float leak, an evidence-thinness class).
   Never one patch for all.
5. **Fix structurally, never by tolerance.** If your first rule overshoots,
   the battery will catch it (it caught the blanket evidence rule killing
   legitimate order-2 stamps within minutes) — recalibrate on principle, not
   on green.
6. **Port to the twin** the same session; the engines never diverge silently.
7. **Lock the misses in forever:** new stress gates + new drift surfaces.
8. **Re-run the external validation that caught it.** Only a clean re-run
   upgrades OPEN → RESOLVED.
9. **Close the issue with the full story** — including what the fix cost
   (honesty ledger: which lucky stamps died, which true stamps now wait for
   more evidence).

## 6 · External validation

```bash
python3 Primus/oeis_live.py                          # cached corpus (offline, in CI)
python3 Primus/oeis_live.py --live                   # re-fetch the curated corpus
python3 Primus/oeis_live.py --live --keyword-core    # the full live sweep (author machine)
```

Rules: the probe list is fixed before grading; post-development fetches are
the honest kind and are labeled; misses are published (see §5); raw sweep
logs are tracked (`Primus/oeis_sweep_*.log`). Known API facts: OEIS's search
JSON is a bare list and stops serving pages around `start=110` — the pager
retries with backoff and grades the honest partial.

Baselines: `bench_symreg_external.py` (gplearn) and `bench_pysr.py` (PySR —
requires the deterministic triple: `deterministic=True`,
`parallelism="serial"`, `random_state`). Results live in
`Primus/SYMREG_RESULTS.md`; PySR's junk `outputs/` dir is gitignored.

## 7 · Growing the Congress

The heartbeat beats every 10 minutes under `chiron serve`: inward is always
on (the vault reading its own organs), outward is **dry-run by default** —
set `CHIRON_HEART_LIVE=1` to let exactly-verified knowledge land. Manual
growing: `python3 Chiron/chiron_grow.py --params Chiron/grow-public/parameters.json`.
Congress growth is committed on purpose ("grow: Congress …" commits); the
memory is part of the organism's story. An offline machine beats green on
inward+reflex and discloses the skip — only a real attempted failure marks a
beat red.

## 8 · Release (PyPI)

Trusted publishing is registered (project `primus-intelligence`, owner
`jiannotti5040`, repo `chiron-vault`, workflow `release.yml`, environment
`pypi`) — no tokens anywhere.

1. Do not release with open external defects. The gates may be green; the
   law is the law.
2. Bump `Primus/pyproject.toml` (the single version source) + `CHANGELOG.md`.
3. Full battery.
4. `git tag v<X.Y.Z>` matching pyproject exactly, push the tag.
5. `release.yml` verifies the match, reruns the gates, checks the LICENSE
   ships inside the wheel (PolyForm requires the notice to travel), publishes.

## 9 · Git, GitHub, and the machine

- **Push:** double-click `PUSH_TO_GITHUB.command` (it shows what's waiting
  and pushes `main`). CI ("Chiron CI") runs the battery on every push;
  `main` is branch-protected with required checks (`chiron`,
  `primus (os, python)` matrix).
- **Pages:** deploy-from-branch (`main` / root, `build_type: legacy` — it was
  once silently stuck in "workflow" mode with zero builds ever; if the site
  404s with Pages "enabled," check `build_type` first). `.nojekyll` keeps
  Pages from running Jekyll at all.
- **Secret scanning:** triage, don't panic. The 23 alerts of 2026-07-11 were
  Google's own frontend keys inside a Google-Docs HTML export — verified by
  reading the blob, dismissed as false-positive with the evidence written
  into each dismissal. Never commit rich-app HTML exports.
- **Never commit:** tokens (obviously), `environment.yml`-less stock
  workflows, rich HTML exports, `/outputs/` PySR droppings.

## 10 · Troubleshooting

| Symptom | Cause → fix |
|---|---|
| Dashboard panels dead / "not connected" | Opened as `file://` → serve it: `python3 bin/chiron serve` |
| Pages 404 though "enabled" | `build_type: workflow` with no workflow → PUT `build_type=legacy`, request a build |
| `git` says index.lock exists | A sandboxed/interrupted write → delete `.git/index.lock` |
| Finder shows files that were deleted | iCloud sync wedged (storage full) → trash the ghosts; disk is truth |
| OEIS sweep crashes on JSON | API shape/paging changed again → the pager's retry+partial logic is the pattern to extend |
| PySR raises about determinism | Set the full triple: `deterministic`, `parallelism="serial"`, `random_state` |
| Windows CI dies at checkout | A filename Windows can't hold (`*`, `"` …) → rename; audit before adding OS matrices |
| A gate went red after your change | Good. §5, step 5. |

## 11 · Epistemic status and what not to build

Label everything plainly: **implemented-and-tested**, **prototype** (planner,
plugins, events bus), or **theory** (HORIZON's outer rings). Overclaiming is
the one style error this project cannot afford — the README's headline claim
was rewritten the night it stopped being exactly true, and that edit mattered
more than any feature.

Do not build new layers, dashboards, folds, or copies of the engine. The
vault grows **outward** — users, external validation, exactness — not inward.
