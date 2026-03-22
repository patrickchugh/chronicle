"""Canonical Architecture format (Principle V: Tool Agnosticism).

Standard architecture format produced by all diagram/infrastructure tool adapters.
Uses a hybrid format: adjacency list for connections plus node metadata dict.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class NodeMetadata:
    """Metadata for a single node in the architecture graph.

    Attributes:
        type: Resource type (e.g., "aws_s3_bucket", "google_compute_instance")
        provider: Cloud provider ("aws", "gcp", "azure")
        name: Human-readable name (optional)
        attributes: Key properties (region, size, etc.)
    """

    type: str
    provider: str
    name: str | None = None
    attributes: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result: dict[str, Any] = {
            "type": self.type,
            "provider": self.provider,
        }
        if self.name:
            result["name"] = self.name
        if self.attributes:
            result["attributes"] = self.attributes
        return result


@dataclass
class CanonicalGraph:
    """Hybrid graph structure: adjacency list for connections, dict for node metadata.

    Example:
        {
            "nodes": {
                "aws_s3_bucket.data": {"type": "aws_s3_bucket", "provider": "aws", "name": "data-bucket"},
                "aws_lambda_function.processor": {"type": "aws_lambda_function", "provider": "aws"}
            },
            "connections": {
                "aws_s3_bucket.data": ["aws_lambda_function.processor"],
                "aws_lambda_function.processor": ["aws_dynamodb_table.results"]
            },
            "cloud_providers": ["aws"]
        }

    Attributes:
        nodes: Node ID → metadata mapping
        connections: Node ID → list of connected node IDs (adjacency list)
        cloud_providers: Providers present ("aws", "gcp", "azure")
    """

    nodes: dict[str, NodeMetadata] = field(default_factory=dict)
    connections: dict[str, list[str]] = field(default_factory=dict)
    cloud_providers: list[str] = field(default_factory=list)

    def add_node(self, node_id: str, metadata: NodeMetadata) -> None:
        """Add a node to the graph."""
        self.nodes[node_id] = metadata
        if metadata.provider not in self.cloud_providers:
            self.cloud_providers.append(metadata.provider)

    def add_connection(self, from_node: str, to_node: str) -> None:
        """Add a connection between two nodes."""
        if from_node not in self.connections:
            self.connections[from_node] = []
        if to_node not in self.connections[from_node]:
            self.connections[from_node].append(to_node)

    def get_node_ids(self) -> list[str]:
        """Get all node IDs in the graph."""
        return list(self.nodes.keys())

    def get_connections_from(self, node_id: str) -> list[str]:
        """Get all nodes connected from the given node."""
        return self.connections.get(node_id, [])

    @property
    def node_count(self) -> int:
        """Return total number of nodes."""
        return len(self.nodes)

    @property
    def connection_count(self) -> int:
        """Return total number of connections."""
        return sum(len(conns) for conns in self.connections.values())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "nodes": {node_id: meta.to_dict() for node_id, meta in self.nodes.items()},
            "connections": self.connections,
            "cloud_providers": self.cloud_providers,
        }


@dataclass
class RenderedImage:
    """Optional pre-rendered visualization of the architecture.

    Attributes:
        data: Embedded image data (for inline rendering)
        path: Path to image file (for file-based rendering)
        format: Image format ("png", "svg")
    """

    format: str
    data: bytes | None = None
    path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result: dict[str, Any] = {"format": self.format}
        if self.path:
            result["path"] = str(self.path)
        # Note: data is not serialized to dict (binary)
        return result


@dataclass
class ArchitectureSource:
    """Metadata about how the architecture was extracted.

    Attributes:
        tool: Tool that generated this (e.g., "terravision")
        tool_version: Version of the tool
        generated_at: When the graph was generated
        source_files: Infrastructure files used (Terraform, etc.)
        source_type: Source format ("terraform", "cloudformation", "pulumi", "manual")
        metadata: Optional additional metadata (e.g., terraform variables)
    """

    tool: str
    tool_version: str
    generated_at: datetime
    source_files: list[str]
    source_type: str
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Ensure timestamp is timezone-aware UTC."""
        if self.generated_at.tzinfo is None:
            self.generated_at = self.generated_at.replace(tzinfo=UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "tool": self.tool,
            "tool_version": self.tool_version,
            "generated_at": self.generated_at.isoformat(),
            "source_files": self.source_files,
            "source_type": self.source_type,
        }
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class CanonicalArchitecture:
    """Standard architecture format produced by all diagram/infrastructure tool adapters.

    This is the canonical internal format that the rest of chronicle consumes.
    Tool adapters (Terravision, etc.) MUST transform their output into this format.

    Attributes:
        graph: The architecture topology (nodes and connections)
        rendered_image: Optional pre-rendered PNG/SVG
        source: Metadata about generation
    """

    graph: CanonicalGraph = field(default_factory=CanonicalGraph)
    rendered_image: RenderedImage | None = None
    source: ArchitectureSource | None = None

    @property
    def has_image(self) -> bool:
        """Check if a rendered image is available."""
        return self.rendered_image is not None

    @property
    def cloud_providers(self) -> list[str]:
        """Get list of cloud providers in this architecture."""
        return self.graph.cloud_providers

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result: dict[str, Any] = {
            "graph": self.graph.to_dict(),
            "node_count": self.graph.node_count,
            "connection_count": self.graph.connection_count,
            "cloud_providers": self.cloud_providers,
        }
        if self.rendered_image:
            result["rendered_image"] = self.rendered_image.to_dict()
        if self.source:
            result["source"] = self.source.to_dict()
        return result
