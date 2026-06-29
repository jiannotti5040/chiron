# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
uma.rsls -- the Recursive Symbiotic Logic System subpackage.

Implements the field-theoretic engine that the existing UMA pipeline
solves: the singular convex barrier V(M), the Maxwell-Cattaneo entropy
flux, the HLL Riemann transport, the Phase A falsification kernel, and
the Menger-sponge AMR substrate.

See docs/RSLS_specification.md for the formal theory and
docs/RSLS_menger_substrate.md for the lattice argument.
"""
from uma.rsls.memory import (
    MemoryConfig,
    V, V_prime, V_double_prime,
    clip_M, ell_star, wall_thickness, interface_width,
    gradient_stress, nec_violation,
    gaussian_pulse, zero_field,
)

from uma.rsls.cattaneo import (
    cattaneo_step, cattaneo_step_2d, cattaneo_cfl, subluminal,
)

from uma.rsls.hll import (
    hll_flux, hll_update_spherical, hll_update_spherical_2var, transport_cfl,
)

from uma.rsls.phase_a import (
    PhaseAConfig, PhaseAResult, run_phase_a, convergence_study,
)

from uma.rsls.menger import (
    MengerSponge, Cell, HAUSDORFF_DIM,
    SURVIVING_OFFSETS, is_surviving,
    theoretical_n_cells, theoretical_volume, theoretical_surface_area,
)

from uma.rsls.coupling import (
    RSLSCoupling, RSLSTensorRecord,
)

from uma.rsls.stage3 import (
    whitham_subcharacteristic, whitham_margin,
    dispersion_polynomial, find_poles, all_poles_stable,
    IsotropisationParams, pseudospectral_envelope_satisfied,
    reflection_coefficient, reflection_spectrum,
    wigner_delay, echo_spacing,
    detectability_bound, macroscopic_ell_star_lower_bound,
)

from uma.rsls.srb import (
    LorenzParams, lorenz_rhs, integrate_lorenz, rk4_step,
    lyapunov_max, srb_histogram, srb_converges,
    koopman_transfer_matrix, koopman_stationary,
    lindblad_step, integrate_lindblad, born_rule_match,
)

from uma.rsls.frame_dragging import (
    FrameDraggingConfig, FrameDraggingResult,
    kerr_like_drag, cone_aperture_full,
    cylindrical_hll_step, lyapunov_kernel, run_frame_dragging,
)

from uma.rsls.stage6 import (
    Stage6Config, Stage6Result,
    off_diagonal_stress, equilibrium_beta_phi,
    beta_phi_causal_step, run_stage6, stage6_lyapunov,
)

from uma.rsls.ligo_lisa import (
    RingdownParams, RingdownAnalysis,
    generate_kerr_ringdown, generate_rsls_echo_train,
    generate_synthetic_strain, autocorrelation,
    analyze_ringdown, synthetic_injection_recovery,
)

__all__ = [
    # memory
    "MemoryConfig", "V", "V_prime", "V_double_prime",
    "clip_M", "ell_star", "wall_thickness", "interface_width",
    "gradient_stress", "nec_violation",
    "gaussian_pulse", "zero_field",
    # cattaneo
    "cattaneo_step", "cattaneo_step_2d", "cattaneo_cfl", "subluminal",
    # hll
    "hll_flux", "hll_update_spherical", "hll_update_spherical_2var", "transport_cfl",
    # phase A
    "PhaseAConfig", "PhaseAResult", "run_phase_a", "convergence_study",
    # menger
    "MengerSponge", "Cell", "HAUSDORFF_DIM",
    "SURVIVING_OFFSETS", "is_surviving",
    "theoretical_n_cells", "theoretical_volume", "theoretical_surface_area",
    # coupling
    "RSLSCoupling", "RSLSTensorRecord",
    # stage 3 -- perturbative analysis
    "whitham_subcharacteristic", "whitham_margin",
    "dispersion_polynomial", "find_poles", "all_poles_stable",
    "IsotropisationParams", "pseudospectral_envelope_satisfied",
    "reflection_coefficient", "reflection_spectrum",
    "wigner_delay", "echo_spacing",
    "detectability_bound", "macroscopic_ell_star_lower_bound",
    # SRB / Lindblad / Lyapunov
    "LorenzParams", "lorenz_rhs", "integrate_lorenz", "rk4_step",
    "lyapunov_max", "srb_histogram", "srb_converges",
    "koopman_transfer_matrix", "koopman_stationary",
    "lindblad_step", "integrate_lindblad", "born_rule_match",
    # frame-dragging (Stage 5)
    "FrameDraggingConfig", "FrameDraggingResult",
    "kerr_like_drag", "cone_aperture_full",
    "cylindrical_hll_step", "lyapunov_kernel", "run_frame_dragging",
    # Stage 6 - self-consistent ADM coupling
    "Stage6Config", "Stage6Result",
    "off_diagonal_stress", "equilibrium_beta_phi",
    "beta_phi_causal_step", "run_stage6", "stage6_lyapunov",
    # LIGO/LISA waveform interface
    "RingdownParams", "RingdownAnalysis",
    "generate_kerr_ringdown", "generate_rsls_echo_train",
    "generate_synthetic_strain", "autocorrelation",
    "analyze_ringdown", "synthetic_injection_recovery",
]
