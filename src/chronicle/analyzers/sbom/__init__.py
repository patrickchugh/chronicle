"""SBOM tool adapters (Principle V: Tool Agnosticism).

All SBOM adapters output CanonicalSBOM format.
"""

from chronicle.analyzers.sbom.base import SBOMAdapter
from chronicle.analyzers.sbom.syft import SyftAdapter

__all__ = ["SBOMAdapter", "SyftAdapter"]
