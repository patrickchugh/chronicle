"""Unit tests for module detector."""

from pathlib import Path

import pytest

from chronicle.analyzers.module_detector import ModuleDetector, detect_modules


class TestModuleDetector:
    """Tests for ModuleDetector."""

    @pytest.fixture
    def detector(self, tmp_path: Path) -> ModuleDetector:
        """Create a module detector instance."""
        return ModuleDetector(tmp_path)

    def test_detect_python_package(self, tmp_path: Path) -> None:
        """Test detecting a Python package with __init__.py."""
        # Create package structure
        pkg_dir = tmp_path / "mypackage"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("# Package init")
        (pkg_dir / "module1.py").write_text("def func1(): pass")
        (pkg_dir / "module2.py").write_text("class MyClass: pass")

        detector = ModuleDetector(tmp_path)
        modules = detector.detect_modules()

        assert len(modules) == 1
        assert modules[0].name == "mypackage"
        assert modules[0].language == "python"
        assert len(modules[0].files) == 3

    def test_detect_multiple_packages(self, tmp_path: Path) -> None:
        """Test detecting multiple Python packages."""
        # Create two packages
        for name in ["pkg_a", "pkg_b"]:
            pkg = tmp_path / name
            pkg.mkdir()
            (pkg / "__init__.py").write_text("")
            (pkg / "core.py").write_text("pass")

        detector = ModuleDetector(tmp_path)
        modules = detector.detect_modules()

        assert len(modules) == 2
        names = {m.name for m in modules}
        assert "pkg_a" in names
        assert "pkg_b" in names

    def test_detect_nested_packages(self, tmp_path: Path) -> None:
        """Test detecting nested Python packages."""
        # Create nested package structure
        parent = tmp_path / "parent"
        parent.mkdir()
        (parent / "__init__.py").write_text("")

        child = parent / "child"
        child.mkdir()
        (child / "__init__.py").write_text("")
        (child / "module.py").write_text("pass")

        detector = ModuleDetector(tmp_path)
        modules = detector.detect_modules()

        # Should detect both parent and child as modules
        assert len(modules) >= 1
        names = {m.name for m in modules}
        assert "parent" in names or "parent/child" in names

    def test_detect_javascript_module(self, tmp_path: Path) -> None:
        """Test detecting JavaScript module with index.js."""
        # Create JS module structure
        js_dir = tmp_path / "jsmodule"
        js_dir.mkdir()
        (js_dir / "index.js").write_text("export default {};")
        (js_dir / "utils.js").write_text("export function util() {}")

        detector = ModuleDetector(tmp_path)
        modules = detector.detect_modules()

        assert len(modules) == 1
        assert modules[0].name == "jsmodule"
        assert modules[0].language == "javascript"

    def test_detect_typescript_module(self, tmp_path: Path) -> None:
        """Test detecting TypeScript module with index.ts."""
        # Create TS module structure
        ts_dir = tmp_path / "tsmodule"
        ts_dir.mkdir()
        (ts_dir / "index.ts").write_text("export interface Config {}")
        (ts_dir / "helpers.ts").write_text("export function helper(): void {}")

        detector = ModuleDetector(tmp_path)
        modules = detector.detect_modules()

        assert len(modules) == 1
        assert modules[0].name == "tsmodule"
        assert modules[0].language == "typescript"

    def test_exclude_common_directories(self, tmp_path: Path) -> None:
        """Test that common directories are excluded."""
        # Create directories that should be excluded
        for exclude_dir in ["node_modules", ".venv", "__pycache__"]:
            dir_path = tmp_path / exclude_dir
            dir_path.mkdir()
            (dir_path / "__init__.py").write_text("")
            (dir_path / "module.py").write_text("pass")

        # Create valid package
        valid = tmp_path / "valid_package"
        valid.mkdir()
        (valid / "__init__.py").write_text("")

        detector = ModuleDetector(tmp_path)
        modules = detector.detect_modules()

        # Should only detect valid_package
        assert len(modules) == 1
        assert modules[0].name == "valid_package"

    def test_detect_module_files(self, tmp_path: Path) -> None:
        """Test that module files are correctly detected."""
        pkg = tmp_path / "mylib"
        pkg.mkdir()
        (pkg / "__init__.py").write_text(
            """
from .core import CoreClass
from .utils import helper_function
"""
        )
        (pkg / "core.py").write_text("class CoreClass: pass")
        (pkg / "utils.py").write_text("def helper_function(): pass")

        detector = ModuleDetector(tmp_path)
        modules = detector.detect_modules()

        assert len(modules) == 1
        # Should detect all files
        assert len(modules[0].files) == 3

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Test detecting modules in empty directory."""
        detector = ModuleDetector(tmp_path)
        modules = detector.detect_modules()

        assert len(modules) == 0

    def test_convenience_function(self, tmp_path: Path) -> None:
        """Test the detect_modules convenience function."""
        pkg = tmp_path / "testpkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")

        modules = detect_modules(tmp_path)

        assert len(modules) == 1
        assert modules[0].name == "testpkg"

    def test_files_list_accuracy(self, tmp_path: Path) -> None:
        """Test that files list is accurate."""
        pkg = tmp_path / "counted"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "a.py").write_text("pass")
        (pkg / "b.py").write_text("pass")
        (pkg / "c.py").write_text("pass")

        detector = ModuleDetector(tmp_path)
        modules = detector.detect_modules()

        assert len(modules) == 1
        assert len(modules[0].files) == 4  # __init__ + 3 modules
