#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
Compatibility shim — the engine's single source of truth now lives at
``src/primus/engine.py`` (the installable ``primus`` package).

This file exists so every historical entry point keeps working unchanged:

    python3 -c "from invariant_engine import collapse; ..."
    python3 test_invariant_engine.py
    python3 benchmark.py
    python3 invariant_engine.py          # the demo run

It aliases this module to ``primus.engine`` wholesale, so every attribute —
public or private — resolves to the one real implementation. Do not add code
here; edit ``src/primus/engine.py``.
"""
import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

if __name__ == "__main__":
    import runpy
    runpy.run_module("primus.engine", run_name="__main__")
else:
    import primus.engine as _engine
    sys.modules[__name__] = _engine
