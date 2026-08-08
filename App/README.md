# Chiron for macOS

This is the local macOS interface for a local Chiron checkout. It is an
operator surface, not another implementation of the verification engine: the
app starts the vault's Python entry points with `Foundation.Process`, decodes
their records, and presents the result. It does not recompute a certificate or
upgrade a disposition.

## Requirements

- macOS 14 or later
- Swift 6 toolchain
- `python3` capable of running the checkout's Primus and Chiron modules
- a local checkout containing `Chiron/` and `Primus/`

Run from the repository's `App/` directory:

```bash
swift run chiron-app
swift test --scratch-path /tmp/chiron-build
```

The scratch path matters when the checkout is in an iCloud-synchronised
Desktop or Documents folder: file-provider metadata can make code signing of a
test bundle fail even when the Swift sources are sound.

## What the app invokes

| App surface | Canonical path | What is preserved |
|---|---|---|
| Workspace | `Chiron/full_stack.py --json --stdin` and `python -m primus.cli certify --json -` | Full-stack and certificate records from the same input bytes. |
| Local source record | `source_provenance.register_local_text_file()` through a fixed stdin-free shim | Metadata-only record for a complete selected file; no raw text or raw path is exported. |
| Attest | `attest.attest()` through a stdin JSON shim | The attestation record returned by Chiron. |
| Gates | Existing vault self-tests | Process exit code and verbatim output. |

Text is passed over standard input rather than as a shell argument. The UI
accepts a bounded 8 MiB UTF-8 text prefix and carries truncation state to the
analysis surface; a partial read must not look like a complete analysis. A
canonical local source record is requested only for a complete selected file
within that bound.

## Command-line use

The executable has a small headless mode for the same local paths used by the
windowed interface:

```bash
swift run chiron-app run "1 1 2 3 5 8 13 21"
swift run chiron-app run ./notes.txt
swift run chiron-app certify "17 * 3 = 51"
```

Use `--json` with `run` or `certify` when a calling script needs the canonical
JSON record. A readable single argument is treated as a text file; otherwise
it is treated as literal text.

## Finding the vault

At launch the app first honors `CHIRON_VAULT`; otherwise it walks upward from
the working directory and executable location until it finds a directory with
both `Chiron/full_stack.py` and `Primus/`. `CHIRON_PYTHON` can select the
interpreter. A double-clickable app does not inherit a shell environment, so
the bundle created below embeds the checkout used at build time. The in-app
folder picker can select a different valid checkout.

```bash
./make_app.sh
open build/Chiron.app
```

The produced bundle is a local, ad-hoc-signed convenience artifact. It carries
no bundled verifier, cloud credential, notarization result, distribution
identity, or deployment claim.

## Operating boundary

The app is intended for a trusted local checkout and interpreter. The engine's
contract still applies: a `VERIFIED` result covers only the exact property the
canonical engine checked; `REFUSED` is a normal and necessary outcome. For
engine limits and validation scope, read
[Chiron's known limitations](../Chiron/docs/KNOWN_LIMITATIONS.md) and the
[research map](../docs/RESEARCH_MAP.md).
