"""Import graph analysis for flow-based documentation.

Extracts import relationships between modules to generate system flow diagrams.
"""

import logging
import re
from pathlib import Path

from chronicle.models.canonical.ast import CanonicalAST, CanonicalModule
from chronicle.models.canonical.module import ImportGraph

logger = logging.getLogger(__name__)


class ImportGraphBuilder:
    """Builds a directed graph of module import relationships.

    Extracts imports from AST analysis and filters to internal modules only,
    excluding external packages like 'requests', 'numpy', etc.
    """

    def __init__(self, repo_path: Path) -> None:
        """Initialize the import graph builder.

        Args:
            repo_path: Path to repository root for resolving relative imports
        """
        self.repo_path = repo_path
        self._internal_modules: set[str] = set()

    def build_import_graph(
        self,
        ast_result: CanonicalAST,
        detected_modules: list[CanonicalModule] | None = None,
    ) -> ImportGraph:
        """Build an import graph from AST analysis.

        Args:
            ast_result: Parsed AST containing modules with imports
            detected_modules: Optional list of detected modules to use for filtering

        Returns:
            ImportGraph with nodes and edges representing module dependencies
        """
        # Identify internal modules
        self._internal_modules = self._identify_internal_modules(
            ast_result, detected_modules
        )

        nodes: set[str] = set()
        edges: list[tuple[str, str]] = []

        # Process each module's imports
        for module in ast_result.modules:
            module_name = self._normalize_module_name(module.path)
            if not module_name:
                continue

            nodes.add(module_name)

            # Parse and filter imports
            for import_stmt in module.imports:
                imported_modules = self._parse_import_statement(
                    import_stmt, module.language
                )

                for imported in imported_modules:
                    # Filter to internal modules only
                    normalized = self._normalize_imported_module(imported)
                    if normalized and normalized in self._internal_modules:
                        nodes.add(normalized)
                        edges.append((module_name, normalized))

        # Remove duplicate edges
        edges = list(set(edges))

        logger.info(
            f"Built import graph with {len(nodes)} nodes and {len(edges)} edges"
        )

        return ImportGraph(nodes=sorted(nodes), edges=edges)

    def _identify_internal_modules(
        self,
        ast_result: CanonicalAST,
        detected_modules: list[CanonicalModule] | None = None,
    ) -> set[str]:
        """Identify which modules are internal to the repository.

        Args:
            ast_result: Parsed AST
            detected_modules: Optional detected modules list

        Returns:
            Set of internal module names
        """
        internal: set[str] = set()

        # Add all modules from AST
        for module in ast_result.modules:
            name = self._normalize_module_name(module.path)
            if name:
                internal.add(name)
                # Also add parent packages
                parts = name.split("/")
                for i in range(1, len(parts)):
                    internal.add("/".join(parts[:i]))

        # Add detected modules if provided
        if detected_modules:
            for module in detected_modules:
                internal.add(module.name)
                internal.add(module.path)

        # Also scan for Python package names
        if self.repo_path.exists():
            for init_file in self.repo_path.rglob("__init__.py"):
                rel_path = init_file.parent.relative_to(self.repo_path)
                pkg_name = str(rel_path).replace("/", ".").replace("\\", ".")
                internal.add(pkg_name)
                # Add dotted form
                internal.add(str(rel_path).replace("\\", "/"))

        return internal

    def _normalize_module_name(self, path: str) -> str | None:
        """Normalize a file path to a module name.

        Args:
            path: File path (e.g., 'src/chronicle/cli.py' or '/abs/path/src/chronicle/cli.py')

        Returns:
            Normalized module name (e.g., 'chronicle/cli') or None
        """
        if not path:
            return None

        # Handle absolute paths by making them relative to repo_path
        path_obj = Path(path)
        if path_obj.is_absolute():
            try:
                path = str(path_obj.relative_to(self.repo_path))
            except ValueError:
                # Path is not relative to repo_path, skip it
                return None

        # Remove leading ./ if present
        if path.startswith("./"):
            path = path[2:]

        # Remove file extension
        path_obj = Path(path)
        if path_obj.suffix in (".py", ".js", ".ts", ".tsx", ".go", ".java"):
            path = str(path_obj.with_suffix(""))

        # Remove __init__ suffix for Python packages
        if path.endswith("/__init__"):
            path = path[:-9]

        # Skip common prefixes
        skip_prefixes = ("src/", "lib/", "pkg/", "app/", "internal/")
        for prefix in skip_prefixes:
            if path.startswith(prefix):
                path = path[len(prefix) :]
                break

        return path if path else None

    def _parse_import_statement(self, import_stmt: str, language: str) -> list[str]:
        """Parse an import statement to extract imported module names.

        Args:
            import_stmt: The import statement text
            language: Programming language

        Returns:
            List of imported module names
        """
        if language == "python":
            return self._parse_python_import(import_stmt)
        elif language in ("javascript", "typescript"):
            return self._parse_js_import(import_stmt)
        elif language == "go":
            return self._parse_go_import(import_stmt)
        elif language == "java":
            return self._parse_java_import(import_stmt)
        return []

    def _parse_python_import(self, import_stmt: str) -> list[str]:
        """Parse Python import statements.

        Handles:
        - import foo
        - import foo.bar
        - from foo import bar
        - from foo.bar import baz
        - from . import foo (relative)
        - from ..foo import bar (relative)
        """
        modules: list[str] = []
        import_stmt = import_stmt.strip()

        # "from X import Y" pattern
        from_match = re.match(r"from\s+([\w.]+)\s+import", import_stmt)
        if from_match:
            module = from_match.group(1)
            # Skip relative imports starting with .
            if not module.startswith("."):
                modules.append(module.replace(".", "/"))
            return modules

        # "import X" pattern
        import_match = re.match(r"import\s+([\w.]+)", import_stmt)
        if import_match:
            module = import_match.group(1)
            modules.append(module.replace(".", "/"))

        return modules

    def _parse_js_import(self, import_stmt: str) -> list[str]:
        """Parse JavaScript/TypeScript import statements.

        Handles:
        - import X from 'module'
        - import { X } from 'module'
        - import 'module'
        - const X = require('module')
        """
        modules: list[str] = []
        import_stmt = import_stmt.strip()

        # ES6 import pattern
        es6_match = re.search(r"from\s+['\"]([^'\"]+)['\"]", import_stmt)
        if es6_match:
            module = es6_match.group(1)
            # Only include relative imports (starting with . or ..)
            if module.startswith("."):
                # Normalize path
                modules.append(module.lstrip("./"))
            return modules

        # CommonJS require pattern
        require_match = re.search(
            r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", import_stmt
        )
        if require_match:
            module = require_match.group(1)
            if module.startswith("."):
                modules.append(module.lstrip("./"))

        return modules

    def _parse_go_import(self, import_stmt: str) -> list[str]:
        """Parse Go import statements.

        Handles:
        - import "package"
        - import alias "package"
        - import (
            "package1"
            "package2"
          )
        """
        modules: list[str] = []

        # Find all quoted strings in import
        matches = re.findall(r'"([^"]+)"', import_stmt)
        for module in matches:
            # Only include if it looks like a local import (doesn't contain domain)
            if "." not in module.split("/")[0]:
                modules.append(module)

        return modules

    def _parse_java_import(self, import_stmt: str) -> list[str]:
        """Parse Java import statements.

        Handles:
        - import com.example.package.Class;
        - import static com.example.package.Class.method;
        """
        modules: list[str] = []
        import_stmt = import_stmt.strip()

        # Match import statement
        match = re.match(r"import\s+(?:static\s+)?([\w.]+);?", import_stmt)
        if match:
            # Get the package (everything before the last dot, which is the class)
            full_path = match.group(1)
            parts = full_path.split(".")
            if len(parts) > 1:
                package = "/".join(parts[:-1])
                modules.append(package)

        return modules

    def _normalize_imported_module(self, imported: str) -> str | None:
        """Normalize an imported module name for comparison.

        Args:
            imported: Imported module name

        Returns:
            Normalized name or None if should be filtered out
        """
        if not imported:
            return None

        # Normalize path separators
        imported = imported.replace("\\", "/")

        # Remove common prefixes used in imports
        if imported.startswith("./"):
            imported = imported[2:]
        if imported.startswith("../"):
            # Parent imports are hard to resolve, skip them
            return None

        return imported


def build_import_graph(
    repo_path: Path,
    ast_result: CanonicalAST,
    detected_modules: list[CanonicalModule] | None = None,
) -> ImportGraph:
    """Build an import graph from AST analysis.

    Convenience function for import graph building.

    Args:
        repo_path: Path to repository root
        ast_result: Parsed AST containing modules with imports
        detected_modules: Optional list of detected modules

    Returns:
        ImportGraph with module dependencies
    """
    builder = ImportGraphBuilder(repo_path)
    return builder.build_import_graph(ast_result, detected_modules)
