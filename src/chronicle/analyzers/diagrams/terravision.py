"""Terravision diagram adapter (Principle V: Tool Agnosticism).

Invokes Terravision to generate architecture diagrams from Terraform files
and transforms output to CanonicalArchitecture.
https://github.com/patrickchugh/terravision

Per Principle III (Preflight Validation), Terravision must be available
before analysis begins. No fallback parsing is provided - run `chronicle check`
to verify dependencies.
"""

import json
import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from chronicle.analyzers.base import ToolExecutionError, ToolNotAvailableError
from chronicle.analyzers.diagrams.base import DiagramGenerator
from chronicle.models.canonical import (
    ArchitectureSource,
    CanonicalArchitecture,
    CanonicalGraph,
    NodeMetadata,
    RenderedImage,
)

logger = logging.getLogger(__name__)


# Resource type prefix to cloud provider mapping
RESOURCE_PREFIX_TO_PROVIDER: dict[str, str] = {
    "aws_": "aws",
    "google_": "gcp",
    "azurerm_": "azure",
    "azuread_": "azure",
    "kubernetes_": "kubernetes",
    "helm_": "kubernetes",
    "null_": "null",
    "local_": "local",
    "random_": "random",
    "tls_": "tls",
    "archive_": "archive",
    "time_": "time",
    "external_": "external",
    "oci_": "oci",
    "digitalocean_": "digitalocean",
    "alicloud_": "alicloud",
    "vsphere_": "vsphere",
    "openstack_": "openstack",
    "cloudflare_": "cloudflare",
}


class TerravisionAdapter(DiagramGenerator):
    """Diagram adapter using Terravision for Terraform.

    Terravision generates architecture diagrams from Terraform configuration files.
    It parses HCL to extract resource definitions and dependencies.

    This adapter:
    1. Validates Terravision availability (raises ToolNotAvailableError if missing)
    2. Invokes Terravision to extract resource nodes and connections
    3. Optionally generates rendered PNG/SVG
    4. Transforms to CanonicalArchitecture format

    Per Principle III, no fallback parsing is provided. Use `chronicle check` to
    verify Terravision is installed before running analysis.
    """

    def __init__(self, name: str = "terravision", use_debug: bool = True) -> None:
        """Initialize Terravision adapter.

        Args:
            name: Adapter name
            use_debug: If True, run with --debug to capture rich metadata from tfdata.json
        """
        super().__init__(name=name)
        self.use_debug = use_debug

    def check_available(self) -> bool:
        """Check if Terravision is installed and accessible."""
        try:
            result = subprocess.run(
                ["terravision", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False

    def get_version(self) -> str | None:
        """Get Terravision version string."""
        try:
            result = subprocess.run(
                ["terravision", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                output = result.stdout.strip()
                # Extract version from output
                if output:
                    return output.split("\n")[0].strip()
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return None

    def execute(self, input_path: Path) -> CanonicalArchitecture:
        """Generate architecture diagram for the given path.

        Args:
            input_path: Repository or directory path containing Terraform files

        Returns:
            CanonicalArchitecture with graph structure and optional rendered image

        Raises:
            ToolNotAvailableError: If Terravision is not installed
            ToolExecutionError: If execution fails
        """
        # Find Terraform files
        tf_files = self._find_terraform_files(input_path)
        if not tf_files:
            logger.warning("No Terraform files found in %s", input_path)
            return CanonicalArchitecture(
                source=ArchitectureSource(
                    tool="terravision",
                    tool_version=self.version or "unknown",
                    generated_at=datetime.now(UTC),
                    source_files=[],
                    source_type="terraform",
                )
            )

        # Per Principle III: Preflight Validation - Terravision must be available
        if not self.check_available():
            raise ToolNotAvailableError(
                self.name,
                "Terravision is not installed. Run `chronicle check` to verify dependencies. "
                "Install from: https://github.com/patrickchugh/terravision",
            )

        return self._execute_terravision(input_path, tf_files)

    def get_supported_sources(self) -> list[str]:
        """Get list of infrastructure source types this tool supports."""
        return ["terraform"]

    def get_supported_providers(self) -> list[str]:
        """Get list of cloud providers this tool supports."""
        return ["aws", "gcp", "azure", "kubernetes"]

    def _find_terraform_files(self, directory: Path) -> list[Path]:
        """Find all Terraform files in directory.

        Args:
            directory: Directory to search

        Returns:
            List of .tf file paths
        """
        tf_files: list[Path] = []
        if directory.is_file() and directory.suffix == ".tf":
            return [directory]

        for pattern in ["*.tf", "**/*.tf"]:
            tf_files.extend(directory.glob(pattern))

        # Filter out common non-main directories
        filtered = []
        for tf_file in tf_files:
            # Skip .terraform directory
            if ".terraform" in tf_file.parts:
                continue
            filtered.append(tf_file)

        return sorted(set(filtered))

    def _execute_terravision(
        self,
        input_path: Path,
        tf_files: list[Path],
    ) -> CanonicalArchitecture:
        """Execute Terravision and transform output.

        Uses 'terravision draw' to generate both the architecture diagram (PNG)
        and the graph data (architecture.json). With --debug, also captures
        rich metadata from tfdata.json.

        Args:
            input_path: Input directory
            tf_files: List of Terraform files

        Returns:
            CanonicalArchitecture
        """
        import shutil

        # Output paths - terravision creates these in cwd
        diagram_path = input_path / "architecture.dot.png"
        graph_json_path = input_path / "architecture.json"
        tfdata_path = input_path / "tfdata.json"

        # Build draw command - generates PNG + architecture.json
        cmd = [
            "terravision",
            "draw",
            "--source",
            str(input_path),
            "--format",
            "png",
        ]
        if self.use_debug:
            cmd.append("--debug")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180,  # Debug mode runs terraform plan, needs more time
                cwd=str(input_path),
            )
        except subprocess.TimeoutExpired:
            self._cleanup_terravision_files(input_path)
            raise ToolExecutionError(
                self.name,
                f"Terravision timed out after 180 seconds processing {input_path}",
            ) from None
        except OSError as e:
            self._cleanup_terravision_files(input_path)
            raise ToolExecutionError(
                self.name,
                f"Failed to execute Terravision: {e}",
            ) from e

        if result.returncode != 0:
            self._cleanup_terravision_files(input_path)
            raise ToolExecutionError(
                self.name,
                f"Terravision failed with exit code {result.returncode}: {result.stderr}",
            )

        # Read and parse outputs
        try:
            tfdata: dict[str, Any] = {}
            tv_output: dict[str, Any] = {}

            # With --debug, tfdata.json has everything: graphdict, meta_data, plandata
            if self.use_debug and tfdata_path.exists():
                try:
                    tfdata = json.loads(tfdata_path.read_text())
                    # graphdict contains the adjacency list (same as graphdata output)
                    tv_output = tfdata.get("graphdict", {})
                    logger.info("Loaded graph and metadata from tfdata.json")
                except json.JSONDecodeError:
                    logger.warning("Failed to parse tfdata.json")

            # Fallback to architecture.json if tfdata not available
            if not tv_output and graph_json_path.exists():
                tv_output = json.loads(graph_json_path.read_text())
                logger.info("Loaded graph from architecture.json")

            if not tv_output:
                raise ToolExecutionError(
                    self.name,
                    "Terravision did not produce graph output",
                )

            # Copy diagram to docs directory if it exists
            rendered_image_path: Path | None = None
            if diagram_path.exists():
                docs_dir = input_path / "docs"
                docs_dir.mkdir(exist_ok=True)
                dest_path = docs_dir / "architecture.png"
                shutil.copy2(diagram_path, dest_path)
                rendered_image_path = dest_path
                logger.info("Copied architecture diagram to %s", dest_path)

            return self._transform_terravision_output(
                tv_output, input_path, tf_files, tfdata, rendered_image_path
            )
        except json.JSONDecodeError as e:
            raise ToolExecutionError(
                self.name,
                f"Failed to parse Terravision JSON output: {e}",
            ) from e
        finally:
            self._cleanup_terravision_files(input_path)

    def _cleanup_terravision_files(self, input_path: Path) -> None:
        """Remove temporary files created by Terravision."""
        for filename in ["architecture.dot.png", "architecture.json", "tfdata.json"]:
            (input_path / filename).unlink(missing_ok=True)

    def _transform_terravision_output(
        self,
        tv_output: dict[str, Any],
        input_path: Path,
        tf_files: list[Path],
        tfdata: dict[str, Any] | None = None,
        rendered_image_path: Path | None = None,
    ) -> CanonicalArchitecture:
        """Transform Terravision JSON output to CanonicalArchitecture.

        Terravision outputs an adjacency list format:
        {
            "aws_lambda_function.bedrock_proxy": ["aws_s3_bucket.data", ...],
            ...
        }

        When run with --debug, tfdata.json provides rich metadata including
        resource attributes from the Terraform plan.

        Args:
            tv_output: Parsed Terravision JSON output (adjacency list)
            input_path: Original input path
            tf_files: List of Terraform files
            tfdata: Optional rich metadata from tfdata.json (debug mode)
            rendered_image_path: Path to rendered PNG diagram if available

        Returns:
            CanonicalArchitecture
        """
        graph = CanonicalGraph()
        meta_data = tfdata.get("meta_data", {}) if tfdata else {}
        variables = tfdata.get("plandata", {}).get("variables", {}) if tfdata else {}

        # Terravision outputs adjacency list: {"resource.name": ["connected_resource", ...]}
        # Keys are node IDs in format "resource_type.resource_name"
        for node_id, connections in tv_output.items():
            # Parse resource type and name from node ID (e.g., "aws_lambda_function.bedrock_proxy")
            parts = node_id.split(".", 1)
            if len(parts) == 2:
                resource_type, resource_name = parts
            else:
                resource_type = "unknown"
                resource_name = node_id

            provider = self._get_provider_from_resource_type(resource_type)

            # Get rich attributes from meta_data if available
            attributes = self._extract_resource_attributes(node_id, meta_data)

            graph.add_node(
                node_id,
                NodeMetadata(
                    type=resource_type,
                    provider=provider,
                    name=resource_name,
                    attributes=attributes,
                ),
            )

            # Add connections (edges)
            if isinstance(connections, list):
                for target in connections:
                    if target:
                        graph.add_connection(node_id, target)

        # Create rendered image reference if diagram was generated
        rendered_image: RenderedImage | None = None
        if rendered_image_path and rendered_image_path.exists():
            rendered_image = RenderedImage(
                format="png",
                path=rendered_image_path,
            )

        # Build source with terraform variables if available
        source = ArchitectureSource(
            tool="terravision",
            tool_version=self.version or "unknown",
            generated_at=datetime.now(UTC),
            source_files=[str(f.relative_to(input_path)) for f in tf_files],
            source_type="terraform",
        )

        # Add terraform variables to source metadata
        if variables:
            source.metadata = {
                "terraform_variables": {k: v.get("value") for k, v in variables.items()}
            }

        return CanonicalArchitecture(
            graph=graph,
            rendered_image=rendered_image,
            source=source,
        )

    def _extract_resource_attributes(
        self,
        node_id: str,
        meta_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Extract useful attributes from meta_data for a resource.

        Filters out computed/dynamic values (marked as True) and internal fields.

        Args:
            node_id: Resource ID (e.g., "aws_lambda_function.bedrock_proxy")
            meta_data: Full meta_data dict from tfdata.json

        Returns:
            Filtered attributes dict
        """
        raw_attrs = meta_data.get(node_id, {})
        if not raw_attrs:
            return {}

        # Keys to always exclude
        exclude_keys = {"module", "id", "arn", "tags_all"}

        # Filter attributes:
        # - Exclude internal fields
        # - Exclude computed values (True means "will be computed")
        # - Exclude None values
        # - Exclude empty lists/dicts
        attributes: dict[str, Any] = {}
        for key, value in raw_attrs.items():
            if key in exclude_keys:
                continue
            if value is True:  # Computed value placeholder
                continue
            if value is None:
                continue
            if isinstance(value, (list, dict)) and not value:
                continue
            # Include meaningful values
            attributes[key] = value

        return attributes

    def _get_provider_from_resource_type(self, resource_type: str) -> str:
        """Get cloud provider from Terraform resource type.

        Args:
            resource_type: Terraform resource type (e.g., "aws_s3_bucket")

        Returns:
            Provider name (e.g., "aws")
        """
        for prefix, provider in RESOURCE_PREFIX_TO_PROVIDER.items():
            if resource_type.startswith(prefix):
                return provider
        return "unknown"
