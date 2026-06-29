# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
uma.rsls.menger -- Menger sponge lattice for RSLS AMR.

Constructs a level-n Menger sponge as the deterministic AMR substrate
for the M field. See docs/RSLS_menger_substrate.md for the structural
argument; this module is the corresponding implementation.

Construction rule for one subdivision step:
    Take a cube. Split into 3x3x3 = 27 sub-cubes at integer offsets
    (i, j, k) for i, j, k in {0, 1, 2}.
    KEEP the sub-cube iff the number of coordinates equal to 1 is <= 1.

    -- 0 ones: 8 corner cubes
    -- 1 one:  12 edge cubes
    -- 2 ones: 6 face-centre cubes (REMOVED)
    -- 3 ones: 1 cube-centre cube (REMOVED)
    Total kept: 20

After n levels:
    20^n surviving cubes, each of side (1/3)^n
    Total volume: (20/27)^n
    Total surface: (8/9) * (20/9)^n
    Hausdorff dimension: log(20) / log(3) ~= 2.7268

This module exposes:
    - MengerSponge(level): construct the sponge
    - .cells           : list of (i, j, k, depth) for each surviving cell
    - .centres         : ndarray (n_cells, 3) of cell-centre coordinates
    - .sides           : ndarray (n_cells,)   of cell side lengths
    - .neighbors(i)    : indices of face-sharing neighbours of cell i
    - .laplacian(field): graph Laplacian acting on a per-cell field
    - .refine(i)       : subdivide cell i, returning new cell indices
    - .coarsen(parent) : reverse refinement (when all children agree)
    - .volume()        : total cell volume
    - .surface_area()  : total cell surface area
    - .hausdorff_dim() : log(20)/log(3) (constant; reported for reference)
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Construction rule
# ---------------------------------------------------------------------------

def is_surviving(i: int, j: int, k: int) -> bool:
    """The Menger sponge survival rule: keep iff at most one coord == 1."""
    return (int(i == 1) + int(j == 1) + int(k == 1)) <= 1


SURVIVING_OFFSETS: Tuple[Tuple[int, int, int], ...] = tuple(
    (i, j, k)
    for i in range(3)
    for j in range(3)
    for k in range(3)
    if is_surviving(i, j, k)
)  # length 20


HAUSDORFF_DIM: float = math.log(20.0) / math.log(3.0)  # ~ 2.7268


# ---------------------------------------------------------------------------
# Cell record
# ---------------------------------------------------------------------------

@dataclass
class Cell:
    """A single surviving cube in the sponge."""
    origin: Tuple[float, float, float]   # lower-left corner
    side: float                          # edge length
    depth: int                           # subdivision level (0 = top)
    parent: Optional[int] = None         # index of parent cell (None if top-level)
    children: Optional[List[int]] = None # indices of 20 children if refined

    @property
    def centre(self) -> Tuple[float, float, float]:
        ox, oy, oz = self.origin
        h = self.side * 0.5
        return (ox + h, oy + h, oz + h)

    @property
    def volume(self) -> float:
        return self.side ** 3

    @property
    def surface_area(self) -> float:
        return 6.0 * self.side ** 2


# ---------------------------------------------------------------------------
# Sponge
# ---------------------------------------------------------------------------

class MengerSponge:
    """
    A Menger sponge built to a given uniform initial level.

    Subsequent calls to .refine(i) push individual cells deeper; calls
    to .coarsen(parent) reverse the refinement. The resulting non-uniform
    sponge is the RSLS adaptive lattice.

    The sponge is canonically positioned with its unit cube at
    origin (0, 0, 0). Pass `side=L` to scale.
    """

    def __init__(self, level: int = 1, side: float = 1.0):
        if level < 0:
            raise ValueError("level must be >= 0")
        self._cells: List[Cell] = []
        # Start with the level-0 unit cube
        root = Cell(origin=(0.0, 0.0, 0.0), side=side, depth=0)
        self._cells.append(root)
        # The set of indices that are "alive" -- not coarsened-out or
        # subdivided. Refinement marks the parent dead and adds children.
        self._alive: Set[int] = {0}
        # Uniformly refine to the requested level
        for _ in range(level):
            self._uniform_refine()

    # -----------------------------------------------------------------
    # Internal: uniform refinement
    # -----------------------------------------------------------------

    def _uniform_refine(self) -> None:
        """Refine every currently-alive cell once."""
        for idx in list(self._alive):
            self._refine_one(idx)

    def _refine_one(self, idx: int) -> List[int]:
        """Refine cell idx in-place. Returns the new child indices."""
        parent = self._cells[idx]
        if parent.children is not None:
            raise RuntimeError(f"Cell {idx} already refined")
        ox, oy, oz = parent.origin
        h = parent.side / 3.0
        child_indices: List[int] = []
        for (ci, cj, ck) in SURVIVING_OFFSETS:
            child = Cell(
                origin=(ox + ci * h, oy + cj * h, oz + ck * h),
                side=h,
                depth=parent.depth + 1,
                parent=idx,
            )
            self._cells.append(child)
            child_indices.append(len(self._cells) - 1)
            self._alive.add(child_indices[-1])
        parent.children = child_indices
        self._alive.discard(idx)
        return child_indices

    # -----------------------------------------------------------------
    # Public API: refine / coarsen
    # -----------------------------------------------------------------

    def refine(self, idx: int) -> List[int]:
        """
        Subdivide the cell at index idx into its 20 children.
        Returns the list of new child indices. The parent is removed
        from the alive set.
        """
        if idx not in self._alive:
            raise ValueError(f"Cell {idx} is not currently alive")
        return self._refine_one(idx)

    def coarsen(self, parent_idx: int) -> int:
        """
        Reverse a refinement: remove all children, restore the parent
        to the alive set. Only allowed if all children are currently
        alive (no grandchildren).
        """
        parent = self._cells[parent_idx]
        if parent.children is None:
            raise ValueError(f"Cell {parent_idx} has no children")
        for c_idx in parent.children:
            if c_idx not in self._alive:
                raise ValueError(
                    f"Cannot coarsen: child {c_idx} is itself subdivided "
                    "or otherwise not alive"
                )
        for c_idx in parent.children:
            self._alive.discard(c_idx)
        parent.children = None
        self._alive.add(parent_idx)
        return parent_idx

    # -----------------------------------------------------------------
    # Bulk properties
    # -----------------------------------------------------------------

    @property
    def cells(self) -> List[Cell]:
        """All cells, including subdivided (dead) ancestors. For only
        the alive cells, see .alive_cells()."""
        return self._cells

    def alive_cells(self) -> List[Cell]:
        return [self._cells[i] for i in sorted(self._alive)]

    def alive_indices(self) -> List[int]:
        return sorted(self._alive)

    @property
    def n_alive(self) -> int:
        return len(self._alive)

    @property
    def hausdorff_dim(self) -> float:
        return HAUSDORFF_DIM

    def centres(self) -> np.ndarray:
        return np.array([self._cells[i].centre for i in sorted(self._alive)])

    def sides(self) -> np.ndarray:
        return np.array([self._cells[i].side for i in sorted(self._alive)])

    def volume(self) -> float:
        return float(sum(self._cells[i].volume for i in self._alive))

    def surface_area(self) -> float:
        """Total surface area of the alive cells (overcounts shared faces;
        consistent with the fractal-limit (20/9)^n scaling)."""
        return float(sum(self._cells[i].surface_area for i in self._alive))

    # -----------------------------------------------------------------
    # Adjacency: graph neighbors
    # -----------------------------------------------------------------

    def neighbors(self, idx: int, tol: float = 1e-9) -> List[int]:
        """
        Face-sharing neighbours of the alive cell at index idx.

        Two alive cells are neighbours iff their bounding boxes share
        a 2-D face (one coordinate matched at the shared face, the
        other two intervals overlap).

        For a uniform sponge this is O(N) per call (cheap at level <= 3).
        """
        if idx not in self._alive:
            raise ValueError(f"Cell {idx} is not alive")
        c = self._cells[idx]
        c_lo = np.array(c.origin)
        c_hi = c_lo + c.side
        out: List[int] = []
        for j in self._alive:
            if j == idx:
                continue
            d = self._cells[j]
            d_lo = np.array(d.origin)
            d_hi = d_lo + d.side
            # Check shared face: exactly one axis has equal coordinates
            # at the touching face; the other two have nonzero overlap.
            shared_face = 0
            disjoint = False
            for ax in range(3):
                touch = (
                    abs(c_hi[ax] - d_lo[ax]) < tol
                    or abs(d_hi[ax] - c_lo[ax]) < tol
                )
                overlap = (c_lo[ax] < d_hi[ax] - tol) and (d_lo[ax] < c_hi[ax] - tol)
                if touch and not overlap:
                    shared_face += 1
                elif not overlap:
                    disjoint = True
                    break
            if not disjoint and shared_face == 1:
                out.append(j)
        return out

    # -----------------------------------------------------------------
    # Adjacency: cached
    # -----------------------------------------------------------------

    def build_adjacency(self) -> Dict[int, List[int]]:
        """Pre-compute the full neighbour map for fast Laplacian application."""
        adj: Dict[int, List[int]] = {}
        idxs = sorted(self._alive)
        for i in idxs:
            adj[i] = self.neighbors(i)
        return adj

    # -----------------------------------------------------------------
    # Graph Laplacian
    # -----------------------------------------------------------------

    def laplacian(
        self,
        field: np.ndarray,
        adjacency: Optional[Dict[int, List[int]]] = None,
    ) -> np.ndarray:
        """
        Symmetric mean-form graph Laplacian acting on a per-cell field.

            (L f)_i = (1 / |N(i)|) * sum_{j in N(i)} (f_j - f_i)

        Returns shape matching `field`. The mapping between alive cell
        indices and array positions is the sorted order returned by
        .alive_indices().
        """
        idxs = self.alive_indices()
        if len(field) != len(idxs):
            raise ValueError(
                f"field length {len(field)} != n_alive {len(idxs)}"
            )
        pos: Dict[int, int] = {ci: p for p, ci in enumerate(idxs)}
        adjacency = adjacency or self.build_adjacency()
        out = np.zeros_like(field, dtype=float)
        for p, ci in enumerate(idxs):
            ns = adjacency[ci]
            if not ns:
                continue
            mean_neighbours = np.mean([field[pos[j]] for j in ns if j in pos])
            out[p] = mean_neighbours - field[p]
        return out


# ---------------------------------------------------------------------------
# Theoretical reference quantities (closed-form for uniform level n)
# ---------------------------------------------------------------------------

def theoretical_n_cells(level: int) -> int:
    """20^level (count of cells at uniform level n)."""
    return 20 ** level


def theoretical_volume(level: int, side: float = 1.0) -> float:
    """(20/27)^n * side^3."""
    return (20.0 / 27.0) ** level * side ** 3


def theoretical_surface_area(level: int, side: float = 1.0) -> float:
    """Asymptotic alive-cell surface area: 6 * 20^n * (side/3^n)^2."""
    return 6.0 * (20 ** level) * (side / 3 ** level) ** 2


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== Menger sponge construction ===\n")
    for L in range(4):
        sp = MengerSponge(level=L)
        print(
            f"  L={L}: alive={sp.n_alive} (expected {theoretical_n_cells(L)})"
            f"    vol={sp.volume():.6e} (expected {theoretical_volume(L):.6e})"
            f"    surf={sp.surface_area():.6e}"
        )
    print(f"  Hausdorff dim = {HAUSDORFF_DIM:.6f}   (log 20 / log 3)")

    print("\n=== Neighbor map at L=1 ===")
    sp = MengerSponge(level=1)
    adj = sp.build_adjacency()
    degrees = [len(adj[i]) for i in sp.alive_indices()]
    print(f"  cells: {sp.n_alive}")
    print(f"  edges (sum of degrees / 2): {sum(degrees) // 2}")
    print(f"  degree distribution: min={min(degrees)} max={max(degrees)} mean={np.mean(degrees):.2f}")

    print("\n=== Graph Laplacian on a sample field at L=1 ===")
    f = np.arange(sp.n_alive, dtype=float)
    Lf = sp.laplacian(f, adj)
    print(f"  ||L f||_inf = {abs(Lf).max():.4f}   (Laplacian is finite and finite-rank)")
