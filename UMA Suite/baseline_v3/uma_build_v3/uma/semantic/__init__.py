"""
uma.semantic -- UMA Semantic Engine (Product Engine).

Architecture:
    SemanticEngine  -> compiles intent into UMA_IR
    UMA_IR          -> execution graph
    UMAExecutor     -> drives UMAClient kernel
    UMAClient       -> physics (untouched by semantic logic)

Quick start:
    from uma import Config, UMAClient
    from uma.semantic import SemanticEngine

    client = UMAClient(Config())
    client.initialize(psi0)

    engine = SemanticEngine(z_target=z_target)
    result = engine.run(client, n_steps=200)
    print(result.summary())

Text input via Engine3 bridge:
    from uma.semantic import string_to_observation
    obs, y = string_to_observation("your input text", dim=client.projection.real_dim)
    result = engine.run(client, n_steps=200, observations=[(obs, y)])
"""
from uma.semantic.constants import (
    SQRT2, SQRT_E, DELTA_S, DELTA_S_SQ, INV_DELTA_S_SQ,
    C1_SILVER, C2_SILVER, SILVER_ANGLE,
    Z_SEED_REAL, Z_SEED_IMAG,
    engine3_complex_state, engine3_E,
    silver_E_target, silver_dz_dt_floor, silver_field_scale,
    CALIBRATED_E_TARGET, CALIBRATED_DZ_DT_FLOOR, CALIBRATED_FIELD_SCALE,
    CALIBRATED_H_TARGET, CALIBRATED_H_STD,
    CALIBRATED_DH_DT_FLOOR, CALIBRATED_DH_DT_P25,
)
from uma.semantic.constraints import (
    EqualityConstraint, LinearConstraint, BallConstraint,
    QuadraticConstraint, ConstraintSet,
)
from uma.semantic.engine import (
    SemanticEngine, SemanticEngineConfig, SemanticEngineResult,
    string_to_observation, tokenize_to_binary_weight,
)
from uma.semantic.executor import UMAExecutor, ExecutorResult
from uma.semantic.friction import (
    SemanticFriction, SemanticFrictionConfig, FrictionRecord,
)
from uma.semantic.inarticulation import (
    Inarticulator, NullInarticulator, ProjectionInarticulator,
    ProductionMetrics, classify_stage,
)
from uma.semantic.ir import IRNode, UMA_IR

__all__ = [
    "SQRT2", "SQRT_E", "DELTA_S", "DELTA_S_SQ", "INV_DELTA_S_SQ",
    "C1_SILVER", "C2_SILVER", "SILVER_ANGLE",
    "Z_SEED_REAL", "Z_SEED_IMAG",
    "engine3_complex_state", "engine3_E",
    "silver_E_target", "silver_dz_dt_floor", "silver_field_scale",
    "CALIBRATED_E_TARGET", "CALIBRATED_DZ_DT_FLOOR", "CALIBRATED_FIELD_SCALE",
    "CALIBRATED_H_TARGET", "CALIBRATED_H_STD",
    "CALIBRATED_DH_DT_FLOOR", "CALIBRATED_DH_DT_P25",
    "EqualityConstraint", "LinearConstraint", "BallConstraint",
    "QuadraticConstraint", "ConstraintSet",
    "SemanticEngine", "SemanticEngineConfig", "SemanticEngineResult",
    "string_to_observation", "tokenize_to_binary_weight",
    "UMAExecutor", "ExecutorResult",
    "SemanticFriction", "SemanticFrictionConfig", "FrictionRecord",
    "Inarticulator", "NullInarticulator", "ProjectionInarticulator",
    "ProductionMetrics", "classify_stage",
    "IRNode", "UMA_IR",
]
