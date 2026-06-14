# THEORY: Sphere Derivation

> Source: `sphere_derivation.txt` (extracted from corpus).
> Inside-out derivation of the Acoustic Sphere Projection System.
> Every parameter is fixed by spherical Bessel zeros; nothing is calibrated.

Acoustic Sphere Projection System

Full Derivation: Inside Out


1. The Sphere (Given)
A perfect standing wave pressure field inside a cubic box of side L. Five fans define
pressure-release boundary conditions on five faces. One open face is the input aperture.

The pressure field satisfies the wave equation:


 ∇²P = (1/c²) ∂²P/∂t²


In spherical coordinates centered at the box center, the solutions are:


 P_nlm(r,θ,φ,t) = j_n(k_nl · r) · Y_lm(θ,φ) · e^(iωt)


Where:

   j_n = spherical Bessel function of order n

   Y_lm = spherical harmonic (l, m)

   k_nl = j_nl_zero / R (Bessel zero divided by sphere radius)

   R = L/2 (sphere radius)

The Bessel zeros j_nl (first few):


 n=0: j_0n = π, 2π, 3π, ...
 n=1: j_1n = 4.493, 7.725, 10.904, ...
 n=2: j_2n = 5.763, 9.095, 12.323, ...


These are exact. Not approximated. Not calibrated.


2. Pendulum (Derived from sphere)

The pendulum sweeps through the pressure field. Its period must match a resonant mode of
the sphere.

Resonant frequencies:


  f_nl = c_air · j_nl_zero / (2π · R)


Pendulum period:


  T = 2π√(L_pend / g)


Setting T = 1/f_nl and solving for pendulum length:


  L_pend = g / (4π² · f_nl²)
          = g · (2π · R)² / (4π² · c_air² · j_nl_zero²)
          = g · R² / (c_air² · j_nl_zero²       / π²) ... simplified:
          = g · R² / (c_air · j_nl_zero / π)²


The pendulum length is EXACT given L, g, c_air, and which mode (n,l).

The pendulum arc traces a great circle through the sphere. Each swing samples pressure
nodes at known angular positions.


3. Venturi Throat r₀ (Derived from Bessel zeros)
The Venturi throat must match a resonant mode of the sphere.


  r₀ = R · j_nl_zero / π


This is exact. When r₀ satisfies this relation, the Venturi is resonant with the standing wave
cavity.

Bernoulli gain at exact resonance:


  G = 1 - (r_in/r₀)²


r_in is set by the next lower Bessel zero:


  r_in = R · j_(n-1)l_zero / π


So G is derived, not chosen.

4. Blind Gate Spacing (Derived from Venturi)
The blind gate acts as a diffraction grating. Its slit spacing d must produce a first-order
diffraction maximum at the Venturi throat radius r₀.

Diffraction condition:


  d · sin(θ) = mλ


The angle θ is set by the geometry:


  sin(θ) = r₀ / √(r₀² + D²)


Where D is the distance from blind to Venturi. Setting m=1 and solving for d:


  d = λ · √(r₀² + D²) / r₀


λ is the wavelength of the interfered light at the lens (derived next).


5. Lens Focal Length (Derived from blind spacing)
The first lens collimates the interfered light. Focal length f₁ must satisfy:


  f₁ = r₀² / λ    (Rayleigh range of the wavefront at Venturi)


The refractor between the two lenses introduces a phase shift:


  φ_refractor = π · n_refractor · d_refractor / λ


Where n_refractor is refractive index and d_refractor is thickness. This is chosen to match
the phase of the synthetic light.


6. Interference Point (Derived from lens geometry)
The starlight and synthetic light interfere at the focal plane of the second lens. The
condition for constructive interference:

 Δφ = φ_star - φ_synthetic = 2πm


φ_star carries the Planck distribution:


 φ_star = hν/kT      (from B(ν,T) = 2hν³/c² · 1/(e^(hν/kT) - 1))


e is already here -- inside the starlight.

The synthetic light phase is controlled by the fan:

 φ_synthetic = ω_fan · t


Constructive interference when:


 ω_fan = hν/kT · (1/t)


The fan frequency is now derived from the sphere AND the starlight temperature.


7. Fan Frequency (Everything converges)
From the sphere: f_fan = c_air · j_nl / (2π · R)

From the starlight: f_fan = hν / (kT · 2π)

Setting equal:


 c_air · j_nl / R = hν / kT


This is the fundamental constraint of the system. Given stellar temperature T and sphere
radius R, the fan frequency and the resonant mode (n,l) are locked together.

Or equivalently: given the fan frequency and box size, the system selects which stellar
temperature it is resonant with.


8. Complete System (Inside Out)

 SPHERE
    j_nl zeros → exact geometry for everything upstream

 PENDULUM
   L_pend = g·R² / (c_air·j_nl/π)²


 VENTURI
   r₀ = R · j_nl / π
   G   = 1 - (r_in/r₀)²


 BLIND GATE
   d = λ·√(r₀²+D²) / r₀


 LENS 1
   f₁ = r₀² / λ


 REFRACTOR
   φ = π·n·d/λ    (phase match to synthetic)


 LENS 2
   Collimates toward open face


 INTERFERENCE
   φ_star = φ_synthetic    →   ω_fan = hν/kT


 FAN
   f_fan = c_air·j_nl / (2π·R)     =   hν/(2π·kT)


 STARLIGHT
   B(ν,T) = 2hν³/c² · 1/(e^(hν/kT) - 1)
   e is already structural to the input


The system is closed. Every parameter derived from the sphere outward.
