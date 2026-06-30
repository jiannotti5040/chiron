#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
build_monolith.py — fold ALL of Chiron's runnable code into one file.

Reads every Chiron/*.py, embeds its byte-identical source (base64) into a single
generated `chiron_monolith.py`, and wraps it in a small loader + dispatcher so that:

  * any cross-import (`import chiron`, `import semic`, `import legal_corpus`, ...)
    resolves to the EMBEDDED copy via a sys.meta_path finder, and
  * any module's command line runs with:  python3 chiron_monolith.py <module> [args...]

Each embedded source is asserted byte-identical to the original at build time, so the
monolith is a lossless fold of the spine, not a rewrite. Data files and each module's
self-source scan resolve against the sibling Chiron/ tree when present (the in-repo case).

    python3 build_monolith.py            # (re)generate chiron_monolith.py
    python3 build_monolith.py --verify   # generate, then run the engine battery through it
"""
import os
import sys
import base64
import argparse
import subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))          # repo root
CHIRON = os.path.join(_HERE, "Chiron")                      # the spine to fold
OUT = os.path.join(_HERE, "Chiron Monolith", "chiron_monolith.py")

# The generated monolith's static head: SPDX + docstring + loader + dispatcher.
# Written with no backslash escapes so it round-trips cleanly into the output file.
HEAD = r'''#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright (c) 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
chiron_monolith.py — ALL of Chiron, folded into ONE file. (generated; do not hand-edit)

Every Chiron module is embedded below as byte-identical base64 source. A sys.meta_path
finder makes `import <name>` resolve to the embedded copy, so the cross-imports between
modules work even with no Chiron/*.py files alongside. Each module's __file__ (used for
self-source scans and _HERE-relative data) points at the sibling Chiron/ directory when
it exists — the normal in-repo case — so behaviour is identical to running the originals.

    python3 chiron_monolith.py --list                # list every embedded module
    python3 chiron_monolith.py <module> [args...]     # run a module's command line
    python3 chiron_monolith.py semic selftest         # -> 56/56 gates
    python3 chiron_monolith.py chiron selftest        # -> CHIRON GREEN
    python3 chiron_monolith.py --selftest             # FULL sweep: every selftest-bearing module
    python3 chiron_monolith.py --smoke                # quick: just the core-engine battery

Regenerate with build_monolith.py. The embedded sources are a lossless fold of the spine —
byte-identical to Chiron/*.py — so the fold runs exactly the gates the full build runs.
"""
import sys
import os
import base64
import importlib.abc
import importlib.machinery

_HERE = os.path.dirname(os.path.abspath(__file__))
_CHIRON = os.path.normpath(os.path.join(_HERE, os.pardir, "Chiron"))


def _decode(name):
    return base64.b64decode(_SOURCES[name]).decode("utf-8")


def _module_file(name):
    """__file__ for an embedded module: the real Chiron/<name>.py when present (so
    self-source scans and _HERE-relative data resolve), else a virtual local path."""
    real = os.path.join(_CHIRON, name + ".py")
    return real if os.path.isfile(real) else os.path.join(_HERE, name + ".py")


class _Loader(importlib.abc.Loader):
    def __init__(self, name):
        self._name = name

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        module.__file__ = _module_file(self._name)
        exec(compile(_decode(self._name), module.__file__, "exec"), module.__dict__)


class _Finder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in _SOURCES:
            return importlib.machinery.ModuleSpec(fullname, _Loader(fullname))
        return None


def _install():
    if not any(isinstance(f, _Finder) for f in sys.meta_path):
        sys.meta_path.insert(0, _Finder())


def run_module(name, argv):
    """Execute an embedded module's command line as if it were __main__.

    The module is registered in sys.modules as both "__main__" and its own name and
    given a real module object, because the spine self-references through
    sys.modules[__name__] (e.g. `veritas = sys.modules[__name__]`) and scans its own
    source via inspect.getsource(sys.modules[__name__]); both must resolve to the
    running module (and its real Chiron/<name>.py source), not to this launcher."""
    import types
    _install()
    if name not in _SOURCES:
        print("unknown module:", name, "(try --list)", file=sys.stderr)
        return 2
    mod = types.ModuleType("__main__")
    mod.__name__ = "__main__"
    mod.__file__ = _module_file(name)
    mod.__package__ = None
    saved_argv = list(sys.argv)
    saved_main = sys.modules.get("__main__")
    saved_named = sys.modules.get(name)
    sys.argv = [name + ".py"] + list(argv)
    sys.modules["__main__"] = mod
    sys.modules[name] = mod
    try:
        exec(compile(_decode(name), mod.__file__, "exec"), mod.__dict__)
        return 0
    except SystemExit as exc:
        if isinstance(exc.code, int):
            return exc.code
        return 1 if exc.code else 0
    finally:
        sys.argv = saved_argv
        if saved_main is not None:
            sys.modules["__main__"] = saved_main
        else:
            sys.modules.pop("__main__", None)
        if saved_named is not None:
            sys.modules[name] = saved_named
        else:
            sys.modules.pop(name, None)


# Servers and corpus-mutating tools are not auto-run in a sweep (identical to the full
# build's build_manifest.NO_AUTORUN), so the fold's coverage matches the spine's exactly.
_NO_AUTORUN = {"assistant_server", "console_server", "chiron_grow", "president_grow",
               "grow_control", "grow_clean", "build_manifest", "ingest_pdf"}
_SMOKE = ["semic", "chiron", "density_emotion", "semic_energy", "epistemic"]


def _run_self(name):
    """Run one embedded module's selftest IN-PROCESS, capturing its output. run_module
    registers/restores sys.modules around each run, so the whole sweep needs only one parse
    of the fold (fast). Falls back from the positional `selftest` to the `--selftest` flag,
    exactly as the full build's runner does, so a module's invocation style never counts as a fail."""
    import io
    import contextlib
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = run_module(name, ["selftest"])
            if rc == 2:
                rc = run_module(name, ["--selftest"])
        out = [ln for ln in buf.getvalue().strip().splitlines() if ln.strip()]
        return rc == 0, (out[-1] if out else "")[:70]
    except Exception as exc:
        return False, repr(exc)[:70]


def _selftest(full=True):
    """full=True sweeps EVERY selftest-bearing embedded module (the same set the full build
    runs); full=False runs only the core-engine smoke battery."""
    if full:
        names = sorted(n for n in _SOURCES
                       if "selftest" in _decode(n) and n not in _NO_AUTORUN)
        title = "full sweep — every selftest-bearing module, through the fold"
    else:
        names = [n for n in _SMOKE if n in _SOURCES]
        title = "smoke battery — the core engines, through the fold"
    rows = [(n, *_run_self(n)) for n in names]
    print("chiron_monolith self-test (%s)" % title)
    for name, ok, tail in rows:
        print("  [%s] %-18s %s" % ("PASS" if ok else "FAIL", name, tail))
    passed = sum(1 for _, ok, _ in rows if ok)
    print("  %d/%d modules green through the fold "
          "(same coverage as the full build's manifest)" % (passed, len(rows)))
    return passed == len(rows)


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if args[0] == "--list":
        for key in sorted(_SOURCES):
            print(key)
        print()
        print("%d modules embedded." % len(_SOURCES))
        return 0
    if args[0] == "--selftest":
        return 0 if _selftest(full=True) else 1
    if args[0] == "--smoke":
        return 0 if _selftest(full=False) else 1
    return run_module(args[0], args[1:])


'''

TAIL = '''
if __name__ == "__main__":
    sys.exit(main())
'''


def build():
    files = sorted(f for f in os.listdir(CHIRON) if f.endswith(".py"))
    entries = []
    total = 0
    for fname in files:
        name = fname[:-3]
        raw = open(os.path.join(CHIRON, fname), "rb").read()
        b64 = base64.b64encode(raw).decode("ascii")
        assert base64.b64decode(b64) == raw, "round-trip failed: " + fname
        entries.append((name, b64))
        total += len(raw)
    with open(OUT, "w", encoding="utf-8") as out:
        out.write(HEAD)
        out.write("_SOURCES = {}\n")
        for name, b64 in entries:
            out.write("_SOURCES[%r] = (\n" % name)
            for i in range(0, len(b64), 120):
                out.write("    %r\n" % b64[i:i + 120])
            out.write(")\n")
        out.write(TAIL)
    return entries, total


def main():
    ap = argparse.ArgumentParser(description="Fold all of Chiron into one file.")
    ap.add_argument("--verify", action="store_true",
                    help="after generating, run the engine battery through the monolith")
    args = ap.parse_args()
    entries, total = build()
    out_bytes = os.path.getsize(OUT)
    print("[monolith] embedded %d modules (%d source bytes) -> %s (%d bytes)"
          % (len(entries), total, os.path.relpath(OUT, _HERE), out_bytes))
    if args.verify:
        print("[monolith] verifying via --selftest ...")
        rc = subprocess.run([sys.executable, OUT, "--selftest"]).returncode
        return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())
