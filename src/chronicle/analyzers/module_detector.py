"""Module detection for flow-based documentation.

Detects code modules/packages at the directory level for generating
module-level summaries instead of function-by-function explanations.
"""

import logging
from collections import defaultdict
from pathlib import Path

from chronicle.models.canonical.ast import (
    CanonicalAST,
    CanonicalClass,
    CanonicalFunction,
)
from chronicle.models.canonical.module import CanonicalModule

logger = logging.getLogger(__name__)


class ModuleDetector:
    """Detects modules in a codebase based on language-specific conventions.

    Module detection rules:
    - Python: Directory with __init__.py or standalone .py file
    - JavaScript/TypeScript: Directory with index.js/ts or standalone file
    - Go: Directory (Go package)
    - Java: Directory matching package structure
    """

    # File extensions that indicate module entry points
    MODULE_ENTRY_FILES = {
        "python": ["__init__.py"],
        "javascript": ["index.js", "index.mjs", "index.cjs"],
        "typescript": ["index.ts", "index.tsx"],
        "go": [],  # Any .go file in directory makes it a module
        "java": [],  # Package structure from directory
    }

    # File extensions by language
    LANGUAGE_EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".go": "go",
        ".java": "java",
    }

    def __init__(self, repo_path: Path) -> None:
        """Initialize the module detector.

        Args:
            repo_path: Path to repository root
        """
        self.repo_path = repo_path

    def detect_modules(
        self, ast_result: CanonicalAST | None = None
    ) -> list[CanonicalModule]:
        """Detect modules in the repository.

        Modules are detected by examining directory structure and looking for
        language-specific module entry points.

        Args:
            ast_result: Optional AST analysis result to enrich module info

        Returns:
            List of detected modules
        """
        modules: dict[str, CanonicalModule] = {}

        # Group files by directory
        file_groups = self._group_files_by_directory()

        # Detect modules for each directory group
        for dir_path, files in file_groups.items():
            module = self._detect_module_from_directory(dir_path, files)
            if module:
                modules[module.path] = module

        # Enrich with AST data if available
        if ast_result:
            self._enrich_with_ast(modules, ast_result)

        logger.info(f"Detected {len(modules)} modules")
        return list(modules.values())

    def _group_files_by_directory(self) -> dict[str, list[Path]]:
        """Group source files by their containing directory.

        Returns:
            Dictionary mapping directory path to list of source files
        """
        groups: dict[str, list[Path]] = defaultdict(list)

        # Find all source files
        for ext in self.LANGUAGE_EXTENSIONS:
            for file_path in self.repo_path.rglob(f"*{ext}"):
                # Skip common non-source directories
                rel_path = file_path.relative_to(self.repo_path)
                if self._should_skip_path(rel_path):
                    continue

                # Group by parent directory
                parent = str(rel_path.parent) if rel_path.parent != Path(".") else "."
                groups[parent].append(file_path)

        return groups

    def _should_skip_path(self, rel_path: Path) -> bool:
        """Check if a path should be skipped (non-source directories).

        Matches DEFAULT_EXCLUDE_PATTERNS from repomix adapter for consistency.

        Args:
            rel_path: Path relative to repository root

        Returns:
            True if path should be skipped
        """
        skip_dirs = {
            # Test directories (FR-031: exclude non-source directories)
            "tests",
            "test",
            "spec",
            "specs",
            "__tests__",
            # Version control
            ".git",
            # Virtual environments
            ".venv",
            "venv",
            "vendor",
            # Node/JS
            "node_modules",
            # Python build artifacts
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            ".eggs",
            ".tox",
            ".nox",
            # Build outputs
            "dist",
            "build",
            "coverage",
            "htmlcov",
            # IDE directories
            ".idea",
            ".vscode",
        }

        parts = rel_path.parts
        for part in parts:
            if part in skip_dirs or part.endswith(".egg-info"):
                return True
        return False

    def _detect_module_from_directory(
        self, dir_path: str, files: list[Path]
    ) -> CanonicalModule | None:
        """Detect a module from a directory and its files.

        Args:
            dir_path: Directory path relative to repo root
            files: Source files in the directory

        Returns:
            CanonicalModule if directory is a module, None otherwise
        """
        if not files:
            return None

        # Determine primary language
        language = self._detect_primary_language(files)
        if not language:
            return None

        # Check if this directory qualifies as a module
        if not self._is_module_directory(dir_path, files, language):
            # For Python, also check if it's just source files without __init__.py
            # (standalone scripts)
            if language == "python" and len(files) == 1:
                # Single Python file is a module by itself
                pass
            elif language in ("javascript", "typescript", "go", "java"):
                # These languages treat any directory with source files as a module
                pass
            else:
                return None

        # Create module
        module_name = self._derive_module_name(dir_path)
        rel_files = [str(f.relative_to(self.repo_path)) for f in files]

        return CanonicalModule(
            name=module_name,
            path=dir_path,
            files=rel_files,
            language=language,
            classes=[],
            functions=[],
            imports=[],
        )

    def _detect_primary_language(self, files: list[Path]) -> str | None:
        """Detect the primary language of files in a directory.

        Args:
            files: List of source files

        Returns:
            Primary language name or None
        """
        lang_counts: dict[str, int] = defaultdict(int)

        for f in files:
            lang = self.LANGUAGE_EXTENSIONS.get(f.suffix.lower())
            if lang:
                lang_counts[lang] += 1

        if not lang_counts:
            return None

        # Return language with most files
        return max(lang_counts, key=lang_counts.get)  # type: ignore[arg-type]

    def _is_module_directory(
        self, dir_path: str, files: list[Path], language: str
    ) -> bool:
        """Check if a directory qualifies as a module.

        Args:
            dir_path: Directory path
            files: Files in the directory
            language: Primary language

        Returns:
            True if directory is a module
        """
        file_names = {f.name for f in files}
        entry_files = self.MODULE_ENTRY_FILES.get(language, [])

        # Python: needs __init__.py for package (or single file for script)
        if language == "python":
            return "__init__.py" in file_names or len(files) > 0

        # JavaScript/TypeScript: any directory with source files is a module
        if language in ("javascript", "typescript"):
            return len(files) > 0

        # Go: any directory with .go files is a package
        if language == "go":
            return any(f.suffix == ".go" for f in files)

        # Java: any directory with .java files is a package
        if language == "java":
            return any(f.suffix == ".java" for f in files)

        return False

    def _derive_module_name(self, dir_path: str) -> str:
        """Derive a human-readable module name from directory path.

        Args:
            dir_path: Directory path

        Returns:
            Module name
        """
        if dir_path == ".":
            return "root"

        # Use the directory name, replacing path separators
        parts = Path(dir_path).parts

        # Skip common prefixes like 'src', 'lib', 'pkg'
        skip_prefixes = {"src", "lib", "pkg", "app", "internal"}
        filtered_parts = [p for p in parts if p not in skip_prefixes]

        if not filtered_parts:
            filtered_parts = list(parts)

        return "/".join(filtered_parts)

    def _enrich_with_ast(
        self, modules: dict[str, CanonicalModule], ast_result: CanonicalAST
    ) -> None:
        """Enrich modules with AST-derived information.

        Args:
            modules: Detected modules to enrich
            ast_result: AST analysis result
        """
        # Map files to modules
        file_to_module: dict[str, CanonicalModule] = {}
        for module in modules.values():
            for file_path in module.files:
                file_to_module[file_path] = module

        # Add classes to modules
        for cls in ast_result.classes:
            if cls.file in file_to_module:
                module = file_to_module[cls.file]
                if cls.name not in module.classes:
                    module.classes.append(cls.name)

        # Add functions to modules
        for func in ast_result.functions:
            if func.file in file_to_module:
                module = file_to_module[func.file]
                if func.name not in module.functions:
                    module.functions.append(func.name)

        # Extract imports from modules
        for module in ast_result.modules:
            # Match by path
            if module.path in modules:
                modules[module.path].imports = module.imports


def detect_modules(
    repo_path: Path, ast_result: CanonicalAST | None = None
) -> list[CanonicalModule]:
    """Detect modules in a repository.

    Convenience function for module detection.

    Args:
        repo_path: Path to repository root
        ast_result: Optional AST analysis to enrich module info

    Returns:
        List of detected modules
    """
    detector = ModuleDetector(repo_path)
    return detector.detect_modules(ast_result)
