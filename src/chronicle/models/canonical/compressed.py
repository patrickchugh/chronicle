"""Canonical models for compressed codebase analysis (Principle V: Tool Agnosticism).

Compressed codebases use tree-sitter skeleton extraction for holistic LLM analysis.
The canonical format is tool-agnostic and can be produced by any compression tool.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class CompressedCodebase:
    """Canonical format for compressed codebase content.

    Uses tree-sitter to extract function signatures (skeletons) without
    implementation bodies, achieving significant token reduction while
    preserving structure for holistic LLM analysis.

    Attributes:
        compressed_content: The compressed codebase content (skeleton format)
        token_count: Estimated token count of compressed content
        file_count: Number of source files processed
        excluded_patterns: Patterns that were excluded from compression
        source_path: Path to the repository that was compressed
        timestamp: When the compression was performed
        tool_version: Version of the compression tool used
    """

    compressed_content: str
    token_count: int = 0
    file_count: int = 0
    excluded_patterns: list[str] = field(default_factory=list)
    source_path: Path | None = None
    timestamp: datetime | None = None
    tool_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "compressed_content": self.compressed_content,
            "token_count": self.token_count,
            "file_count": self.file_count,
            "excluded_patterns": self.excluded_patterns,
            "source_path": str(self.source_path) if self.source_path else None,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "tool_version": self.tool_version,
        }


@dataclass
class ExternalIntegrationInfo:
    """Structured information about an external integration.

    Attributes:
        name: Service/library name (e.g., "PostgreSQL", "LiteLLM", "Redis")
        type: Integration type (Database, Cache, Queue, LLM, HTTP API, Storage, Cloud)
        purpose: Brief description of how it's used
    """

    name: str
    type: str
    purpose: str = ""

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary."""
        return {"name": self.name, "type": self.type, "purpose": self.purpose}


@dataclass
class HolisticOverview:
    """LLM-generated holistic overview of the entire codebase.

    Generated from compressed codebase in a single LLM call
    for system-wide understanding.

    Attributes:
        purpose: What the system does (1-2 sentences)
        architecture_style: Architecture pattern (monolith, microservices, etc.)
        core_components: Main components/modules and their roles
        data_flow: How data flows through the system
        design_patterns: Notable design patterns used
        external_integrations: External services/APIs the system connects to
        entry_points: Main entry points (CLI, API, etc.)
        raw_response: The original LLM response
    """

    purpose: str = ""
    architecture_style: str = ""
    core_components: list[str] = field(default_factory=list)
    data_flow: str = ""
    design_patterns: list[str] = field(default_factory=list)
    external_integrations: list[ExternalIntegrationInfo] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)
    raw_response: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "purpose": self.purpose,
            "architecture_style": self.architecture_style,
            "core_components": self.core_components,
            "data_flow": self.data_flow,
            "design_patterns": self.design_patterns,
            "external_integrations": [i.to_dict() for i in self.external_integrations],
            "entry_points": self.entry_points,
        }

    def _is_valid_content(self, text: str) -> bool:
        """Check if content is valid (not a negative assertion or hedging).

        Args:
            text: Content to validate

        Returns:
            True if content is valid and should be included
        """
        if not text or not text.strip():
            return False

        lower = text.lower()

        # Negative assertion patterns
        negative_patterns = [
            "not found",
            "not detected",
            "not determinable",
            "unable to determine",
            "none identified",
            "cannot be determined",
            "from the provided",
            "from the analysis",
            "from the available",
        ]

        # Hedging patterns
        hedging_patterns = [
            "appears to",
            "seems to",
            "likely",
            "probably",
            "possibly",
            "may be",
            "might be",
            "could be",
        ]

        return all(pattern not in lower for pattern in negative_patterns + hedging_patterns)

    def to_markdown(self) -> str:
        """Convert to markdown format for template rendering.

        Automatically filters out any negative assertions or hedging language
        that may have slipped through LLM generation.
        """
        lines = []

        if self._is_valid_content(self.purpose):
            lines.append(f"**Purpose**: {self.purpose}")
            lines.append("")

        if self._is_valid_content(self.architecture_style):
            lines.append(f"**Architecture**: {self.architecture_style}")
            lines.append("")

        # Filter core_components for valid entries
        valid_components = [c for c in self.core_components if self._is_valid_content(c)]
        if valid_components:
            lines.append("**Core Components**:")
            for component in valid_components:
                lines.append(f"- {component}")
            lines.append("")

        if self._is_valid_content(self.data_flow):
            lines.append(f"**Data Flow**: {self.data_flow}")
            lines.append("")

        # Filter design_patterns for valid entries
        valid_patterns = [p for p in self.design_patterns if self._is_valid_content(p)]
        if valid_patterns:
            lines.append(f"**Design Patterns**: {', '.join(valid_patterns)}")
            lines.append("")

        # Filter entry_points for valid entries
        valid_entry_points = [e for e in self.entry_points if self._is_valid_content(e)]
        if valid_entry_points:
            lines.append(f"**Entry Points**: {', '.join(valid_entry_points)}")
            lines.append("")

        return "\n".join(lines).strip()
