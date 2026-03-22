"""Unit tests for core models."""

from datetime import UTC
from pathlib import Path

import pytest

from chronicle.models import AnalysisError, Repository, VersionEntry
from chronicle.models.analysis import AuthorType


class TestRepository:
    """Tests for Repository entity."""

    def test_create_from_path(self, tmp_path: Path) -> None:
        """Test creating a repository from a path."""
        repo = Repository.from_path(tmp_path)

        assert repo.path == tmp_path.resolve()
        assert repo.name == tmp_path.name
        assert repo.git_ref is None
        assert repo.detected_languages == []

    def test_create_with_custom_name(self, tmp_path: Path) -> None:
        """Test creating a repository with a custom name."""
        repo = Repository.from_path(tmp_path, name="my-project")

        assert repo.name == "my-project"

    def test_validate_existing_directory(self, tmp_path: Path) -> None:
        """Test validating an existing directory."""
        repo = Repository.from_path(tmp_path)
        warnings = repo.validate()

        # Should warn about missing .git directory
        assert len(warnings) == 1
        assert ".git" in warnings[0]

    def test_validate_with_git_directory(self, tmp_path: Path) -> None:
        """Test validating a directory with .git."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        repo = Repository.from_path(tmp_path)
        warnings = repo.validate()

        assert len(warnings) == 0
        assert repo.is_git_repo is True

    def test_validate_nonexistent_path(self) -> None:
        """Test validating a non-existent path."""
        repo = Repository(path=Path("/nonexistent/path"), name="test")

        with pytest.raises(ValueError, match="does not exist"):
            repo.validate()

    def test_validate_file_path(self, tmp_path: Path) -> None:
        """Test validating a file path (not directory)."""
        file_path = tmp_path / "file.txt"
        file_path.touch()

        repo = Repository(path=file_path, name="test")

        with pytest.raises(ValueError, match="not a directory"):
            repo.validate()

    def test_path_converted_to_absolute(self) -> None:
        """Test that relative paths are converted to absolute."""
        repo = Repository(path=Path("."), name="test")

        assert repo.path.is_absolute()

    def test_is_git_repo_false_without_git(self, tmp_path: Path) -> None:
        """Test is_git_repo returns False without .git directory."""
        repo = Repository.from_path(tmp_path)

        assert repo.is_git_repo is False


class TestAnalysisError:
    """Tests for AnalysisError entity."""

    def test_create_error(self) -> None:
        """Test creating an analysis error."""
        error = AnalysisError(
            component="syft",
            message="Tool not found",
            file_path="/path/to/file",
            recoverable=True,
        )

        assert error.component == "syft"
        assert error.message == "Tool not found"
        assert error.file_path == "/path/to/file"
        assert error.recoverable is True

    def test_to_dict(self) -> None:
        """Test converting error to dictionary."""
        error = AnalysisError(
            component="ast",
            message="Parse error",
            recoverable=False,
        )

        data = error.to_dict()

        assert data["component"] == "ast"
        assert data["message"] == "Parse error"
        assert data["file_path"] is None
        assert data["recoverable"] is False


class TestVersionEntry:
    """Tests for VersionEntry entity (SC-011)."""

    def test_create_automated_entry(self) -> None:
        """Test creating an automated version entry."""
        entry = VersionEntry.create_automated(
            version="1.0.0",
            changes="Initial documentation",
            git_ref="abc123",
        )

        assert entry.version == "1.0.0"
        assert entry.author == "chronicle"
        assert entry.author_type == AuthorType.AUTOMATED
        assert entry.changes == "Initial documentation"
        assert entry.git_ref == "abc123"
        assert entry.timestamp.tzinfo is not None  # UTC aware

    def test_to_dict(self) -> None:
        """Test converting entry to dictionary."""
        entry = VersionEntry.create_automated(
            version="1.0.0",
            changes="Test",
        )

        data = entry.to_dict()

        assert data["version"] == "1.0.0"
        assert data["author"] == "chronicle"
        assert data["author_type"] == "automated"
        assert "timestamp" in data

    def test_human_entry(self) -> None:
        """Test creating a human-authored entry."""
        from datetime import datetime

        entry = VersionEntry(
            version="1.1.0",
            timestamp=datetime.now(UTC),
            author="John Doe",
            author_type=AuthorType.HUMAN,
            changes="Updated security section",
        )

        assert entry.author == "John Doe"
        assert entry.author_type == AuthorType.HUMAN
