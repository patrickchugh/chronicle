"""Integration tests for chronicle CLI commands (T059, T060).

These tests exercise the full CLI workflow against sample repositories.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from chronicle.cli import app
from tests.fixtures import PYTHON_PROJECT_PATH

runner = CliRunner()


class TestchronicleWrite:
    """Integration tests for `chronicle write` command (T059)."""

    @pytest.fixture
    def sample_repo(self) -> Path:
        """Get the sample Python project path."""
        return PYTHON_PROJECT_PATH

    @pytest.fixture
    def output_path(self, tmp_path: Path) -> Path:
        """Create temporary output path."""
        return tmp_path / "SYSTEM.md"

    def test_write_generates_documentation(
        self,
        sample_repo: Path,
        output_path: Path,
    ) -> None:
        """Test that write command generates documentation for sample repo."""
        result = runner.invoke(
            app,
            [
                "write",
                "--repo",
                str(sample_repo),
                "--output",
                str(output_path),
                "--skip-sbom",  # Skip external tools for CI
                "--skip-architecture",  # Skip external tools for CI
                "--skip-llm",  # Skip LLM for CI (no Ollama running)
            ],
        )

        # Should complete (exit codes 0 or 2 for warnings)
        assert result.exit_code in [0, 2], f"Command failed: {result.output}"

        # Output file should exist
        assert output_path.exists(), "Documentation file was not created"

        # Check content
        content = output_path.read_text()
        assert "python_project" in content.lower() or "System Documentation" in content
        assert "Technology Stack" in content
        assert "Dependencies" in content

    def test_write_detects_python_language(
        self,
        sample_repo: Path,
        output_path: Path,
    ) -> None:
        """Test that write command detects Python in sample repo."""
        result = runner.invoke(
            app,
            [
                "write",
                "--repo",
                str(sample_repo),
                "--output",
                str(output_path),
                "--skip-sbom",
                "--skip-architecture",
                "--skip-llm",
            ],
        )

        assert result.exit_code in [0, 2]

        content = output_path.read_text()
        # Should detect Python as a language
        assert "python" in content.lower()

    def test_write_detects_dependencies(
        self,
        sample_repo: Path,
        output_path: Path,
    ) -> None:
        """Test that write command detects dependencies from pyproject.toml."""
        result = runner.invoke(
            app,
            [
                "write",
                "--repo",
                str(sample_repo),
                "--output",
                str(output_path),
                "--skip-sbom",
                "--skip-architecture",
                "--skip-llm",
            ],
        )

        assert result.exit_code in [0, 2]

        content = output_path.read_text()
        # Should detect Flask from pyproject.toml
        assert "flask" in content.lower()

    def test_write_dry_run_no_file(
        self,
        sample_repo: Path,
        output_path: Path,
    ) -> None:
        """Test that --dry-run doesn't create files."""
        result = runner.invoke(
            app,
            [
                "write",
                "--repo",
                str(sample_repo),
                "--output",
                str(output_path),
                "--skip-sbom",
                "--skip-architecture",
                "--skip-llm",
                "--dry-run",
            ],
        )

        # Should complete successfully
        assert result.exit_code == 0

        # Output file should NOT exist
        assert not output_path.exists(), "Dry run should not create files"

        # Preview should be in output
        assert "Preview" in result.output or "System Documentation" in result.output

    def test_write_exit_code_success(
        self,
        sample_repo: Path,
        output_path: Path,
    ) -> None:
        """Test that successful write returns exit code 0."""
        result = runner.invoke(
            app,
            [
                "write",
                "--repo",
                str(sample_repo),
                "--output",
                str(output_path),
                "--skip-sbom",
                "--skip-architecture",
                "--skip-llm",
            ],
        )

        # With skip flags, should complete without errors
        assert result.exit_code in [0, 2]  # 0=success, 2=warnings

    def test_write_nonexistent_repo_fails(
        self,
        output_path: Path,
    ) -> None:
        """Test that write fails for nonexistent repository."""
        result = runner.invoke(
            app,
            [
                "write",
                "--repo",
                "/nonexistent/path",
                "--output",
                str(output_path),
            ],
        )

        # Should fail with exit code 1 or 2
        assert result.exit_code != 0


class TestchronicleCheck:
    """Integration tests for `chronicle check` command (T060)."""

    def test_check_runs_preflight(self) -> None:
        """Test that check command runs preflight validation."""
        result = runner.invoke(app, ["check"])

        # Should complete (even if some tools missing)
        assert result.exit_code in [0, 1, 2]

        # Should show preflight output
        assert "Preflight" in result.output or "git" in result.output.lower()

    def test_check_json_output(self) -> None:
        """Test that --json flag produces valid JSON."""
        result = runner.invoke(app, ["check", "--json"])

        # Should complete
        assert result.exit_code in [0, 1, 2]

        # Output should be valid JSON
        try:
            data = json.loads(result.output)
            assert isinstance(data, dict)
            assert "checks" in data or "errors" in data or "warnings" in data
        except json.JSONDecodeError:
            pytest.fail(f"Invalid JSON output: {result.output}")

    def test_check_detects_git(self) -> None:
        """Test that check detects git availability."""
        result = runner.invoke(app, ["check", "--json"])

        # Parse JSON output
        data = json.loads(result.output)

        # Should have checks array
        assert "checks" in data

        # Should include git check
        check_names = [c.get("name", "") for c in data["checks"]]
        assert "git" in check_names

    def test_check_exit_codes(self) -> None:
        """Test that check returns appropriate exit codes."""
        result = runner.invoke(app, ["check"])

        # Exit code meanings:
        # 0 = all checks passed
        # 1 = required tool missing
        # 2 = optional tool missing (warnings only)
        assert result.exit_code in [0, 1, 2]


class TestchronicleInit:
    """Integration tests for `chronicle init` command."""

    def test_init_creates_config(self, tmp_path: Path) -> None:
        """Test that init creates configuration files."""
        # Change to temp directory
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            result = runner.invoke(app, ["init", "--non-interactive"])

            # Should succeed
            assert result.exit_code == 0

            # Should create .chronicle directory
            chronicle_dir = tmp_path / ".chronicle"
            assert chronicle_dir.exists()

            # Should create config file
            config_file = chronicle_dir / "config.yaml"
            assert config_file.exists()

            # Should create sections directory
            sections_dir = chronicle_dir / "sections"
            assert sections_dir.exists()

        finally:
            os.chdir(original_cwd)

    def test_init_force_overwrites(self, tmp_path: Path) -> None:
        """Test that --force overwrites existing config."""
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # First init
            runner.invoke(app, ["init", "--non-interactive"])

            # Modify config
            config_file = tmp_path / ".chronicle" / "config.yaml"
            config_file.write_text("# Modified")

            # Second init without force should fail
            result = runner.invoke(app, ["init", "--non-interactive"])
            assert result.exit_code == 1

            # Second init with force should succeed
            result = runner.invoke(app, ["init", "--force", "--non-interactive"])
            assert result.exit_code == 0

            # Config should be reset
            assert "Modified" not in config_file.read_text()

        finally:
            os.chdir(original_cwd)


class TestchronicleValidate:
    """Integration tests for `chronicle validate` command."""

    def test_validate_valid_template(self, tmp_path: Path) -> None:
        """Test that validate accepts valid Jinja2 template."""
        template = tmp_path / "test.md.j2"
        template.write_text("# {{ title }}\n\n{{ content }}")

        result = runner.invoke(app, ["validate", str(template)])

        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    def test_validate_invalid_template(self, tmp_path: Path) -> None:
        """Test that validate rejects invalid Jinja2 template."""
        template = tmp_path / "bad.md.j2"
        template.write_text("# {{ title }\n\n{% for %}")  # Invalid syntax

        result = runner.invoke(app, ["validate", str(template)])

        assert result.exit_code == 1
        assert "error" in result.output.lower()
