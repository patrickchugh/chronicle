"""Unit tests for template renderer."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from chronicle.models.analysis import (
    AnalysisResult,
    AnalysisStatus,
    Dependency,
    LanguageInfo,
    TechnologyStack,
    VersionEntry,
)
from chronicle.templates import DocumentRenderer, SectionLoader


class TestSectionLoader:
    """Tests for SectionLoader."""

    def test_load_nonexistent_section(self, tmp_path: Path) -> None:
        """Test loading a section that doesn't exist."""
        loader = SectionLoader()
        content = loader.load_section("overview", tmp_path)

        assert content is None

    def test_load_all_sections_empty(self, tmp_path: Path) -> None:
        """Test loading sections with no config."""
        loader = SectionLoader()
        sections = loader.load_all_sections(tmp_path)

        assert sections == {}


class TestDocumentRenderer:
    """Tests for DocumentRenderer."""

    @pytest.fixture
    def renderer(self) -> DocumentRenderer:
        """Create a renderer instance."""
        return DocumentRenderer()

    @pytest.fixture
    def sample_result(self, tmp_path: Path) -> AnalysisResult:
        """Create a sample analysis result."""
        return AnalysisResult(
            repository_path=tmp_path,
            repository_name="test-project",
            timestamp=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
            status=AnalysisStatus.COMPLETED,
            technology_stack=TechnologyStack(
                languages=[
                    LanguageInfo(name="python", version="3.11", file_count=10),
                    LanguageInfo(name="javascript", file_count=5),
                ],
                dependencies=[
                    Dependency(
                        name="flask",
                        ecosystem="pypi",
                        version="2.3.0",
                        license="MIT",
                        source_file="requirements.txt",
                    ),
                    Dependency(
                        name="express",
                        ecosystem="npm",
                        version="4.18.0",
                        source_file="package.json",
                    ),
                ],
            ),
            git_ref="abc123def456",
            tool_versions={"dependency": "1.0.0"},
        )

    def test_render_basic(
        self,
        renderer: DocumentRenderer,
        sample_result: AnalysisResult,
    ) -> None:
        """Test basic rendering."""
        content = renderer.render(sample_result)

        assert "test-project" in content
        assert "System Documentation" in content
        assert "Technology Stack" in content
        assert "Dependencies" in content

    def test_render_includes_languages(
        self,
        renderer: DocumentRenderer,
        sample_result: AnalysisResult,
    ) -> None:
        """Test that languages are included in output."""
        content = renderer.render(sample_result)

        assert "python" in content
        assert "javascript" in content
        assert "3.11" in content

    def test_render_includes_dependencies(
        self,
        renderer: DocumentRenderer,
        sample_result: AnalysisResult,
    ) -> None:
        """Test that dependencies are included in output."""
        content = renderer.render(sample_result)

        assert "flask" in content
        assert "express" in content
        assert "2.3.0" in content
        assert "MIT" in content
        assert "pypi" in content
        assert "npm" in content

    def test_render_includes_git_ref(
        self,
        renderer: DocumentRenderer,
        sample_result: AnalysisResult,
    ) -> None:
        """Test that git reference is included."""
        content = renderer.render(sample_result)

        assert "abc123def456" in content

    def test_render_includes_timestamp(
        self,
        renderer: DocumentRenderer,
        sample_result: AnalysisResult,
    ) -> None:
        """Test that timestamp is included."""
        content = renderer.render(sample_result)

        assert "2024-01-15" in content

    def test_render_with_version_history(
        self,
        renderer: DocumentRenderer,
        sample_result: AnalysisResult,
    ) -> None:
        """Test rendering with version history."""
        history = [
            VersionEntry.create_automated(
                version="1.0.0",
                changes="Initial documentation",
                git_ref="abc123",
            ),
        ]

        content = renderer.render(sample_result, version_history=history)

        assert "Version History" in content
        assert "1.0.0" in content
        assert "Initial documentation" in content
        assert "chronicle" in content

    def test_render_to_file(
        self,
        renderer: DocumentRenderer,
        sample_result: AnalysisResult,
        tmp_path: Path,
    ) -> None:
        """Test rendering to file."""
        output_path = tmp_path / "docs" / "SYSTEM.md"

        result_path = renderer.render_to_file(sample_result, output_path)

        assert result_path == output_path
        assert output_path.exists()

        content = output_path.read_text()
        assert "test-project" in content

    def test_preview(
        self,
        renderer: DocumentRenderer,
        sample_result: AnalysisResult,
    ) -> None:
        """Test preview functionality."""
        preview = renderer.preview(sample_result, max_lines=10)

        lines = preview.strip().split("\n")
        # Should be truncated with indicator
        assert "more lines" in preview or len(lines) <= 10

    def test_render_empty_result(
        self,
        renderer: DocumentRenderer,
        tmp_path: Path,
    ) -> None:
        """Test rendering with minimal/empty result."""
        result = AnalysisResult(
            repository_path=tmp_path,
            repository_name="empty-project",
            status=AnalysisStatus.COMPLETED,
        )

        content = renderer.render(result)

        assert "empty-project" in content
        # Per FR-029, empty sections now show "N/A" instead of "No X detected"
        assert "N/A" in content

    def test_render_with_errors(
        self,
        renderer: DocumentRenderer,
        sample_result: AnalysisResult,
    ) -> None:
        """Test rendering with analysis errors."""
        from chronicle.models import AnalysisError

        sample_result.add_error(
            AnalysisError(
                component="sbom",
                message="Syft not installed",
                recoverable=True,
            )
        )

        content = renderer.render(sample_result)

        assert "Analysis Errors" in content or "error" in content.lower()
        assert "sbom" in content
        assert "Syft not installed" in content
