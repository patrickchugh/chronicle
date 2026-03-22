"""Abstract base class for SBOM tool adapters.

All SBOM adapters MUST implement this interface and output CanonicalSBOM format.
"""

from abc import abstractmethod
from pathlib import Path

from chronicle.analyzers.base import ToolAdapter
from chronicle.models.canonical import CanonicalSBOM


class SBOMAdapter(ToolAdapter[CanonicalSBOM]):
    """Abstract interface for SBOM generation tools.

    Implementations:
    - SyftAdapter: Uses Anchore Syft for SBOM generation
    - TrivyAdapter: Uses Aqua Trivy for SBOM generation (future)

    All implementations MUST output CanonicalSBOM format.
    """

    def __init__(self, name: str) -> None:
        """Initialize SBOM adapter.

        Args:
            name: Tool identifier (e.g., "syft", "trivy")
        """
        super().__init__(name=name, capability="sbom")

    @abstractmethod
    def execute(self, input_path: Path) -> CanonicalSBOM:
        """Generate SBOM for the given path.

        Args:
            input_path: Repository or directory path to scan

        Returns:
            CanonicalSBOM with all detected packages
        """
        pass

    @abstractmethod
    def get_supported_ecosystems(self) -> list[str]:
        """Get list of package ecosystems this tool supports.

        Returns:
            List of ecosystem names (e.g., ["npm", "pypi", "go", "maven"])
        """
        pass
