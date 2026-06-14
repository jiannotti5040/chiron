"""
uma — Universal Manifold Architecture.

A stochastic metriplectic field engine. Inside-out geometry from spherical
Bessel zeros, GENERIC dynamics with exact MSR response, projection-based
state filtering, and a tensor bridge that ties the field's stress-energy
to the linearized Einstein tensor.

Top-level objects:
    Config          configuration dataclass
    UMAClient       orchestrates projection / dynamics / filter
    UMAPipeline     end-to-end runner (sphere -> field -> closure)
    SemanticEngine  intent compiler -> UMA_IR -> kernel
"""
from uma.config import Config, GridConfig, GENERICConfig, FilterConfig
from uma.client import UMAClient

__all__ = ["Config", "GridConfig", "GENERICConfig", "FilterConfig", "UMAClient"]

__version__ = "0.3.0"
