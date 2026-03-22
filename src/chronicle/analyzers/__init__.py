"""chronicle analyzers - deterministic analysis tools.

This module contains all deterministic analyzers that run BEFORE any LLM invocation
(Principle I: Deterministic-First).

Analyzers:
- AST Parser: Multi-language source code analysis via tree-sitter
- Dependency Parser: Dependency file parsing (package.json, requirements.txt, etc.)
- SBOM Adapters: SBOM generation via Syft or other tools
- Diagram Adapters: Architecture diagram generation via Terravision or other tools
"""

from chronicle.analyzers.ast_parser import ASTParser
from chronicle.analyzers.base import (
    ToolAdapter,
    ToolExecutionError,
    ToolNotAvailableError,
)
from chronicle.analyzers.dependency import DependencyParser, DirectDependencyResolver
from chronicle.analyzers.diagrams import DiagramGenerator, TerravisionAdapter
from chronicle.analyzers.registry import ToolRegistry, get_registry, reset_registry
from chronicle.analyzers.sbom import SBOMAdapter, SyftAdapter

__all__ = [
    "ASTParser",
    "DependencyParser",
    "DiagramGenerator",
    "DirectDependencyResolver",
    "SBOMAdapter",
    "SyftAdapter",
    "TerravisionAdapter",
    "ToolAdapter",
    "ToolExecutionError",
    "ToolNotAvailableError",
    "ToolRegistry",
    "get_registry",
    "reset_registry",
    "setup_default_adapters",
]


def setup_default_adapters(registry: ToolRegistry | None = None) -> ToolRegistry:
    """Register all default tool adapters.

    Args:
        registry: Registry to populate (uses global if None)

    Returns:
        Populated ToolRegistry
    """
    if registry is None:
        registry = get_registry()

    # Register SBOM adapters
    registry.register_sbom_adapter("syft", SyftAdapter, is_default=True)

    # Register diagram adapters
    registry.register_diagram_adapter(
        "terravision", TerravisionAdapter, is_default=True
    )

    return registry
