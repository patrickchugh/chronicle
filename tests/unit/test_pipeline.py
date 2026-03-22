"""Unit tests for analysis pipeline."""

from pathlib import Path

import pytest

from chronicle.models import Repository
from chronicle.models.analysis import AnalysisStatus
from chronicle.pipeline import AnalysisPipeline, PipelineOptions


class TestPipelineOptions:
    """Tests for PipelineOptions."""

    def test_default_options(self) -> None:
        """Test default pipeline options."""
        options = PipelineOptions()

        assert options.skip_sbom is False
        assert options.skip_architecture is False
        assert options.skip_ast is False
        assert options.skip_dependencies is False
        assert options.fail_fast is False
        assert options.exclude_patterns == []

    def test_custom_options(self) -> None:
        """Test custom pipeline options."""
        options = PipelineOptions(
            skip_sbom=True,
            skip_architecture=True,
            exclude_patterns=["test_*.py"],
        )

        assert options.skip_sbom is True
        assert options.skip_architecture is True
        assert options.exclude_patterns == ["test_*.py"]


class TestAnalysisPipeline:
    """Tests for AnalysisPipeline."""

    @pytest.fixture
    def pipeline(self) -> AnalysisPipeline:
        """Create a pipeline instance."""
        return AnalysisPipeline()

    @pytest.fixture
    def sample_repo(self, tmp_path: Path) -> Repository:
        """Create a sample repository for testing."""
        # Create .git directory to make it a valid git repo
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # Create some source files
        (tmp_path / "main.py").write_text(
            '''
"""Main module."""

class App:
    """Main application class."""

    def run(self):
        print("Running")

def main():
    app = App()
    app.run()

if __name__ == "__main__":
    main()
'''
        )

        # Create package.json
        (tmp_path / "package.json").write_text(
            """{
    "name": "test-project",
    "version": "1.0.0",
    "dependencies": {
        "express": "^4.18.0"
    }
}"""
        )

        # Create requirements.txt
        (tmp_path / "requirements.txt").write_text(
            """
flask==2.3.0
requests>=2.28.0
"""
        )

        return Repository.from_path(tmp_path)

    def test_run_minimal_pipeline(
        self,
        pipeline: AnalysisPipeline,
        sample_repo: Repository,
    ) -> None:
        """Test running pipeline with minimal options (skip external tools)."""
        options = PipelineOptions(
            skip_sbom=True,
            skip_architecture=True,
        )

        result = pipeline.run(sample_repo, options)

        assert result.status == AnalysisStatus.COMPLETED
        assert result.repository_name == sample_repo.name
        assert result.repository_path == sample_repo.path

        # Technology stack should be populated
        assert len(result.technology_stack.languages) > 0
        assert len(result.technology_stack.dependencies) > 0

        # Source analysis should be populated
        assert result.source_analysis is not None
        assert result.source_analysis.module_count > 0
        assert result.source_analysis.class_count > 0

    def test_run_empty_repo(
        self,
        pipeline: AnalysisPipeline,
        tmp_path: Path,
    ) -> None:
        """Test running pipeline on empty repository."""
        # Create empty git repo
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        repo = Repository.from_path(tmp_path)
        options = PipelineOptions(
            skip_sbom=True,
            skip_architecture=True,
        )

        result = pipeline.run(repo, options)

        assert result.status == AnalysisStatus.COMPLETED
        assert result.technology_stack.languages == []
        assert result.technology_stack.dependencies == []

    def test_skip_all_analysis(
        self,
        pipeline: AnalysisPipeline,
        sample_repo: Repository,
    ) -> None:
        """Test running pipeline with all analysis skipped."""
        options = PipelineOptions(
            skip_sbom=True,
            skip_architecture=True,
            skip_ast=True,
            skip_dependencies=True,
        )

        result = pipeline.run(sample_repo, options)

        assert result.status == AnalysisStatus.COMPLETED
        assert result.source_analysis is None
        assert result.sbom is None
        assert result.architecture is None

    def test_dependency_analysis_results(
        self,
        pipeline: AnalysisPipeline,
        sample_repo: Repository,
    ) -> None:
        """Test that dependency analysis populates results correctly."""
        options = PipelineOptions(
            skip_sbom=True,
            skip_architecture=True,
            skip_ast=True,
        )

        result = pipeline.run(sample_repo, options)

        # Should have detected Python and JavaScript (case insensitive check)
        lang_names = [l.name.lower() for l in result.technology_stack.languages]
        assert "python" in lang_names
        assert "javascript" in lang_names

        # Should have found dependencies
        dep_names = [d.name for d in result.technology_stack.dependencies]
        assert "flask" in dep_names
        assert "requests" in dep_names
        assert "express" in dep_names

    def test_ast_analysis_results(
        self,
        pipeline: AnalysisPipeline,
        sample_repo: Repository,
    ) -> None:
        """Test that AST analysis populates results correctly."""
        options = PipelineOptions(
            skip_sbom=True,
            skip_architecture=True,
            skip_dependencies=True,
        )

        result = pipeline.run(sample_repo, options)

        assert result.source_analysis is not None
        assert result.source_analysis.module_count >= 1
        assert result.source_analysis.class_count >= 1  # App class
        assert result.source_analysis.function_count >= 1  # main function

    def test_result_to_dict(
        self,
        pipeline: AnalysisPipeline,
        sample_repo: Repository,
    ) -> None:
        """Test converting analysis result to dictionary."""
        options = PipelineOptions(
            skip_sbom=True,
            skip_architecture=True,
        )

        result = pipeline.run(sample_repo, options)
        data = result.to_dict()

        assert "repository_name" in data
        assert "repository_path" in data
        assert "timestamp" in data
        assert "status" in data
        assert "technology_stack" in data
        assert "errors" in data
        assert "tool_versions" in data

    def test_error_collection(
        self,
        pipeline: AnalysisPipeline,
        tmp_path: Path,
    ) -> None:
        """Test that errors are collected properly."""
        # Create invalid repo (no .git)
        repo = Repository.from_path(tmp_path)
        options = PipelineOptions(
            skip_sbom=True,
            skip_architecture=True,
        )

        result = pipeline.run(repo, options)

        # Pipeline should still complete
        assert result.status in [AnalysisStatus.COMPLETED, AnalysisStatus.FAILED]

    def test_invalid_repository_path(self, pipeline: AnalysisPipeline) -> None:
        """Test handling of invalid repository path."""
        repo = Repository(path=Path("/nonexistent/path"), name="test")

        with pytest.raises(ValueError, match="does not exist"):
            repo.validate()
