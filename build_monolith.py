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
    python3 chiron_monolith.py --selftest             # battery across the core engines

Regenerate with build_monolith.py. The embedded sources are a lossless fold of the spine.
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


_BATTERY = [("semic", ["selftest"]), ("chiron", ["selftest"]),
            ("density_emotion", ["selftest"]), ("semic_energy", ["selftest"]),
            ("epistemic", ["selftest"])]


def _selftest():
    """Run each core engine's selftest in a fresh subprocess of THIS monolith, so the
    fold is exercised exactly as a standalone run would be, with full isolation."""
    import subprocess
    rows = []
    me = os.path.abspath(__file__)
    for name, argv in _BATTERY:
        if name not in _SOURCES:
            rows.append((name, False, "not embedded"))
            continue
        try:
            proc = subprocess.run([sys.executable, me, name] + argv,
                                  capture_output=True, text=True, timeout=300)
            ok = (proc.returncode == 0)
            lines = [ln for ln in (proc.stdout + proc.stderr).strip().splitlines()
                     if ln.strip()]
            tail = (lines[-1] if lines else "")[:64]
        except Exception as exc:
            ok, tail = False, repr(exc)[:64]
        rows.append((name, ok, tail))
    print("chiron_monolith self-test (each engine run through the embedded fold)")
    for name, ok, tail in rows:
        print("  [%s] %-16s %s" % ("PASS" if ok else "FAIL", name, tail))
    passed = sum(1 for _, ok, _ in rows if ok)
    print("  %d/%d engines green through the monolith" % (passed, len(rows)))
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
        return 0 if _selftest() else 1
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
