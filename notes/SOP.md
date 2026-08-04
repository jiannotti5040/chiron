# Chiron Vault — Standard Operating Procedures

**This manual is the interface.** The dashboard is one way in; these
procedures are the real one. Every engine in the vault runs on its own, from
a shell or a Python import or an agent, and composes with the others however
you want. Part I tells you how to operate each engine for *your* purposes.
Part II tells you how to maintain the vault without breaking its one law.
Every command and output below is from a real session, unedited.

Companions: [DICTIONARY.md](DICTIONARY.md) (the vocabulary),
[ENCYCLOPEDIA.md](ENCYCLOPEDIA.md) (all 72 modules, generated from the
manifest), [RUNNING.md](../Chiron/docs/RUNNING.md) (the dashboard guide).

---

# PART I — OPERATING THE ENGINES

Setup once — the seed engine + certify gate; one dependency (numpy). Or skip
installs entirely: see §1.11 and §1.12. **Every command block in this manual
is paste-safe** (no inline comments, no placeholders — macOS zsh chokes on
both) and is executed as a gate by `ci/sop_smoke.py`, so if a documented
command breaks, CI goes red.

```bash
pip install ./Primus
```

Each procedure below follows the same shape: **what it's for → the
procedure → what you get back → how to cater it.**

## 1.1 · Recover the exact rule behind data

*For:* any structured stream you suspect has a law — sensor readings, ID
sequences, ledger deltas, generated series, puzzle data.

```bash
primus collapse "1 1 2 3 5 8 13 21 34 55 89 144"
```

> `VERIFIED generator 'linear_recurrence_order2' {'coeffs': [1.0, 1.0], 'seeds': [1.0, 1.0]}.
> Recovered from the first 9 terms, this rule then EXACTLY predicts all 3
> held-out terms — 90 bits of data it had never seen … Compresses 325→97 bits.`

From Python, with the full result object:

```python
from primus import collapse
inv = collapse([1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144])
inv.verified          # True — proven on withheld terms, exactly
inv.model_class       # 'linear_recurrence_order2'
inv.params            # the recovered law's parameters
inv.predict(20)       # extend it — exact integers out
inv.explanation       # the human-readable proof statement
```

**What "verified" costs:** exact prediction of held-out terms, in exact
arithmetic, with evidence scaled to model capacity. If the engine can't pay
that price it says so (`verified=False`, honest classification) — **refusal
is an answer**, and it's the answer that makes the stamps worth something.

**Cater it:** feed any integer/rational sequence (≥ 3 terms; more terms = 
more verifiable structure — an order-p recurrence needs enough held-out
evidence, see the DICTIONARY's *evidence rule*). Strings, ciphertexts, and
code go through Chiron's wider front door: `python3 Chiron/chiron.py` verbs,
or `trace.py` below.

## 1.2 · Gate an LLM or agent pipeline

*For:* refusing to let a model's arithmetic/factual errors flow downstream —
in CI, in an agent loop, in a data pipeline.

Pipe any model output in; the exit code is the gate — 0 clean, 1 if ANY
claim is REFUTED:

```bash
echo "17*3 = 51 and 2+2 = 5" | primus certify - --gate
```

A real certificate (`2^10 = 1025` is the model's error):

> `[✓ VERIFIED] aggregate    sum of 2, 3 and 7 is 12`
> `[✓ VERIFIED] arithmetic   17*3 = 51`
> `[✗ REFUTED ] arithmetic   2^10 = 1025`
> `VERDICT: Of 3 checkable claim(s): 2 verified, 1 refuted … coverage: 69.3% of input was checkable`

Pipeline mode — one hash-chained JSON certificate per line, tamper-evident
across the whole run:

```bash
cat model_outputs.txt | primus certify - --jsonl > certificates.jsonl
# stderr: {"chain_head":"daf31da5…","refuted_lines":1}
```

From Python / from agents:

```python
from primus import certify
cert = certify(model_output)
cert["counts"]                    # {'checkable': 2, 'verified': 1, 'refuted': 1, 'refused': 0}
cert["coverage"]                  # how much of the text was checkable AT ALL
cert["unverifiable_remainder"]    # True — free text is reported, never blessed
```

Register certify + collapse as native tools for any MCP agent:

```bash
claude mcp add primus -- primus-mcp
```

**Operational readings:** `--gate` exit codes make it a CI step; `coverage`
stops "nothing refuted" from meaning "nothing checked"; the schema contract
consumers should pin is `primus.certificate/2` (`Primus/SCHEMA.md`).

**Cater it:** ten claim kinds ship (arithmetic, aggregates, primality,
binomials, gcd/modular, dates, powers, sums/averages…). Adding your own kind
is a maintainer act — see Part II §4.

## 1.3 · The full accountability certificate (candor + law + math, one stamp)

*For:* auditing a model answer the way a skeptical reviewer would — tone,
checkable claims, and governance in one artifact.

```bash
python3 Chiron/llm_certify.py --text "The sum of 2 and 3 is 5, and 2^10 = 1025. Trust me, this is definitely correct."
```

> `Candor ......... 0.317  (patronizing/over-asserted)`
> `Checkable ...... 0/0 verified, 0 refused` *(a claim-form differences demo — the certify layer §1.2 catches the math)*
> `Governance ..... REJECT — critical non-compliance (AIA-ART-14: Reg (EU) 2024/1689, Art. 14)`
> `Attestation .... merkle=67d7b893…  ·  Legal status: assurance artifact, not a legal determination`

**Cater it:** `--domain` selects the governance regime; `--json` for the full
machine-readable certificate.

## 1.4 · Audit language for candor (Candor, standalone)

*For:* de-patronizing anything — model output, your own writing, docs.

```bash
python3 Chiron/chiron.py audit "Great question! You're absolutely right to ask. It's probably fine."
```

> `CANDOR — score 0.76/1.00  [mostly candid]`
> `  condescension 0.24 · unearned_confidence 0.00 · evasion 0.00 · opacity 0.00`
> `  [condescension] "Great question" — unearned praise, not substance`
> `  LIMITS: lexical/structural detector, not semantic … findings are spans to inspect, never a verdict.`

Note the engine states its own limits on every run. That honesty is the
product; keep it when you embed this.

## 1.5 · See the reasoning, not just the answer

*For:* trust-building, teaching, debugging a surprising result.

```bash
python3 Chiron/trace.py "1 1 2 3 5 8 13 21 34 55"
```

> `STEP 1 — candidate generators, ranked by description length`
> `   #1  linear_recurrence_order2   24.27 bits   conf 1.00  <== WINNER`
> `STEP 2 — why this winner: 24.27 bits vs 98.76 bits to list the raw terms …`

Strings and ciphertexts work too (`trace.py "wkh fdw vdw"`). Add
`--json` to get the whole ranked ladder programmatically. To seed the memory
with a cryptography basis first: `python3 Chiron/chiron_ciphers.py`.

## 1.6 · Cross-examine a finding adversarially

*For:* attacking your own result before someone else does.

```bash
python3 Chiron/cross_examine.py examine 1 1 2 3 5 8 13 21 34 55
```

Perturbs, truncates, and re-derives — reports what survives. `demo` shows
the full routine.

## 1.7 · Turn a verified law into a governed decision

*For:* the last mile — forecast, anomaly flag, and a recommendation that has
passed a governance gate, from one command.

```bash
python3 Chiron/actionable_intelligence.py brief 100 103 106 109 112 115 118 121
```

> `WHAT IT IS      VERIFIED generator 'arithmetic'.`
> `WHAT'S NEXT     forecast (+3): [124, 127, 130]`
> `WHAT'S WRONG    none — every entry obeys the recovered law`
> `HOW SURE + WHY  verified=True  compression=4.881x  margin=20.183`

`batch` processes many streams; `--horizon N` sets the forecast length;
`--json` feeds your own tooling. The governance layer alone:
`python3 Chiron/govern.py gate|comply|walk` (thresholds via `--Cx --Ar --Hp
--Mc --V`, regime via `--domain`).

## 1.8 · Build your own validation system (compose the engines)

*For:* the real point of the vault — **you design the checks.** Wire any
engines into a chain, a team, or a swarm, arbitrated by the one gate, and get
back a single signed verdict. The rule never lies: **the pipeline verifies
only if every required stage verified; any refusal or refutation makes it
abstain or fail.** No stage can upgrade another's verdict.

Five composable components, all exact, all already in the vault:
`collapse` (prove a rule), `cross_examine` (attack it), `certify` (judge a
text's claims), `govern` (clear against a regime), `candor` (audit tone).

Three modes: **chain** (stages in order over one input, stop on a required
failure), **team** (every stage over the same input, verdict = AND of
required), **swarm** (a chain fanned across many inputs).

See the built-in worked examples and the composer's own gates:

```bash
python3 Chiron/pipeline.py demo
python3 Chiron/pipeline.py selftest
```

Run a validation system you declared as data — this one recovers a rule and
then adversarially attacks it, passing only if both hold:

```bash
python3 Chiron/pipeline.py run '{"mode":"chain","input":"1 1 2 3 5 8 13 21 34 55","stages":[{"component":"collapse"},{"component":"cross_examine"}]}'
```

> `PIPELINE (chain) -> VERIFIED`
> `  [PASS] collapse       VERIFIED linear_recurrence_order2`
> `  [PASS] cross_examine  SURVIVES CROSS-EXAMINATION — search space exhausted, no peer generator`

From Python, the fluent builder — this is how you cater it to whatever a
court, an auditor, or a pipeline needs:

```python
from pipeline import Pipeline

# a text-integrity gate: the claims must verify AND the tone must be candid
verdict = Pipeline("team").certify().candor().run("The total of 2 and 3 is 5.")
verdict["verified"]        # True only if BOTH required stages passed

# a swarm: one proof-chain fanned across a whole batch, each independently judged
batch = Pipeline("swarm").collapse().run(inputs=["1 1 2 3 5 8", "2 4 6 8 10", "4 6 8 9 10 12"])
batch["verified_count"]    # how many of the batch earned a stamp
```

Mark a stage `required=False` to make it advisory (it reports but can't sink
the verdict). Add stages, reorder them, mix text and numeric components —
the AND-of-required rule holds no matter what you build. **This is the
system for designing whatever validations-and-checks you need**, and it runs
from the shell, from Python, or from the dashboard's Run tab (§1.11).

## 1.9 · Compose toward a goal (bounded agency)

*For:* multi-step work where every step must pass the gate and anything
irreversible must reach a human. This is the vault's answer to "agent mode."

```bash
python3 Chiron/planner.py run "1 1 2 3 5 8 13 21 34 55 89 144"
```

> `{"intent": "recover, verify, and prepare to publish a rule", "status": "ESCALATED",`
> ` "steps": [ {"step": "observe", "ok": true, "verdict": "parsed 12 terms"},`
> `            {"step": "analyze", "ok": true, "verdict": "collapse -> linear_recurrence_order2 (verified=True)"}, … ]}`

The contract: an unverifiable surface **halts** at the gate; the publish
step **escalates** instead of executing; `--budget` bounds the campaign;
every step lands in the run ledger. Passive wiring between your own
components: `from chiron_events import Bus` (events carry the engine's
verdict verbatim, never upgrade it). Both are labeled **prototype** — read
their docstrings before leaning hard.

## 1.9 · Grow the memory on YOUR corpus

*For:* making the organism learn your domain — only exactly-verified laws
ever land.

```bash
python3 Chiron/chiron_grow.py --params Chiron/grow-public/parameters.json --dry-run --once
python3 Chiron/grow_clean.py --help
```

(`grow_clean` feeds any file, a Wikipedia preset, or LLM-proposed material —
all through the same verified-or-refused gate.)

Point `parameters.json` at your topics or feed files directly. The Congress
(`chiron_memory.json`) is the replayable journal of everything earned;
`python3 Chiron/chiron.py` can search and summarize it. Unattended: the
heartbeat's outward beat stays **dry-run** until you set
`CHIRON_HEART_LIVE=1` — growth is opt-in by design.

## 1.10 · The same contract on meaning, protocols, everything else

The discipline is one interface — `Surface → Hypothesis → Constraint →
Verify → Certificate` — instantiated across domains:

In order: the contract walked end to end; the semantic calculus (56 gates);
a multi-surface sweep; the head-to-head with general compressors (a law, not
a dictionary); six domains vs established baselines.

```bash
python3 Chiron/epistemic.py demo
python3 Chiron/semic.py selftest
python3 Chiron/discover.py 3 6 9 12 "abcabcabc"
python3 Chiron/compare.py
python3 Chiron/bench_suite.py
```

Every other module — authorship, legal corpus, protocol inference,
aesthetics, energy layer — follows the same shape and is catalogued with its
commands and lenses in the [ENCYCLOPEDIA](ENCYCLOPEDIA.md).

## 1.11 · Ship it your way (no dashboard required)

- **One file.** `Chiron Monolith/chiron_monolith.py` carries all 69 modules:
  `python3 chiron_monolith.py <module> [args…]` runs any of the above with
  zero siblings. `--list` shows everything.
- **Extend without rebuilding.** Drop `yourmodule.py` into
  `Chiron Monolith/plugins/` and run it the same way; your module may
  `import chiron` and friends. Embedded modules always win over plugins —
  you can add to the runtime, never silently replace the certified spine.
- **HTTP, if you want services.** `python3 bin/chiron serve` starts the
  stack; the endpoints are plain JSON you can hit from anything —
  `GET :8769/api/assistant/manifest` (the module index),
  `:8768/api/console/…` (run any function), `:8767/api/control/…` (grower).
  The dashboard is just a client of these.
- **Machine-readable results.** Every certifying run leaves
  `Chiron/artifacts/<module>/latest.json` — poll those files instead of
  parsing stdout.
- **Agents.** `primus-mcp` (§1.2) makes the gate a native tool for any MCP
  agent.

## 1.12 · Zero-install: the browser

<https://jiannotti5040.github.io/chiron-vault/playground.html> — the real
engine sources, fetched verbatim from this repo, running client-side on
CPython/WebAssembly. Nothing leaves the tab.

---

# PART II — MAINTAINING THE VAULT

## 2.0 · The one law

**Zero false verifications.** A change that makes any engine stamp something
it cannot exactly prove is wrong even if every benchmark number improves.
Refusal is a feature. When recall and honesty conflict, choose honesty.

## 2.1 · Sources of truth (edit these; never their copies)

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

## 2.2 · The gate battery

Run the relevant gates BEFORE claiming a change works; run the standard
battery before any commit that touches an engine or a gate. **A failing gate
is information, not an obstacle** — investigate the root cause; never widen a
tolerance to get green.

The standard battery, and the full one (adds benchmark, fuzz, MCP, cached
OEIS, full sweep):

```bash
python3 bin/chiron test
python3 bin/chiron test --full
```

| Suite (from `Primus/` unless noted) | Command | Green |
|---|---|---|
| Engine stress | `python3 test_invariant_engine.py` | 55/55 |
| Internal benchmark | `python3 benchmark.py` | PASS, zero false confidence |
| Certify + engine | `primus selftest` | PRIMUS GREEN (27/27) |
| Adversarial fuzz | `python3 test_certify_fuzz.py` | 13/13 |
| Certify property grid | `python3 test_certify_property.py` | 2646 claims, 0/0 |
| MCP handshake | `python3 test_mcp_server.py` | 10/10 |
| Twins cross-lock | `python3 test_twins_exact.py` | green |
| Drift (seed vs Chiron) | `python3 drift_check.py` | 42/42, ledger empty |
| Live OEIS (cached) | `python3 oeis_live.py` | zero false verifications |
| Spine | `python3 Chiron/chiron.py selftest` (root) | CHIRON GREEN 12/12 |
| Fold sweep | `python3 chiron_monolith.py --selftest` | 47/47 through the fold |
| Stress probes | `python3 Chiron/stress_test.py` | 23/23 |
| Parity | `bin/chiron parity` | 138/138 both incarnations |

## 2.3 · Change playbooks

**Any engine change.** Exact arithmetic only on the stamping path —
Fractions, exact integer equality, floats ≥ 2⁵³ refused. New families must
recover, predict held-out terms exactly, or abstain. Then the full battery
INCLUDING `oeis_live.py` and `drift_check.py`. If seed and Chiron disagree
on purpose, add a dated `SEED_AHEAD_LEDGER` entry; port promptly so it
empties.

**New certify claim kind.** Exact semantics only; deterministic work bounds
against hostile input; gates for VERIFIED / REFUTED / REFUSED; a fuzz case if
it adds a scan pattern; document in `SCHEMA.md`; bump the schema string if
fields change; anchor-window any new regex scan.

**Commit style.** One logical change per commit; the message states what
changed, what got proven (gate counts), and any honest caveat. **Never
`git add -A` at the vault root** (the untracked Xcode app contains an
embedded git repo). Fresh certificates after battery runs are normal.

**Session discipline.** `git fetch && git status -sb` FIRST — this folder
has lagged origin by 12 commits before.

## 2.4 · Defect-response protocol (the important one)

When external data catches a false verification — it has, three times — with
the 2026-07-11→12 night as the worked example:

1. **Publish the miss the same night** (dated OPEN section in
   `Primus/EXTERNAL_VALIDATION.md`, raw log tracked, README/About
   de-overclaimed *before* fixing). The miss list is the product.
2. **File the defect issue** — one suspected root cause per miss.
3. **Reproduce fail-first** in a scratch harness.
4. **Root-cause each miss separately** — three misses were three different
   defect classes. Never one patch for all.
5. **Fix structurally, never by tolerance.** If your rule overshoots, the
   battery catches it (it caught the blanket evidence rule within minutes) —
   recalibrate on principle, not on green.
6. **Port to the twin** the same session.
7. **Lock the misses in forever:** new stress gates + drift surfaces.
8. **Re-run the external validation that caught it.** Only a clean re-run
   upgrades OPEN → RESOLVED.
9. **Close the issue with the full story,** including the honesty ledger of
   what the fix cost.

## 2.5 · External validation

Cached (offline, what CI runs) · live re-fetch of the curated corpus · the
full live sweep (author machine, needs oeis.org):

```bash
python3 Primus/oeis_live.py
python3 Primus/oeis_live.py --live
python3 Primus/oeis_live.py --live --keyword-core
```

Probe lists fixed before grading; post-development fetches labeled; misses
published; sweep logs tracked (`Primus/oeis_sweep_*.log`). Known API facts:
OEIS search JSON is a bare list and stops paging near `start=110` — the
pager retries and grades the honest partial. Baselines:
`bench_symreg_external.py` (gplearn), `bench_pysr.py` (PySR — needs
`deterministic=True, parallelism="serial", random_state`). Results:
`Primus/SYMREG_RESULTS.md`.

## 2.6 · Release (PyPI)

Trusted publishing registered (project `primus-intelligence`, owner
`jiannotti5040`, repo `chiron-vault`, workflow `release.yml`, environment
`pypi`).

1. **Never release with open external defects** — green gates don't override
   the law.
2. Bump `Primus/pyproject.toml` + `CHANGELOG.md`.
3. Full battery.
4. Tag matching pyproject exactly, then push the tag — e.g. for 0.6.0:
   `git tag v0.6.0` and `git push origin v0.6.0`.
5. `release.yml` verifies the match, reruns gates, checks the LICENSE ships
   in the wheel, publishes.

## 2.7 · Git, GitHub, machine

Push via `bin/push-to-github.command`; CI runs the battery per push; `main` is
protected with required checks. Pages is deploy-from-branch
(`build_type: legacy` — if the site 404s while "enabled," check that field
first; `.nojekyll` keeps Jekyll out). Secret-scanning alerts get triaged
with evidence, not panic (the 23 of 2026-07-11 were Google's own frontend
keys inside a Docs HTML export — never commit rich-app exports).

## 2.8 · Troubleshooting

| Symptom | Cause → fix |
|---|---|
| Dashboard panels dead | Opened as `file://` → `python3 bin/chiron serve` |
| Pages 404 though "enabled" | `build_type: workflow`, no workflow → set `legacy`, request build |
| `.git/index.lock` exists | Interrupted write → delete the lock |
| Finder shows deleted files | iCloud sync wedged → trash the ghosts; disk is truth |
| OEIS sweep JSON crash | API shape/paging drifted again → extend the pager's retry+partial pattern |
| PySR determinism error | Set the full triple (serial + seed + deterministic) |
| Windows CI dies at checkout | Illegal filename (`*`, `"`…) → rename |
| A gate went red after your change | Good. §2.4, step 5. |

## 2.9 · Epistemic status and what not to build

Label everything plainly: **implemented-and-tested**, **prototype** (planner,
plugins, events bus), or **theory** (HORIZON's outer rings). Overclaiming is
the one style error this project cannot afford. Do not build new layers,
dashboards, folds, or copies of the engine — the vault grows **outward**:
users, external validation, exactness.
