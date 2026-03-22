"""Abstract base class for diagram generation tool adapters.

All diagram adapters MUST implement this interface and output CanonicalArchitecture format.
"""

from abc import abstractmethod
from pathlib import Path

from chronicle.analyzers.base import ToolAdapter
from chronicle.models.canonical import CanonicalArchitecture


class DiagramGenerator(ToolAdapter[CanonicalArchitecture]):
    """Abstract interface for architecture diagram generation tools.

    Implementations:
    - TerravisionAdapter: Uses Terravision for Terraform diagrams

    All implementations MUST output CanonicalArchitecture format.
    Multi-cloud support: implementations MUST NOT assume a single cloud provider.
    """

    def __init__(self, name: str) -> None:
        """Initialize diagram generator adapter.

        Args:
            name: Tool identifier (e.g., "terravision")
        """
        super().__init__(name=name, capability="diagram")

    @abstractmethod
    def execute(self, input_path: Path) -> CanonicalArchitecture:
        """Generate architecture diagram for the given path.

        Args:
            input_path: Repository or directory path containing infrastructure files

        Returns:
            CanonicalArchitecture with graph structure and optional rendered image
        """
        pass

    @abstractmethod
    def get_supported_sources(self) -> list[str]:
        """Get list of infrastructure source types this tool supports.

        Returns:
            List of source types (e.g., ["terraform", "cloudformation"])
        """
        pass

    @abstractmethod
    def get_supported_providers(self) -> list[str]:
        """Get list of cloud providers this tool supports.

        Returns:
            List of provider names (e.g., ["aws", "gcp", "azure"])
        """
        pass
