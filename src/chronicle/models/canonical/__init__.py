"""Canonical data formats for tool agnosticism (Principle V).

These are the standard internal formats that all tool adapters MUST produce.
The rest of chronicle only works with these canonical formats, never with
tool-specific output. This enables true tool swappability.

Canonical formats:
- CanonicalSBOM: Standard SBOM format from any SBOM tool
- CanonicalArchitecture: Standard architecture graph from any diagram tool
- CanonicalAST: Standard AST format from any parser
- ModuleSummary: Flow-based module documentation
"""

from chronicle.models.canonical.architecture import (
    ArchitectureSource,
    CanonicalArchitecture,
    CanonicalGraph,
    NodeMetadata,
    RenderedImage,
)
from chronicle.models.canonical.ast import (
    ASTSource,
    CanonicalAST,
    CanonicalClass,
    CanonicalEntryPoint,
    CanonicalFunction,
    CanonicalModule,
)
from chronicle.models.canonical.module import (
    EntryPoint,
    ExternalIntegration,
    ImportGraph,
    ModuleFlowDiagram,
    ModuleSummary,
)
from chronicle.models.canonical.compressed import (
    CompressedCodebase,
    HolisticOverview,
)
from chronicle.models.canonical.sbom import (
    CanonicalPackage,
    CanonicalSBOM,
    SBOMSource,
)

__all__ = [
    # SBOM
    "CanonicalSBOM",
    "CanonicalPackage",
    "SBOMSource",
    # Architecture
    "CanonicalArchitecture",
    "CanonicalGraph",
    "NodeMetadata",
    "RenderedImage",
    "ArchitectureSource",
    # AST
    "CanonicalAST",
    "CanonicalModule",
    "CanonicalClass",
    "CanonicalFunction",
    "CanonicalEntryPoint",
    "ASTSource",
    # Flow-based documentation
    "ModuleSummary",
    "EntryPoint",
    "ExternalIntegration",
    "ImportGraph",
    "ModuleFlowDiagram",
    # Compressed codebase/Holistic overview
    "CompressedCodebase",
    "HolisticOverview",
]
