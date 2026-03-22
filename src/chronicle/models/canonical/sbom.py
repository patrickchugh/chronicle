"""Canonical SBOM format (Principle V: Tool Agnosticism).

Standard SBOM format produced by all SBOM tool adapters (Syft, Trivy, etc.).
The rest of the codebase MUST only consume this format, never tool-specific output.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class SBOMSource:
    """Metadata about the SBOM generation.

    Attributes:
        tool: Tool that generated this (e.g., "syft", "trivy")
        tool_version: Version of the tool
        scanned_at: When the scan was performed
        target: What was scanned (path or image name)
    """

    tool: str
    tool_version: str
    scanned_at: datetime
    target: str

    def __post_init__(self) -> None:
        """Ensure timestamp is timezone-aware UTC."""
        if self.scanned_at.tzinfo is None:
            self.scanned_at = self.scanned_at.replace(tzinfo=UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tool": self.tool,
            "tool_version": self.tool_version,
            "scanned_at": self.scanned_at.isoformat(),
            "target": self.target,
        }


@dataclass
class CanonicalPackage:
    """Standard package representation across all SBOM tools.

    Attributes:
        name: Package name
        ecosystem: Package ecosystem (npm, pypi, go, maven, cargo, etc.)
        version: Version string (if available)
        license: SPDX license identifier (if available)
        source_file: File where dependency was declared (if available)
        purl: Package URL - standardized identifier (if available)
        is_direct: Whether this is a direct dependency (declared in manifest) vs transitive
    """

    name: str
    ecosystem: str
    version: str | None = None
    license: str | None = None
    source_file: str | None = None
    purl: str | None = None
    is_direct: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result: dict[str, Any] = {
            "name": self.name,
            "ecosystem": self.ecosystem,
        }
        if self.version:
            result["version"] = self.version
        if self.license:
            result["license"] = self.license
        if self.source_file:
            result["source_file"] = self.source_file
        if self.purl:
            result["purl"] = self.purl
        if self.is_direct:
            result["is_direct"] = self.is_direct
        return result


@dataclass
class CanonicalSBOM:
    """Standard SBOM format produced by all SBOM tool adapters.

    This is the canonical internal format that the rest of chronicle consumes.
    Tool adapters (Syft, Trivy, etc.) MUST transform their output into this format.

    Attributes:
        packages: All detected packages
        source: Metadata about the scan
    """

    packages: list[CanonicalPackage] = field(default_factory=list)
    source: SBOMSource | None = None

    def add_package(self, package: CanonicalPackage) -> None:
        """Add a package to the SBOM."""
        self.packages.append(package)

    def get_packages_by_ecosystem(self, ecosystem: str) -> list[CanonicalPackage]:
        """Get all packages for a specific ecosystem."""
        return [p for p in self.packages if p.ecosystem == ecosystem]

    def get_unique_ecosystems(self) -> list[str]:
        """Get list of unique ecosystems in this SBOM."""
        return sorted(set(p.ecosystem for p in self.packages))

    def get_direct_packages(self) -> list[CanonicalPackage]:
        """Get only direct dependencies (declared in manifest files).

        Returns:
            List of packages where is_direct=True
        """
        return [p for p in self.packages if p.is_direct]

    def get_transitive_packages(self) -> list[CanonicalPackage]:
        """Get only transitive dependencies (pulled in automatically).

        Returns:
            List of packages where is_direct=False
        """
        return [p for p in self.packages if not p.is_direct]

    @property
    def package_count(self) -> int:
        """Return total number of packages."""
        return len(self.packages)

    @property
    def direct_package_count(self) -> int:
        """Return number of direct dependencies."""
        return len(self.get_direct_packages())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result: dict[str, Any] = {
            "packages": [p.to_dict() for p in self.packages],
            "package_count": self.package_count,
            "direct_package_count": self.direct_package_count,
            "ecosystems": self.get_unique_ecosystems(),
        }
        if self.source:
            result["source"] = self.source.to_dict()
        return result
