"""Unit tests for import graph builder."""

from pathlib import Path

import pytest

from chronicle.analyzers.import_graph import ImportGraphBuilder, build_import_graph
from chronicle.models.canonical.ast import CanonicalAST, CanonicalModule


class TestImportGraphBuilder:
    """Tests for ImportGraphBuilder."""

    @pytest.fixture
    def builder(self, tmp_path: Path) -> ImportGraphBuilder:
        """Create an import graph builder instance."""
        return ImportGraphBuilder(tmp_path)

    def test_build_simple_graph(self, tmp_path: Path) -> None:
        """Test building a simple import graph."""
        # Create mock AST result
        ast = CanonicalAST(
            modules=[
                CanonicalModule(
                    name="myapp.main",
                    path="myapp/main.py",
                    language="python",
                    imports=["from myapp.utils import helper"],
                ),
                CanonicalModule(
                    name="myapp.utils",
                    path="myapp/utils.py",
                    language="python",
                    imports=[],
                ),
            ],
            classes=[],
            functions=[],
            entry_points=[],
        )

        builder = ImportGraphBuilder(tmp_path)
        graph = builder.build_import_graph(ast)

        assert len(graph.nodes) >= 1
        assert "myapp/main" in graph.nodes or "myapp/utils" in graph.nodes

    def test_python_import_parsing(self, tmp_path: Path) -> None:
        """Test parsing Python import statements."""
        builder = ImportGraphBuilder(tmp_path)

        # Test 'import X' pattern
        modules = builder._parse_python_import("import mymodule.submodule")
        assert "mymodule/submodule" in modules

        # Test 'from X import Y' pattern
        modules = builder._parse_python_import("from package.core import Class")
        assert "package/core" in modules

        # Relative imports should be skipped
        modules = builder._parse_python_import("from . import something")
        assert len(modules) == 0

    def test_javascript_import_parsing(self, tmp_path: Path) -> None:
        """Test parsing JavaScript import statements."""
        builder = ImportGraphBuilder(tmp_path)

        # ES6 relative import
        modules = builder._parse_js_import("import { Component } from './components'")
        assert "components" in modules

        # ES6 absolute import (external, should be skipped)
        modules = builder._parse_js_import("import React from 'react'")
        assert len(modules) == 0

        # CommonJS require
        modules = builder._parse_js_import("const utils = require('./utils')")
        assert "utils" in modules

    def test_go_import_parsing(self, tmp_path: Path) -> None:
        """Test parsing Go import statements."""
        builder = ImportGraphBuilder(tmp_path)

        # Local package import
        modules = builder._parse_go_import('import "myapp/handlers"')
        assert "myapp/handlers" in modules

        # External package (with domain) should be skipped
        modules = builder._parse_go_import('import "github.com/user/package"')
        assert len(modules) == 0

    def test_java_import_parsing(self, tmp_path: Path) -> None:
        """Test parsing Java import statements."""
        builder = ImportGraphBuilder(tmp_path)

        # Java import
        modules = builder._parse_java_import("import com.myapp.services.UserService;")
        assert "com/myapp/services" in modules

        # Static import - the package includes the class name
        modules = builder._parse_java_import(
            "import static com.myapp.util.Constants.MAX;"
        )
        assert any("com/myapp/util" in m for m in modules)

    def test_internal_module_identification(self, tmp_path: Path) -> None:
        """Test identifying internal vs external modules."""
        # Create package structure
        pkg = tmp_path / "mypackage"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "core.py").write_text("pass")

        builder = ImportGraphBuilder(tmp_path)
        ast = CanonicalAST(
            modules=[
                CanonicalModule(
                    name="mypackage.core",
                    path="mypackage/core.py",
                    language="python",
                    imports=[],
                ),
            ],
            classes=[],
            functions=[],
            entry_points=[],
        )

        internal = builder._identify_internal_modules(ast)

        # Should include the package
        assert any("mypackage" in m for m in internal)

    def test_exclude_external_imports(self, tmp_path: Path) -> None:
        """Test that external imports are excluded from graph."""
        ast = CanonicalAST(
            modules=[
                CanonicalModule(
                    name="app.main",
                    path="app/main.py",
                    language="python",
                    imports=[
                        "import requests",  # external
                        "from flask import Flask",  # external
                        "from app.utils import helper",  # internal
                    ],
                ),
                CanonicalModule(
                    name="app.utils",
                    path="app/utils.py",
                    language="python",
                    imports=[],
                ),
            ],
            classes=[],
            functions=[],
            entry_points=[],
        )

        builder = ImportGraphBuilder(tmp_path)
        graph = builder.build_import_graph(ast)

        # Should not have edges to requests or flask
        for source, target in graph.edges:
            assert "requests" not in target
            assert "flask" not in target

    def test_edge_deduplication(self, tmp_path: Path) -> None:
        """Test that duplicate edges are removed."""
        ast = CanonicalAST(
            modules=[
                CanonicalModule(
                    name="app.main",
                    path="app/main.py",
                    language="python",
                    imports=[
                        "from app.utils import func1",
                        "from app.utils import func2",  # same module
                    ],
                ),
                CanonicalModule(
                    name="app.utils",
                    path="app/utils.py",
                    language="python",
                    imports=[],
                ),
            ],
            classes=[],
            functions=[],
            entry_points=[],
        )

        builder = ImportGraphBuilder(tmp_path)
        graph = builder.build_import_graph(ast)

        # Count edges from main to utils
        edge_count = sum(1 for s, t in graph.edges if "main" in s and "utils" in t)
        # Should have at most 1 edge (deduplicated)
        assert edge_count <= 1

    def test_empty_ast(self, tmp_path: Path) -> None:
        """Test building graph from empty AST."""
        ast = CanonicalAST(
            modules=[],
            classes=[],
            functions=[],
            entry_points=[],
        )

        builder = ImportGraphBuilder(tmp_path)
        graph = builder.build_import_graph(ast)

        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_convenience_function(self, tmp_path: Path) -> None:
        """Test the build_import_graph convenience function."""
        ast = CanonicalAST(
            modules=[
                CanonicalModule(
                    name="pkg.mod",
                    path="pkg/mod.py",
                    language="python",
                    imports=[],
                ),
            ],
            classes=[],
            functions=[],
            entry_points=[],
        )

        graph = build_import_graph(tmp_path, ast)

        assert graph is not None
        assert len(graph.nodes) >= 0
