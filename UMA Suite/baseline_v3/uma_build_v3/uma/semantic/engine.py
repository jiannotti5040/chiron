"""
SemanticEngine -- compiler + runner.

STACK (correct separation):
    SemanticEngine          compiles intent -> UMA_IR
        |
    UMA_IR                  execution graph
        |
    UMAExecutor             drives kernel
        |
    UMAClient               physics (untouched)

ENGINE3 BRIDGE -- Silver grounded:
    binary weight: x = len(binary(s)) / len(binary(anchor))
    complex state: z_c = x * ((1 - sqrt 2) + i sqrt e)
    E_integral:    E = |z_c|^2 / 2 = x^2 * (3 - 2 sqrt 2 + e) / 2
    dH_dt:         (H - H_prev) / dt
    friction:      walks down by step_weight / (1 + |dH_dt| / floor)

The imaginary component sqrt(e) is the architectural bridge between:
    pi    (continuous spacetime geometry)
    delta_S (discrete Silver Ratio / Pell recursion)

Closure (Omega) when:
    friction < 0.15
    |dH_dt|  < CALIBRATED_DH_DT_FLOOR
    |z - z*| < 2 * field_scale
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from uma.observations.base import Observation, GaussianObservation
from uma.semantic.constants import (
    INV_DELTA_S_SQ, DELTA_S, C1_SILVER, SQRT_E,
    engine3_complex_state, engine3_E,
    silver_E_target, silver_field_scale, CALIBRATED_FIELD_SCALE,
)
from uma.semantic.constraints import ConstraintSet, EqualityConstraint
from uma.semantic.executor import UMAExecutor, ExecutorResult
from uma.semantic.friction import (
    SemanticFriction, SemanticFrictionConfig, FrictionRecord,
)
from uma.semantic.inarticulation import (
    Inarticulator, NullInarticulator, ProductionMetrics,
)
from uma.semantic.ir import IRNode, UMA_IR


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class SemanticEngineConfig:
    friction: SemanticFrictionConfig = field(default_factory=SemanticFrictionConfig)
    stop_on_closure: bool = True
    verbose: bool = False
    obs_every: int = 1
    constrain_every: int = 1

    @classmethod
    def from_uma_config(cls, cfg, dt: float = 0.04, **kwargs) -> "SemanticEngineConfig":
        return cls(
            friction=SemanticFrictionConfig.from_uma_config(cfg, dt=dt),
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class SemanticEngineResult:
    is_closed: bool
    closure_node: Optional[str]
    friction_records: List[FrictionRecord]
    friction_summary: Dict[str, Any]
    final_posterior: Any
    z_final: np.ndarray
    production_metrics: ProductionMetrics
    nodes_executed: int
    ir: UMA_IR

    def summary(self) -> str:
        pm = self.production_metrics
        fs = self.friction_summary
        f_final = fs.get('friction_final', 0.0) if isinstance(fs, dict) else 0.0
        dH_dt   = fs.get('dH_dt_final',   0.0) if isinstance(fs, dict) else 0.0
        H_final = fs.get('H_final',        0.0) if isinstance(fs, dict) else 0.0
        H_target = fs.get('H_target',     0.0) if isinstance(fs, dict) else 0.0
        floor = fs.get('dH_dt_floor',     0.0) if isinstance(fs, dict) else 0.0
        return (
            "\nSemanticEngine Result\n"
            f"   IR:                 {self.ir.summary()}\n"
            f"   Nodes executed:     {self.nodes_executed}\n"
            f"   Stage:              {pm.stage}\n"
            f"   Closed (Omega):     {self.is_closed}\n"
            f"   Closure node:       {self.closure_node}\n"
            f"   Friction:           {f_final:.4f}\n"
            f"   dH/dt final:        {dH_dt:.4e}\n"
            f"   dH/dt floor:        {floor:.4e}\n"
            f"   H_final:            {H_final:.6e}\n"
            f"   H_target:           {H_target:.6e}\n"
            f"   Semantic density:   {pm.semantic_density:.4f}\n"
            f"   Stability index:    {pm.stability_index:.4f}\n"
            f"   1/delta_S^2 =       {INV_DELTA_S_SQ:.6f}\n"
        )


# ---------------------------------------------------------------------------
# SemanticEngine -- compiler
# ---------------------------------------------------------------------------

class SemanticEngine:
    """Compiles intent -> UMA_IR, then runs via UMAExecutor."""

    def __init__(
        self,
        z_target: np.ndarray,
        config: Optional[SemanticEngineConfig] = None,
        constraints: Optional[List[EqualityConstraint]] = None,
        inarticulator: Optional[Inarticulator] = None,
    ):
        self.z_target = np.asarray(z_target, dtype=float)
        self.config = config or SemanticEngineConfig()
        self._user_constraints = constraints
        self.inarticulator = inarticulator or NullInarticulator()

    @classmethod
    def from_uma_config(
        cls, cfg, z_target: np.ndarray, dt: float = 0.04, **kwargs
    ) -> "SemanticEngine":
        engine_cfg = SemanticEngineConfig.from_uma_config(cfg, dt=dt)
        return cls(z_target=z_target, config=engine_cfg, **kwargs)

    def compile(
        self,
        n_steps: int,
        dt: float,
        observations: Optional[List[Tuple[Observation, np.ndarray]]],
        constraint_set: ConstraintSet,
    ) -> UMA_IR:
        ir = UMA_IR()
        ir.metadata = {"z_target": self.z_target, "n_steps": n_steps, "dt": dt}

        obs_cycle = len(observations) if observations else 0
        obs_idx = 0

        for step in range(n_steps):
            sid = f"s{step:04d}"
            ir.append(IRNode(f"{sid}_evolve", "evolve", {"dt": dt}))

            if observations and step % self.config.obs_every == 0:
                obs, y = observations[obs_idx % obs_cycle]
                obs_idx += 1
                ir.append(IRNode(
                    f"{sid}_observe", "observe",
                    {"observation": obs, "y": y},
                ))

            if step % self.config.constrain_every == 0:
                ir.append(IRNode(
                    f"{sid}_constrain", "constrain",
                    {"constraint_set": constraint_set},
                ))

            ir.append(IRNode(f"{sid}_ckpt", "checkpoint", {}))

        return ir

    def run(
        self,
        client,
        n_steps: int = 100,
        dt: float = 0.04,
        observations: Optional[List[Tuple[Observation, np.ndarray]]] = None,
    ) -> SemanticEngineResult:
        dim = len(self.z_target)
        cs = (
            ConstraintSet(self._user_constraints, max_iters=20, tol=1e-6)
            if self._user_constraints
            else ConstraintSet.default_semantic_constraints(dim, self.z_target)
        )

        ir = self.compile(n_steps, dt, observations, cs)
        if self.config.verbose:
            print(f"[SemanticEngine] {ir.summary()}")

        # Hamiltonian function for friction tracker
        def H_of_z(z: np.ndarray) -> float:
            psi = client.projection.lift(z)
            return float(client.dynamics.cfg.dt and 0.0 + 0.0)  # placeholder
        # actually use the client's hamiltonian directly:
        def H_of_z_real(z: np.ndarray) -> float:
            psi = client.projection.lift(z)
            from uma.dynamics.generic import hamiltonian
            return hamiltonian(psi, lam=client.config.generic.reaction)

        friction = SemanticFriction(
            self.z_target, self.config.friction, hamiltonian_fn=H_of_z_real,
        )
        executor = UMAExecutor(
            friction=friction,
            inarticulator=self.inarticulator,
            stop_on_closure=self.config.stop_on_closure,
            verbose=self.config.verbose,
        )
        ex: ExecutorResult = executor.run(ir, client)

        return SemanticEngineResult(
            is_closed=ex.is_closed,
            closure_node=ex.closure_node,
            friction_records=ex.friction_records,
            friction_summary=ex.friction_summary,
            final_posterior=ex.final_posterior,
            z_final=ex.z_final,
            production_metrics=ex.production_metrics,
            nodes_executed=ex.nodes_executed,
            ir=ir,
        )


# ---------------------------------------------------------------------------
# Engine3 bridge
# ---------------------------------------------------------------------------

def tokenize_to_binary_weight(s: str, anchor: str = "dIse") -> float:
    """Engine3's binary mapping: len(binary(s)) / len(binary(anchor))."""
    binary = ''.join(format(ord(c), '08b') for c in s)
    a_bin = ''.join(format(ord(c), '08b') for c in anchor)
    return len(binary) / max(len(a_bin), 1)


def string_to_observation(
    s: str,
    dim: int,
    anchor: str = "dIse",
    cfg=None,
) -> Tuple[GaussianObservation, np.ndarray]:
    """
    Engine3 -> UMA bridge, Silver-grounded.

    Pipeline:
        s -> x (binary weight)
        x -> z_complex = x * ((1 - sqrt 2) + i sqrt e)
        E = |z_complex|^2 / 2
        E -> normalized to field scale
        y = direction * E_normalized
    """
    x = tokenize_to_binary_weight(s, anchor)

    z_c = engine3_complex_state(x)
    E_raw = engine3_E(x)

    if cfg is not None:
        kT = cfg.generic.kT
        N = cfg.grid.N
        fs = silver_field_scale(kT, N, 1.0)
        x_norm = x / (x + 1.0)
        y_scale = fs * x_norm
    else:
        x_norm = x / (x + 1.0)
        y_scale = x_norm * math.sqrt(2.0 * E_raw)

    y = np.full(dim, y_scale / max(dim, 1) * math.sqrt(dim))
    noise_var = max(y_scale ** 2 * INV_DELTA_S_SQ, 1e-10)
    R = noise_var * np.eye(dim)
    obs = GaussianObservation(H=np.eye(dim), R=R)
    return obs, y
