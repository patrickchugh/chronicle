"""Abstract base class for tool adapters (Principle V: Tool Agnosticism).

All tool adapters MUST implement this interface. Each adapter:
1. Invokes the external tool with appropriate arguments
2. Parses tool-specific output (JSON, text, etc.)
3. Transforms to canonical format (CanonicalSBOM, CanonicalArchitecture, etc.)
4. Handles tool-specific errors gracefully
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Generic, TypeVar

# Generic type for the canonical output format
T = TypeVar("T")


class ToolAdapter(ABC, Generic[T]):
    """Abstract interface for pluggable analysis tools.

    Each adapter transforms tool-specific output to canonical format.
    Adding a new tool MUST NOT require changes outside the adapter module.

    Type Parameters:
        T: The canonical output type (CanonicalSBOM, CanonicalArchitecture, etc.)

    Attributes:
        name: Tool identifier (e.g., "syft", "trivy", "terravision")
        capability: Capability type ("sbom", "diagram", "ast")
        version: Tool version if available
    """

    def __init__(self, name: str, capability: str) -> None:
        """Initialize the adapter.

        Args:
            name: Tool identifier
            capability: Capability type
        """
        self.name = name
        self.capability = capability
        self._version: str | None = None

    @property
    def version(self) -> str | None:
        """Get the tool version (cached after first check)."""
        if self._version is None:
            self._version = self.get_version()
        return self._version

    @abstractmethod
    def check_available(self) -> bool:
        """Verify tool is installed and accessible.

        Returns:
            True if tool is available, False otherwise
        """
        pass

    @abstractmethod
    def get_version(self) -> str | None:
        """Return tool version string.

        Returns:
            Version string if available, None otherwise
        """
        pass

    @abstractmethod
    def execute(self, input_path: Path) -> T:
        """Run tool and return canonical format output.

        This method MUST:
        1. Invoke the external tool
        2. Parse tool-specific output
        3. Transform to canonical format
        4. Handle errors gracefully

        Args:
            input_path: Path to analyze (repository root, file, etc.)

        Returns:
            Canonical format output (CanonicalSBOM, CanonicalArchitecture, etc.)

        Raises:
            ToolNotAvailableError: If tool is not installed
            ToolExecutionError: If tool execution fails
        """
        pass

    def get_metadata(self) -> dict[str, Any]:
        """Get adapter metadata for logging and debugging.

        Returns:
            Dictionary with adapter info
        """
        return {
            "name": self.name,
            "capability": self.capability,
            "version": self.version,
            "available": self.check_available(),
        }


class ToolNotAvailableError(Exception):
    """Raised when a required tool is not installed or accessible."""

    def __init__(self, tool_name: str, message: str | None = None) -> None:
        self.tool_name = tool_name
        self.message = message or f"Tool not available: {tool_name}"
        super().__init__(self.message)


class ToolExecutionError(Exception):
    """Raised when a tool execution fails."""

    def __init__(
        self,
        tool_name: str,
        message: str,
        exit_code: int | None = None,
        stderr: str | None = None,
    ) -> None:
        self.tool_name = tool_name
        self.exit_code = exit_code
        self.stderr = stderr
        full_message = f"Tool execution failed: {tool_name} - {message}"
        if exit_code is not None:
            full_message += f" (exit code: {exit_code})"
        super().__init__(full_message)
