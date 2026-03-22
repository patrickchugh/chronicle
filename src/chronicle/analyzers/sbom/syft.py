"""Syft SBOM adapter (Principle V: Tool Agnosticism).

Invokes Anchore Syft to generate SBOM and transforms output to CanonicalSBOM.
https://github.com/anchore/syft
"""

import json
import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from chronicle.analyzers.base import ToolExecutionError, ToolNotAvailableError
from chronicle.analyzers.dependency import DirectDependencyResolver
from chronicle.analyzers.sbom.base import SBOMAdapter
from chronicle.models.canonical import CanonicalPackage, CanonicalSBOM, SBOMSource

logger = logging.getLogger(__name__)


# Mapping from Syft package types to canonical ecosystem names
SYFT_TYPE_TO_ECOSYSTEM: dict[str, str] = {
    "npm": "npm",
    "python": "pypi",
    "pip": "pypi",
    "go-module": "go",
    "gomod": "go",
    "java-archive": "maven",
    "maven": "maven",
    "gem": "rubygems",
    "cargo": "cargo",
    "rust-crate": "cargo",
    "nuget": "nuget",
    "dotnet": "nuget",
    "deb": "deb",
    "rpm": "rpm",
    "apk": "apk",
    "cocoapods": "cocoapods",
    "swift": "swift",
    "composer": "composer",
    "php-composer": "composer",
    "hackage": "hackage",
    "hex": "hex",
    "pub": "pub",
    "conan": "conan",
    "cpan": "cpan",
    "cran": "cran",
}


class SyftAdapter(SBOMAdapter):
    """SBOM adapter using Anchore Syft.

    Syft is a CLI tool that generates SBOMs from container images and filesystems.
    It supports many package ecosystems and outputs in various formats.

    This adapter:
    1. Invokes `syft <path> -o json` to get JSON output
    2. Parses the JSON to extract package artifacts
    3. Cross-references with DirectDependencyResolver to mark direct dependencies
    4. Transforms to CanonicalSBOM format
    """

    def __init__(
        self,
        name: str = "syft",
        dependency_resolver: DirectDependencyResolver | None = None,
    ) -> None:
        """Initialize Syft adapter.

        Args:
            name: Adapter name
            dependency_resolver: Optional resolver for marking direct dependencies
        """
        super().__init__(name=name)
        self._dependency_resolver = dependency_resolver

    def check_available(self) -> bool:
        """Check if Syft is installed and accessible."""
        try:
            result = subprocess.run(
                ["syft", "version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False

    def get_version(self) -> str | None:
        """Get Syft version string."""
        try:
            result = subprocess.run(
                ["syft", "version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                # Output format: "syft x.y.z" or just version info
                output = result.stdout.strip()
                # Try to extract version from various output formats
                for line in output.split("\n"):
                    if "version" in line.lower() or line.strip().startswith("syft"):
                        parts = line.split()
                        if len(parts) >= 2:
                            return parts[-1].strip()
                # Fallback: return first line
                return output.split("\n")[0].strip() if output else None
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return None

    def execute(self, input_path: Path) -> CanonicalSBOM:
        """Generate SBOM for the given path using Syft.

        Args:
            input_path: Repository or directory path to scan

        Returns:
            CanonicalSBOM with all detected packages

        Raises:
            ToolNotAvailableError: If Syft is not installed
            ToolExecutionError: If Syft execution fails
        """
        if not self.check_available():
            raise ToolNotAvailableError(
                self.name,
                "Syft is not installed. Install with: curl -sSfL "
                "https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s",
            )

        # Run syft with JSON output
        try:
            logger.info("Running Syft on %s", input_path)
            result = subprocess.run(
                [
                    "syft",
                    str(input_path),
                    "-o",
                    "json",
                    "--quiet",  # Suppress progress output
                ],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout for large repos
            )
        except subprocess.TimeoutExpired as e:
            raise ToolExecutionError(
                self.name,
                f"Syft timed out after 300 seconds scanning {input_path}",
                stderr=str(e),
            )
        except OSError as e:
            raise ToolExecutionError(
                self.name,
                f"Failed to execute Syft: {e}",
            )

        if result.returncode != 0:
            raise ToolExecutionError(
                self.name,
                "Syft scan failed",
                exit_code=result.returncode,
                stderr=result.stderr,
            )

        # Parse JSON output
        try:
            syft_output = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise ToolExecutionError(
                self.name,
                f"Failed to parse Syft JSON output: {e}",
                stderr=result.stderr,
            )

        # Resolve direct dependencies if resolver provided
        if self._dependency_resolver:
            self._dependency_resolver.resolve_from_directory(input_path)

        # Transform to canonical format
        return self._transform_to_canonical(syft_output, input_path)

    def get_supported_ecosystems(self) -> list[str]:
        """Get list of package ecosystems Syft supports."""
        return sorted(set(SYFT_TYPE_TO_ECOSYSTEM.values()))

    def _transform_to_canonical(
        self,
        syft_output: dict[str, Any],
        input_path: Path,
    ) -> CanonicalSBOM:
        """Transform Syft JSON output to CanonicalSBOM.

        Args:
            syft_output: Parsed Syft JSON output
            input_path: Original scan target path

        Returns:
            CanonicalSBOM with transformed package data
        """
        # Extract source metadata
        source_info = SBOMSource(
            tool="syft",
            tool_version=self.version or "unknown",
            scanned_at=datetime.now(UTC),
            target=str(input_path),
        )

        # Create SBOM
        sbom = CanonicalSBOM(source=source_info)

        # Extract packages from artifacts
        artifacts = syft_output.get("artifacts", [])
        logger.debug("Found %d artifacts in Syft output", len(artifacts))

        for artifact in artifacts:
            package = self._transform_artifact(artifact)
            if package:
                sbom.add_package(package)

        logger.info(
            "Transformed %d packages (%d direct, %s ecosystems)",
            sbom.package_count,
            sbom.direct_package_count,
            len(sbom.get_unique_ecosystems()),
        )

        return sbom

    def _transform_artifact(self, artifact: dict[str, Any]) -> CanonicalPackage | None:
        """Transform a single Syft artifact to CanonicalPackage.

        Args:
            artifact: Single artifact from Syft output

        Returns:
            CanonicalPackage or None if artifact cannot be transformed
        """
        name = artifact.get("name")
        if not name:
            return None

        # Get package type and map to ecosystem
        pkg_type = artifact.get("type", "").lower()
        ecosystem = SYFT_TYPE_TO_ECOSYSTEM.get(pkg_type, pkg_type)

        if not ecosystem:
            logger.debug("Unknown package type: %s for %s", pkg_type, name)
            ecosystem = "unknown"

        # Extract version
        version = artifact.get("version")

        # Extract license (Syft provides licenses as array)
        license_str: str | None = None
        licenses = artifact.get("licenses", [])
        if licenses:
            if isinstance(licenses, list):
                # Join multiple licenses with AND
                license_parts = []
                for lic in licenses:
                    if isinstance(lic, dict):
                        license_parts.append(lic.get("value", str(lic)))
                    else:
                        license_parts.append(str(lic))
                license_str = " AND ".join(filter(None, license_parts))
            else:
                license_str = str(licenses)

        # Extract PURL
        purl = artifact.get("purl")

        # Extract source file location
        source_file: str | None = None
        locations = artifact.get("locations", [])
        if locations and isinstance(locations, list):
            first_loc = locations[0]
            if isinstance(first_loc, dict):
                source_file = first_loc.get("path")
            elif isinstance(first_loc, str):
                source_file = first_loc

        # Check if this is a direct dependency
        is_direct = False
        if self._dependency_resolver:
            is_direct = self._dependency_resolver.is_direct(name, ecosystem)

        return CanonicalPackage(
            name=name,
            ecosystem=ecosystem,
            version=version,
            license=license_str,
            source_file=source_file,
            purl=purl,
            is_direct=is_direct,
        )
