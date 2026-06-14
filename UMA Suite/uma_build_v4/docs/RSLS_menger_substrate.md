# RSLS — The Menger Sponge as Predicted Substrate

This document develops the argument that the Menger sponge is not an
arbitrary discretisation choice, but the **predicted geometry** of the
saturated information attractor that RSLS Stages 4C–4F describe.

## 1. The structural claim

RSLS Stage 4C resolves the gradient catastrophe by adding a parabolic
penalty −μ ΔM that diffuses the saturation boundary across an emergent
length scale

> ℓ_*² ≈ μ / V''(M)

The wall is then a "finite, continuous diffuse-interface phase
boundary in BV space." Stage 4F gives the dynamical reason it does
not collapse: as M → M_max the bulk modulus diverges, ∇·U → 0, and
the geometric driver shuts off. The wall has to:

1. Carry an unbounded **surface area** (so the divergent V'(M) has
   somewhere to express itself thermodynamically)
2. Bound a **finite volume** (so the spatial integral of M is
   well-defined and ‖M‖_∞ < M_max)
3. Be **connected** (so U^μ can still propagate through it; the
   manifold doesn't fall apart)
4. Be **self-similar across scales** (so AMR refinement is principled
   rather than arbitrary)
5. Have **fractional Hausdorff dimension** (so the Laplacian on the
   wall produces anomalous transport, consistent with Stage 4E)

There is one canonical mathematical object satisfying all five: a
self-similar fractal lattice. The Menger sponge is the natural such
lattice in 3D (the Sierpiński carpet is the 2D analog; the Cantor
set, the 1D analog).

## 2. Properties of the Menger sponge

Construction. Begin with a unit cube. Subdivide into 3×3×3 = 27
sub-cubes. Remove the centre sub-cube and the six face-centre
sub-cubes, leaving 20. Recurse on each.

After n levels:

| Quantity | Formula | Asymptote |
|----------|---------|-----------|
| Sub-cubes surviving | 20^n | → ∞ |
| Side of one cube | (1/3)^n | → 0 |
| Total volume | (20/27)^n | → 0 |
| Total surface area | (8/9) · 20^n · (1/3)^(2n) = (8/9)(20/9)^n | → ∞ |
| Hausdorff dimension | log 20 / log 3 ≈ 2.7268 | const |

The volume law (20/27)^n → 0 and surface law (20/9)^n → ∞ are the
exact signature the singular convex barrier produces:

> V(M) = − λ log(1 − M/M_max)

with M = removed volume fraction and M_max = 1. The volume scales as
(20/27)^n exactly, so

> 1 − M_n / M_max = (20/27)^n
> V(M_n) = − λ log((20/27)^n) = n λ log(27/20)

V grows **linearly in level n**, and V'(M_n) diverges as M → 1.
Discrete sponge depth is, up to a constant, the continuous M field.

## 3. Mapping onto the RSLS equations

### 3.1. M field discretisation

Place the M field at surviving cube centres of a level-n sponge:

> M_i  for  i = 1 … 20^n

When a cube is "full" (M_i ≈ M_max), subdivide it: it is replaced by
its 20 surviving children at the next level, each starting at the
common value M_i. This is the **refinement** step. The reverse
operation (coarsen) is permitted when all 20 children agree within
tolerance.

This is exactly the AMR scheme RSLS-XI step 3 demands, with the
refinement ratio fixed at 1:3 (the sponge's intrinsic self-similar
ratio) rather than the arbitrary 1:2 of standard AMR.

### 3.2. Laplacian on the sponge

The graph Laplacian on the sponge connectivity is

> (Δ M)_i = (1 / |N(i)|) Σ_{j ∈ N(i)} (M_j − M_i)

where N(i) is the set of face-sharing neighbours. The spectrum of
this Laplacian has known fractal structure: eigenvalues organise into
log-periodic bands with ratio 9 (= 3² because the sponge is a
self-similar 2.7268-dimensional surface). The continuous limit of
this operator on the Menger sponge is the **anomalous Laplacian**
with diffusion exponent

> d_w = log(27/8) / log(3) ≈ 2.097

(slightly greater than the 2 of standard Brownian motion — exactly the
"sub-diffusive transport" Stage 4E predicts).

### 3.3. Entropy flux on edges

The Maxwell–Cattaneo flux J_μ lives on the edges of the sponge graph
(face-sharing connections between surviving cubes). The implicit
update

> J_{ij}^{n+1} = (J_{ij}^n − (dt μ/τ_J)(M_j − M_i)) / (1 + dt/τ_J)

is unconditionally stable in dt and respects the c_diff² = μ/(τ_J τ_M)
bound when computed against the natural sponge metric (edge length
(1/3)^n).

### 3.4. Self-quenching as automatic refinement

The Stage 4F self-quenching feedback is automatic on the sponge:

1. M_i → M_max in some cube ⇒ V''(M_i) → ∞
2. The closure trigger fires ⇒ refine cube i to its 20 children
3. Each child now has capacity M_max − M_i_initial (positive again)
4. The local ∇·U driver shuts off because the available volume just
   doubled (each child has volume (1/27) of the parent, but 20 of them
   exist; total available = 20/27 of parent, with M reset to its
   pre-saturation value in each child)

This is the geometric realisation of "the geometric driver shuts off
dynamically, severing the mode coupling before resonance can form."
No explicit feedback law is needed; the topology of the sponge
implements it.

## 4. The observational prediction

Discrete scale invariance with ratio 3 is **the** distinguishing
signature of a Menger-sponge wall versus a smooth diffuse boundary.
It manifests in two observables:

### 4.1. Log-periodic echo comb (Stage 3D)

The Wigner time delay between successive echoes is

> Δt_echo = Δt_geom + τ_M

In the smooth Stage 4C picture, τ_M is a single number and successive
echoes are evenly spaced. On a Menger wall, τ_M has a **log-periodic
modulation** at frequencies log 3 · k for k = 1, 2, 3 …

> τ_M(ω) = τ_M,0 · [1 + α cos(2π log(ω/ω_0) / log 3) + …]

LIGO/LISA detection of evenly-spaced echoes would be consistent with
*either* picture. Detection of a **factor-of-3 modulation** in the
echo-spacing series would distinguish them — and would be specific
evidence of a fractal entropy wall.

### 4.2. Photon-sphere multipole structure (Stage 2.IV.4)

The exterior metric correction in Stage 2 is

> δg ∼ O(ℓ_*² / r³)

For a smooth wall, ℓ_* is a single length. For a Menger wall, the
spectral comb of the sponge generates a multipole expansion at
log-periodic radii r_k = ℓ_* · 3^k:

> δg(r) ∼ Σ_k (ℓ_*² / r³)(3^k r / ℓ_*)^(2 − d_H)

The (2 − d_H) ≈ −0.7268 exponent is the **fractal correction** to the
Schwarzschild-like multipole expansion. In principle measurable in
EHT-class imaging of supermassive black hole shadows.

## 5. Why the sponge specifically (and not the Sierpiński carpet)

- The carpet is 2D (d_H = log 8 / log 3 ≈ 1.8928) — it can't carry a
  3D M field directly.
- The sponge has d_H ≈ 2.7268, comfortably between the 2D Hawking-area
  bound (the holographic limit) and the 3D bulk volume. This is the
  range Stage 4D demands: the wall must be high-dimensional enough
  to carry information bulk but low-dimensional enough to enforce
  the holographic "infinite surface area in finite volume" structure.
- The sponge is the **unique** symmetric fractal in 3D with these
  properties under the natural symmetry group (cubic, all 48
  reflections). Other candidate fractals (Cantor dust at d_H = log 8/log 3
  in 3D, etc.) either lack connectivity or break the cubic symmetry
  required by the principal-symbol analysis of Section IV.

## 6. Implementation summary

The Menger sponge enters the build at three points:

1. **As a discretisation lattice** for the M field — `uma/rsls/menger.py`
   constructs a level-n sponge and exposes its connectivity graph.
2. **As an AMR scheme** — `MengerSponge.refine(cell_id)` subdivides a
   cube on demand; `coarsen(cell_id)` reverses it. The trigger is
   |∇M| > threshold (the AMR criterion from RSLS-XI).
3. **As a substrate for the Laplacian** — the graph Laplacian on
   sponge connectivity implements the −μ ΔM penalty of Stage 4C with
   the correct anomalous-diffusion exponent built in.

The result: the existing UMA pipeline gets a new closure condition
("Menger-sponge AMR has stabilised at level n_*"), the TensorBridge
gets a new T_{μν}^{(∇M)} contribution from the sponge gradient, and
the falsification check ℓ_* → const is run as a level-by-level
convergence study.

This is the working content of `examples/rsls_menger_substrate.py`.

## 7. What this is and isn't

This **is** a structural proposal: the Menger sponge fits the RSLS
spec's stated requirements for the saturated information attractor
better than any other canonical geometric object, and the integration
is concrete (a buildable lattice, a buildable Laplacian, two
falsifiable astrophysical predictions).

This **isn't** a claim that the universe literally has a Menger-sponge
event horizon. It is a claim that *if* RSLS Stage 4 is correct, *then*
the saturated entropy wall must have fractal substructure with
properties indistinguishable from a Menger sponge at the scales where
the spec applies. The sponge is the canonical representative of that
class.

The falsification path: if the LIGO/LISA echo data shows even-spaced
(linear in t) echoes with no log-periodic modulation, the Menger
hypothesis is dead. If it shows factor-of-3 modulation, RSLS
Stage 3D acquires a sharp positive signature.
