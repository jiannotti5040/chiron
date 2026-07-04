# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
primus — exact invariant recovery with held-out verification and refusal.

Two operations, one discipline:

    from primus import collapse
    inv = collapse([1, 1, 2, 3, 5, 8, 13, 21])
    inv.verified          # True only if the rule predicted held-out terms exactly
    inv.explanation       # what was recovered, why it is believed

    from primus import certify
    cert = certify("The sequence 2 4 6 8 continues as 10, 12. Also 2+2=5.")
    cert["verdict"]       # verified/refuted/refused counts — never a blanket blessing

``collapse`` recovers the minimal generator beneath a codified surface
(numbers, strings, ciphers, graphs, schemas, code) under a two-part MDL
criterion in exact arithmetic, and stamps *verified* only when the rule
exactly predicts data it never saw. ``certify`` turns that discipline into
an accountability wrapper for LLM/agent output: each checkable claim is
VERIFIED, REFUTED, or REFUSED; free text is honestly UNVERIFIABLE.

The engine never certifies what it cannot exactly verify. That refusal is
the product.
"""
from primus.engine import (  # noqa: F401
    collapse,
    same_family,
    same_generator,
    same_structure,
    cast,
    transcode,
    build_record_translator,
    discover_twins,
    CombinatorialSpace,
    TwinBijection,
    make_twin,
    compose_spaces,
    caramuel_twin_spaces,
    Invariant,
    InvariantError,
    OWNER,
)
from primus.certify import certify, extract_claims  # noqa: F401

# Single source of version truth is pyproject.toml; read it from the
# installed package metadata, with a fallback for raw source-tree use.
try:
    from importlib.metadata import version as _pkg_version
    __version__ = _pkg_version("primus-intelligence")
except Exception:  # not installed (e.g. sys.path use via the shim)
    __version__ = "0.4.0+source"

__all__ = [
    "collapse", "same_family", "same_generator", "same_structure", "cast",
    "transcode", "build_record_translator", "discover_twins",
    "CombinatorialSpace", "TwinBijection", "make_twin", "compose_spaces",
    "caramuel_twin_spaces", "Invariant", "InvariantError", "OWNER",
    "certify", "extract_claims", "__version__",
]
