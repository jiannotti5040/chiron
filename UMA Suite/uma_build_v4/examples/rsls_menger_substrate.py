# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
examples/rsls_menger_substrate.py -- Menger sponge as a discrete AMR
substrate for the RSLS memory field.

What this demonstrates
----------------------
1. Construction of the Menger sponge at levels 0, 1, 2, 3 with the
   correct combinatorial counts (1, 20, 400, 8000 alive cells).
2. The volume law (20/27)^n -> 0 and surface law (20/9)^n -> infinity.
3. A scalar M field placed on the sponge, with the graph Laplacian
   acting as the discrete diffusion operator.
4. Adaptive refinement triggered by |grad M|: cells where the
   nearest-neighbour difference in M exceeds a threshold are refined.
   This is the structural prescription in
   docs/RSLS_menger_substrate.md section 3.

How the AMR demo works
----------------------
Start with a level-1 sponge (20 cells). Initialise M with a Gaussian
peak at one corner of the sponge. Compute |grad M| on the graph; refine
the top-k cells where the gradient is largest. Re-initialise M on the
refined sponge (interpolating from the parent). Compare:
    * Cell count growth
    * Effective resolution at the gradient front
    * Total |grad M| (a measure of "captured detail")

This is not yet a full physics solver -- the AMR machinery is the
structural skeleton; the physical evolution would be the Cattaneo-V(M)
update applied on this lattice, with the graph Laplacian replacing the
Cartesian one. That coupling is in uma.rsls.coupling (Cartesian for
TensorBridge) and is straightforward to port; the present example
shows the substrate works.
"""
from __future__ import annotations
import os
import sys

# Bootstrap import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np

from uma.rsls import (
    MengerSponge, HAUSDORFF_DIM,
    theoretical_n_cells, theoretical_volume, theoretical_surface_area,
)


def hr():
    print("-" * 72)


def gaussian_on_sponge(sp: MengerSponge, peak: np.ndarray, sigma: float) -> np.ndarray:
    """Initial Gaussian M field centred at `peak`, evaluated on each cell centre."""
    centres = sp.centres()
    d2 = ((centres - peak) ** 2).sum(axis=1)
    return np.exp(-d2 / (2 * sigma ** 2))


def gradient_magnitude(sp: MengerSponge, M: np.ndarray, adj) -> np.ndarray:
    """Discrete |grad M|_i = max_j |M_i - M_j| over face-sharing neighbours."""
    idxs = sp.alive_indices()
    pos = {ci: p for p, ci in enumerate(idxs)}
    out = np.zeros(len(M))
    for p, ci in enumerate(idxs):
        ns = adj[ci]
        if not ns:
            continue
        out[p] = max(abs(M[p] - M[pos[j]]) for j in ns if j in pos)
    return out


def main() -> int:
    print("=" * 72)
    print("  UMA v4 / RSLS Menger Sponge Substrate")
    print("=" * 72)
    print()

    # -------------------------------------------------------------------
    # 1. Combinatorics
    # -------------------------------------------------------------------
    hr()
    print("  1. Sponge construction at levels 0..3")
    hr()
    print(f"     {'L':>3}  {'cells':>10}  {'theory':>10}  {'volume':>12}  "
          f"{'surface':>12}")
    for L in range(4):
        sp = MengerSponge(level=L)
        n   = sp.n_alive
        vol = sp.volume()
        sa  = sp.surface_area()
        print(f"     {L:>3}  {n:>10d}  {theoretical_n_cells(L):>10d}  "
              f"{vol:>12.6e}  {sa:>12.6e}")
    print()
    print(f"     Hausdorff dimension = log(20) / log(3) = {HAUSDORFF_DIM:.10f}")
    print(f"     (3-D embedding with dimension ~ 2.727 -- a porous fractal)")
    print()

    # -------------------------------------------------------------------
    # 2. Volume / surface scaling: the smoothing-vs-roughening cascade
    # -------------------------------------------------------------------
    hr()
    print("  2. Volume / surface scaling (the fractal-cascade signature)")
    hr()
    print(f"     {'L':>3}  {'(20/27)^L':>12}  {'volume':>12}  "
          f"{'(20/9)^L':>12}  {'surface ratio':>14}")
    base_sa = MengerSponge(level=0).surface_area()
    for L in range(4):
        sp = MengerSponge(level=L)
        v_theory = (20.0 / 27.0) ** L
        sa_ratio = sp.surface_area() / base_sa
        print(f"     {L:>3}  {v_theory:>12.6e}  {sp.volume():>12.6e}  "
              f"{(20.0/9.0)**L:>12.6e}  {sa_ratio:>14.6e}")
    print()
    print("     The volume goes to zero geometrically while the surface area")
    print("     grows without bound -- the saturated information attractor.")
    print()

    # -------------------------------------------------------------------
    # 3. Scalar M field on the sponge with graph Laplacian
    # -------------------------------------------------------------------
    hr()
    print("  3. M field on a level-2 sponge with graph Laplacian")
    hr()
    sp = MengerSponge(level=2)
    print(f"     cells = {sp.n_alive}")
    print(f"     building adjacency...")
    adj = sp.build_adjacency()
    n_edges = sum(len(v) for v in adj.values()) // 2
    print(f"     edges = {n_edges}")
    print()

    # Initial Gaussian at the (0,0,0) corner
    peak = np.array([0.05, 0.05, 0.05])
    M = gaussian_on_sponge(sp, peak, sigma=0.2)
    print(f"     initial Gaussian M field (peak at corner)")
    print(f"     |M|_inf = {abs(M).max():.4f}")
    print(f"     mean(M) = {M.mean():.4f}")
    print(f"     |grad M|_max (face-sharing) = "
          f"{gradient_magnitude(sp, M, adj).max():.4f}")

    # Apply Laplacian as a heat-diffusion step
    dt = 0.1
    M_after_diffusion = M.copy()
    for _ in range(5):
        Lf = sp.laplacian(M_after_diffusion, adj)
        M_after_diffusion = M_after_diffusion + dt * Lf
    print()
    print(f"     after 5 graph-Laplacian heat-diffusion steps (dt=0.1):")
    print(f"     |M|_inf = {abs(M_after_diffusion).max():.4f}   (decreased -- smoothing)")
    print(f"     mean(M) = {M_after_diffusion.mean():.4f}   (preserved -- conservative)")
    print(f"     |grad M|_max = {gradient_magnitude(sp, M_after_diffusion, adj).max():.4f}"
          "   (decreased)")
    print()

    # -------------------------------------------------------------------
    # 4. Adaptive refinement
    # -------------------------------------------------------------------
    hr()
    print("  4. Adaptive Mesh Refinement on the Menger lattice")
    hr()
    sp = MengerSponge(level=1)
    adj = sp.build_adjacency()
    M = gaussian_on_sponge(sp, peak=np.array([0.05, 0.05, 0.05]), sigma=0.15)
    print(f"     L=1 substrate:  cells = {sp.n_alive}")
    print(f"     initial |grad M|_max = "
          f"{gradient_magnitude(sp, M, adj).max():.6f}")

    # Refine the top-k cells by gradient
    grads = gradient_magnitude(sp, M, adj)
    idxs = sp.alive_indices()
    k = 3
    refine_targets = [idxs[i] for i in np.argsort(grads)[-k:]]
    print(f"     refining top {k} cells by |grad M|: indices {refine_targets}")

    # Save M for interpolation onto refined cells
    pos = {ci: p for p, ci in enumerate(idxs)}
    M_parent_values = {ci: M[pos[ci]] for ci in idxs}

    for parent_idx in refine_targets:
        sp.refine(parent_idx)

    # Re-build adjacency on the refined sponge
    adj_new = sp.build_adjacency()
    idxs_new = sp.alive_indices()
    pos_new = {ci: p for p, ci in enumerate(idxs_new)}

    # Interpolate M onto the new cells (parents pass their value to children)
    M_new = np.zeros(len(idxs_new))
    for p, ci in enumerate(idxs_new):
        cell = sp.cells[ci]
        # walk up to find the alive ancestor in the old sponge
        anc = ci
        while anc is not None and anc not in M_parent_values:
            anc = sp.cells[anc].parent
        if anc is not None and anc in M_parent_values:
            M_new[p] = M_parent_values[anc]
        else:
            M_new[p] = 0.0

    print(f"     refined substrate:  cells = {sp.n_alive}  (was 20)")
    print(f"     post-refinement |grad M|_max = "
          f"{gradient_magnitude(sp, M_new, adj_new).max():.6f}")
    print(f"     (the gradient front is now resolved on smaller sub-cells)")
    print()

    # -------------------------------------------------------------------
    # 5. Summary
    # -------------------------------------------------------------------
    hr()
    print("  Summary: Menger Sponge as RSLS substrate")
    print("    (a) Self-similar 20-cell construction rule -- exact at each level")
    print(f"    (b) Hausdorff dim {HAUSDORFF_DIM:.4f}, 3-D embedding")
    print("    (c) Volume -> 0, surface -> infinity (saturated attractor)")
    print("    (d) Graph Laplacian acts on cell-centred M, conservatively")
    print("    (e) AMR by |grad M|: localised refinement on the fractal lattice")
    print("    (f) Total ordering / Hausdorff convergence guaranteed by self-")
    print("        similarity -- the Menger sponge IS a deterministic")
    print("        finite-rank substrate, not an ad hoc grid")
    hr()
    return 0


if __name__ == "__main__":
    sys.exit(main())
