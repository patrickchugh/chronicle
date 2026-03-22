"""Canonical AST format (Principle V: Tool Agnosticism).

Standard AST analysis format produced by all AST tool adapters (tree-sitter, etc.).
Provides a unified view of code structure across Python, JavaScript, TypeScript, Go, and Java.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class CanonicalModule:
    """Standard module/package representation.

    Attributes:
        name: Module/package name
        path: File path
        language: Programming language
        imports: Import statements
    """

    name: str
    path: str
    language: str
    imports: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "path": self.path,
            "language": self.language,
            "imports": self.imports,
        }


@dataclass
class CanonicalClass:
    """Standard class representation.

    Attributes:
        name: Class name
        file: File path
        line: Line number
        methods: Method names
        bases: Base classes
        docstring: Extracted class docstring (T071e)
        description: LLM-generated explanation of class responsibility (T071f)
    """

    name: str
    file: str
    line: int
    methods: list[str] = field(default_factory=list)
    bases: list[str] = field(default_factory=list)
    docstring: str | None = None
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "name": self.name,
            "file": self.file,
            "line": self.line,
            "methods": self.methods,
            "bases": self.bases,
        }
        if self.docstring is not None:
            result["docstring"] = self.docstring
        if self.description is not None:
            result["description"] = self.description
        return result


@dataclass
class CanonicalFunction:
    """Standard function representation.

    Attributes:
        name: Function name
        file: File path
        line: Line number
        parameters: Parameter names
        is_async: Whether function is async
        docstring: Extracted docstring/JSDoc/Go comment (T071a)
        return_type: Return type annotation if available (T071b)
        source_snippet: First N lines of function body for LLM context (T071c)
        description: LLM-generated explanation of function behavior (T071d)
    """

    name: str
    file: str
    line: int
    parameters: list[str] = field(default_factory=list)
    is_async: bool = False
    docstring: str | None = None
    return_type: str | None = None
    source_snippet: str | None = None
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "name": self.name,
            "file": self.file,
            "line": self.line,
            "parameters": self.parameters,
            "is_async": self.is_async,
        }
        if self.docstring is not None:
            result["docstring"] = self.docstring
        if self.return_type is not None:
            result["return_type"] = self.return_type
        if self.source_snippet is not None:
            result["source_snippet"] = self.source_snippet
        if self.description is not None:
            result["description"] = self.description
        return result


@dataclass
class CanonicalEntryPoint:
    """Standard entry point representation.

    Attributes:
        name: Entry point name
        type: Type ("main", "cli_command", "api_endpoint", "handler")
        file: File path
        line: Line number
    """

    name: str
    type: str
    file: str
    line: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "type": self.type,
            "file": self.file,
            "line": self.line,
        }


@dataclass
class ASTSource:
    """Metadata about how the AST was parsed.

    Attributes:
        tool: Parser used (e.g., "tree-sitter")
        languages: Languages parsed
        files_parsed: Number of files successfully parsed
        files_failed: Number of files that failed to parse
        parsed_at: When parsing was performed
    """

    tool: str
    languages: list[str]
    files_parsed: int
    files_failed: int
    parsed_at: datetime

    def __post_init__(self) -> None:
        """Ensure timestamp is timezone-aware UTC."""
        if self.parsed_at.tzinfo is None:
            self.parsed_at = self.parsed_at.replace(tzinfo=UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tool": self.tool,
            "languages": self.languages,
            "files_parsed": self.files_parsed,
            "files_failed": self.files_failed,
            "parsed_at": self.parsed_at.isoformat(),
        }


@dataclass
class CanonicalAST:
    """Standard AST analysis format produced by all AST tool adapters.

    This is the canonical internal format that the rest of chronicle consumes.
    Tool adapters (tree-sitter, etc.) MUST transform their output into this format.

    Attributes:
        modules: Detected modules/packages
        classes: Class definitions
        functions: Top-level functions
        entry_points: Main functions, CLI commands, API endpoints
        source: Metadata about parsing
    """

    modules: list[CanonicalModule] = field(default_factory=list)
    classes: list[CanonicalClass] = field(default_factory=list)
    functions: list[CanonicalFunction] = field(default_factory=list)
    entry_points: list[CanonicalEntryPoint] = field(default_factory=list)
    source: ASTSource | None = None

    def add_module(self, module: CanonicalModule) -> None:
        """Add a module to the AST."""
        self.modules.append(module)

    def add_class(self, cls: CanonicalClass) -> None:
        """Add a class to the AST."""
        self.classes.append(cls)

    def add_function(self, func: CanonicalFunction) -> None:
        """Add a function to the AST."""
        self.functions.append(func)

    def add_entry_point(self, entry_point: CanonicalEntryPoint) -> None:
        """Add an entry point to the AST."""
        self.entry_points.append(entry_point)

    def get_classes_in_file(self, file_path: str) -> list[CanonicalClass]:
        """Get all classes in a specific file."""
        return [c for c in self.classes if c.file == file_path]

    def get_functions_in_file(self, file_path: str) -> list[CanonicalFunction]:
        """Get all functions in a specific file."""
        return [f for f in self.functions if f.file == file_path]

    def get_languages(self) -> list[str]:
        """Get list of unique languages in this AST."""
        return sorted(set(m.language for m in self.modules))

    @property
    def module_count(self) -> int:
        """Return total number of modules."""
        return len(self.modules)

    @property
    def class_count(self) -> int:
        """Return total number of classes."""
        return len(self.classes)

    @property
    def function_count(self) -> int:
        """Return total number of functions."""
        return len(self.functions)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result: dict[str, Any] = {
            "modules": [m.to_dict() for m in self.modules],
            "classes": [c.to_dict() for c in self.classes],
            "functions": [f.to_dict() for f in self.functions],
            "entry_points": [e.to_dict() for e in self.entry_points],
            "module_count": self.module_count,
            "class_count": self.class_count,
            "function_count": self.function_count,
            "languages": self.get_languages(),
        }
        if self.source:
            result["source"] = self.source.to_dict()
        return result
