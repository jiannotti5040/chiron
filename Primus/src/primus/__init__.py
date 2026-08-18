# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
primus — exact invariant recovery with held-out verification and refusal.

Two operations, one discipline:

    from primus import collapse
    inv = collapse([1, 1, 2, 3, 5, 8, 13, 21])
    inv.verified          # True only if the rule predicted held-out terms exactly
    inv.explanation       # what was recovered, why it is believed

    from primus import certify
    cert = certify("1,240 units at 25 dollars each for a total of 31,000.")
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
from pathlib import Path
import re
from typing import Optional

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
from primus.conjecture import conjecture, verify_closed_form  # noqa: F401

def _source_tree_version() -> Optional[str]:
    """Read the project version when this module runs directly from the tree.

    Package metadata describes the last installed wheel, which can be older
    than checked-out source during development or a release gate. Prefer the
    adjacent project file only in that source-tree case; installed wheels keep
    using their distribution metadata.
    """
    project_file = Path(__file__).resolve().parents[2] / "pyproject.toml"
    try:
        text = project_file.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r'^version\s*=\s*"([^"\n]+)"\s*$', text, re.MULTILINE)
    return match.group(1) if match else None


# `pyproject.toml` is authoritative in a checkout; package metadata is
# authoritative in an installed wheel.
__version__ = _source_tree_version()
if __version__ is None:
    try:
        from importlib.metadata import version as _pkg_version
        __version__ = _pkg_version("primus-intelligence")
    except Exception:  # not installed and no readable project file
        # Do NOT name a version here. This string is stamped into every
        # certificate as `engine.version`, and a hardcoded literal goes stale
        # silently — this one sat at "0.7.2+source" while the package was at
        # 0.9.0, so a 0.9.0 engine could issue a certificate claiming 0.7.2.
        # An engine that cannot read its own version says so.
        __version__ = "0+unknown"

__all__ = [
    "collapse", "same_family", "same_generator", "same_structure", "cast",
    "transcode", "build_record_translator", "discover_twins",
    "CombinatorialSpace", "TwinBijection", "make_twin", "compose_spaces",
    "caramuel_twin_spaces", "Invariant", "InvariantError", "OWNER",
    "certify", "extract_claims", "conjecture", "verify_closed_form",
    "__version__",
]
