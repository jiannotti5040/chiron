# Link audit — public repo

**Audit date: 2026-07-23.** Read-only audit; no repository file was modified by this pass
except the creation of this report.

> Provenance note, so no number here is unsourced: the HTTP probes below were executed on
> this host with `curl 8.7.1`, host clock reading `2026-07-25T21:19:08Z`. The audit is dated
> 2026-07-23 as assigned; the status codes are the ones the real probe returned.

**External links were checked by HTTP status code only.** Every external check was a single
`curl -s -o /dev/null -w "%{http_code}" -m 20 --location URL` request. Nothing was clicked,
submitted, executed, or authenticated. A status code is evidence of reachability, not of
correct page content.

---

## Summary

| Measure | Count |
|---|---|
| Files crawled (`.md` + `.html`) | 16 |
| Internal / relative links extracted | 49 |
| **Broken internal links** | **0** |
| External URLs extracted (unique) | 25 |
| External URLs probed by HTTP status | 25 |
| External URLs returning a non-200 code | 4 (all explained below; none broken as used) |
| `mailto:` / in-page-fragment links | 9 |
| Gate-number disagreements with `docs/BATTERIES.md` | 7 |
| Other numeric inconsistencies (no BATTERIES entry to disagree with) | 3 |

Files crawled:

```
LICENSE.md            PRICING.md            README.md
VerifiedInk/VERIFIED_INK.md                 VerifiedInk/verified_ink.html
docs/ARCHITECTURE.md  docs/BATTERIES.md     docs/GATES.md
docs/GOVERNANCE.md    docs/PHILOSOPHY.md    docs/SYMREG.md
docs/index.html       docs/playground/index.html
eval/README.md        examples/README.md    prototype/README.md
```

Link forms extracted: markdown `[text](target)`, HTML `href=` / `src=`, angle-bracket
autolinks `<https://…>`, bare URLs in prose, plus a manual sweep of `https?://` inside
HTML `<meta>` content and JavaScript string literals (which the markdown/HTML attribute
patterns do not reach).

---

## Broken internal links

**None. 0 broken internal links.**

All 49 internal/relative targets resolve on disk relative to their containing file — 30 to
existing files, 19 to existing directories.

Two extraction artifacts are recorded here so a future run does not re-raise them as findings:

- `docs/playground/index.html:865` — `"//gc.zgo.at/count.js"`. A naive relative-path resolver
  reports this as missing. It is **not an internal link**: it is a protocol-relative external
  URL inside a JavaScript string, and it is behind a disabled guard —
  `docs/playground/index.html:863` sets `const GC_CODE = "";` and the block only runs
  `if (GC_CODE)`, so nothing is ever loaded. Probed anyway: `https://gc.zgo.at/count.js` → **200**.
- `docs/playground/index.html:37` — `data:image/svg+xml,…` favicon. A data URI, not a path.
  The `http://www.w3.org/2000/svg` inside it is an XML namespace identifier, not a fetchable link.

In-page fragment targets were verified to exist:

| Fragment link | Cited at | Anchor defined at | Result |
|---|---|---|---|
| `#claim-checker` | `docs/playground/index.html:368`; also the tail of the external playground URL in `README.md:20`, `PRICING.md:5` | `docs/playground/index.html:371` (`id="claim-checker"`) | resolves |
| `#sequence-lab` | `docs/index.html:242` | `docs/playground/index.html:392` (`id="sequence-lab"`) | resolves |
| `#proof` | `docs/index.html:186`, `docs/index.html:201` | `docs/index.html:215` (`id="proof"`) | resolves |
| `#how-it-works` | `docs/index.html:185` | `docs/index.html:223` (`id="how-it-works"`) | resolves |

Two related integrity checks, since the pages make claims about the files they link to:

- The CI badges at `README.md:5` and `README.md:6` point at `proof.yml` and `live-eval.yml`;
  both exist in `.github/workflows/`.
- `docs/playground/index.html:8` claims the playground's local `.py` copies are byte-identical
  to `prototype/`. Verified with `shasum -a 256`:
  `browser_core.py` → `06414b155866141daf3c3215d3e33406fef3f33a2890c4d189c62fa3b34f1d0e` (identical),
  `primus_prototype.py` → `5cf6c0d97f292aaf1b27ba7ae0a2a3814e0de35899511f6da2a7b8bc80a65cb0` (identical).

---

## External link status table

All codes from `curl -s -o /dev/null -w "%{http_code}" -m 20 --location URL`. **Status only —
page content was not inspected.**

| URL | Cited at | Code | Read |
|---|---|---|---|
| `https://polyformproject.org/licenses/noncommercial/1.0.0` | `LICENSE.md:7`, `LICENSE.md:13` | **200** | OK |
| `https://jiannotti5040.github.io/chiron/` | `docs/index.html:8`, `:12`, `:25` | **200** | OK |
| `https://jiannotti5040.github.io/chiron/playground/` | `README.md:36`, `docs/playground/index.html:17`, `:27`, `:31` | **200** | OK |
| `https://jiannotti5040.github.io/chiron/playground/#claim-checker` | `README.md:20`, `PRICING.md:5` | **200** | OK (base URL; anchor verified above) |
| `https://jiannotti5040.github.io/chiron/assets/chiron-social.jpg` | `docs/index.html:13`, `:17`; `docs/playground/index.html:32`, `:36` | **200** | OK |
| `https://jiannotti5040.github.io/chiron/sitemap.xml` | `docs/robots.txt:4` | **200** | OK |
| `https://buy.stripe.com/7sYaEX1817df9047KR67S0c` | `PRICING.md:11`, `PRICING.md:46`, `docs/index.html:295` | **200** | OK |
| `https://buy.stripe.com/8x29AT03X9lna486GN67S0d` | `PRICING.md:12`, `PRICING.md:47`, `docs/index.html:302` | **200** | OK |
| `https://buy.stripe.com/fZufZh5oh4134JO4yF67S0e` | `PRICING.md:13`, `PRICING.md:48`, `docs/index.html:303` | **200** | OK |
| `https://github.com/jiannotti5040/chiron` | `README.md:42`, `docs/index.html:187`, `:323`, `docs/playground/index.html:356`, `:488` | **200** | OK |
| `…/actions/workflows/proof.yml/badge.svg` | `README.md:5` | **200** | OK |
| `…/actions/workflows/live-eval.yml/badge.svg` | `README.md:6` | **200** | OK |
| `https://github.com/jiannotti5040/chiron/blob/main/PRICING.md` | `docs/index.html:189`, `:296`, `:324`; `docs/playground/index.html:357`, `:469`, `:490`, `:625` | **200** | OK |
| `https://github.com/jiannotti5040/chiron/blob/main/docs/BATTERIES.md` | `docs/playground/index.html:475` | **200** | OK |
| `https://github.com/jiannotti5040/chiron/tree/main/eval` | `docs/index.html:218`, `:322`; `docs/playground/index.html:423`, `:455`, `:475`, `:489` | **200** | OK |
| `https://github.com/jiannotti5040/chiron/tree/main/VerifiedInk` | `docs/playground/index.html:721` | **200** | OK |
| `https://raw.githubusercontent.com/…/main/prototype/browser_core.py` | fetch base at `docs/playground/index.html:501` | **200** | OK |
| `https://raw.githubusercontent.com/…/main/prototype/primus_prototype.py` | fetch base at `docs/playground/index.html:501` | **200** | OK |
| `https://cdnjs.cloudflare.com/ajax/libs/p5.js/1.7.0/p5.min.js` | `VerifiedInk/verified_ink.html:11` | **200** | OK |
| `https://fonts.googleapis.com/css2?family=Poppins…&family=Lora…` | `VerifiedInk/verified_ink.html:14` | **200** | OK |
| `https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js` | `docs/playground/index.html:496` | **200** | OK |
| `https://gc.zgo.at/count.js` | `docs/playground/index.html:865` (JS string, disabled) | **200** | OK |
| `https://fonts.googleapis.com` | `VerifiedInk/verified_ink.html:12` | **404** | **Not broken.** `rel="preconnect"` hint — a TCP/TLS warm-up target, never fetched as a document. The bare origin is not expected to serve a page. |
| `https://fonts.gstatic.com` | `VerifiedInk/verified_ink.html:13` | **404** | **Not broken.** Same: `rel="preconnect" crossorigin`. |
| `https://chiron-engine.onrender.com` | `README.md:73`, `:74`; `docs/BATTERIES.md:20`; `docs/playground/index.html:461`, `:503`; `eval/README.md:71`, `:72`, `:73` | **404** at root | **Not broken as used.** It is never navigated to as a page — it is a base URL that `eval/remote.py --url …` and the playground append routes to. The service is live: `https://chiron-engine.onrender.com/health` → **200**. |
| `https://chiron-engine.onrender.com/health` | `docs/playground/index.html:464`; referenced in prose at `eval/README.md:80` | **200** | OK — confirms the demo endpoint is up. |
| `https://chiron.goatcounter.com` | `docs/playground/index.html:862` | **400** | **Not a link.** It appears only inside a source comment as an example of what a GoatCounter code would produce. Analytics is off (`GC_CODE = ""`). No page ever requests it. |

Not probed, with reasons:

- `http://localhost:8000/docs/playground/` (`README.md:37`) — a local instruction to the reader
  (`python3 -m http.server` from the repo root), not a published resource. Nothing was served
  during this audit, so probing it would have produced a meaningless failure.
- `https://schema.org` (`docs/index.html:20`, `:36`) — a JSON-LD `@context` vocabulary
  identifier, not a navigable link.
- `http://www.w3.org/2000/svg` (`docs/playground/index.html:37`) — an XML namespace URI inside
  the `data:` favicon, not a navigable link.

### On the Stripe codes specifically

All three `buy.stripe.com` checkout links returned **200**. No non-200 code had to be
interpreted, so nothing here rests on the "a bot may legitimately get a non-200" allowance.
A 200 means the checkout page is served; **it is not evidence that the price, product, or tier
mapping behind it is correct.** That mapping is asserted by the repo text quoted in the next
section and was not independently verified against the Stripe account.

---

## Stripe links verified

All three checkout links are present in `PRICING.md`, each appearing twice — once in the tier
table and once in the "Start commercial access" list — and the pairs are consistent. Verbatim lines:

**Individual — $100/month**

```
PRICING.md:11:| **Individual / Research** | [**$100 / month — start checkout**](https://buy.stripe.com/7sYaEX1817df9047KR67S0c) | one developer, researcher, or independent builder | 1 seat · commercial use · full `chiron-vault` access · modify for your own use · contribute improvements back |
PRICING.md:46:- [Start Individual — $100/month](https://buy.stripe.com/7sYaEX1817df9047KR67S0c)
```

**Team — $500/month**

```
PRICING.md:12:| **Team** | [**$500 / month — start checkout**](https://buy.stripe.com/8x29AT03X9lna486GN67S0d) | small teams and startups | up to 5 seats · everything above · shared internal deployment |
PRICING.md:47:- [Start Team — $500/month](https://buy.stripe.com/8x29AT03X9lna486GN67S0d)
```

**Business — $2,000/month**

```
PRICING.md:13:| **Business** | [**$2,000 / month — start checkout**](https://buy.stripe.com/fZufZh5oh4134JO4yF67S0e) | growing companies putting AI into real workflows | up to 25 seats · priority on accepted contributions · onboarding call |
PRICING.md:48:- [Start Business — $2,000/month](https://buy.stripe.com/fZufZh5oh4134JO4yF67S0e)
```

Tiering result:

| Tier | Price stated | Checkout URL | Consistent across both citations | Distinct URL |
|---|---|---|---|---|
| Individual / Research | $100 / month | `…/7sYaEX1817df9047KR67S0c` | yes (`:11`, `:46`) | yes |
| Team | $500 / month | `…/8x29AT03X9lna486GN67S0d` | yes (`:12`, `:47`) | yes |
| Business | $2,000 / month | `…/fZufZh5oh4134JO4yF67S0e` | yes (`:13`, `:48`) | yes |

The same three URLs appear on the landing page at `docs/index.html:295` (Individual),
`docs/index.html:302` (Team), and `docs/index.html:303` (Business), matching the `PRICING.md`
tier assignment.

Two tiers deliberately have **no** checkout link, consistent with `PRICING.md:44`
("Checkout is live for Individual, Team, and Business"): **Business Scale**
(`PRICING.md:14`, "up to $10,000 / month") and **Enterprise** (`PRICING.md:15`, "Custom").
`PRICING.md:54` routes both through the email contact instead. That is correct, not a gap.

Scope limit, stated plainly: this confirms *presence, tiering, and internal consistency of the
links in the repo, plus a 200 from each URL*. It does not confirm what price Stripe charges.

---

## Gate-number disagreements

`docs/BATTERIES.md` is the source of truth. Every row below is reported as
`file:line — cited number vs BATTERIES number`. **Nothing was fixed.**

### 1. Full folded sweep: 48/48 vs 49/49 (two occurrences)

| # | Location | Cited | BATTERIES says |
|---|---|---|---|
| 1 | `docs/GATES.md:11` | **48/48** | **49/49** (`docs/BATTERIES.md:52`) |
| 2 | `docs/GATES.md:20–21` | **(48/48)** | **49/49** (`docs/BATTERIES.md:52`, restated `:76`) |

```
docs/GATES.md:11:| **Full folded sweep** (in-repo) | **48/48** | every selftest-bearing module runs green through the fold (49/49 on the 2026-07-21 build — the sweep grows with the spine; the reconciled map of every battery lives in [BATTERIES.md](BATTERIES.md)) |
docs/GATES.md:20:The broader in-repo sweep
docs/GATES.md:21:(48/48) includes orchestration and serving modules — live servers, the packaged
```

```
docs/BATTERIES.md:52:| Monolith full folded sweep | every selftest-bearing module, through the fold | **49/49** |
docs/BATTERIES.md:76:no vault beside it; the 49/49 sweep includes modules (servers, packaged
```

The headline figure a reader sees in the `GATES.md` table is 48/48. The parenthetical does
name 49/49 as the 2026-07-21 build, so the page is not *hiding* the newer number — but the
number in the result column disagrees with the source of truth. `README.md:214` gets this
right (`**49/49** … (2026-07-21 build; 48/48 on 2026-07-16 …)`).

### 2. External OEIS validation on n=29: 18 vs 20 (three occurrences)

| # | Location | Cited | BATTERIES says |
|---|---|---|---|
| 3 | `docs/SYMREG.md:29` | **Primus 18 exact / 0 wrong / 11 refused** | **20 verified / 0 false / n=29** (`docs/BATTERIES.md:42`) |
| 4 | `docs/SYMREG.md:56` | **Primus 18 exact / 0 wrong / 11 refused** | **20 verified / 0 false / n=29** (`docs/BATTERIES.md:42`) |
| 5 | `README.md:222` | **Primus 18 exact / 0 wrong / 11 refused** | **20 verified / 0 false / n=29** (`docs/BATTERIES.md:42`) |

```
docs/SYMREG.md:17:each of 29 live-fetched OEIS sequences (corpus fetched 2026-07-04, before the
docs/SYMREG.md:29:| **Primus** | **18** | **0** | 11 |
docs/SYMREG.md:36:closed-form equation, and answered wrong, 24 times. Primus stamped 18
docs/SYMREG.md:56:| **Primus** | **18** | **0** | 11 |
```

```
docs/BATTERIES.md:42:| **External OEIS validation** | live-fetched sequences the author didn't write; graded on exact prediction of unseen terms | **20 verified / 0 false / n=29** |
```

Why this is a real disagreement and not two different batteries: `docs/SYMREG.md:16` opens the
protocol section with *"Same as the external validation"*, and both pages state the same
corpus size, **n=29**. On that same 29-sequence corpus, SYMREG reports Primus stamping **18**
(18 + 11 refused = 29) while BATTERIES reports **20 verified**. The `0 wrong` / `0 false`
halves agree; the stamped count does not. One of the two is stale, or SYMREG is grading on the
next-4-terms rule (`docs/SYMREG.md:19`) while BATTERIES is grading a different held-out depth —
in which case the two rows need to say so, because as written they claim to be the same run.

### 3. Prototype vs vault gate total: "97" has no BATTERIES entry

| # | Location | Cited | BATTERIES says |
|---|---|---|---|
| 6 | `prototype/README.md:68` | **"the vault's real 97"** | *no 97 anywhere in `docs/BATTERIES.md`* |

```
prototype/README.md:67:
prototype/README.md:68:The prototype's own gate battery — honestly **26 gates**, *not* the vault's real
prototype/README.md:69:97 — enforces:
```

The `26` is correct (`docs/BATTERIES.md:16` — **26/26**). The `97` is unreconciled: no battery,
sum, or subtotal in `BATTERIES.md` equals 97. For reference, the Tier-2 counts as listed sum to
163 for Primus (55 + 51 + 16 + 11 + 18 + 12) and 105 for the Chiron spine (12 + 5 + 49 + 23 + 7 + 9).
Whatever 97 was, `BATTERIES.md` no longer carries it.

### 4. Build-date labels attached to the numbers

| # | Location | Cited | BATTERIES says |
|---|---|---|---|
| 7 | `docs/GATES.md:6` | **"Current build — 2026-07-16, Python 3.14"** | Tier 2 is dated **2026-07-21** (`docs/BATTERIES.md:28`) |

```
docs/GATES.md:6:## Current build — 2026-07-16, Python 3.14
docs/BATTERIES.md:28:## Tier 2 — the vault build (delivered with a license) — as most recently run, 2026-07-21
```

`GATES.md` is internally consistent with its own 2026-07-16 header (48/48 was the 2026-07-16
number), so this is the same staleness as finding #1 rather than an independent error — but it
is the reason the number is wrong, so it is listed separately for whoever fixes it.

Closely related, and worth fixing in the same pass though it is a self-inconsistency rather
than a BATTERIES disagreement: `README.md:209` introduces its table with *"On the current build
(2026-07-16, Python 3.14), the full battery is green"*, and the very next rows report the
**2026-07-21** figures (`README.md:214`, 49/49). The prose date and the table's numbers are from
different builds.

### Numbers that were checked and AGREE with BATTERIES

Recorded so a future pass does not re-verify them:

| Claim | Cited at | BATTERIES |
|---|---|---|
| Prototype selftest **26/26** | `prototype/README.md:66`, `:101`; `README.md:84`; `docs/playground/index.html:8`, `:481` ("26 gates") | `:16` ✓ |
| Browser demo core **17/17** | `prototype/README.md:132`; `README.md:84` | `:17` ✓ |
| **22 stamped / 22 correct / 0 false / 12 refusals** | `README.md:12`, `:59`, `:220`; `docs/PHILOSOPHY.md:12–13`; `eval/README.md:29–31`; `docs/index.html:217`, `:218`, `:219`; `docs/playground/index.html:423`, `:455` | `:18` ✓ |
| Endpoint gates **18/18** | `README.md:78`; `eval/README.md:66` | `:20`, `:38` ✓ |
| Standalone core smoke **5/5** | `README.md:213`; `docs/GATES.md:10`, `:19` | `:51` ✓ |
| JDICert **280/280** | `README.md:213`; `docs/GATES.md:10`; `docs/ARCHITECTURE.md:23` | `:51` ✓ |
| semic **56/56** | `README.md:213`; `docs/GATES.md:10` | `:51` ✓ |
| Stress probes **23/23** | `README.md:215`; `docs/GATES.md:12` | `:53` ✓ |
| Pipeline composer **7/7** | `README.md:216`; `docs/GATES.md:13` | `:54` ✓ |
| Documented-command smoke **9/9** | `README.md:217`; `docs/GATES.md:14` | `:55` ✓ |
| 34 sequences, 12 shown, terms 13..20 held out | `README.md:220`; `eval/README.md:17` | `:18` ✓ |
| TWIN PROOF `279,608,910,057,308,160` | `README.md:218`; `docs/GATES.md:15`; `prototype/README.md:46`, `:57`, `:60` | consistent across all five ✓ |

The eval headline was additionally re-derived from the artifact itself rather than taken on
trust. Reading `eval/frozen_predictions.json` directly:

```
n rows: 34
status Counter({'VERIFIED': 22, 'REFUSED': 12})
engine {"name": "primus", "version": "0.6.0+source"}
frozen_utc "2026-07-21T11:26:51+00:00"
protocol {"shown_terms": 12, "frozen_predictions_per_stamp": 8}
```

22 + 12 = 34, matching `docs/BATTERIES.md:18` and every page that cites it. This confirms the
*composition of the frozen file*; it does not re-grade the predictions against OEIS, which is
what `eval/grade.py` is for and which this audit did not run.

### Other numeric inconsistencies (no BATTERIES entry to disagree with)

Not gate-count disagreements — flagged because they are numeric claims a reader can check.

1. **`eval/README.md:30–31` — "against both pinned snapshots."** Only one snapshot ships:
   `eval/oeis_snapshot_2026-07-07.json`. `eval/grade.py:19` says so in its own help text —
   *"a pinned public snapshot (**one** ships in this folder with its fetch date)"*, and
   `eval/README.md:20` itself lists exactly one. "Both" appears to be left over from an earlier
   two-snapshot layout.

2. **`README.md:198` and `PRICING.md:22` — "72+ modules" / "72+ folded modules."** No total
   module count exists in `BATTERIES.md`. This is reconcilable rather than contradictory —
   `docs/BATTERIES.md:52` counts *"every selftest-bearing module"* (49), which is a subset of
   all modules — but the two figures sit next to each other in the README with nothing telling a
   reader why 49 and 72+ are both true.

3. **`README.md:12` and `docs/PHILOSOPHY.md:13–14` — the historical sweep: "109-sequence sweep",
   "3 false stamps" / "three false stamps", "44 verified and zero false."** The two pages agree
   with each other. `BATTERIES.md` carries no entry for this run, so it is unreconciled rather
   than contradicted — a deliberately-published prior failure with no row on the map that is
   supposed to hold every count.

---

## What this audit does not establish

Stated so the report is not read as more than it is:

- HTTP status codes prove reachability, not content. A 200 from a Stripe checkout URL does not
  prove the price behind it; a 200 from a GitHub blob URL does not prove the file's contents.
- No page was rendered, no JavaScript executed, no form submitted, no checkout started.
- The gate numbers above were cross-checked **for agreement between documents**. Except for the
  composition of `eval/frozen_predictions.json` (34 rows, 22 VERIFIED, 12 REFUSED, read
  directly), no battery was re-run and no count was independently reproduced. A number that
  agrees everywhere is consistent, not thereby verified.
- The three tier prices were read from `PRICING.md`; they were not checked against Stripe.
