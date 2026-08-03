# Release, reach, and drift — exact steps (2026-07-07)

> **CLOSED 2026-08-03.** The false stamp that blocked this plan was fixed in
> Primus v0.5.1 (`42453bc`) and the battery has been green since; see the
> RESOLVED banner on `EXTERNAL_VALIDATION_ADDENDUM_2026-07-07.md`. The version
> and tag facts below are a snapshot of 2026-07-07 and are now stale — the
> package is at 0.7.0 under Apache-2.0. Kept as a working record, not as
> current instructions.

Covers items 3–5 of the "what Primus needs" map.

## Item 4 — release (tag + PyPI). [historical: was blocked pending the seed fix]

State verified today: `pyproject` version = **0.5.0**; **no git tags exist**
(untagged, so nothing has been published). `python -m build` is not available in
this session, so the wheel build + license-in-wheel check is an author-machine
step. When the false stamp is fixed and the full battery is green:

```bash
# from the repo root, on your machine
python -m build Primus --outdir dist/           # build sdist + wheel
python Primus/ci/check_wheel_license.py         # Apache-2.0 notice must ship inside the wheel
git tag v0.5.1                                   # bump first if the fix changes behavior (it does)
git push origin main --tags                      # release.yml verifies tag == pyproject, reruns gates
```

Note: because the fix changes stamping behavior, bump to **v0.5.1** (or 0.6.0)
with a CHANGELOG entry — don't publish 0.5.0 as-is. `release.yml` will refuse a
tag that doesn't match `pyproject`.

## Item 3 — reach (GitHub Pages + playground). Unaffected by the bug.

`playground.html` exists at the repo root and runs the real engine in-browser.
To put it online:

1. GitHub → repo **Settings → Pages**.
2. **Build and deployment → Source:** "Deploy from a branch".
3. **Branch:** `main`, **folder:** `/ (root)` → **Save**.
4. Wait ~1 min, then open
   `https://jiannotti5040.github.io/chiron-vault/playground.html`
   and do one sanity pass (enter a sequence, confirm a VERIFIED and a REFUSED).

Show HN post is drafted in `SHOW_HN_DRAFT.md` — **hold it until the fix lands**;
the fix makes the draft stronger (a second falsify-and-repair).

## Item 5 — drift is green, but had a blind spot. Concrete guard.

`drift_check.py` is GREEN (37/37 agree) — but it did **not** compare seed vs
Chiron on companion Pell, which is exactly where they disagree (seed wrong,
Chiron right). Green-but-blind is the risk the after-action named.

Action, to fold into the fix commit:
1. Add `A002203` (companion Pell) to the drift surfaces so the seed/Chiron
   differential covers it permanently.
2. Add 1–2 more linear-recurrence-vs-holonomic boundary cases (e.g. companion
   Lucas / other `a(n)=k·a(n-1)+a(n-2)` families) — the class where the seed
   mis-recovers as holonomic.
3. Keep the standing OEIS battery pointed at the extended cache (or fold the 7
   new probes into the curated one) so this stays externally guarded.

The general principle, restated: two engines are held together only by the
surfaces you list. When you find a disagreement, the surface goes on the list.
