# Contributing

This repository is licensed under the **PolyForm Noncommercial License 1.0.0** (see
[`LICENSE.md`](LICENSE.md)). You are free to clone it, run it, modify it, and share
your changes for any **noncommercial** purpose — experiment freely. Commercial use is
reserved to the author; for that, contact jiannotti5040@gmail.com.

## Run it / experiment

Everything runs offline on the Python standard library (numpy/scipy optional):

```bash
python3 Chiron/chiron.py selftest      # the embedded gate suite (prints GREEN)
python3 Chiron/benchmark.py            # the reproducible benchmark (VERDICT: PASS)
```

Fork it, point the grower at your own sources, try the tools — that's encouraged.

## Contributing back — the public grow

The most welcome place to contribute is the **public grow** (`Chiron/grow-public/`):
new **sources** or **profiles** (a website, a JSON API, an OEIS slice, a subject
configuration), or corrections to public-grow configuration and documentation. Open a
Pull Request.

## Engine changes

You may modify the engine in your own fork freely (noncommercially). For a change to be
merged **upstream**, keep it additive and verifiable, and confirm before opening a PR:

```bash
python3 Chiron/chiron.py selftest      # must stay GREEN
python3 Chiron/benchmark.py            # must end VERDICT: PASS (0 false positives)
```

PRs that break the self-test or introduce a false positive will not be merged. For a
larger engine change, open an **issue** describing the case and the evidence first.

## Attribution and licensing

Contributions are accepted under the repository's PolyForm Noncommercial terms. Grown
content carries its sources' attribution — Wikipedia (CC BY-SA), OEIS, and the
public-domain Caramuel source; see [`NOTICE.md`](NOTICE.md). By opening a PR you
confirm you have the right to contribute the material and that it is attributed
correctly.

## Conduct

Be precise, cite evidence, and prefer reproducible claims. The whole project rests on
the idea that a claim arrives with what would falsify it — contributions are held to
the same standard.
