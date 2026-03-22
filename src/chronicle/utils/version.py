"""Version history tracking (SC-011).

Tracks document version history for audit purposes:
- Who made the change (Human or chronicle)
- When the change was made (timestamp)
- What git ref was used
- Summary of changes
"""

import hashlib
import json
import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from chronicle.models.analysis import AuthorType, VersionEntry

if TYPE_CHECKING:
    from chronicle.models.analysis import AnalysisResult

logger = logging.getLogger(__name__)


class VersionTracker:
    """Tracks document version history for reproducibility and audit.

    Provides methods to:
    - Get current git ref
    - Create version entries
    - Compare outputs for reproducibility testing
    """

    def __init__(self, repo_path: Path | None = None) -> None:
        """Initialize version tracker.

        Args:
            repo_path: Path to git repository
        """
        self.repo_path = repo_path or Path.cwd()

    def get_git_ref(self) -> str | None:
        """Get current git commit SHA.

        Returns:
            Commit SHA if available, None otherwise
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return None

    def get_git_branch(self) -> str | None:
        """Get current git branch name.

        Returns:
            Branch name if available, None otherwise
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return None

    def get_git_remote_url(self) -> str | None:
        """Get git remote origin URL.

        Returns:
            Remote URL if available, None otherwise
        """
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return None

    def create_automated_entry(
        self,
        version: str,
        changes: str,
    ) -> VersionEntry:
        """Create a version entry for chronicle-generated content.

        Args:
            version: Version identifier (e.g., "1.0.0")
            changes: Summary of changes

        Returns:
            VersionEntry for the automated update
        """
        return VersionEntry(
            version=version,
            timestamp=datetime.now(UTC),
            author="chronicle",
            author_type=AuthorType.AUTOMATED,
            changes=changes,
            git_ref=self.get_git_ref(),
        )

    def create_human_entry(
        self,
        version: str,
        author: str,
        changes: str,
    ) -> VersionEntry:
        """Create a version entry for human-authored content.

        Args:
            version: Version identifier
            author: Human author name
            changes: Summary of changes

        Returns:
            VersionEntry for the human update
        """
        return VersionEntry(
            version=version,
            timestamp=datetime.now(UTC),
            author=author,
            author_type=AuthorType.HUMAN,
            changes=changes,
            git_ref=self.get_git_ref(),
        )

    def increment_version(self, current: str, bump: str = "patch") -> str:
        """Increment a semantic version string.

        Args:
            current: Current version (e.g., "1.0.0")
            bump: Type of bump ("major", "minor", "patch")

        Returns:
            Incremented version string
        """
        try:
            parts = current.split(".")
            major = int(parts[0]) if len(parts) > 0 else 0
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0

            if bump == "major":
                major += 1
                minor = 0
                patch = 0
            elif bump == "minor":
                minor += 1
                patch = 0
            else:  # patch
                patch += 1

            return f"{major}.{minor}.{patch}"
        except (ValueError, IndexError):
            return "1.0.0"

    @staticmethod
    def compare_outputs(output1: str, output2: str) -> tuple[bool, list[str]]:
        """Compare two outputs for reproducibility testing.

        Per SC-005: Minor variations in punctuation or filler words are acceptable.

        Args:
            output1: First output string
            output2: Second output string

        Returns:
            Tuple of (are_identical, list_of_differences)
        """
        # Split into lines for comparison
        lines1 = output1.strip().split("\n")
        lines2 = output2.strip().split("\n")

        differences: list[str] = []

        # Check line count
        if len(lines1) != len(lines2):
            differences.append(f"Line count differs: {len(lines1)} vs {len(lines2)}")

        # Compare lines
        max_lines = max(len(lines1), len(lines2))
        for i in range(max_lines):
            line1 = lines1[i] if i < len(lines1) else "<missing>"
            line2 = lines2[i] if i < len(lines2) else "<missing>"

            if line1 != line2:
                # Check if difference is just whitespace/punctuation
                normalized1 = _normalize_for_comparison(line1)
                normalized2 = _normalize_for_comparison(line2)

                if normalized1 != normalized2:
                    differences.append(
                        f"Line {i + 1} differs:\n  - {line1}\n  + {line2}"
                    )

        return len(differences) == 0, differences

    def _get_history_file(self) -> Path:
        """Get path to version history file."""
        return self.repo_path / ".chronicle" / "version_history.json"

    def load_history(self) -> list[VersionEntry]:
        """Load version history from file.

        Returns:
            List of version entries, newest first
        """
        history_file = self._get_history_file()
        if not history_file.exists():
            return []

        try:
            data = json.loads(history_file.read_text(encoding="utf-8"))
            entries = []
            for entry_data in data.get("entries", []):
                entries.append(
                    VersionEntry(
                        version=entry_data["version"],
                        timestamp=datetime.fromisoformat(entry_data["timestamp"]),
                        author=entry_data["author"],
                        author_type=AuthorType(entry_data["author_type"]),
                        changes=entry_data["changes"],
                        git_ref=entry_data.get("git_ref"),
                    )
                )
            return entries
        except Exception as e:
            logger.warning("Failed to load version history: %s", e)
            return []

    def save_entry(self, entry: VersionEntry) -> None:
        """Save a version entry to history.

        Args:
            entry: Version entry to save
        """
        history_file = self._get_history_file()
        history_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing history
        history = self.load_history()

        # Add new entry
        history.insert(0, entry)

        # Serialize to JSON
        data = {
            "entries": [
                {
                    "version": e.version,
                    "timestamp": e.timestamp.isoformat(),
                    "author": e.author,
                    "author_type": e.author_type.value,
                    "changes": e.changes,
                    "git_ref": e.git_ref,
                }
                for e in history
            ]
        }

        history_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.debug("Saved version entry %s to %s", entry.version, history_file)

    def create_version_entry(
        self,
        result: "AnalysisResult",
        output_path: Path,
    ) -> VersionEntry | None:
        """Create a version entry for the current analysis run.

        Args:
            result: Analysis result
            output_path: Path where output was written

        Returns:
            VersionEntry or None if version couldn't be determined
        """
        # Load existing history to determine next version
        history = self.load_history()

        if history:
            current_version = history[0].version
            next_version = self.increment_version(current_version, "patch")
        else:
            next_version = "1.0.0"

        # Build changes summary
        changes_parts = []
        if result.technology_stack:
            ts = result.technology_stack
            changes_parts.append(
                f"Analyzed {len(ts.languages)} languages, "
                f"{len(ts.dependencies)} dependencies"
            )

        if result.sbom:
            changes_parts.append(f"SBOM: {result.sbom.package_count} packages")

        if result.architecture:
            arch = result.architecture
            changes_parts.append(f"Architecture: {arch.graph.node_count} resources")

        if result.errors:
            changes_parts.append(f"{len(result.errors)} analysis warning(s)")

        changes = "; ".join(changes_parts) if changes_parts else "Documentation updated"

        return self.create_automated_entry(next_version, changes)

    def get_content_hash(self, content: str) -> str:
        """Get a hash of content for change detection.

        Args:
            content: Content to hash

        Returns:
            SHA256 hash of content
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]


def _normalize_for_comparison(text: str) -> str:
    """Normalize text for reproducibility comparison.

    Removes acceptable variations per SC-005:
    - Extra whitespace
    - Punctuation variations
    - Filler words (the, an, a)
    """
    import re

    # Lowercase
    text = text.lower()

    # Remove extra whitespace
    text = " ".join(text.split())

    # Remove common punctuation variations
    text = re.sub(r"[.,;:!?]", "", text)

    # Remove filler words (careful to preserve meaning)
    # Only remove when they're standalone words
    text = re.sub(r"\bthe\b", "", text)
    text = re.sub(r"\ban\b", "", text)
    text = re.sub(r"\ba\b", "", text)

    # Clean up multiple spaces again
    text = " ".join(text.split())

    return text
