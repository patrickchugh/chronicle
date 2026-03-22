"""Integration tests for full pipeline (T068, T070).

Tests reproducibility (SC-005) and version history (SC-011).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chronicle.config import LLMConfig, chronicleConfig, OutputConfig, ToolConfig
from chronicle.models import Repository
from chronicle.models.analysis import AuthorType
from chronicle.pipeline import AnalysisPipeline, PipelineOptions
from chronicle.utils.version import VersionTracker


class TestReproducibility:
    """Tests for reproducibility (T068, SC-005)."""

    @pytest.fixture
    def sample_repo(self, tmp_path: Path) -> Repository:
        """Create a sample repository for testing."""
        # Create sample Python file
        (tmp_path / "main.py").write_text("def main():\n    print('hello')\n")

        # Create requirements.txt
        (tmp_path / "requirements.txt").write_text("requests==2.31.0\nboto3==1.28.0\n")

        return Repository(path=tmp_path, name="test-repo")

    @pytest.fixture
    def config(self) -> chronicleConfig:
        """Create test configuration with LLM disabled."""
        return chronicleConfig(
            output=OutputConfig(path=Path("docs/system.md")),
            tools=ToolConfig(),
            llm=LLMConfig(enabled=False),
        )

    def test_consecutive_runs_produce_identical_output(
        self, sample_repo: Repository, config: chronicleConfig
    ) -> None:
        """Test that two consecutive runs on the same repo produce identical output (T068)."""
        pipeline = AnalysisPipeline(config)
        options = PipelineOptions(
            skip_sbom=True,
            skip_architecture=True,
            skip_llm=True,
        )

        # Run twice
        result1 = pipeline.run(sample_repo, options)
        result2 = pipeline.run(sample_repo, options)

        # Compare deterministic data
        assert result1.repository_name == result2.repository_name
        assert result1.repository_path == result2.repository_path

        # Technology stack should be identical
        ts1 = result1.technology_stack.to_dict()
        ts2 = result2.technology_stack.to_dict()
        assert ts1 == ts2

        # Source analysis should be identical
        if result1.source_analysis and result2.source_analysis:
            assert (
                result1.source_analysis.module_count
                == result2.source_analysis.module_count
            )
            assert (
                result1.source_analysis.function_count
                == result2.source_analysis.function_count
            )

    def test_output_comparison_utility(self) -> None:
        """Test the output comparison utility handles acceptable variations (T063)."""
        tracker = VersionTracker()

        # Identical content should match
        output1 = "# Title\n\nThis is a test.\n"
        output2 = "# Title\n\nThis is a test.\n"
        is_identical, diffs = tracker.compare_outputs(output1, output2)
        assert is_identical is True
        assert len(diffs) == 0

        # Minor whitespace should be acceptable
        output3 = "# Title\n\nThis is  a test.\n"
        is_identical, diffs = tracker.compare_outputs(output1, output3)
        assert is_identical is True

        # Major content changes should be detected
        output4 = "# Different Title\n\nCompletely different content.\n"
        is_identical, diffs = tracker.compare_outputs(output1, output4)
        assert is_identical is False
        assert len(diffs) > 0

    def test_filler_words_ignored_in_comparison(self) -> None:
        """Test that filler words (the, an, a) are ignored per SC-005."""
        tracker = VersionTracker()

        output1 = "The system uses AWS Lambda."
        output2 = "System uses AWS Lambda."
        is_identical, diffs = tracker.compare_outputs(output1, output2)
        assert is_identical is True

        output3 = "A function handles requests."
        output4 = "Function handles requests."
        is_identical, diffs = tracker.compare_outputs(output3, output4)
        assert is_identical is True


class TestVersionHistory:
    """Tests for version history (T070, SC-011)."""

    @pytest.fixture
    def version_tracker(self, tmp_path: Path) -> VersionTracker:
        """Create version tracker for testing."""
        return VersionTracker(repo_path=tmp_path)

    def test_create_automated_entry(self, version_tracker: VersionTracker) -> None:
        """Test creating an automated version entry."""
        entry = version_tracker.create_automated_entry(
            version="1.0.0",
            changes="Initial documentation",
        )

        assert entry.version == "1.0.0"
        assert entry.author == "chronicle"
        assert entry.author_type == AuthorType.AUTOMATED
        assert entry.changes == "Initial documentation"
        assert entry.timestamp is not None

    def test_create_human_entry(self, version_tracker: VersionTracker) -> None:
        """Test creating a human version entry."""
        entry = version_tracker.create_human_entry(
            version="1.0.1",
            author="John Doe",
            changes="Added security section",
        )

        assert entry.version == "1.0.1"
        assert entry.author == "John Doe"
        assert entry.author_type == AuthorType.HUMAN
        assert entry.changes == "Added security section"

    def test_version_increment(self, version_tracker: VersionTracker) -> None:
        """Test semantic version incrementing."""
        assert version_tracker.increment_version("1.0.0", "patch") == "1.0.1"
        assert version_tracker.increment_version("1.0.0", "minor") == "1.1.0"
        assert version_tracker.increment_version("1.0.0", "major") == "2.0.0"
        assert version_tracker.increment_version("1.2.3", "patch") == "1.2.4"

    def test_save_and_load_history(self, version_tracker: VersionTracker) -> None:
        """Test saving and loading version history."""
        # Create and save entries
        entry1 = version_tracker.create_automated_entry("1.0.0", "Initial version")
        version_tracker.save_entry(entry1)

        entry2 = version_tracker.create_human_entry("1.0.1", "Jane", "Added overview")
        version_tracker.save_entry(entry2)

        # Load history
        history = version_tracker.load_history()

        assert len(history) == 2
        # Most recent first
        assert history[0].version == "1.0.1"
        assert history[1].version == "1.0.0"

    def test_history_includes_git_ref(
        self, version_tracker: VersionTracker, tmp_path: Path
    ) -> None:
        """Test that version entries include git ref when available."""
        # Initialize git repo
        import subprocess

        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path,
            capture_output=True,
        )
        (tmp_path / "README.md").write_text("# Test\n")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=tmp_path,
            capture_output=True,
        )

        entry = version_tracker.create_automated_entry("1.0.0", "Test")

        assert entry.git_ref is not None
        assert len(entry.git_ref) == 40  # Full SHA


class TestSBOMCompleteness:
    """Tests for SBOM completeness (T069)."""

    def test_canonical_package_has_license(self) -> None:
        """Test that CanonicalPackage includes license info."""
        from chronicle.models.canonical import CanonicalPackage

        pkg = CanonicalPackage(
            name="requests",
            ecosystem="pypi",
            version="2.31.0",
            license="Apache-2.0",
        )

        assert pkg.license == "Apache-2.0"
        assert "license" in pkg.to_dict()

    def test_canonical_package_has_purl(self) -> None:
        """Test that CanonicalPackage includes PURL."""
        from chronicle.models.canonical import CanonicalPackage

        pkg = CanonicalPackage(
            name="requests",
            ecosystem="pypi",
            version="2.31.0",
            purl="pkg:pypi/requests@2.31.0",
        )

        assert pkg.purl == "pkg:pypi/requests@2.31.0"
        assert "purl" in pkg.to_dict()

    def test_all_dependencies_have_versions(self) -> None:
        """Test that dependencies include version information when available."""
        from chronicle.models.canonical import CanonicalPackage, CanonicalSBOM

        packages = [
            CanonicalPackage(name="requests", ecosystem="pypi", version="2.31.0"),
            CanonicalPackage(name="boto3", ecosystem="pypi", version="1.28.0"),
            CanonicalPackage(name="unknown-pkg", ecosystem="pypi"),  # No version
        ]

        sbom = CanonicalSBOM(packages=packages)

        # Check that we can identify packages with/without versions
        pkgs_with_version = [p for p in sbom.packages if p.version]
        pkgs_without_version = [p for p in sbom.packages if not p.version]

        assert len(pkgs_with_version) == 2
        assert len(pkgs_without_version) == 1

    def test_sbom_ecosystem_grouping(self) -> None:
        """Test SBOM packages can be grouped by ecosystem."""
        from chronicle.models.canonical import CanonicalPackage, CanonicalSBOM

        packages = [
            CanonicalPackage(name="requests", ecosystem="pypi", version="2.31.0"),
            CanonicalPackage(name="boto3", ecosystem="pypi", version="1.28.0"),
            CanonicalPackage(name="react", ecosystem="npm", version="18.2.0"),
            CanonicalPackage(name="lodash", ecosystem="npm", version="4.17.21"),
        ]

        sbom = CanonicalSBOM(packages=packages)

        ecosystems = sbom.get_unique_ecosystems()
        assert set(ecosystems) == {"pypi", "npm"}

        pypi_pkgs = sbom.get_packages_by_ecosystem("pypi")
        assert len(pypi_pkgs) == 2

        npm_pkgs = sbom.get_packages_by_ecosystem("npm")
        assert len(npm_pkgs) == 2
