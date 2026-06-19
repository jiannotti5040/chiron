# Contributing

This repository is the proprietary work of Jacob Iannotti (see the license terms in
the root README). The **engine and the private grow are owner-only.** One surface is
open to outside contribution: the **public grow**.

## What you can contribute

The public grow — `Chiron/grow-public/` — accepts contributions by Pull Request:

- new **sources** or **profiles** (a website, a JSON API, an OEIS slice, a subject
  configuration) under `grow-public/`;
- corrections to public grow configuration and documentation.

## What is owner-only

- `chiron.py` (the engine) and any change to its behavior;
- `Chiron/grow-private/` and the operated private Congress;
- anything outside `grow-public/`.

If you believe the engine itself should change, open an **issue** describing the
case and the evidence — do not submit engine edits in a PR.

## Before you open a PR

Run these from inside `Chiron/` and confirm they pass:

```bash
python3 chiron.py selftest      # must print GREEN
python3 benchmark.py            # must end VERDICT: PASS (0 false positives)
```

Keep changes additive and scoped to `grow-public/`. PRs that touch the engine,
break the self-test, or introduce any false positive will not be merged.

## Attribution and licensing

Contributions are accepted under the repository's existing terms. Grown content
carries its sources' attribution — Wikipedia text is CC BY-SA and OEIS data carries
its own terms; see `NOTICE.md`. By opening a PR you confirm you have the right to
contribute the material and that it is attributed correctly.

## Conduct

Be precise, cite evidence, and prefer reproducible claims. The whole project is
built on the idea that a claim arrives with what would falsify it — contributions
are held to the same standard.
