"""
UMAExecutor -- schedules and runs a UMA_IR graph against a UMAClient kernel.

This is the bridge layer:
    SemanticEngine (compiler/planner)
        |  emits
    UMA_IR
        |  consumed by
    UMAExecutor          <-- THIS FILE
        |  drives
    UMAClient (kernel)

The executor knows nothing about semantic intent. It only:
    1. Iterates the IR schedule
    2. Dispatches each node to the correct kernel call
    3. Records friction at every checkpoint node
    4. Returns a structured result

No semantic logic leaks into the kernel.

NOTE: This rebuild adapts the canonical executor to the single-
representation FieldPosterior. Behaviour is identical to the canonical
multi-rep executor on the 'full' representation.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

from uma.core.state import FieldPosterior
from uma.semantic.ir import UMA_IR, IRNode
from uma.semantic.friction import SemanticFriction, FrictionRecord
from uma.semantic.constraints import ConstraintSet
from uma.semantic.inarticulation import (
    Inarticulator, NullInarticulator, ProductionMetrics,
)


@dataclass
class ExecutorResult:
    """Raw output from UMAExecutor.run()."""
    is_closed: bool
    closure_node: Optional[str]
    friction_records: List[FrictionRecord]
    friction_summary: Dict[str, Any]
    final_posterior: FieldPosterior
    z_final: np.ndarray
    production_metrics: ProductionMetrics
    nodes_executed: int


class UMAExecutor:
    """
    Executes a UMA_IR schedule against a live UMAClient.
    Stateless across runs -- all state lives in the client.
    """

    def __init__(
        self,
        friction: SemanticFriction,
        inarticulator: Optional[Inarticulator] = None,
        stop_on_closure: bool = True,
        verbose: bool = False,
    ):
        self.friction = friction
        self.inarticulator = inarticulator or NullInarticulator()
        self.stop_on_closure = stop_on_closure
        self.verbose = verbose

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"[UMAExecutor] {msg}")

    def run(self, ir: UMA_IR, client) -> ExecutorResult:
        """Execute ir.schedule against client. Client must be initialized."""
        posterior = client.filter.posterior
        self.friction.reset(posterior)

        z_target = ir.metadata.get("z_target", np.zeros(posterior.dim))
        node_map = {n.node_id: n for n in ir.nodes}

        last_constraint_report: Dict[str, Any] = {
            "converged": True, "final_total_violation": 0.0,
        }
        closure_node: Optional[str] = None

        nodes_executed = 0
        t = client.t

        for node_id in ir.schedule:
            node: IRNode = node_map[node_id]
            nodes_executed += 1

            if node.kind == "evolve":
                dt = node.payload.get("dt", None)
                client.evolve(dt=dt)
                t = client.t

            elif node.kind == "observe":
                obs = node.payload["observation"]
                y = node.payload["y"]
                client.observe(obs, y)

            elif node.kind == "constrain":
                cs: ConstraintSet = node.payload["constraint_set"]
                z = client.filter.posterior.mean.copy()
                z_anchored, report = cs.apply(z)
                last_constraint_report = report
                client.filter.posterior = FieldPosterior(
                    mean=z_anchored, cov=client.filter.posterior.cov,
                )
                client.psi = client.projection.lift(z_anchored)

            elif node.kind == "checkpoint":
                rec = self.friction.update(client.filter.posterior, t)
                self._log(
                    f"{node_id}  t={t:.3f}  "
                    f"H={rec.H:.4f}  dH/dt={rec.dH_dt:.4e}  "
                    f"friction={rec.friction:.4f}  closed={rec.closed}"
                )
                if self.stop_on_closure and rec.closed:
                    closure_node = node_id
                    self._log(f"Closure (Omega) at {node_id}")
                    break
            else:
                self._log(f"Unknown IR node kind: {node.kind!r}")

        posterior = client.filter.posterior
        z_final = posterior.mean.copy()
        friction_summary = self.friction.summary()

        production_metrics = self.inarticulator.translate(
            z_omega=z_final,
            posterior=posterior,
            z_target=z_target,
            friction_summary=friction_summary,
            constraint_report=last_constraint_report,
        )

        return ExecutorResult(
            is_closed=self.friction.is_closed,
            closure_node=closure_node,
            friction_records=self.friction.records,
            friction_summary=friction_summary,
            final_posterior=posterior,
            z_final=z_final,
            production_metrics=production_metrics,
            nodes_executed=nodes_executed,
        )
