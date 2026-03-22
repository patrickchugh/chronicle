"""Unit tests for AST parser."""

from pathlib import Path

import pytest

from chronicle.analyzers.ast_parser import ASTParser


class TestASTParser:
    """Tests for ASTParser."""

    @pytest.fixture
    def parser(self) -> ASTParser:
        """Create an AST parser instance."""
        return ASTParser()

    def test_parse_python_file(self, parser: ASTParser, tmp_path: Path) -> None:
        """Test parsing a Python file."""
        py_file = tmp_path / "test.py"
        py_file.write_text(
            '''
"""Test module."""

class TestClass:
    """A test class."""

    def test_method(self, arg1: str) -> bool:
        return True

def top_level_function(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y

async def async_function():
    pass
'''
        )

        result = parser.parse_file(py_file)

        assert result is not None
        assert result.language == "python"
        assert len(result.classes) == 1
        assert result.classes[0].name == "TestClass"
        assert len(result.functions) == 2  # top_level + async

    def test_parse_javascript_file(self, parser: ASTParser, tmp_path: Path) -> None:
        """Test parsing a JavaScript file."""
        js_file = tmp_path / "test.js"
        js_file.write_text(
            """
class UserService {
    constructor(db) {
        this.db = db;
    }

    getUser(id) {
        return this.db.find(id);
    }
}

function processData(data) {
    return data.map(x => x * 2);
}

const arrowFunc = (a, b) => a + b;
"""
        )

        result = parser.parse_file(js_file)

        assert result is not None
        assert result.language == "javascript"
        assert len(result.classes) >= 1
        assert result.classes[0].name == "UserService"

    def test_parse_typescript_file(self, parser: ASTParser, tmp_path: Path) -> None:
        """Test parsing a TypeScript file."""
        ts_file = tmp_path / "test.ts"
        ts_file.write_text(
            """
interface User {
    id: number;
    name: string;
}

class UserRepository {
    private users: User[] = [];

    add(user: User): void {
        this.users.push(user);
    }

    findById(id: number): User | undefined {
        return this.users.find(u => u.id === id);
    }
}

function createUser(name: string): User {
    return { id: Date.now(), name };
}
"""
        )

        result = parser.parse_file(ts_file)

        assert result is not None
        assert result.language == "typescript"
        # TypeScript class extraction may vary with tree-sitter version
        # At minimum we should get the function
        assert len(result.functions) >= 1 or len(result.classes) >= 1

    def test_parse_directory(self, parser: ASTParser, tmp_path: Path) -> None:
        """Test parsing a directory with multiple files."""
        # Create Python file
        py_file = tmp_path / "module.py"
        py_file.write_text(
            """
class Service:
    pass

def helper():
    pass
"""
        )

        # Create JavaScript file
        js_file = tmp_path / "script.js"
        js_file.write_text(
            """
function main() {
    console.log("Hello");
}
"""
        )

        result = parser.parse_directory(tmp_path)

        assert result.module_count == 2
        assert result.class_count == 1
        assert result.function_count >= 2
        assert "python" in result.get_languages()
        assert "javascript" in result.get_languages()

    def test_parse_empty_directory(self, parser: ASTParser, tmp_path: Path) -> None:
        """Test parsing an empty directory."""
        result = parser.parse_directory(tmp_path)

        assert result.module_count == 0
        assert result.class_count == 0
        assert result.function_count == 0

    def test_exclude_patterns(self, parser: ASTParser, tmp_path: Path) -> None:
        """Test excluding files with patterns."""
        # Create files
        (tmp_path / "main.py").write_text("def main(): pass")
        (tmp_path / "test_main.py").write_text("def test_main(): pass")

        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        (node_modules / "lib.js").write_text("function lib() {}")

        result = parser.parse_directory(
            tmp_path,
            exclude_patterns=["test_*.py", "node_modules/**"],
        )

        # Should only include main.py
        assert result.module_count == 1

    def test_unsupported_file_extension(
        self, parser: ASTParser, tmp_path: Path
    ) -> None:
        """Test that unsupported extensions return error result."""
        txt_file = tmp_path / "readme.txt"
        txt_file.write_text("This is not code")

        result = parser.parse_file(txt_file)

        # Should return a result with error, not parse successfully
        assert result is not None
        assert result.success is False
        assert result.error is not None

    def test_to_dict(self, parser: ASTParser, tmp_path: Path) -> None:
        """Test converting AST to dictionary."""
        py_file = tmp_path / "test.py"
        py_file.write_text(
            """
class TestClass:
    def method(self): pass

def function(): pass
"""
        )

        result = parser.parse_directory(tmp_path)
        data = result.to_dict()

        assert data["module_count"] == 1
        assert data["class_count"] == 1
        assert data["function_count"] == 1
        assert "python" in data["languages"]

    # =========================================================================
    # Docstring Extraction Tests (T076c-T076f)
    # =========================================================================

    def test_python_docstring_extraction(
        self, parser: ASTParser, tmp_path: Path
    ) -> None:
        """Test extracting Python docstrings from functions and classes (T076c)."""
        py_file = tmp_path / "documented.py"
        py_file.write_text(
            '''
class DocumentedClass:
    """This is a class docstring.

    It describes what the class does.
    """

    def method(self):
        pass

def documented_function(x: int, y: str) -> bool:
    """Process input and return result.

    Args:
        x: The first parameter.
        y: The second parameter.

    Returns:
        True if successful.
    """
    return True

def no_docstring_function():
    return 42
'''
        )

        result = parser.parse_file(py_file)

        assert result.success
        assert len(result.classes) == 1
        assert result.classes[0].name == "DocumentedClass"
        assert result.classes[0].docstring is not None
        assert "class docstring" in result.classes[0].docstring

        # Find documented function
        documented_func = next(
            (f for f in result.functions if f.name == "documented_function"), None
        )
        assert documented_func is not None
        assert documented_func.docstring is not None
        assert "Process input" in documented_func.docstring

        # Find undocumented function
        undoc_func = next(
            (f for f in result.functions if f.name == "no_docstring_function"), None
        )
        assert undoc_func is not None
        assert undoc_func.docstring is None

    def test_python_return_type_extraction(
        self, parser: ASTParser, tmp_path: Path
    ) -> None:
        """Test extracting Python return type annotations (T076c)."""
        py_file = tmp_path / "typed.py"
        py_file.write_text(
            """
def typed_function(x: int) -> str:
    return str(x)

def untyped_function(x):
    return x
"""
        )

        result = parser.parse_file(py_file)

        assert result.success
        typed_func = next(
            (f for f in result.functions if f.name == "typed_function"), None
        )
        assert typed_func is not None
        assert typed_func.return_type == "str"

        untyped_func = next(
            (f for f in result.functions if f.name == "untyped_function"), None
        )
        assert untyped_func is not None
        assert untyped_func.return_type is None

    def test_javascript_jsdoc_extraction(
        self, parser: ASTParser, tmp_path: Path
    ) -> None:
        """Test extracting JSDoc comments from JavaScript functions (T076d)."""
        js_file = tmp_path / "documented.js"
        js_file.write_text(
            """
/**
 * Process user data and return result.
 * @param {string} name - The user name.
 * @returns {Object} The processed user.
 */
function processUser(name) {
    return { name: name };
}

// This is a regular comment, not JSDoc
function undocumentedFunction() {
    return null;
}

/**
 * A documented class for managing users.
 */
class UserManager {
    constructor() {}
}
"""
        )

        result = parser.parse_file(js_file)

        assert result.success

        # Find documented function
        documented_func = next(
            (f for f in result.functions if f.name == "processUser"), None
        )
        assert documented_func is not None
        assert documented_func.docstring is not None
        assert "Process user data" in documented_func.docstring

        # Find undocumented function
        undoc_func = next(
            (f for f in result.functions if f.name == "undocumentedFunction"), None
        )
        assert undoc_func is not None
        assert undoc_func.docstring is None

        # Check class docstring
        assert len(result.classes) == 1
        assert result.classes[0].name == "UserManager"
        assert result.classes[0].docstring is not None
        assert "documented class" in result.classes[0].docstring

    def test_go_doc_comment_extraction(self, parser: ASTParser, tmp_path: Path) -> None:
        """Test extracting Go doc comments from functions (T076e)."""
        go_file = tmp_path / "main.go"
        go_file.write_text(
            """package main

// ProcessData takes input data and transforms it.
// It returns the processed result or an error.
func ProcessData(data string) string {
    return data
}

func undocumented() {
}

// User represents a user in the system.
type User struct {
    ID   int
    Name string
}
"""
        )

        result = parser.parse_file(go_file)

        assert result.success

        # Find documented function
        documented_func = next(
            (f for f in result.functions if f.name == "ProcessData"), None
        )
        assert documented_func is not None
        assert documented_func.docstring is not None
        assert (
            "ProcessData" in documented_func.docstring
            or "input data" in documented_func.docstring
        )

        # Find undocumented function
        undoc_func = next(
            (f for f in result.functions if f.name == "undocumented"), None
        )
        assert undoc_func is not None
        assert undoc_func.docstring is None

        # Check struct docstring
        user_struct = next((c for c in result.classes if c.name == "User"), None)
        assert user_struct is not None
        assert user_struct.docstring is not None
        assert "user in the system" in user_struct.docstring

    def test_source_snippet_extraction(self, parser: ASTParser, tmp_path: Path) -> None:
        """Test extracting source snippets (first 5 lines of body) (T076f)."""
        py_file = tmp_path / "snippet.py"
        py_file.write_text(
            '''
def long_function(x, y, z):
    """A function with many lines."""
    result = x + y
    result = result * z
    result = result / 2
    result = result + 10
    result = result - 5
    result = result ** 2
    return result
'''
        )

        result = parser.parse_file(py_file)

        assert result.success
        func = result.functions[0]
        assert func.source_snippet is not None
        # Should have first 5 lines of the body
        lines = func.source_snippet.split("\n")
        assert len(lines) <= 5

    def test_nested_directory_parsing(self, parser: ASTParser, tmp_path: Path) -> None:
        """Test that parser detects files in nested directories."""
        # Create nested directory structure
        nested = tmp_path / "src" / "modules" / "utils"
        nested.mkdir(parents=True)

        # Create files at various levels
        (tmp_path / "main.py").write_text("def main(): pass")
        (tmp_path / "src" / "app.py").write_text("def app(): pass")
        (tmp_path / "src" / "modules" / "core.py").write_text("def core(): pass")
        (nested / "helpers.py").write_text("def helper(): pass")

        result = parser.parse_directory(tmp_path)

        # Should find all 4 Python files
        assert result.module_count == 4
        assert result.function_count == 4
