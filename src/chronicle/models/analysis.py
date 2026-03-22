"""Analysis result entities.

This module contains entities related to analysis results:
- AnalysisError: Non-fatal errors encountered during analysis
- VersionEntry: Document version history entry (SC-011)
- Dependency: Single third-party dependency
- TechnologyStack: Detected languages, frameworks, dependencies
- AnalysisResult: Aggregated analysis data
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any


class AnalysisStatus(Enum):
    """Status of an analysis operation."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AuthorType(Enum):
    """Type of author for version history entries."""

    AUTOMATED = "automated"  # chronicle-generated
    HUMAN = "human"  # Human-authored


@dataclass
class AnalysisError:
    """Non-fatal error encountered during analysis.

    Attributes:
        component: Component that failed (syft, terravision, ast, dependency)
        message: Error description
        file_path: File that caused the error (if applicable)
        recoverable: Whether analysis continued after this error
    """

    component: str
    message: str
    file_path: str | None = None
    recoverable: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "component": self.component,
            "message": self.message,
            "file_path": self.file_path,
            "recoverable": self.recoverable,
        }


@dataclass
class VersionEntry:
    """Single entry in the document version history (SC-011).

    Tracks who made changes, when, and what changed for audit purposes.

    Attributes:
        version: Version identifier (e.g., "1.0.0", "1.0.1")
        timestamp: Change timestamp in UTC
        author: Author name ("chronicle" or human name)
        author_type: Whether automated or human
        changes: Summary of changes
        git_ref: Git commit SHA for this version
    """

    version: str
    timestamp: datetime
    author: str
    author_type: AuthorType
    changes: str
    git_ref: str | None = None

    def __post_init__(self) -> None:
        """Ensure timestamp is timezone-aware UTC."""
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "version": self.version,
            "timestamp": self.timestamp.isoformat(),
            "author": self.author,
            "author_type": self.author_type.value,
            "changes": self.changes,
            "git_ref": self.git_ref,
        }

    @classmethod
    def create_automated(
        cls,
        version: str,
        changes: str,
        git_ref: str | None = None,
    ) -> "VersionEntry":
        """Create an automated (chronicle-generated) version entry."""
        return cls(
            version=version,
            timestamp=datetime.now(UTC),
            author="chronicle",
            author_type=AuthorType.AUTOMATED,
            changes=changes,
            git_ref=git_ref,
        )


@dataclass
class Dependency:
    """Single third-party dependency with version information.

    Attributes:
        name: Package name
        version: Version specifier (may be range or exact)
        source_file: File where dependency was declared
        ecosystem: Package ecosystem (npm, pypi, go, maven)
        license: License identifier if available from SBOM
    """

    name: str
    ecosystem: str
    source_file: str
    version: str | None = None
    license: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "version": self.version,
            "ecosystem": self.ecosystem,
            "source_file": self.source_file,
            "license": self.license,
        }


@dataclass
class LanguageInfo:
    """Information about a detected programming language."""

    name: str
    version: str | None = None
    file_count: int = 0
    line_count: int = 0


@dataclass
class Framework:
    """Information about a detected framework."""

    name: str
    version: str | None = None
    language: str | None = None


@dataclass
class TechnologyStack:
    """Inventory of detected languages, frameworks, and dependencies.

    Derived from dependency files and Syft scanning.

    Attributes:
        languages: Detected programming languages with versions
        frameworks: Detected frameworks (e.g., FastAPI, React)
        dependencies: Third-party dependencies with versions
        dev_dependencies: Development-only dependencies
    """

    languages: list[LanguageInfo] = field(default_factory=list)
    frameworks: list[Framework] = field(default_factory=list)
    dependencies: list[Dependency] = field(default_factory=list)
    dev_dependencies: list[Dependency] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "languages": [
                {
                    "name": lang.name,
                    "version": lang.version,
                    "file_count": lang.file_count,
                }
                for lang in self.languages
            ],
            "frameworks": [
                {"name": fw.name, "version": fw.version, "language": fw.language}
                for fw in self.frameworks
            ],
            "dependencies": [dep.to_dict() for dep in self.dependencies],
            "dev_dependencies": [dep.to_dict() for dep in self.dev_dependencies],
        }


@dataclass
class AnalysisResult:
    """Aggregated analysis data from all deterministic analyzers.

    Serves as input to template rendering and LLM summarization.

    Attributes:
        repository_path: Path to the analyzed repository
        repository_name: Name of the repository
        timestamp: Analysis execution timestamp (UTC)
        status: Current analysis status
        technology_stack: Detected languages, frameworks, dependencies
        errors: Non-fatal errors encountered during analysis
        tool_versions: External tool versions used (for reproducibility)
        git_ref: Git commit SHA at time of analysis
    """

    repository_path: Path
    repository_name: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    status: AnalysisStatus = AnalysisStatus.PENDING
    technology_stack: TechnologyStack = field(default_factory=TechnologyStack)
    errors: list[AnalysisError] = field(default_factory=list)
    tool_versions: dict[str, str] = field(default_factory=dict)
    git_ref: str | None = None

    # Optional analysis components (populated by analyzers)
    sbom: Any | None = None  # CanonicalSBOM when available
    architecture: Any | None = None  # CanonicalArchitecture when available
    source_analysis: Any | None = None  # CanonicalAST when available

    # LLM-generated summaries (populated by pipeline Stage 5)
    # Keys: overview, tech_stack, architecture, dependencies, code_structure
    llm_summaries: dict[str, str] = field(default_factory=dict)

    # Flow-based documentation (Phase 4e)
    modules: list[Any] = field(default_factory=list)  # list[ModuleSummary]
    entry_points: list[Any] = field(default_factory=list)  # list[EntryPoint]
    external_integrations: list[Any] = field(
        default_factory=list
    )  # list[ExternalIntegration]
    module_flow_diagram: Any | None = None  # ModuleFlowDiagram when available

    # Repomix integration (Phase 4g)
    compressed_codebase: Any | None = None  # CompressedCodebase from Repomix
    holistic_overview: Any | None = None  # HolisticOverview from LLM analysis

    def add_error(self, error: AnalysisError) -> None:
        """Add an analysis error."""
        self.errors.append(error)

    def has_errors(self) -> bool:
        """Check if any errors were recorded."""
        return len(self.errors) > 0

    def get_errors_by_component(self, component: str) -> list[AnalysisError]:
        """Get errors for a specific component."""
        return [e for e in self.errors if e.component == component]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for template rendering."""
        return {
            "repository_path": str(self.repository_path),
            "repository_name": self.repository_name,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "technology_stack": self.technology_stack.to_dict(),
            "errors": [e.to_dict() for e in self.errors],
            "tool_versions": self.tool_versions,
            "git_ref": self.git_ref,
        }
