# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
uma.rsls.lyapunov -- the validity checks that decide whether a
twin-trajectory statistic may be called a Lyapunov exponent.

Both Stage 5 (`frame_dragging.lyapunov_kernel`) and Stage 6
(`stage6.stage6_lyapunov`) reported a bare float named `lyapunov_max`, and
both were read as measurements of chaos. Neither number survives the standard
checks (2026-08-11):

  * no convergence -- widening the window moves Stage 5 through -0.017,
    +5.50, +6.42, +9.44, +5.61 and Stage 6 through -0.013, +3.16, +8.95,
    +39.12;
  * no independence from the perturbation size -- Stage 5 gives +0.34, +5.50,
    -0.024, -0.021 at delta = 1e-6, 1e-8, 1e-10, 1e-12, changing sign;
  * one renormalisation block of 72 (growth x87) is 82% of the Stage-5 sum,
    while the MEDIAN block contracts (54 of 72). It measures one transient
    amplification, not a rate.

So the estimators here return a `LyapunovReport` that refuses unless the
statistic passes. The refusal is checked against systems with known answers
in `tests/test_stage6.py::TestLyapunovReportControls`: it accepts Lorenz and
recovers +0.9032 against the literature's +0.906, accepts a pure decay at
exactly -0.5, and refuses a single-spike record and a blown-up trajectory. A
gate that says no to everything proves nothing, so those controls are part of
the suite.

See `studies/rsls_lyapunov/` for the full investigation, including two
separate defects in the underlying kernel (a fixed timestep that violates CFL
by ~550x, and a finite-time vacuum) that this module only reports around.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# A block supplying more than this share of the total log variation means the
# statistic is one transient event rather than a rate. Stage 5 sits at 0.82.
MAX_BLOCK_SHARE = 0.25
# Second half vs whole window must agree this closely, in rate units.
CONVERGE_ATOL = 0.10
# Beyond this the state counts as blown up rather than chaotic.
BLOWUP = 1e6
# Fewer blocks than this cannot support an average.
MIN_BLOCKS = 8


@dataclass
class LyapunovReport:
    """A twin-trajectory estimate plus the checks that qualify it.

    `value` is always the raw statistic, kept for diagnosis. Read it as an
    exponent only when `converged` is True; otherwise `reason` names the check
    that failed.
    """
    value: float                  # raw log-growth rate (diagnostic)
    converged: bool               # may `value` be read as lambda_max?
    reason: str                   # "" when converged, else the failing check
    n_blocks: int
    top_block_share: float        # largest block's share of total variation
    contracting_fraction: float   # blocks whose separation shrank
    second_half_value: float      # same statistic over the last half
    bounded: bool                 # did the reference trajectory stay finite?

    def summary(self) -> dict:
        return {
            "lyapunov_converged":   self.converged,
            "lyapunov_reason":      self.reason,
            "lyapunov_raw":         round(self.value, 6),
            "lyapunov_blocks":      self.n_blocks,
            "lyapunov_top_share":   round(self.top_block_share, 4),
            "lyapunov_contracting": round(self.contracting_fraction, 4),
            "lyapunov_second_half": round(self.second_half_value, 6),
            "lyapunov_bounded":     self.bounded,
        }


def lyapunov_report(logs: np.ndarray, times: np.ndarray,
                    bounded: bool = True) -> LyapunovReport:
    """Turn per-block log-growths and block durations into a report.

    `times` is per-block so a partial final block is credited only the time it
    actually ran -- crediting it a whole block was one of the original bugs.
    """
    logs = np.asarray(logs, dtype=float)
    times = np.asarray(times, dtype=float)
    total_t = float(times.sum()) if times.size else 0.0
    if total_t <= 0 or logs.size == 0:
        return LyapunovReport(float("nan"), False,
                              "no usable renormalisation blocks",
                              0, float("nan"), float("nan"), float("nan"), bounded)

    value = float(logs.sum() / total_t)
    # Share of total VARIATION, not of the signed sum: when blocks nearly
    # cancel, |max|/|sum| exceeds 100% and stops being readable.
    denom = float(np.abs(logs).sum())
    top_share = float(np.abs(logs).max() / denom) if denom > 0 else float("inf")
    contracting = float((logs < 0).sum() / logs.size)
    half = logs.size // 2
    second = (float(logs[half:].sum() / times[half:].sum())
              if half < logs.size and times[half:].sum() > 0 else float("nan"))

    reason = ""
    if not bounded:
        reason = ("reference trajectory left the physical range -- the growth "
                  "measured is a numerical instability, not chaos")
    elif logs.size < MIN_BLOCKS:
        reason = f"only {logs.size} renormalisation blocks; too few to average"
    elif top_share > MAX_BLOCK_SHARE:
        reason = (f"one block supplies {top_share:.0%} of the log sum "
                  f"(limit {MAX_BLOCK_SHARE:.0%}) -- this is a single "
                  f"transient amplification, not a rate")
    elif not np.isfinite(second) or abs(second - value) > CONVERGE_ATOL:
        reason = (f"not plateaued: second half gives {second:+.4f} against "
                  f"{value:+.4f} over the whole window "
                  f"(tolerance {CONVERGE_ATOL})")

    return LyapunovReport(value, reason == "", reason, int(logs.size),
                          top_share, contracting, second, bounded)
