"""Entry point detection for flow-based documentation.

Detects public entry points in a codebase:
- CLI commands (Typer, Click, argparse)
- API endpoints (FastAPI, Flask, Express, Django)
- Main functions (if __name__ == "__main__")
- Lambda/Cloud function handlers
"""

import logging
import re
from pathlib import Path

from chronicle.models.canonical.module import EntryPoint

logger = logging.getLogger(__name__)


class EntryPointDetector:
    """Detects entry points across multiple frameworks and languages.

    Entry points are public interfaces where external systems interact with the code:
    - CLI commands
    - API endpoints
    - Event handlers
    - Main functions
    """

    # Patterns for detecting decorators (Python)
    PYTHON_DECORATOR_PATTERNS = {
        # Typer CLI
        r'@app\.command\s*\(\s*["\']?(\w*)["\']?\s*\)': ("cli_command", "typer"),
        r'@cli\.command\s*\(\s*["\']?(\w*)["\']?\s*\)': ("cli_command", "typer"),
        # Click CLI
        r'@click\.command\s*\(\s*["\']?(\w*)["\']?\s*\)': ("cli_command", "click"),
        r'@cli\.command\s*\(\s*["\']?(\w*)["\']?\s*\)': ("cli_command", "click"),
        # FastAPI
        r'@app\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']': (
            "api_endpoint",
            "fastapi",
        ),
        r'@router\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']': (
            "api_endpoint",
            "fastapi",
        ),
        # Flask
        r'@app\.route\s*\(\s*["\']([^"\']+)["\']': ("api_endpoint", "flask"),
        r'@bp\.route\s*\(\s*["\']([^"\']+)["\']': ("api_endpoint", "flask"),
        r'@blueprint\.route\s*\(\s*["\']([^"\']+)["\']': ("api_endpoint", "flask"),
    }

    # Patterns for JavaScript/TypeScript
    JS_PATTERNS = {
        # Express.js
        r'app\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']': (
            "api_endpoint",
            "express",
        ),
        r'router\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']': (
            "api_endpoint",
            "express",
        ),
    }

    def __init__(self, repo_path: Path) -> None:
        """Initialize the entry point detector.

        Args:
            repo_path: Path to repository root
        """
        self.repo_path = repo_path

    def detect_entry_points(
        self, file_paths: list[Path] | None = None
    ) -> list[EntryPoint]:
        """Detect entry points in the repository.

        Args:
            file_paths: Optional specific files to scan. If None, scans all supported files.

        Returns:
            List of detected entry points
        """
        entry_points: list[EntryPoint] = []

        if file_paths is None:
            file_paths = self._find_source_files()

        for file_path in file_paths:
            try:
                file_entry_points = self._detect_in_file(file_path)
                entry_points.extend(file_entry_points)
            except Exception as e:
                logger.warning(f"Failed to detect entry points in {file_path}: {e}")

        # Deduplicate by (name, file, line)
        seen: set[tuple[str, str, int]] = set()
        unique_entry_points: list[EntryPoint] = []
        for ep in entry_points:
            key = (ep.name, ep.file, ep.line)
            if key not in seen:
                seen.add(key)
                unique_entry_points.append(ep)

        logger.info(f"Detected {len(unique_entry_points)} entry points")
        return unique_entry_points

    def _find_source_files(self) -> list[Path]:
        """Find all source files in the repository.

        Returns:
            List of source file paths
        """
        extensions = [".py", ".js", ".ts", ".tsx", ".go", ".java"]
        skip_dirs = {
            ".git",
            ".venv",
            "venv",
            "node_modules",
            "__pycache__",
            "dist",
            "build",
            "tests",
            "test",
            "spec",
            "specs",
        }

        files: list[Path] = []
        for ext in extensions:
            for file_path in self.repo_path.rglob(f"*{ext}"):
                # Skip excluded directories
                if any(skip_dir in file_path.parts for skip_dir in skip_dirs):
                    continue
                files.append(file_path)

        return files

    def _detect_in_file(self, file_path: Path) -> list[EntryPoint]:
        """Detect entry points in a single file.

        Args:
            file_path: Path to source file

        Returns:
            List of entry points found in the file
        """
        entry_points: list[EntryPoint] = []
        rel_path = str(file_path.relative_to(self.repo_path))

        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.split("\n")
        except (UnicodeDecodeError, PermissionError):
            return []

        suffix = file_path.suffix.lower()

        if suffix == ".py":
            entry_points.extend(
                self._detect_python_entry_points(rel_path, content, lines)
            )
        elif suffix in (".js", ".ts", ".tsx", ".mjs"):
            entry_points.extend(self._detect_js_entry_points(rel_path, content, lines))
        elif suffix == ".go":
            entry_points.extend(self._detect_go_entry_points(rel_path, content, lines))
        elif suffix == ".java":
            entry_points.extend(
                self._detect_java_entry_points(rel_path, content, lines)
            )

        return entry_points

    def _detect_python_entry_points(
        self, file_path: str, content: str, lines: list[str]
    ) -> list[EntryPoint]:
        """Detect Python entry points (decorators and main blocks)."""
        entry_points: list[EntryPoint] = []

        # Track decorator matches to find the function they decorate
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            # Check for decorator patterns
            for pattern, (ep_type, framework) in self.PYTHON_DECORATOR_PATTERNS.items():
                match = re.search(pattern, stripped)
                if match:
                    # Get the function name from the next non-decorator line
                    func_name, func_line, docstring = self._find_decorated_function(
                        lines, line_num - 1
                    )
                    if func_name:
                        # Determine entry point name
                        if ep_type == "api_endpoint":
                            # For API endpoints, use the path
                            if "fastapi" in framework or "flask" in framework:
                                groups = match.groups()
                                if len(groups) >= 2:
                                    method = groups[0].upper()
                                    path = groups[1]
                                    name = f"{method} {path}"
                                else:
                                    path = groups[0] if groups else func_name
                                    name = path
                                    method = None
                            else:
                                name = func_name
                                method = None
                                path = None

                            entry_points.append(
                                EntryPoint(
                                    name=name,
                                    type=ep_type,
                                    file=file_path,
                                    line=func_line,
                                    description=docstring,
                                    method=method if "method" in dir() else None,
                                )
                            )
                        else:
                            # For CLI commands
                            cmd_name = match.group(1) if match.groups() else func_name
                            if not cmd_name:
                                cmd_name = func_name
                            entry_points.append(
                                EntryPoint(
                                    name=cmd_name,
                                    type=ep_type,
                                    file=file_path,
                                    line=func_line,
                                    description=docstring,
                                )
                            )

            # Check for if __name__ == "__main__" pattern
            if "__name__" in stripped and "__main__" in stripped:
                entry_points.append(
                    EntryPoint(
                        name="__main__",
                        type="main",
                        file=file_path,
                        line=line_num,
                        description="Main entry point",
                    )
                )

        return entry_points

    def _find_decorated_function(
        self, lines: list[str], decorator_line_idx: int
    ) -> tuple[str | None, int, str | None]:
        """Find the function following a decorator.

        Args:
            lines: All lines in the file
            decorator_line_idx: Index of the decorator line

        Returns:
            Tuple of (function_name, line_number, docstring)
        """
        # Look for 'def' or 'async def' after the decorator
        for i in range(
            decorator_line_idx + 1, min(decorator_line_idx + 10, len(lines))
        ):
            line = lines[i].strip()

            # Skip other decorators
            if line.startswith("@"):
                continue

            # Check for function definition
            match = re.match(r"(?:async\s+)?def\s+(\w+)\s*\(", line)
            if match:
                func_name = match.group(1)
                line_num = i + 1

                # Try to extract docstring
                docstring = self._extract_python_docstring(lines, i)
                return func_name, line_num, docstring

        return None, 0, None

    def _extract_python_docstring(
        self, lines: list[str], func_line_idx: int
    ) -> str | None:
        """Extract docstring from a Python function.

        Args:
            lines: All lines in the file
            func_line_idx: Index of the function definition line

        Returns:
            Docstring content or None
        """
        # Look for docstring in the lines following the function definition
        for i in range(func_line_idx + 1, min(func_line_idx + 5, len(lines))):
            line = lines[i].strip()
            if line.startswith('"""') or line.startswith("'''"):
                # Single-line docstring
                if line.count('"""') >= 2 or line.count("'''") >= 2:
                    return line.strip("\"'").strip()
                # Multi-line docstring - just get first line
                return line.strip("\"'").strip()
            elif line and not line.startswith("#"):
                # Non-empty, non-comment line before docstring
                break
        return None

    def _detect_js_entry_points(
        self, file_path: str, content: str, lines: list[str]
    ) -> list[EntryPoint]:
        """Detect JavaScript/TypeScript entry points."""
        entry_points: list[EntryPoint] = []

        for line_num, line in enumerate(lines, 1):
            for pattern, (ep_type, framework) in self.JS_PATTERNS.items():
                match = re.search(pattern, line)
                if match:
                    groups = match.groups()
                    if len(groups) >= 2:
                        method = groups[0].upper()
                        path = groups[1]
                        name = f"{method} {path}"
                    else:
                        name = groups[0] if groups else "unknown"
                        method = None

                    entry_points.append(
                        EntryPoint(
                            name=name,
                            type=ep_type,
                            file=file_path,
                            line=line_num,
                            method=method,
                        )
                    )

        # Check for exports.handler (Lambda)
        if "exports.handler" in content or "export const handler" in content:
            for line_num, line in enumerate(lines, 1):
                if "exports.handler" in line or "export const handler" in line:
                    entry_points.append(
                        EntryPoint(
                            name="handler",
                            type="handler",
                            file=file_path,
                            line=line_num,
                            description="Lambda/Cloud function handler",
                        )
                    )
                    break

        return entry_points

    def _detect_go_entry_points(
        self, file_path: str, content: str, lines: list[str]
    ) -> list[EntryPoint]:
        """Detect Go entry points."""
        entry_points: list[EntryPoint] = []

        for line_num, line in enumerate(lines, 1):
            # Check for main function
            if re.match(r"\s*func\s+main\s*\(\s*\)", line):
                entry_points.append(
                    EntryPoint(
                        name="main",
                        type="main",
                        file=file_path,
                        line=line_num,
                    )
                )

            # Check for HTTP handlers (common patterns)
            handler_match = re.search(
                r'http\.HandleFunc\s*\(\s*["\']([^"\']+)["\']', line
            )
            if handler_match:
                path = handler_match.group(1)
                entry_points.append(
                    EntryPoint(
                        name=path,
                        type="api_endpoint",
                        file=file_path,
                        line=line_num,
                    )
                )

        return entry_points

    def _detect_java_entry_points(
        self, file_path: str, content: str, lines: list[str]
    ) -> list[EntryPoint]:
        """Detect Java entry points."""
        entry_points: list[EntryPoint] = []

        for line_num, line in enumerate(lines, 1):
            # Check for main method
            if "public static void main" in line:
                entry_points.append(
                    EntryPoint(
                        name="main",
                        type="main",
                        file=file_path,
                        line=line_num,
                    )
                )

            # Check for Spring endpoints
            spring_match = re.search(
                r'@(GetMapping|PostMapping|PutMapping|DeleteMapping|RequestMapping)\s*\(\s*["\']?([^"\')\s]*)',
                line,
            )
            if spring_match:
                mapping_type = spring_match.group(1)
                path = spring_match.group(2) or "/"

                method_map = {
                    "GetMapping": "GET",
                    "PostMapping": "POST",
                    "PutMapping": "PUT",
                    "DeleteMapping": "DELETE",
                    "RequestMapping": None,
                }
                method = method_map.get(mapping_type)

                entry_points.append(
                    EntryPoint(
                        name=f"{method + ' ' if method else ''}{path}",
                        type="api_endpoint",
                        file=file_path,
                        line=line_num,
                        method=method,
                    )
                )

        return entry_points


def detect_entry_points(
    repo_path: Path, file_paths: list[Path] | None = None
) -> list[EntryPoint]:
    """Detect entry points in a repository.

    Convenience function for entry point detection.

    Args:
        repo_path: Path to repository root
        file_paths: Optional specific files to scan

    Returns:
        List of detected entry points
    """
    detector = EntryPointDetector(repo_path)
    return detector.detect_entry_points(file_paths)
