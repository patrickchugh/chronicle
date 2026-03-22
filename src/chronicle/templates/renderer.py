"""Template renderer for documentation generation (Principle II: Reproducibility).

Renders analysis results to markdown using Jinja2 templates.
All output is deterministic - same input always produces same output.
"""

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape

from chronicle.config import chronicleConfig
from chronicle.models.analysis import AnalysisResult, VersionEntry
from chronicle.renderers.filters import replace_negative_assertions

logger = logging.getLogger(__name__)


class SectionLoader:
    """Loads custom section content from external markdown files.

    Section files allow human-authored content to be merged into generated docs.
    This implements SC-007 (human annotation persistence).
    """

    def __init__(self, config: chronicleConfig | None = None) -> None:
        """Initialize section loader.

        Args:
            config: chronicle configuration with section definitions
        """
        self.config = config
        self._cache: dict[str, str] = {}

    def load_section(
        self,
        section_name: str,
        repo_path: Path,
    ) -> str | None:
        """Load a section file content.

        Args:
            section_name: Name of the section (e.g., "overview", "security")
            repo_path: Repository root path

        Returns:
            Section content or None if not found
        """
        if self.config is None or section_name not in self.config.sections:
            return None

        section_config = self.config.sections[section_name]
        section_path = repo_path / section_config.file

        if not section_path.exists():
            logger.debug("Section file not found: %s", section_path)
            return None

        try:
            content = section_path.read_text(encoding="utf-8")
            logger.debug("Loaded section %s from %s", section_name, section_path)
            return content.strip()
        except Exception as e:
            logger.warning("Failed to load section %s: %s", section_name, e)
            return None

    def load_all_sections(self, repo_path: Path) -> dict[str, str]:
        """Load all configured sections.

        Args:
            repo_path: Repository root path

        Returns:
            Dictionary of section name → content
        """
        sections: dict[str, str] = {}

        if self.config is None:
            return sections

        for section_name in self.config.sections:
            content = self.load_section(section_name, repo_path)
            if content:
                sections[section_name] = content

        return sections


def format_datetime(dt: datetime | str | None) -> str:
    """Format datetime for display in documentation.

    Args:
        dt: Datetime object or ISO string

    Returns:
        Formatted date string
    """
    if dt is None:
        return "N/A"

    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return dt

    # Ensure UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


class DocumentRenderer:
    """Renders analysis results to markdown documentation.

    This is the main entry point for template rendering.
    Templates are loaded from the package and customizable via config.

    Usage:
        renderer = DocumentRenderer(config)
        markdown = renderer.render(analysis_result, version_history)
    """

    def __init__(self, config: chronicleConfig | None = None) -> None:
        """Initialize the document renderer.

        Args:
            config: chronicle configuration
        """
        self.config = config
        self._section_loader = SectionLoader(config)

        # Set up Jinja2 environment with package templates
        self._env = Environment(
            loader=PackageLoader("chronicle", "templates"),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

        # Register custom filters
        self._env.filters["format_datetime"] = format_datetime
        self._env.filters["replace_negative_assertions"] = replace_negative_assertions

    def render(
        self,
        result: AnalysisResult,
        version_history: list[VersionEntry] | None = None,
        template_name: str = "SYSTEM.md.j2",
    ) -> str:
        """Render analysis result to markdown.

        Args:
            result: Analysis result from pipeline
            version_history: Document version history
            template_name: Template file to use

        Returns:
            Rendered markdown string
        """
        # Load template
        try:
            template = self._env.get_template(template_name)
        except Exception as e:
            logger.error("Failed to load template %s: %s", template_name, e)
            raise ValueError(f"Template not found: {template_name}") from e

        # Load custom sections
        sections = self._section_loader.load_all_sections(result.repository_path)

        # Build template context
        context = self._build_context(result, version_history, sections)

        # Render template
        try:
            rendered = template.render(**context)
            logger.info("Rendered documentation (%d characters)", len(rendered))
            return rendered
        except Exception as e:
            logger.error("Template rendering failed: %s", e)
            raise ValueError(f"Template rendering failed: {e}") from e

    def _build_context(
        self,
        result: AnalysisResult,
        version_history: list[VersionEntry] | None,
        sections: dict[str, str],
    ) -> dict[str, Any]:
        """Build the template rendering context.

        Args:
            result: Analysis result
            version_history: Version history entries
            sections: Custom section content

        Returns:
            Template context dictionary
        """
        # Convert AnalysisResult to template-friendly format
        context: dict[str, Any] = {
            # Core metadata
            "repository_name": result.repository_name,
            "repository_path": str(result.repository_path),
            "timestamp": result.timestamp,
            "status": result.status.value,
            "git_ref": result.git_ref,
            # Technology stack
            "technology_stack": (
                result.technology_stack.to_dict() if result.technology_stack else {}
            ),
            # Analysis results
            "sbom": result.sbom,
            "architecture": result.architecture,
            "source_analysis": result.source_analysis,
            # Tool versions and errors
            "tool_versions": result.tool_versions,
            "errors": [e.to_dict() for e in result.errors],
            # Version history
            "version_history": [entry.to_dict() for entry in (version_history or [])],
            # Custom sections
            "sections": sections,
            # LLM-generated summaries
            "llm_summaries": result.llm_summaries or {},
            # Flow-based documentation (T084)
            "modules": result.modules or [],
            "entry_points": result.entry_points or [],
            "external_integrations": result.external_integrations or [],
            "module_flow_diagram": result.module_flow_diagram,
            # Holistic overview (Phase 4g: Repomix integration)
            "holistic_overview": result.holistic_overview,
        }

        # Convert nested objects for easier template access
        if result.technology_stack:
            ts = result.technology_stack
            context["technology_stack"] = {
                "languages": [
                    {
                        "name": lang.name,
                        "version": lang.version,
                        "file_count": lang.file_count,
                    }
                    for lang in ts.languages
                ],
                "frameworks": [
                    {"name": f.name, "version": f.version, "language": f.language}
                    for f in ts.frameworks
                ],
                "dependencies": [d.to_dict() for d in ts.dependencies],
                "dev_dependencies": [d.to_dict() for d in ts.dev_dependencies],
            }

        return context

    def render_to_file(
        self,
        result: AnalysisResult,
        output_path: Path,
        version_history: list[VersionEntry] | None = None,
        template_name: str = "SYSTEM.md.j2",
    ) -> Path:
        """Render analysis result and write to file.

        Args:
            result: Analysis result from pipeline
            output_path: Path to write output file
            version_history: Document version history
            template_name: Template file to use

        Returns:
            Path to written file
        """
        # Render content
        content = self.render(result, version_history, template_name)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        output_path.write_text(content, encoding="utf-8")
        logger.info("Wrote documentation to %s", output_path)

        return output_path

    def preview(
        self,
        result: AnalysisResult,
        version_history: list[VersionEntry] | None = None,
        max_lines: int = 50,
    ) -> str:
        """Generate a preview of the rendered output.

        Args:
            result: Analysis result
            version_history: Version history
            max_lines: Maximum lines to include in preview

        Returns:
            Preview string with truncation indicator
        """
        full_content = self.render(result, version_history)
        lines = full_content.split("\n")

        if len(lines) <= max_lines:
            return full_content

        preview_lines = lines[:max_lines]
        preview_lines.append(f"\n... [{len(lines) - max_lines} more lines] ...")

        return "\n".join(preview_lines)
