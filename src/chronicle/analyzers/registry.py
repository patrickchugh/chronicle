"""Tool registry for pluggable analyzers (Principle V: Tool Agnosticism).

The registry maintains available tool adapters for each capability.
Tools are configured in YAML config, not hardcoded.
"""

from typing import Any

from chronicle.analyzers.base import ToolNotAvailableError
from chronicle.analyzers.diagrams.base import DiagramGenerator
from chronicle.analyzers.sbom.base import SBOMAdapter


class ToolRegistry:
    """Registry of available tool adapters for each capability.

    Configuration example:
        tools:
          sbom: syft          # → uses SyftAdapter → outputs CanonicalSBOM
          diagrams: terravision  # → uses TerravisionAdapter → outputs CanonicalArchitecture

    Adding a new tool:
        1. Implement the appropriate adapter interface (e.g., SBOMAdapter)
        2. Transform tool output to canonical format
        3. Register in ToolRegistry
        4. No changes needed to rest of codebase

    Attributes:
        sbom_adapters: Registered SBOM adapters by name
        diagram_adapters: Registered diagram adapters by name
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._sbom_adapters: dict[str, type[SBOMAdapter]] = {}
        self._diagram_adapters: dict[str, type[DiagramGenerator]] = {}
        self._default_sbom: str | None = None
        self._default_diagram: str | None = None

    # =========================================================================
    # Registration
    # =========================================================================

    def register_sbom_adapter(
        self,
        name: str,
        adapter_class: type[SBOMAdapter],
        is_default: bool = False,
    ) -> None:
        """Register an SBOM adapter.

        Args:
            name: Tool identifier (e.g., "syft")
            adapter_class: Adapter class to register
            is_default: Whether this is the default SBOM tool
        """
        self._sbom_adapters[name] = adapter_class
        if is_default:
            self._default_sbom = name

    def register_diagram_adapter(
        self,
        name: str,
        adapter_class: type[DiagramGenerator],
        is_default: bool = False,
    ) -> None:
        """Register a diagram generator adapter.

        Args:
            name: Tool identifier (e.g., "terravision")
            adapter_class: Adapter class to register
            is_default: Whether this is the default diagram tool
        """
        self._diagram_adapters[name] = adapter_class
        if is_default:
            self._default_diagram = name

    # =========================================================================
    # Retrieval
    # =========================================================================

    def get_sbom_adapter(self, name: str | None = None) -> SBOMAdapter:
        """Get an SBOM adapter instance.

        Args:
            name: Tool name (uses default if None)

        Returns:
            Instantiated SBOM adapter

        Raises:
            ToolNotAvailableError: If tool is not registered
        """
        tool_name = name or self._default_sbom
        if tool_name is None:
            raise ToolNotAvailableError("sbom", "No SBOM tool configured")

        if tool_name not in self._sbom_adapters:
            available = list(self._sbom_adapters.keys())
            raise ToolNotAvailableError(
                tool_name,
                f"SBOM tool '{tool_name}' not registered. Available: {available}",
            )

        return self._sbom_adapters[tool_name](tool_name)

    def get_diagram_adapter(self, name: str | None = None) -> DiagramGenerator:
        """Get a diagram generator adapter instance.

        Args:
            name: Tool name (uses default if None)

        Returns:
            Instantiated diagram adapter

        Raises:
            ToolNotAvailableError: If tool is not registered
        """
        tool_name = name or self._default_diagram
        if tool_name is None:
            raise ToolNotAvailableError("diagram", "No diagram tool configured")

        if tool_name not in self._diagram_adapters:
            available = list(self._diagram_adapters.keys())
            raise ToolNotAvailableError(
                tool_name,
                f"Diagram tool '{tool_name}' not registered. Available: {available}",
            )

        return self._diagram_adapters[tool_name](tool_name)

    # =========================================================================
    # Introspection
    # =========================================================================

    def list_sbom_adapters(self) -> list[str]:
        """Get list of registered SBOM adapter names."""
        return list(self._sbom_adapters.keys())

    def list_diagram_adapters(self) -> list[str]:
        """Get list of registered diagram adapter names."""
        return list(self._diagram_adapters.keys())

    def get_available_tools(self) -> dict[str, list[str]]:
        """Get all available tools by capability.

        Returns:
            Dictionary mapping capability to list of tool names
        """
        return {
            "sbom": self.list_sbom_adapters(),
            "diagram": self.list_diagram_adapters(),
        }

    def check_tool_availability(self) -> dict[str, dict[str, bool]]:
        """Check availability of all registered tools.

        Returns:
            Dictionary mapping capability → tool → availability
        """
        result: dict[str, dict[str, bool]] = {"sbom": {}, "diagram": {}}

        for name, adapter_class in self._sbom_adapters.items():
            try:
                adapter = adapter_class(name)
                result["sbom"][name] = adapter.check_available()
            except Exception:
                result["sbom"][name] = False

        for name, adapter_class in self._diagram_adapters.items():
            try:
                adapter = adapter_class(name)
                result["diagram"][name] = adapter.check_available()
            except Exception:
                result["diagram"][name] = False

        return result

    def get_metadata(self) -> dict[str, Any]:
        """Get registry metadata for logging and debugging."""
        return {
            "sbom_adapters": self.list_sbom_adapters(),
            "diagram_adapters": self.list_diagram_adapters(),
            "default_sbom": self._default_sbom,
            "default_diagram": self._default_diagram,
        }


# Global registry instance
_registry: ToolRegistry | None = None


def get_registry() -> ToolRegistry:
    """Get the global tool registry instance.

    Returns:
        Global ToolRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def reset_registry() -> None:
    """Reset the global registry (primarily for testing)."""
    global _registry
    _registry = None
