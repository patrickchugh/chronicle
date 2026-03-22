"""Repomix adapter for codebase compression (Principle V: Tool Agnosticism).

Repomix compresses codebases into AI-friendly format using tree-sitter
skeleton extraction, achieving ~70% token reduction while preserving
function signatures and structure for holistic LLM analysis.
"""

import logging
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from chronicle.models.canonical import CompressedCodebase

logger = logging.getLogger(__name__)

# Default patterns to exclude from compression
# Per FR-031: Exclude non-source directories
DEFAULT_EXCLUDE_PATTERNS: list[str] = [
    "tests/*",
    "test/*",
    "spec/*",
    "specs/*",
    "__tests__/*",
    "node_modules/*",
    "dist/*",
    "build/*",
    "coverage/*",
    "__pycache__/*",
    ".venv/*",
    "venv/*",
    "vendor/*",
    ".git/*",
    ".tox/*",
    ".mypy_cache/*",
    ".pytest_cache/*",
    "*.egg-info/*",
    ".eggs/*",
]


class RepomixAdapter:
    """Adapter for running Repomix codebase compression.

    Implements Principle V: Tool Agnosticism by wrapping the external
    Repomix tool and producing CompressedCodebase.

    Usage:
        adapter = RepomixAdapter()
        result = adapter.compress(repo_path)
    """

    def __init__(
        self,
        exclude_patterns: list[str] | None = None,
        timeout: int = 300,
    ) -> None:
        """Initialize Repomix adapter.

        Args:
            exclude_patterns: Patterns to exclude (uses DEFAULT_EXCLUDE_PATTERNS if None)
            timeout: Timeout in seconds for Repomix execution
        """
        self.exclude_patterns = exclude_patterns or DEFAULT_EXCLUDE_PATTERNS.copy()
        self.timeout = timeout
        self._repomix_cmd = self._find_repomix()

    def _find_repomix(self) -> list[str]:
        """Find Repomix command (global or npx).

        Returns:
            Command list to execute Repomix

        Raises:
            RuntimeError: If Repomix is not found
        """
        # Try global installation
        if shutil.which("repomix"):
            return ["repomix"]

        # Try npx
        if shutil.which("npx"):
            return ["npx", "repomix"]

        raise RuntimeError("Repomix not found. Install via: npm install -g repomix")

    def compress(
        self,
        repo_path: Path,
        output_path: Path | None = None,
        additional_excludes: list[str] | None = None,
    ) -> CompressedCodebase:
        """Compress a repository using Repomix.

        Uses --compress flag for tree-sitter skeleton extraction.

        Args:
            repo_path: Path to the repository to compress
            output_path: Optional path for output file (uses temp if None)
            additional_excludes: Additional patterns to exclude

        Returns:
            CompressedCodebase with compressed content

        Raises:
            RuntimeError: If Repomix execution fails
        """
        repo_path = Path(repo_path).resolve()

        if not repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")

        # Build exclude patterns
        excludes = self.exclude_patterns.copy()
        if additional_excludes:
            excludes.extend(additional_excludes)

        # Use temp file if no output path specified
        if output_path is None:
            temp_dir = tempfile.mkdtemp(prefix="repomix_")
            output_path = Path(temp_dir) / "repomix-output.txt"

        # Build command
        cmd = self._repomix_cmd + [
            "--compress",  # Use tree-sitter skeleton extraction
            "--output",
            str(output_path),
        ]

        # Add exclude patterns
        for pattern in excludes:
            cmd.extend(["--ignore", pattern])

        logger.info("Running Repomix on %s", repo_path)
        logger.debug("Command: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            if result.returncode != 0:
                logger.error("Repomix failed: %s", result.stderr)
                raise RuntimeError(f"Repomix failed: {result.stderr}")

            # Parse output
            return self._parse_output(
                output_path=output_path,
                source_path=repo_path,
                excludes=excludes,
                stdout=result.stdout,
            )

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Repomix timed out after {self.timeout}s")
        except Exception as e:
            logger.error("Repomix error: %s", e)
            raise RuntimeError(f"Repomix error: {e}") from e

    def _parse_output(
        self,
        output_path: Path,
        source_path: Path,
        excludes: list[str],
        stdout: str,
    ) -> CompressedCodebase:
        """Parse Repomix output into canonical format.

        Args:
            output_path: Path to Repomix output file
            source_path: Original repository path
            excludes: Exclude patterns used
            stdout: Repomix stdout for metadata

        Returns:
            CompressedCodebase with compressed content
        """
        if not output_path.exists():
            raise RuntimeError(f"Repomix output file not found: {output_path}")

        content = output_path.read_text(encoding="utf-8")

        # Extract metadata from stdout if available
        token_count = self._extract_token_count(stdout)
        file_count = self._extract_file_count(stdout)
        version = self._extract_version(stdout)

        return CompressedCodebase(
            compressed_content=content,
            token_count=token_count,
            file_count=file_count,
            excluded_patterns=excludes,
            source_path=source_path,
            timestamp=datetime.now(UTC),
            tool_version=version,
        )

    def _extract_token_count(self, stdout: str) -> int:
        """Extract token count from Repomix output."""
        # Repomix outputs "Token count: X" or similar
        for line in stdout.split("\n"):
            if "token" in line.lower():
                # Try to extract number
                import re

                match = re.search(r"(\d+)", line)
                if match:
                    return int(match.group(1))
        return 0

    def _extract_file_count(self, stdout: str) -> int:
        """Extract file count from Repomix output."""
        for line in stdout.split("\n"):
            if "file" in line.lower() and (
                "processed" in line.lower() or "packed" in line.lower()
            ):
                import re

                match = re.search(r"(\d+)", line)
                if match:
                    return int(match.group(1))
        return 0

    def _extract_version(self, stdout: str) -> str | None:
        """Extract Repomix version from output."""
        for line in stdout.split("\n"):
            if "repomix" in line.lower() and (
                "v" in line.lower() or "version" in line.lower()
            ):
                import re

                match = re.search(r"v?(\d+\.\d+\.\d+)", line)
                if match:
                    return match.group(1)
        return None

    def get_version(self) -> str | None:
        """Get Repomix version.

        Returns:
            Version string or None if unable to determine
        """
        try:
            result = subprocess.run(
                self._repomix_cmd + ["--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip().split("\n")[0]
        except Exception:
            pass
        return None
