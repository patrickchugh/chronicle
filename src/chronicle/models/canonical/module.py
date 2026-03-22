"""Canonical module and entry point models for flow-based documentation.

This module defines data structures for module-level documentation,
replacing function-by-function explanations with flow-based summaries.
"""

from dataclasses import dataclass, field


@dataclass
class CanonicalModule:
    """Represents a detected code module/package for flow-based documentation.

    Attributes:
        name: Module name (e.g., "analyzers", "llm")
        path: Relative path from repo root
        files: Files contained in this module
        classes: Class names in this module
        functions: Top-level function names in this module
        imports: Internal modules this module imports
        language: Primary language of the module
    """

    name: str
    path: str
    files: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    language: str = "unknown"


@dataclass
class ModuleSummary:
    """Module with LLM-generated responsibility summary for documentation output.

    Attributes:
        name: Module name
        path: Relative path from repo root
        language: Primary language of the module
        responsibility: LLM-generated 1-2 sentence summary of what this module does
        key_classes: Most important classes in the module (max 5)
        key_functions: Most important functions in the module (max 5)
        file_count: Number of files in the module
    """

    name: str
    path: str
    language: str = "unknown"
    responsibility: str = ""
    key_classes: list[str] = field(default_factory=list)
    key_functions: list[str] = field(default_factory=list)
    file_count: int = 0


@dataclass
class EntryPoint:
    """Represents a public entry point (CLI command, API endpoint, handler).

    Attributes:
        name: Entry point name (e.g., "write", "/api/users")
        type: Type of entry point (cli_command, api_endpoint, handler, main)
        file: Source file path
        line: Line number
        description: Extracted docstring or annotation description
        method: HTTP method for API endpoints (GET, POST, etc.)
    """

    name: str
    type: str  # cli_command, api_endpoint, handler, main
    file: str
    line: int
    description: str | None = None
    method: str | None = None


@dataclass
class ExternalIntegration:
    """Represents a detected external service integration.

    Attributes:
        name: Service/library name (e.g., "PostgreSQL", "Redis")
        type: Type of integration (database, http, queue, cache, storage)
        library: Library used (e.g., "sqlalchemy", "requests", "boto3")
        locations: Files where this integration is used
    """

    name: str
    type: str  # database, http, queue, cache, storage
    library: str
    locations: list[str] = field(default_factory=list)


@dataclass
class ImportGraph:
    """Directed graph of module import relationships for flow diagram generation.

    Attributes:
        nodes: Module names
        edges: (importing_module, imported_module) pairs
    """

    nodes: list[str] = field(default_factory=list)
    edges: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class ModuleFlowDiagram:
    """Generated Mermaid diagram showing module relationships.

    Attributes:
        mermaid: Mermaid flowchart syntax
        node_count: Number of nodes in diagram
        simplified: Whether sub-modules were grouped to reduce complexity
        title: Diagram title
    """

    mermaid: str
    node_count: int
    simplified: bool = False
    title: str = "Module Dependencies"
