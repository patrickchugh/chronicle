"""Tests for config context collector."""

from pathlib import Path

import pytest

from chronicle.analyzers.config_context import collect_config_context


class TestConfigContextCollector:
    """Tests for collect_config_context function."""

    def test_collect_from_repo_with_readme(self, tmp_path: Path) -> None:
        """Test collecting context from a repo with README."""
        # Create a README
        readme = tmp_path / "README.md"
        readme.write_text("# Test Project\n\nThis is a test project.")

        context = collect_config_context(tmp_path)

        assert "README.md" in context
        assert "Test Project" in context
        assert "CONFIGURATION AND DOCUMENTATION CONTEXT" in context

    def test_collect_from_repo_with_pyproject(self, tmp_path: Path) -> None:
        """Test collecting context from a repo with pyproject.toml."""
        # Create a pyproject.toml
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "test-project"\n' 'dependencies = ["requests", "boto3"]'
        )

        context = collect_config_context(tmp_path)

        assert "pyproject.toml" in context
        assert "test-project" in context
        assert "requests" in context

    def test_collect_from_repo_with_chronicle_config(self, tmp_path: Path) -> None:
        """Test collecting context from a repo with .chronicle/config.yaml."""
        # Create .chronicle/config.yaml
        chronicle_dir = tmp_path / ".chronicle"
        chronicle_dir.mkdir()
        config = chronicle_dir / "config.yaml"
        config.write_text(
            'llm:\n  provider: "bedrock"\n'
            '  model: "anthropic.claude-3-sonnet-20240229-v1:0"'
        )

        context = collect_config_context(tmp_path)

        assert ".chronicle/config.yaml" in context
        assert "bedrock" in context
        assert "anthropic" in context

    def test_collect_empty_repo(self, tmp_path: Path) -> None:
        """Test collecting context from empty repo."""
        context = collect_config_context(tmp_path)

        assert context == ""

    def test_collect_multiple_files(self, tmp_path: Path) -> None:
        """Test collecting multiple config files."""
        # Create README
        (tmp_path / "README.md").write_text("# Project")

        # Create pyproject.toml
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"')

        # Create package.json
        (tmp_path / "package.json").write_text('{"name": "test"}')

        context = collect_config_context(tmp_path)

        assert "README.md" in context
        assert "pyproject.toml" in context
        assert "package.json" in context

    def test_skip_large_files(self, tmp_path: Path) -> None:
        """Test that large files are skipped."""
        # Create a very large README (over 50KB)
        large_content = "x" * 60_000
        (tmp_path / "README.md").write_text(large_content)

        # Create a normal pyproject.toml
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"')

        context = collect_config_context(tmp_path)

        # Large README should be skipped (check for actual file entry, not header mention)
        assert "File: README.md" not in context
        # But pyproject.toml should be included
        assert "File: pyproject.toml" in context

    def test_docker_compose_detection(self, tmp_path: Path) -> None:
        """Test collecting docker-compose.yml."""
        docker = tmp_path / "docker-compose.yml"
        docker.write_text(
            "services:\n  db:\n    image: postgres:15\n  redis:\n    image: redis:7"
        )

        context = collect_config_context(tmp_path)

        assert "docker-compose.yml" in context
        assert "postgres" in context
        assert "redis" in context

    def test_source_of_truth_labels(self, tmp_path: Path) -> None:
        """Test that files are labeled with source-of-truth indicators."""
        # Create a README (documentation - reference only)
        (tmp_path / "README.md").write_text("# Test")

        # Create a config file (authoritative)
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"')

        context = collect_config_context(tmp_path)

        # README should be labeled as reference
        assert "File: README.md [REFERENCE - may be outdated]" in context

        # pyproject.toml should be labeled as authoritative
        assert "File: pyproject.toml [AUTHORITATIVE CONFIG]" in context

        # Header should include precedence instructions
        assert "SOURCE OF TRUTH PRECEDENCE" in context
        assert "trust the config/code" in context
