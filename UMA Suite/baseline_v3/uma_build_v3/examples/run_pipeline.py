"""
Canonical UMA pipeline run.

Demonstrates:
    * Inside-out sphere geometry from spherical Bessel zeros
    * GENERIC dynamics with H[psi] tracking and entropy production
    * Cross-domain Venturi injection
    * Semantic friction walk against the calibrated H-floor
    * Live MSR <-> Einstein consistency (TensorBridge)
    * Convergence to Omega (closure) at deterministic step
"""
from __future__ import annotations
import os
import sys
import warnings

# Make `uma` importable when run from examples/ as `python3 examples/run_pipeline.py`
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

warnings.filterwarnings("ignore", category=RuntimeWarning)

from uma.pipeline import UMAPipeline


def main() -> None:
    pipe = UMAPipeline(
        L=1.0,
        n_mode=0, l_mode=0, mode_index=1,   # j_{0,1} = pi exactly
        n_steps=200,
        dt=0.04,
        seed=42,
        verbose=True,
    )
    result = pipe.run()
    print()
    result.report()


if __name__ == "__main__":
    main()
