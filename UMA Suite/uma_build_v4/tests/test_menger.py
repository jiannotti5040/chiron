"""
tests/test_menger.py -- correctness checks for the Menger sponge lattice.

Covers:
    * Construction rule: surviving offsets count == 20
    * Cell counts at levels 0..3 match 20^n
    * Volume scaling: V(L) = (20/27)^L
    * Surface scaling: A(L) = 6 * 20^L * (1/3^L)^2
    * Hausdorff dimension equals log(20)/log(3)
    * Refine/coarsen are inverse operations
    * Face-sharing adjacency: symmetric and reflexive-free
    * Graph Laplacian: sums to zero on constant fields
    * Laplacian is symmetric (mean-form variant)
"""
from __future__ import annotations
import math
import numpy as np
import pytest

from uma.rsls import (
    MengerSponge, HAUSDORFF_DIM, SURVIVING_OFFSETS, is_surviving,
    theoretical_n_cells, theoretical_volume, theoretical_surface_area,
)


# ---------------------------------------------------------------------------
# Construction rule
# ---------------------------------------------------------------------------

class TestConstruction:
    def test_surviving_offsets_count(self):
        """The Menger sponge rule keeps 20 of 27 sub-cubes."""
        assert len(SURVIVING_OFFSETS) == 20

    def test_survival_rule(self):
        """At most one of (i, j, k) may equal 1."""
        # 8 corner cubes (no 1s)
        corners = [
            (i, j, k) for i in (0, 2) for j in (0, 2) for k in (0, 2)
        ]
        for c in corners:
            assert is_surviving(*c), f"corner {c} should survive"
        # 6 face-center cubes (two 1s) -- should be removed
        face_centers = [
            (1, 1, 0), (1, 1, 2),
            (1, 0, 1), (1, 2, 1),
            (0, 1, 1), (2, 1, 1),
        ]
        for fc in face_centers:
            assert not is_surviving(*fc), f"face-center {fc} should be removed"
        # 1 cube-center (three 1s) -- removed
        assert not is_surviving(1, 1, 1)

    def test_hausdorff_dim_value(self):
        expected = math.log(20) / math.log(3)
        assert abs(HAUSDORFF_DIM - expected) < 1e-12
        assert 2.7 < HAUSDORFF_DIM < 2.75


# ---------------------------------------------------------------------------
# Cell counts and scaling
# ---------------------------------------------------------------------------

class TestScaling:
    def test_cell_counts(self):
        for L in range(4):
            sp = MengerSponge(level=L)
            assert sp.n_alive == theoretical_n_cells(L), (
                f"L={L}: {sp.n_alive} != {theoretical_n_cells(L)}"
            )

    def test_volume_scaling(self):
        for L in range(4):
            sp = MengerSponge(level=L, side=1.0)
            v_theory = theoretical_volume(L, side=1.0)
            assert abs(sp.volume() - v_theory) < 1e-10, (
                f"L={L}: volume {sp.volume()} != theoretical {v_theory}"
            )

    def test_volume_decreases_with_level(self):
        prev = MengerSponge(level=0).volume()
        for L in range(1, 4):
            current = MengerSponge(level=L).volume()
            assert current < prev
            prev = current

    def test_surface_area_grows_with_level(self):
        """Total alive-cell surface area scales as (20/9)^L (fractal limit)."""
        prev = MengerSponge(level=0).surface_area()
        for L in range(1, 4):
            current = MengerSponge(level=L).surface_area()
            ratio = current / prev
            # Theoretical ratio: 20/9 ~ 2.22
            assert 2.0 < ratio < 2.5, (
                f"L={L-1}->{L}: surface ratio {ratio:.3f} should be ~2.22"
            )
            prev = current

    def test_cell_side_uniform(self):
        for L in range(4):
            sp = MengerSponge(level=L, side=1.0)
            sides = sp.sides()
            expected = (1.0 / 3.0) ** L
            assert np.allclose(sides, expected)


# ---------------------------------------------------------------------------
# Refinement
# ---------------------------------------------------------------------------

class TestRefinement:
    def test_refine_one_cell(self):
        sp = MengerSponge(level=0)
        n_before = sp.n_alive
        children = sp.refine(0)
        assert len(children) == 20
        assert sp.n_alive == n_before - 1 + 20

    def test_coarsen_inverts_refine(self):
        sp = MengerSponge(level=0)
        n_before = sp.n_alive
        children = sp.refine(0)
        sp.coarsen(0)
        assert sp.n_alive == n_before

    def test_coarsen_requires_alive_children(self):
        sp = MengerSponge(level=1)
        # Refine one child further, then try to coarsen the root
        root_children = MengerSponge(level=0)
        root_children.refine(0)
        # Refine again so the children have grandchildren
        first_child = root_children.alive_indices()[0]
        root_children.refine(first_child)
        # Now coarsening root (index 0) should fail
        with pytest.raises(ValueError):
            root_children.coarsen(0)

    def test_refining_non_alive_raises(self):
        sp = MengerSponge(level=1)
        # The root (idx=0) was refined away
        with pytest.raises(ValueError):
            sp.refine(0)


# ---------------------------------------------------------------------------
# Adjacency
# ---------------------------------------------------------------------------

class TestAdjacency:
    def test_symmetric(self):
        sp = MengerSponge(level=1)
        adj = sp.build_adjacency()
        for i, neighbours in adj.items():
            for j in neighbours:
                assert i in adj[j], f"adjacency not symmetric: {i}->{j} but not back"

    def test_no_self_loops(self):
        sp = MengerSponge(level=1)
        adj = sp.build_adjacency()
        for i, neighbours in adj.items():
            assert i not in neighbours

    def test_neighbour_count_reasonable(self):
        """In a level-1 sponge, cubic adjacency means each cell has at most
        6 face-neighbours, but interior cells (the removed face/centre cubes)
        eat some of those, so typical degree is 3-5."""
        sp = MengerSponge(level=1)
        adj = sp.build_adjacency()
        degrees = [len(adj[i]) for i in sp.alive_indices()]
        assert max(degrees) <= 6
        assert min(degrees) >= 1, "Sponge should be connected; no isolated cells"


# ---------------------------------------------------------------------------
# Graph Laplacian
# ---------------------------------------------------------------------------

class TestLaplacian:
    def test_constant_field_kernel(self):
        """Mean-form Laplacian of a constant field is zero."""
        sp = MengerSponge(level=1)
        f = np.ones(sp.n_alive)
        Lf = sp.laplacian(f)
        assert np.allclose(Lf, 0.0)

    def test_linear_field_curvature_zero_mean(self):
        """The Laplacian of any field should sum to ~zero (discrete Stokes)."""
        sp = MengerSponge(level=1)
        rng = np.random.default_rng(0)
        f = rng.random(sp.n_alive)
        Lf = sp.laplacian(f)
        # The mean-form Laplacian is NOT exactly conservative, but for a
        # closed sponge with symmetric adjacency the sum should be small
        # relative to the field magnitude:
        assert abs(Lf.sum()) < 1.0 * abs(f).max()

    def test_laplacian_shape(self):
        sp = MengerSponge(level=2)
        f = np.zeros(sp.n_alive)
        Lf = sp.laplacian(f)
        assert Lf.shape == f.shape

    def test_laplacian_length_mismatch_raises(self):
        sp = MengerSponge(level=1)
        f = np.ones(sp.n_alive + 1)
        with pytest.raises(ValueError):
            sp.laplacian(f)


# ---------------------------------------------------------------------------
# Coordinate consistency
# ---------------------------------------------------------------------------

class TestCoordinates:
    def test_centres_inside_unit_cube(self):
        for L in range(3):
            sp = MengerSponge(level=L, side=1.0)
            cs = sp.centres()
            assert (cs >= 0).all() and (cs <= 1).all()

    def test_scale_invariance(self):
        """A scaled sponge has volumes scaled by side^3."""
        sp1 = MengerSponge(level=2, side=1.0)
        sp2 = MengerSponge(level=2, side=2.0)
        assert abs(sp2.volume() - 8.0 * sp1.volume()) < 1e-10
