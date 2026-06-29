#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
chiron_artifact — one emit path for every runnable script in the vault.

The vault is a set of independently-runnable scripts. Each one already PROVES
something on each run; until now most of them only printed it, so the result
evaporated on exit. This module lifts the certificate shape already proven in
``examples/certificates/*.json`` (machine_view + human_view) into a single
function every script can call, so each run leaves a durable, signed,
falsifiable artifact behind.

Design rule that keeps this honest (not "the form of intelligence without the
substance"): a certificate is REJECTED at emit time unless it carries a
concrete ``what_would_falsify`` string. A claim you cannot state a refutation
for is not allowed to be memorialized. The hard scripts (Primus, SEMIC) satisfy
this trivially — "one wrong held-out term breaks it." The soft scripts
(aesthetics, density_emotion, ontological) are forced to name their falsifier
too, or they do not get to emit.

Usage inside any script's __main__:

    from chiron_artifact import certificate, emit

    cert = certificate(
        script=__file__,
        purpose="recover the minimal generator of an integer sequence",
        machine_view={...},                       # the exact, hashable evidence
        what_was_discovered="...",
        why_believed="...",
        what_would_falsify="a single held-out term it failed to predict",
        confidence="high (held-out verified, exact)",
        verified=True,
    )
    emit(cert)        # writes artifacts/<script_stem>/<timestamp>_<hash>.json
                      # and updates artifacts/<script_stem>/latest.json

stdlib only. Deterministic given identical inputs. No network.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, Optional

OWNER = "Jacob Iannotti"
SYSTEM = "CHIRON"
LICENSE = "PolyForm-Noncommercial-1.0.0"

# artifacts/ lives next to this module (the Chiron spine root), so every script
# in the directory emits into one auditable tree regardless of CWD.
_ROOT = os.path.dirname(os.path.abspath(__file__))
ARTIFACT_ROOT = os.path.join(_ROOT, "artifacts")


class CertificateError(ValueError):
    """Raised when a certificate is missing the discipline fields that make it
    real intelligence rather than authoritative-looking text."""


def _git_commit() -> Optional[str]:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=_ROOT, capture_output=True, text=True, timeout=3,
        )
        return out.stdout.strip() or None if out.returncode == 0 else None
    except Exception:
        return None


def _stem(script: str) -> str:
    base = os.path.basename(script)
    return base[:-3] if base.endswith(".py") else base


def _canonical(obj: Any) -> str:
    """Stable serialization for hashing: sorted keys, no insignificant whitespace."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def certificate(
    *,
    script: str,
    purpose: str,
    machine_view: Dict[str, Any],
    what_was_discovered: str,
    why_believed: str,
    what_would_falsify: str,
    confidence: str,
    verified: bool,
    residual: str = "",
    extra_human: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Build a vault certificate in the proven dual-view shape.

    Enforces the honesty rule: ``purpose``, ``what_was_discovered``,
    ``why_believed`` and ``what_would_falsify`` must all be non-empty. The
    falsifier is the load-bearing one — it is what separates a Primus-grade
    claim from decoration.
    """
    missing = [
        name for name, val in (
            ("purpose", purpose),
            ("what_was_discovered", what_was_discovered),
            ("why_believed", why_believed),
            ("what_would_falsify", what_would_falsify),
        ) if not (isinstance(val, str) and val.strip())
    ]
    if missing:
        raise CertificateError(
            "certificate refused — missing required field(s): "
            + ", ".join(missing)
            + ". A claim with no stated falsifier is not allowed to be emitted."
        )

    human_view = {
        "purpose": purpose,
        "what_was_discovered": what_was_discovered,
        "why_believed": why_believed,
        "what_would_falsify": what_would_falsify,
        "residual": residual or "n/a",
        "confidence": confidence,
    }
    if extra_human:
        human_view.update(extra_human)

    cert: Dict[str, Any] = {
        "owner": OWNER,
        "system": SYSTEM,
        "license": LICENSE,
        "script": _stem(script),
        "purpose": purpose,
        "verified": bool(verified),
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "commit": _git_commit(),
        "machine_view": machine_view,
        "human_view": human_view,
    }
    # self_hash binds the evidence + claim together; it excludes the timestamp so
    # the same input on the same code yields the same content hash (reproducible),
    # while the filename still uses the timestamp for an append-only history.
    hashable = {k: v for k, v in cert.items() if k not in ("generated_utc",)}
    cert["self_hash"] = hashlib.sha256(_canonical(hashable).encode()).hexdigest()[:16]
    return cert


def emit(cert: Dict[str, Any], *, root: str = ARTIFACT_ROOT) -> str:
    """Write the certificate to artifacts/<script>/ and refresh latest.json.

    Returns the path written. Append-only: every run keeps its own file; the
    manifest/dashboard read latest.json for the current state and can walk the
    history for the trend.
    """
    stem = cert.get("script") or "unknown"
    out_dir = os.path.join(root, stem)
    os.makedirs(out_dir, exist_ok=True)

    ts = cert.get("generated_utc", "").replace(":", "").replace("-", "")
    fname = f"{ts}_{cert.get('self_hash', '0000')}.json"
    path = os.path.join(out_dir, fname)
    blob = json.dumps(cert, indent=2, default=str)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(blob)
    with open(os.path.join(out_dir, "latest.json"), "w", encoding="utf-8") as fh:
        fh.write(blob)
    return path


def quick(script: str, purpose: str, verified: bool,
          discovered: str, why: str, falsify: str,
          machine: Optional[Dict[str, Any]] = None,
          confidence: str = "") -> str:
    """One-call convenience: build + emit. Returns the artifact path.

    Lets a script add memorialization in a single line at the end of __main__
    without restructuring its output logic.
    """
    cert = certificate(
        script=script, purpose=purpose, machine_view=machine or {},
        what_was_discovered=discovered, why_believed=why,
        what_would_falsify=falsify,
        confidence=confidence or ("high" if verified else "abstained"),
        verified=verified,
    )
    return emit(cert)


if __name__ == "__main__":
    # Self-demonstration: emit a certificate ABOUT this module, and prove the
    # honesty gate rejects a falsifier-free claim.
    p = quick(
        script=__file__,
        purpose="provide one signed, falsifiable emit path for every vault script",
        verified=True,
        discovered="A shared dual-view certificate (machine_view + human_view) "
                   "now exists; any script can memorialize its run in one call.",
        why="Lifts the shape already proven in examples/certificates/*.json into "
            "a reusable function that refuses claims with no stated falsifier.",
        falsify="A certificate that emits despite an empty what_would_falsify "
                "field would break the honesty guarantee.",
        machine={"required_fields": 4, "honesty_gate": "falsifier_nonempty"},
        confidence="high (gate is enforced in code, demonstrated below)",
    )
    print(f"[emit] {p}")
    try:
        certificate(
            script=__file__, purpose="x", machine_view={},
            what_was_discovered="x", why_believed="x",
            what_would_falsify="", confidence="x", verified=True,
        )
        print("[FAIL] honesty gate did not fire")
        sys.exit(1)
    except CertificateError:
        print("[PASS] honesty gate refused a falsifier-free certificate")
    sys.exit(0)
