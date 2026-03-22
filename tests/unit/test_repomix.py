"""Unit tests for Repomix integration (Phase 4g)."""

import pytest
from pathlib import Path
from datetime import datetime, UTC

from chronicle.models.canonical import CompressedCodebase, HolisticOverview


class TestCompressedCodebase:
    """Tests for CompressedCodebase dataclass."""

    def test_create_compressed_codebase(self) -> None:
        """Test creating a CompressedCodebase instance."""
        content = "def hello(): pass"
        compressed = CompressedCodebase(
            compressed_content=content,
            token_count=10,
            file_count=5,
            excluded_patterns=["tests/*", "node_modules/*"],
        )

        assert compressed.compressed_content == content
        assert compressed.token_count == 10
        assert compressed.file_count == 5
        assert len(compressed.excluded_patterns) == 2

    def test_to_dict(self) -> None:
        """Test CompressedCodebase.to_dict() method."""
        compressed = CompressedCodebase(
            compressed_content="code here",
            token_count=100,
            file_count=10,
            source_path=Path("/tmp/test"),
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            tool_version="1.0.0",
        )

        result = compressed.to_dict()

        assert result["compressed_content"] == "code here"
        assert result["token_count"] == 100
        assert result["file_count"] == 10
        assert result["source_path"] == "/tmp/test"
        assert "2024-01-01" in result["timestamp"]
        assert result["tool_version"] == "1.0.0"


class TestHolisticOverview:
    """Tests for HolisticOverview dataclass."""

    def test_create_holistic_overview(self) -> None:
        """Test creating a HolisticOverview instance."""
        from chronicle.models.canonical.compressed import ExternalIntegrationInfo

        overview = HolisticOverview(
            purpose="A CLI tool for documentation generation",
            architecture_style="CLI Tool",
            core_components=["cli", "analyzers", "pipeline"],
            data_flow="Repository -> Pipeline -> Documentation",
            design_patterns=["Adapter", "Pipeline"],
            external_integrations=[
                ExternalIntegrationInfo(
                    name="LiteLLM", type="LLM", purpose="LLM provider"
                ),
                ExternalIntegrationInfo(
                    name="Syft", type="Tool", purpose="SBOM generation"
                ),
            ],
            entry_points=["chronicle write", "chronicle check"],
        )

        assert "documentation" in overview.purpose.lower()
        assert overview.architecture_style == "CLI Tool"
        assert len(overview.core_components) == 3
        assert len(overview.design_patterns) == 2
        assert len(overview.external_integrations) == 2

    def test_to_dict(self) -> None:
        """Test HolisticOverview.to_dict() method."""
        overview = HolisticOverview(
            purpose="Test purpose",
            architecture_style="Monolith",
        )

        result = overview.to_dict()

        assert result["purpose"] == "Test purpose"
        assert result["architecture_style"] == "Monolith"
        assert "raw_response" not in result  # Should not include raw_response

    def test_to_markdown(self) -> None:
        """Test HolisticOverview.to_markdown() method."""
        overview = HolisticOverview(
            purpose="A test system",
            architecture_style="Microservices",
            core_components=["API Gateway", "User Service"],
            design_patterns=["CQRS"],
        )

        md = overview.to_markdown()

        assert "**Purpose**:" in md
        assert "A test system" in md
        assert "**Architecture**:" in md
        assert "Microservices" in md
        assert "**Core Components**:" in md
        assert "- API Gateway" in md
        assert "CQRS" in md

    def test_to_markdown_empty(self) -> None:
        """Test HolisticOverview.to_markdown() with empty data returns empty string."""
        overview = HolisticOverview()

        md = overview.to_markdown()

        # Empty overview returns empty string, not N/A
        # Template decides how to handle empty overview
        assert md == ""


class TestRepomixAdapter:
    """Tests for RepomixAdapter (requires Repomix installed)."""

    def test_default_exclude_patterns(self) -> None:
        """Test that default exclude patterns are defined."""
        from chronicle.analyzers.repomix.adapter import DEFAULT_EXCLUDE_PATTERNS

        # Should have common exclusions
        assert "tests/*" in DEFAULT_EXCLUDE_PATTERNS
        assert "node_modules/*" in DEFAULT_EXCLUDE_PATTERNS
        assert "__pycache__/*" in DEFAULT_EXCLUDE_PATTERNS
        assert ".git/*" in DEFAULT_EXCLUDE_PATTERNS

    def test_adapter_initialization(self) -> None:
        """Test RepomixAdapter initialization."""
        from chronicle.analyzers.repomix.adapter import (
            RepomixAdapter,
            DEFAULT_EXCLUDE_PATTERNS,
        )

        try:
            adapter = RepomixAdapter()
            # If Repomix is available, it should initialize
            assert adapter.exclude_patterns == DEFAULT_EXCLUDE_PATTERNS
        except RuntimeError as e:
            # If Repomix is not installed, that's OK for unit tests
            assert "not found" in str(e).lower()

    def test_adapter_custom_excludes(self) -> None:
        """Test RepomixAdapter with custom exclude patterns."""
        from chronicle.analyzers.repomix.adapter import RepomixAdapter

        try:
            adapter = RepomixAdapter(exclude_patterns=["custom/*"])
            assert adapter.exclude_patterns == ["custom/*"]
        except RuntimeError:
            # Repomix not installed
            pass
