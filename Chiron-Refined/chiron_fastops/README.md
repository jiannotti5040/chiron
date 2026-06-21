# chiron_fastops — optional native hot-path

An **optional** Rust crate that accelerates a few exact kernels. It is never
required: `../fastops.py` falls back to exact pure-Python implementations when this
library is not built, so Chiron always runs with zero installs. Native is an
*accelerator*, not a dependency — the same contract as the C kernel already embedded
in `chiron.py`.

## Kernels

- `chiron_poly_degree` — finite-difference degree of an integer sequence (the hot
  inner step of polynomial recovery), exact in `i128`.
- `chiron_hexameter_feet_ok` — does a syllable-quantity string segment into six
  dactylic-hexameter feet? This is the portable inner loop of strict Latin scansion —
  the piece that makes true proteus-verse counting fast at the n! scale where the
  pure-Python scanner and the coarse fallback are the bottleneck.

Both are exposed over the C ABI and loaded by `fastops.py` via `ctypes`.

## Build (native shared library)

```bash
cd chiron_fastops
cargo build --release
# produces target/release/libchiron_fastops.{dylib,so} (or .dll on Windows),
# which fastops.py auto-discovers on next run.
```

Verify it took over:

```bash
python3 ../fastops.py        # backend: native (compiled chiron_fastops)
```

Without the build, `python3 ../fastops.py` prints `backend: pure-python fallback`
and the identical results — that path is what runs in CI and on any machine without
a Rust toolchain.

## Build (WebAssembly, for the dashboard)

```bash
rustup target add wasm32-unknown-unknown
cargo build --release --target wasm32-unknown-unknown
# or, for a JS-friendly package:
#   wasm-pack build --target web
```

The WASM artifact lets the offline dashboard run `collapse`-adjacent kernels and
scansion **in the browser**, with no server — the standout demo this native path
enables.

## Why Rust

Memory safety (no UB in a portfolio engine), first-class big integers and
combinatorics for the enumeration-heavy Primus direction, reproducible `cargo`
builds, and a clean path to WebAssembly. C remains the embedded fallback kernel in
`chiron.py`; this crate is the portable upgrade. See `../../PRIMUS_EXPLORATION.md`
for where native backing helps and where it deliberately does not.
