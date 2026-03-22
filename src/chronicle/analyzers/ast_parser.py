"""Multi-language AST parsing via tree-sitter.

Extracts code structure (modules, classes, functions, entry points) from:
- Python (.py)
- JavaScript (.js)
- TypeScript (.ts)
- Go (.go)
- Java (.java)

All output is transformed to CanonicalAST format (Principle V: Tool Agnosticism).

NOTE: tree-sitter is a required dependency. Per Principle III (Preflight Validation),
all dependencies must be verified before analysis begins. No fallback parsing is
implemented - if tree-sitter fails, analysis fails.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Maximum number of lines to include in source snippets
MAX_SNIPPET_LINES = 5

from chronicle.models.canonical import (
    ASTSource,
    CanonicalAST,
    CanonicalClass,
    CanonicalEntryPoint,
    CanonicalFunction,
    CanonicalModule,
)
from chronicle.utils.logging import get_logger

_logger = get_logger()

# Language to file extension mapping
LANGUAGE_EXTENSIONS: dict[str, list[str]] = {
    "python": [".py"],
    "javascript": [".js", ".mjs", ".cjs"],
    "typescript": [".ts", ".tsx"],
    "go": [".go"],
    "java": [".java"],
}

# Reverse mapping: extension to language
EXTENSION_TO_LANGUAGE: dict[str, str] = {}
for lang, exts in LANGUAGE_EXTENSIONS.items():
    for ext in exts:
        EXTENSION_TO_LANGUAGE[ext] = lang


class TreeSitterUnavailableError(Exception):
    """Raised when tree-sitter is not available.

    Per Principle III (Preflight Validation), tree-sitter must be available
    before analysis begins. Run `chronicle check` to verify dependencies.
    """

    def __init__(self, message: str | None = None) -> None:
        self.message = message or (
            "tree-sitter is not available. "
            "Run `chronicle check` to verify dependencies."
        )
        super().__init__(self.message)


@dataclass
class ParseResult:
    """Result of parsing a single file."""

    file_path: str
    language: str
    success: bool
    module: CanonicalModule | None = None
    classes: list[CanonicalClass] | None = None
    functions: list[CanonicalFunction] | None = None
    entry_points: list[CanonicalEntryPoint] | None = None
    error: str | None = None


class ASTParser:
    """Multi-language AST parser using tree-sitter.

    Provides deterministic code structure extraction for documentation.
    All output is in CanonicalAST format.

    Per Principle III (Preflight Validation), tree-sitter must be installed
    and functional. No fallback parsing is implemented.
    """

    def __init__(self) -> None:
        """Initialize the AST parser."""
        self._parsers: dict[str, Any] = {}
        self._initialized = False
        self._init_error: str | None = None

    def _ensure_initialized(self) -> None:
        """Initialize tree-sitter parsers.

        Raises:
            TreeSitterUnavailableError: If tree-sitter cannot be initialized
        """
        if self._initialized:
            return

        if self._init_error:
            raise TreeSitterUnavailableError(self._init_error)

        try:
            # Import tree-sitter-language-pack
            from tree_sitter_language_pack import get_parser

            # Initialize parsers for each language
            for language in LANGUAGE_EXTENSIONS:
                try:
                    self._parsers[language] = get_parser(language)
                    _logger.debug(f"Initialized tree-sitter parser for {language}")
                except Exception as e:
                    _logger.warning(f"Failed to initialize parser for {language}: {e}")

            if not self._parsers:
                self._init_error = "No language parsers could be initialized"
                raise TreeSitterUnavailableError(self._init_error)

            self._initialized = True

        except ImportError as e:
            self._init_error = f"tree-sitter-language-pack not installed: {e}"
            raise TreeSitterUnavailableError(self._init_error)

    def check_available(self) -> bool:
        """Check if tree-sitter is available.

        Returns:
            True if tree-sitter is functional, False otherwise
        """
        try:
            self._ensure_initialized()
            return True
        except TreeSitterUnavailableError:
            return False

    def get_supported_languages(self) -> list[str]:
        """Get list of languages this parser supports."""
        return list(LANGUAGE_EXTENSIONS.keys())

    def get_language_for_file(self, file_path: Path) -> str | None:
        """Determine the language for a file based on extension.

        Args:
            file_path: Path to the file

        Returns:
            Language name or None if unsupported
        """
        ext = file_path.suffix.lower()
        return EXTENSION_TO_LANGUAGE.get(ext)

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse a single source file.

        Args:
            file_path: Path to source file

        Returns:
            ParseResult with extracted code structure
        """
        language = self.get_language_for_file(file_path)
        if language is None:
            return ParseResult(
                file_path=str(file_path),
                language="unknown",
                success=False,
                error=f"Unsupported file extension: {file_path.suffix}",
            )

        # Ensure tree-sitter is available (no fallback)
        try:
            self._ensure_initialized()
        except TreeSitterUnavailableError as e:
            return ParseResult(
                file_path=str(file_path),
                language=language,
                success=False,
                error=str(e),
            )

        parser = self._parsers.get(language)
        if parser is None:
            return ParseResult(
                file_path=str(file_path),
                language=language,
                success=False,
                error=f"No parser available for {language}",
            )

        try:
            source_code = file_path.read_text(encoding="utf-8")
            tree = parser.parse(bytes(source_code, "utf-8"))

            # Extract based on language
            if language == "python":
                return self._extract_python(file_path, source_code, tree)
            elif language == "javascript":
                return self._extract_javascript(file_path, source_code, tree)
            elif language == "typescript":
                return self._extract_typescript(file_path, source_code, tree)
            elif language == "go":
                return self._extract_go(file_path, source_code, tree)
            elif language == "java":
                return self._extract_java(file_path, source_code, tree)
            else:
                return ParseResult(
                    file_path=str(file_path),
                    language=language,
                    success=False,
                    error=f"No extractor implemented for {language}",
                )

        except Exception as e:
            _logger.warning(f"Failed to parse {file_path}: {e}")
            return ParseResult(
                file_path=str(file_path),
                language=language,
                success=False,
                error=str(e),
            )

    # =========================================================================
    # Docstring and Snippet Extraction Helpers
    # =========================================================================

    def _get_source_snippet(
        self, source_code: str, node: Any, max_lines: int = MAX_SNIPPET_LINES
    ) -> str | None:
        """Extract the first N lines of a function/method body.

        Args:
            source_code: Full source code
            node: AST node containing the body
            max_lines: Maximum number of lines to include

        Returns:
            Source snippet or None if extraction fails
        """
        try:
            body_text = source_code[node.start_byte : node.end_byte]
            lines = body_text.split("\n")
            snippet_lines = lines[:max_lines]
            return "\n".join(snippet_lines).strip() or None
        except Exception:
            return None

    def _extract_python_docstring(self, source_code: str, body_node: Any) -> str | None:
        """Extract Python docstring from function/class body.

        Python docstrings are the first statement in a function/class body
        if that statement is a string literal.

        Args:
            source_code: Full source code
            body_node: The block node containing the body

        Returns:
            Docstring text (without quotes) or None
        """
        if body_node is None:
            return None

        # Find first statement in block
        for child in body_node.children:
            # Direct string node (tree-sitter may represent docstring directly)
            if child.type == "string":
                raw = source_code[child.start_byte : child.end_byte]
                # Strip quotes (""", ''', ", ')
                if raw.startswith('"""') or raw.startswith("'''"):
                    return raw[3:-3].strip()
                elif raw.startswith('"') or raw.startswith("'"):
                    return raw[1:-1].strip()
                return raw.strip()
            # Expression statement wrapping a string (some tree-sitter versions)
            elif child.type == "expression_statement":
                # Check if it's a string literal
                for expr_child in child.children:
                    if expr_child.type == "string":
                        raw = source_code[expr_child.start_byte : expr_child.end_byte]
                        # Strip quotes (""", ''', ", ')
                        if raw.startswith('"""') or raw.startswith("'''"):
                            return raw[3:-3].strip()
                        elif raw.startswith('"') or raw.startswith("'"):
                            return raw[1:-1].strip()
                        return raw.strip()
                break  # Only check first statement
            elif child.type not in ("comment", "pass_statement"):
                # First non-comment statement is not a string
                break
        return None

    def _extract_python_return_type(
        self, source_code: str, func_node: Any
    ) -> str | None:
        """Extract Python return type annotation from function definition.

        Args:
            source_code: Full source code
            func_node: The function_definition node

        Returns:
            Return type annotation as string or None
        """
        for child in func_node.children:
            if child.type == "type":
                return source_code[child.start_byte : child.end_byte].strip()
        return None

    def _extract_jsdoc_comment(self, source_code: str, node: Any) -> str | None:
        """Extract JSDoc comment preceding a function/class.

        JSDoc comments start with /** and appear immediately before the declaration.

        Args:
            source_code: Full source code
            node: The function/class declaration node

        Returns:
            JSDoc comment content (without /** */) or None
        """
        # Look for preceding sibling comments
        prev_sibling = node.prev_sibling
        while prev_sibling:
            if prev_sibling.type == "comment":
                text = source_code[prev_sibling.start_byte : prev_sibling.end_byte]
                if text.startswith("/**"):
                    # Strip /** and */ and clean up * prefixes
                    content = text[3:-2] if text.endswith("*/") else text[3:]
                    lines = content.split("\n")
                    cleaned = []
                    for line in lines:
                        line = line.strip()
                        if line.startswith("*"):
                            line = line[1:].strip()
                        if line:
                            cleaned.append(line)
                    return " ".join(cleaned) if cleaned else None
                # Non-JSDoc comment, skip
                prev_sibling = prev_sibling.prev_sibling
            else:
                break
        return None

    def _extract_go_doc_comment(self, source_code: str, node: Any) -> str | None:
        """Extract Go doc comment preceding a function.

        Go doc comments are consecutive // comments immediately before func.

        Args:
            source_code: Full source code
            node: The function_declaration node

        Returns:
            Combined doc comment text or None
        """
        comments = []
        prev_sibling = node.prev_sibling

        # Collect consecutive comments
        while prev_sibling and prev_sibling.type == "comment":
            text = source_code[prev_sibling.start_byte : prev_sibling.end_byte]
            if text.startswith("//"):
                comments.insert(0, text[2:].strip())
            prev_sibling = prev_sibling.prev_sibling

        return " ".join(comments) if comments else None

    def _extract_javadoc_comment(self, source_code: str, node: Any) -> str | None:
        """Extract Javadoc comment preceding a method/class.

        Javadoc comments start with /** and appear before declarations.

        Args:
            source_code: Full source code
            node: The method/class declaration node

        Returns:
            Javadoc comment content or None
        """
        # Same logic as JSDoc
        return self._extract_jsdoc_comment(source_code, node)

    # =========================================================================
    # Python Extraction
    # =========================================================================

    def _extract_python(
        self, file_path: Path, source_code: str, tree: Any
    ) -> ParseResult:
        """Extract Python code structure using tree-sitter."""
        classes: list[CanonicalClass] = []
        functions: list[CanonicalFunction] = []
        imports: list[str] = []
        entry_points: list[CanonicalEntryPoint] = []

        def visit(node: Any) -> None:
            # Import statements
            if node.type == "import_statement" or node.type == "import_from_statement":
                imports.append(source_code[node.start_byte : node.end_byte])

            # Class definitions
            elif node.type == "class_definition":
                class_name = None
                methods: list[str] = []
                bases: list[str] = []
                class_body = None
                class_docstring = None

                for child in node.children:
                    if child.type == "identifier":
                        class_name = source_code[child.start_byte : child.end_byte]
                    elif child.type == "argument_list":
                        # Base classes
                        for arg in child.children:
                            if arg.type == "identifier":
                                bases.append(source_code[arg.start_byte : arg.end_byte])
                    elif child.type == "block":
                        class_body = child
                        # Extract class docstring
                        class_docstring = self._extract_python_docstring(
                            source_code, child
                        )
                        # Find methods
                        for block_child in child.children:
                            if block_child.type == "function_definition":
                                for fc in block_child.children:
                                    if fc.type == "identifier":
                                        methods.append(
                                            source_code[fc.start_byte : fc.end_byte]
                                        )
                                        break

                if class_name:
                    classes.append(
                        CanonicalClass(
                            name=class_name,
                            file=str(file_path),
                            line=node.start_point[0] + 1,
                            methods=methods,
                            bases=bases,
                            docstring=class_docstring,
                        )
                    )

            # Function definitions (top-level)
            elif node.type == "function_definition" and node.parent.type == "module":
                func_name = None
                params: list[str] = []
                is_async = False
                func_body = None
                return_type = None

                for child in node.children:
                    if child.type == "identifier":
                        func_name = source_code[child.start_byte : child.end_byte]
                    elif child.type == "parameters":
                        for param in child.children:
                            if param.type == "identifier":
                                params.append(
                                    source_code[param.start_byte : param.end_byte]
                                )
                            elif param.type == "typed_parameter":
                                for pc in param.children:
                                    if pc.type == "identifier":
                                        params.append(
                                            source_code[pc.start_byte : pc.end_byte]
                                        )
                                        break
                    elif child.type == "type":
                        # Return type annotation
                        return_type = source_code[child.start_byte : child.end_byte]
                    elif child.type == "block":
                        func_body = child

                # Extract docstring and source snippet
                docstring = self._extract_python_docstring(source_code, func_body)
                source_snippet = (
                    self._get_source_snippet(source_code, func_body)
                    if func_body
                    else None
                )

                if func_name:
                    functions.append(
                        CanonicalFunction(
                            name=func_name,
                            file=str(file_path),
                            line=node.start_point[0] + 1,
                            parameters=params,
                            is_async=is_async,
                            docstring=docstring,
                            return_type=return_type,
                            source_snippet=source_snippet,
                        )
                    )

                    # Check for entry points
                    if func_name == "main":
                        entry_points.append(
                            CanonicalEntryPoint(
                                name="main",
                                type="main",
                                file=str(file_path),
                                line=node.start_point[0] + 1,
                            )
                        )

            # Recurse
            for child in node.children:
                visit(child)

        visit(tree.root_node)

        # Check for if __name__ == "__main__" pattern
        if "__name__" in source_code and "__main__" in source_code:
            # Find the line
            for i, line in enumerate(source_code.split("\n")):
                if "__name__" in line and "__main__" in line:
                    entry_points.append(
                        CanonicalEntryPoint(
                            name="__main__",
                            type="main",
                            file=str(file_path),
                            line=i + 1,
                        )
                    )
                    break

        module = CanonicalModule(
            name=file_path.stem,
            path=str(file_path),
            language="python",
            imports=imports,
        )

        return ParseResult(
            file_path=str(file_path),
            language="python",
            success=True,
            module=module,
            classes=classes,
            functions=functions,
            entry_points=entry_points,
        )

    # =========================================================================
    # JavaScript Extraction
    # =========================================================================

    def _extract_javascript(
        self, file_path: Path, source_code: str, tree: Any
    ) -> ParseResult:
        """Extract JavaScript code structure using tree-sitter."""
        classes: list[CanonicalClass] = []
        functions: list[CanonicalFunction] = []
        imports: list[str] = []
        entry_points: list[CanonicalEntryPoint] = []

        def visit(node: Any) -> None:
            # Import statements
            if node.type == "import_statement":
                imports.append(source_code[node.start_byte : node.end_byte])

            # Class declarations
            elif node.type == "class_declaration":
                class_name = None
                methods: list[str] = []
                bases: list[str] = []
                class_docstring = self._extract_jsdoc_comment(source_code, node)

                for child in node.children:
                    if child.type == "identifier":
                        class_name = source_code[child.start_byte : child.end_byte]
                    elif child.type == "class_heritage":
                        for hc in child.children:
                            if hc.type == "identifier":
                                bases.append(source_code[hc.start_byte : hc.end_byte])
                    elif child.type == "class_body":
                        for method in child.children:
                            if method.type == "method_definition":
                                for mc in method.children:
                                    if mc.type == "property_identifier":
                                        methods.append(
                                            source_code[mc.start_byte : mc.end_byte]
                                        )
                                        break

                if class_name:
                    classes.append(
                        CanonicalClass(
                            name=class_name,
                            file=str(file_path),
                            line=node.start_point[0] + 1,
                            methods=methods,
                            bases=bases,
                            docstring=class_docstring,
                        )
                    )

            # Function declarations
            elif node.type == "function_declaration":
                func_name = None
                params: list[str] = []
                is_async = False
                func_body = None
                jsdoc = self._extract_jsdoc_comment(source_code, node)

                for child in node.children:
                    if child.type == "identifier":
                        func_name = source_code[child.start_byte : child.end_byte]
                    elif child.type == "formal_parameters":
                        for param in child.children:
                            if param.type == "identifier":
                                params.append(
                                    source_code[param.start_byte : param.end_byte]
                                )
                    elif child.type == "statement_block":
                        func_body = child

                source_snippet = (
                    self._get_source_snippet(source_code, func_body)
                    if func_body
                    else None
                )

                if func_name:
                    functions.append(
                        CanonicalFunction(
                            name=func_name,
                            file=str(file_path),
                            line=node.start_point[0] + 1,
                            parameters=params,
                            is_async=is_async,
                            docstring=jsdoc,
                            source_snippet=source_snippet,
                        )
                    )

            # Recurse
            for child in node.children:
                visit(child)

        visit(tree.root_node)

        module = CanonicalModule(
            name=file_path.stem,
            path=str(file_path),
            language="javascript",
            imports=imports,
        )

        return ParseResult(
            file_path=str(file_path),
            language="javascript",
            success=True,
            module=module,
            classes=classes,
            functions=functions,
            entry_points=entry_points,
        )

    # =========================================================================
    # TypeScript Extraction
    # =========================================================================

    def _extract_typescript(
        self, file_path: Path, source_code: str, tree: Any
    ) -> ParseResult:
        """Extract TypeScript code structure using tree-sitter.

        Similar to JavaScript but handles TypeScript-specific constructs.
        """
        # TypeScript is similar enough to JavaScript for basic extraction
        result = self._extract_javascript(file_path, source_code, tree)
        if result.module:
            result.module.language = "typescript"
        result.language = "typescript"
        return result

    # =========================================================================
    # Go Extraction
    # =========================================================================

    def _extract_go(self, file_path: Path, source_code: str, tree: Any) -> ParseResult:
        """Extract Go code structure using tree-sitter."""
        classes: list[CanonicalClass] = []  # Go uses structs
        functions: list[CanonicalFunction] = []
        imports: list[str] = []
        entry_points: list[CanonicalEntryPoint] = []

        def visit(node: Any) -> None:
            # Import declarations
            if node.type == "import_declaration":
                imports.append(source_code[node.start_byte : node.end_byte])

            # Type declarations (structs)
            elif node.type == "type_declaration":
                struct_docstring = self._extract_go_doc_comment(source_code, node)
                for child in node.children:
                    if child.type == "type_spec":
                        struct_name = None
                        for tc in child.children:
                            if tc.type == "type_identifier":
                                struct_name = source_code[tc.start_byte : tc.end_byte]
                                break
                        if struct_name:
                            classes.append(
                                CanonicalClass(
                                    name=struct_name,
                                    file=str(file_path),
                                    line=node.start_point[0] + 1,
                                    methods=[],
                                    bases=[],
                                    docstring=struct_docstring,
                                )
                            )

            # Function declarations
            elif node.type == "function_declaration":
                func_name = None
                params: list[str] = []
                func_body = None
                doc_comment = self._extract_go_doc_comment(source_code, node)
                return_type = None

                for child in node.children:
                    if child.type == "identifier":
                        func_name = source_code[child.start_byte : child.end_byte]
                    elif child.type == "parameter_list":
                        for param in child.children:
                            if param.type == "parameter_declaration":
                                for pc in param.children:
                                    if pc.type == "identifier":
                                        params.append(
                                            source_code[pc.start_byte : pc.end_byte]
                                        )
                    elif child.type == "block":
                        func_body = child
                    elif child.type in (
                        "type_identifier",
                        "pointer_type",
                        "slice_type",
                        "map_type",
                    ):
                        # Return type
                        return_type = source_code[child.start_byte : child.end_byte]
                    elif child.type == "parameter_list" and child != node.children[1]:
                        # Multiple return values (Go returns as tuple)
                        return_type = source_code[child.start_byte : child.end_byte]

                source_snippet = (
                    self._get_source_snippet(source_code, func_body)
                    if func_body
                    else None
                )

                if func_name:
                    functions.append(
                        CanonicalFunction(
                            name=func_name,
                            file=str(file_path),
                            line=node.start_point[0] + 1,
                            parameters=params,
                            is_async=False,
                            docstring=doc_comment,
                            return_type=return_type,
                            source_snippet=source_snippet,
                        )
                    )

                    if func_name == "main":
                        entry_points.append(
                            CanonicalEntryPoint(
                                name="main",
                                type="main",
                                file=str(file_path),
                                line=node.start_point[0] + 1,
                            )
                        )

            # Recurse
            for child in node.children:
                visit(child)

        visit(tree.root_node)

        module = CanonicalModule(
            name=file_path.stem,
            path=str(file_path),
            language="go",
            imports=imports,
        )

        return ParseResult(
            file_path=str(file_path),
            language="go",
            success=True,
            module=module,
            classes=classes,
            functions=functions,
            entry_points=entry_points,
        )

    # =========================================================================
    # Java Extraction
    # =========================================================================

    def _extract_java(
        self, file_path: Path, source_code: str, tree: Any
    ) -> ParseResult:
        """Extract Java code structure using tree-sitter."""
        classes: list[CanonicalClass] = []
        functions: list[CanonicalFunction] = []
        imports: list[str] = []
        entry_points: list[CanonicalEntryPoint] = []

        def visit(node: Any) -> None:
            # Import declarations
            if node.type == "import_declaration":
                imports.append(source_code[node.start_byte : node.end_byte])

            # Class declarations
            elif node.type == "class_declaration":
                class_name = None
                methods: list[str] = []
                bases: list[str] = []
                class_docstring = self._extract_javadoc_comment(source_code, node)

                for child in node.children:
                    if child.type == "identifier":
                        class_name = source_code[child.start_byte : child.end_byte]
                    elif child.type == "superclass":
                        for sc in child.children:
                            if sc.type == "type_identifier":
                                bases.append(source_code[sc.start_byte : sc.end_byte])
                    elif child.type == "class_body":
                        for member in child.children:
                            if member.type == "method_declaration":
                                method_name = None
                                method_body = None
                                method_return_type = None
                                method_docstring = self._extract_javadoc_comment(
                                    source_code, member
                                )

                                for mc in member.children:
                                    if mc.type == "identifier":
                                        method_name = source_code[
                                            mc.start_byte : mc.end_byte
                                        ]
                                    elif mc.type == "block":
                                        method_body = mc
                                    elif mc.type in (
                                        "type_identifier",
                                        "void_type",
                                        "integral_type",
                                        "boolean_type",
                                        "generic_type",
                                    ):
                                        method_return_type = source_code[
                                            mc.start_byte : mc.end_byte
                                        ]

                                if method_name:
                                    methods.append(method_name)

                                    # Extract method as a function for detailed documentation
                                    source_snippet = (
                                        self._get_source_snippet(
                                            source_code, method_body
                                        )
                                        if method_body
                                        else None
                                    )

                                    functions.append(
                                        CanonicalFunction(
                                            name=(
                                                f"{class_name}.{method_name}"
                                                if class_name
                                                else method_name
                                            ),
                                            file=str(file_path),
                                            line=member.start_point[0] + 1,
                                            parameters=[],  # Could be extracted from formal_parameters
                                            is_async=False,
                                            docstring=method_docstring,
                                            return_type=method_return_type,
                                            source_snippet=source_snippet,
                                        )
                                    )

                                    # Check for main method
                                    if method_name == "main":
                                        entry_points.append(
                                            CanonicalEntryPoint(
                                                name="main",
                                                type="main",
                                                file=str(file_path),
                                                line=member.start_point[0] + 1,
                                            )
                                        )

                if class_name:
                    classes.append(
                        CanonicalClass(
                            name=class_name,
                            file=str(file_path),
                            line=node.start_point[0] + 1,
                            methods=methods,
                            bases=bases,
                            docstring=class_docstring,
                        )
                    )

            # Recurse
            for child in node.children:
                visit(child)

        visit(tree.root_node)

        module = CanonicalModule(
            name=file_path.stem,
            path=str(file_path),
            language="java",
            imports=imports,
        )

        return ParseResult(
            file_path=str(file_path),
            language="java",
            success=True,
            module=module,
            classes=classes,
            functions=functions,
            entry_points=entry_points,
        )

    # =========================================================================
    # Directory Parsing
    # =========================================================================

    def parse_directory(
        self,
        directory: Path,
        exclude_patterns: list[str] | None = None,
    ) -> CanonicalAST:
        """Parse all supported source files in a directory.

        Args:
            directory: Root directory to scan
            exclude_patterns: Glob patterns to exclude (default: common ignores)

        Returns:
            CanonicalAST with all extracted code structure

        Raises:
            TreeSitterUnavailableError: If tree-sitter is not available
        """
        # Verify tree-sitter is available before starting (Principle III)
        self._ensure_initialized()

        if exclude_patterns is None:
            exclude_patterns = [
                "**/node_modules/**",
                "**/.venv/**",
                "**/venv/**",
                "**/__pycache__/**",
                "**/dist/**",
                "**/build/**",
                "**/.git/**",
                "**/vendor/**",
                "**/target/**",
            ]

        ast = CanonicalAST()
        files_parsed = 0
        files_failed = 0
        languages_seen: set[str] = set()

        # Pre-compute excluded directory names from patterns
        # Patterns like "**/.venv/**" or "**/node_modules/**" -> extract ".venv", "node_modules"
        excluded_dirs: set[str] = set()
        file_patterns: list[str] = []
        for pattern in exclude_patterns:
            # Check if it's a directory pattern (contains ** or ends with /**)
            if "**" in pattern:
                # Extract directory name from pattern (e.g., "**/.venv/**" -> ".venv")
                parts = (
                    pattern.replace("**/", "").replace("/**", "").strip("/").split("/")
                )
                for part in parts:
                    if part and not part.startswith("*"):
                        excluded_dirs.add(part)
            else:
                # It's a file pattern (e.g., "test_*.py")
                file_patterns.append(pattern)

        # Find all source files
        for ext, language in EXTENSION_TO_LANGUAGE.items():
            for file_path in directory.rglob(f"*{ext}"):
                # Check exclusions by checking if any excluded dir is in the path parts
                should_exclude = False
                path_parts = file_path.parts
                for excluded_dir in excluded_dirs:
                    if excluded_dir in path_parts:
                        should_exclude = True
                        break

                # Also check file patterns against the filename
                if not should_exclude:
                    for pattern in file_patterns:
                        if file_path.match(pattern):
                            should_exclude = True
                            break

                if should_exclude:
                    continue

                # Skip binary files
                try:
                    file_path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, PermissionError):
                    _logger.debug(f"Skipping binary/unreadable file: {file_path}")
                    continue

                result = self.parse_file(file_path)

                if result.success:
                    files_parsed += 1
                    languages_seen.add(result.language)

                    if result.module:
                        ast.add_module(result.module)
                    if result.classes:
                        for cls in result.classes:
                            ast.add_class(cls)
                    if result.functions:
                        for func in result.functions:
                            ast.add_function(func)
                    if result.entry_points:
                        for ep in result.entry_points:
                            ast.add_entry_point(ep)
                else:
                    files_failed += 1
                    _logger.debug(f"Failed to parse {file_path}: {result.error}")

        # Set source metadata
        ast.source = ASTSource(
            tool="tree-sitter",
            languages=sorted(languages_seen),
            files_parsed=files_parsed,
            files_failed=files_failed,
            parsed_at=datetime.now(UTC),
        )

        _logger.info(
            f"Parsed {files_parsed} files ({files_failed} failed) "
            f"in {len(languages_seen)} languages"
        )

        return ast
