"""chronicle CLI interface.

Commands:
- write: Generate documentation for a repository
- check: Validate external tool availability (Principle III)
- init: Initialize chronicle configuration
- validate: Validate a Jinja2 template

Global options:
- --config: Path to configuration file
- --verbose: Enable verbose output with timestamps
- --quiet: Suppress info messages
- --version: Show version and exit
"""

from pathlib import Path
from typing import Annotated

import typer

from chronicle import __version__
from chronicle.config import chronicleConfig, load_config
from chronicle.utils.logging import configure_from_cli, get_logger

# Create Typer app
app = typer.Typer(
    name="chronicle",
    help="Automated Enterprise grade system documentation generator",
    add_completion=False,
    no_args_is_help=True,
)

# Global state
_config: chronicleConfig | None = None
_logger = get_logger()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"chronicle {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            help="Path to configuration file",
            exists=True,
            dir_okay=False,
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Enable verbose output with timestamps",
        ),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            "-q",
            help="Suppress info messages (warnings and errors only)",
        ),
    ] = False,
    ci: Annotated[
        bool,
        typer.Option(
            "--ci",
            help="Enable CI mode with JSON output",
        ),
    ] = False,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit",
        ),
    ] = False,
) -> None:
    """chronicle - Automated System Documentation Generator.

    Generate comprehensive system documentation for Enterprise IT audit,
    architecture, security, and business stakeholders.
    """
    global _config

    # Configure logging based on CLI flags
    configure_from_cli(verbose=verbose, quiet=quiet, ci=ci)

    # Load configuration
    try:
        _config = load_config(config_path=config)
        if _config.config_path:
            _logger.debug(f"Loaded config from: {_config.config_path}")
    except FileNotFoundError as e:
        _logger.error(str(e))
        raise typer.Exit(1)
    except Exception as e:
        _logger.error(f"Failed to load config: {e}")
        raise typer.Exit(1)


# =============================================================================
# check command (Principle III: Preflight Validation)
# =============================================================================


@app.command()
def check(
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output results as JSON",
        ),
    ] = False,
    repo: Annotated[
        Path | None,
        typer.Option(
            "--repo",
            "-r",
            help="Repository path (for context-aware checks)",
            exists=True,
            file_okay=False,
        ),
    ] = None,
) -> None:
    """Validate external tool availability.

    Checks that all required tools (Syft, Terravision, etc.) are installed
    and accessible before running analysis.

    Exit codes:
        0: All required tools available
        1: One or more required tools missing
        2: Only optional tools missing (warnings)
    """
    import json as json_module

    from chronicle.utils.preflight import PreflightChecker

    checker = PreflightChecker()
    repo_path = repo or Path.cwd()

    # Get tool configuration from loaded config
    sbom_tool = _config.tools.sbom if _config else "syft"
    diagram_tool = _config.tools.diagrams if _config else "terravision"

    # Get LLM configuration (required for documentation generation)
    llm_provider = _config.llm.provider if _config else "ollama"
    llm_api_key = _config.llm.api_key if _config else None
    llm_api_base = _config.llm.api_base if _config else "http://localhost:11434"
    llm_model = _config.llm.model if _config else None

    result = checker.check_all(
        repo_path=repo_path,
        sbom_tool=sbom_tool,
        diagram_tool=diagram_tool,
        llm_provider=llm_provider,
        llm_api_key=llm_api_key,
        llm_api_base=llm_api_base,
        llm_model=llm_model,
    )

    if json_output:
        typer.echo(json_module.dumps(result.to_dict(), indent=2))
    else:
        # Human-readable output
        typer.echo("\n🔍 Preflight Check Results\n")

        for check_result in result.checks:
            status = "✅" if check_result.available else "❌"
            version_str = f" ({check_result.version})" if check_result.version else ""
            required_str = " [required]" if check_result.required else " [optional]"

            typer.echo(f"  {status} {check_result.name}{version_str}{required_str}")
            if check_result.available and check_result.path:
                typer.echo(f"     └─ {check_result.path}")
            elif not check_result.available:
                typer.echo(f"     └─ {check_result.message}")

        typer.echo()

        if result.errors:
            typer.echo("❌ Preflight check FAILED")
            for error in result.errors:
                typer.echo(f"   • {error}")
            raise typer.Exit(1)
        elif result.warnings:
            typer.echo("⚠️  Preflight check passed with WARNINGS")
            for warning in result.warnings:
                typer.echo(f"   • {warning}")
            raise typer.Exit(2)
        else:
            typer.echo("✅ All preflight checks passed")
            raise typer.Exit(0)


# =============================================================================
# write command
# =============================================================================


@app.command()
def write(
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output file path (overrides config)",
        ),
    ] = None,
    format: Annotated[
        str | None,
        typer.Option(
            "--format",
            "-f",
            help="Output format: markdown, html, confluence",
        ),
    ] = None,
    repo: Annotated[
        Path,
        typer.Option(
            "--repo",
            "-r",
            help="Repository path to analyze",
            exists=True,
            file_okay=False,
        ),
    ] = Path("."),
    skip_sbom: Annotated[
        bool,
        typer.Option(
            "--skip-sbom",
            help="Skip SBOM generation",
        ),
    ] = False,
    skip_architecture: Annotated[
        bool,
        typer.Option(
            "--skip-architecture",
            help="Skip architecture diagram generation",
        ),
    ] = False,
    skip_llm: Annotated[
        bool,
        typer.Option(
            "--skip-llm",
            help="Skip LLM summary generation (use placeholder text instead)",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Preview output without writing files",
        ),
    ] = False,
) -> None:
    """Generate documentation for a repository.

    Runs deterministic analysis first (AST parsing, Syft SBOM, Terravision diagrams),
    then uses LLM to fill gaps and summarize sections.

    Exit codes:
        0: Documentation generated successfully
        1: Error during generation
        2: Generated with warnings
    """
    from chronicle.models import Repository
    from chronicle.pipeline import AnalysisPipeline, PipelineOptions
    from chronicle.templates import DocumentRenderer
    from chronicle.utils.version import VersionTracker

    repo_path = repo.resolve()
    _logger.info(f"Analyzing repository: {repo_path}")

    # Apply CLI overrides to config
    output_path = (
        output or Path(_config.output.path) if _config else Path("docs/SYSTEM.md")
    )
    output_format = format or (_config.output.format if _config else "markdown")

    _logger.info(f"Output: {output_path} (format: {output_format})")

    # Create repository model
    try:
        repository = Repository.from_path(repo_path)
        warnings = repository.validate()
        for warning in warnings:
            _logger.warning(f"Repository: {warning}")
    except ValueError as e:
        _logger.error(f"Invalid repository: {e}")
        raise typer.Exit(1)

    # Run preflight checks (Principle III: Preflight Validation)
    from chronicle.utils.preflight import PreflightChecker

    _logger.info("Running preflight checks...")
    checker = PreflightChecker()
    preflight_result = checker.check_all(
        repo_path=repo_path,
        sbom_tool=_config.tools.sbom if _config else "syft",
        diagram_tool=_config.tools.diagrams if _config else "terravision",
        llm_provider=_config.llm.provider if _config else "ollama",
        llm_api_key=_config.llm.api_key if _config else None,
        llm_api_base=_config.llm.api_base if _config else None,
        llm_model=_config.llm.model if _config else None,
        skip_sbom=skip_sbom,
        skip_architecture=skip_architecture,
        skip_llm=skip_llm,
    )

    if not preflight_result.success:
        _logger.error("Preflight checks failed:")
        for error in preflight_result.errors:
            _logger.error(f"  {error}")
        raise typer.Exit(1)

    if preflight_result.warnings:
        for warning in preflight_result.warnings:
            _logger.warning(f"  {warning}")

    # Configure pipeline options
    options = PipelineOptions(
        skip_sbom=skip_sbom,
        skip_architecture=skip_architecture,
        skip_llm=skip_llm,
    )

    # Run the analysis pipeline
    _logger.info("Running analysis pipeline...")
    pipeline = AnalysisPipeline(config=_config)

    try:
        result = pipeline.run(repository, options)
    except Exception as e:
        _logger.error(f"Pipeline failed: {e}")
        raise typer.Exit(1)

    # Report analysis results
    status_emoji = "✅" if result.status.value == "completed" else "⚠️"
    _logger.info(f"{status_emoji} Analysis {result.status.value}")

    if result.errors:
        _logger.warning(f"Encountered {len(result.errors)} error(s)")
        for error in result.errors:
            _logger.warning(f"  [{error.component}] {error.message}")

    # Load version history
    version_tracker = VersionTracker(repo_path)
    version_history = version_tracker.load_history()

    # Render documentation
    _logger.info("Rendering documentation...")
    renderer = DocumentRenderer(config=_config)

    try:
        if dry_run:
            # Preview mode
            preview = renderer.preview(result, version_history, max_lines=100)
            typer.echo("\n--- Documentation Preview ---\n")
            typer.echo(preview)
            typer.echo("\n--- End Preview ---")
            _logger.info("Dry run complete - no files written")
        else:
            # Full render and write
            rendered_path = renderer.render_to_file(
                result,
                output_path,
                version_history,
            )

            # Update version history
            new_version = version_tracker.create_version_entry(
                result,
                output_path,
            )
            if new_version:
                version_tracker.save_entry(new_version)
                _logger.info(f"Created version entry: {new_version.version}")

            typer.echo(f"\n📄 Documentation written to: {rendered_path}")

    except Exception as e:
        _logger.error(f"Rendering failed: {e}")
        raise typer.Exit(1)

    # Exit with appropriate code
    if result.errors and any(not e.recoverable for e in result.errors):
        raise typer.Exit(1)
    elif result.errors:
        raise typer.Exit(2)
    else:
        raise typer.Exit(0)


# =============================================================================
# init command
# =============================================================================


def _generate_config_yaml(
    llm_provider: str,
    llm_model: str,
    llm_api_key: str | None,
    llm_api_base: str,
) -> str:
    """Generate YAML configuration content.

    Args:
        llm_provider: LLM provider (ollama, claude, gemini, bedrock)
        llm_model: Model identifier
        llm_api_key: API key (may be env var reference like ${ANTHROPIC_API_KEY})
        llm_api_base: API base URL (for Ollama)

    Returns:
        YAML configuration string
    """
    # Build LLM section based on provider
    if llm_provider == "ollama":
        llm_section = f"""llm:
  provider: "ollama"
  model: "{llm_model}"
  api_base: "{llm_api_base}"
  temperature: 0  # MUST be 0 for reproducibility (Principle II)
  max_tokens: 4096"""
    elif llm_provider in {"claude", "gemini"}:
        api_key_line = (
            f'  api_key: "{llm_api_key}"'
            if llm_api_key
            else f'  # api_key: "${{{"ANTHROPIC_API_KEY" if llm_provider == "claude" else "GOOGLE_API_KEY"}}}"'
        )
        llm_section = f"""llm:
  provider: "{llm_provider}"
  model: "{llm_model}"
{api_key_line}
  temperature: 0  # MUST be 0 for reproducibility (Principle II)
  max_tokens: 4096"""
    else:  # bedrock
        llm_section = f"""llm:
  provider: "bedrock"
  model: "{llm_model}"
  # AWS credentials loaded from environment or ~/.aws/credentials
  temperature: 0  # MUST be 0 for reproducibility (Principle II)
  max_tokens: 4096"""

    return f"""# chronicle Configuration
# Documentation: https://github.com/chronicle/chronicle

# Output settings
output:
  path: "docs/SYSTEM.md"
  format: "markdown"  # markdown, html, confluence

# Tool selection (Principle V: Tool Agnosticism)
tools:
  sbom: "syft"           # SBOM tool: syft, trivy
  diagrams: "terravision"  # Diagram tool: terravision

# LLM settings (REQUIRED for generating documentation summaries)
{llm_section}

# Human section content (Principle VI: Human Annotation Persistence)
# sections:
#   overview:
#     file: ".chronicle/sections/overview.md"
#     strategy: "prepend"  # prepend, append, replace
#   security:
#     file: ".chronicle/sections/security.md"
#     strategy: "append"

# CI/CD settings
ci:
  fail_on_warning: false
  json_output: false
  timeout: 300
"""


@app.command()
def init(
    format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Config format: yaml or toml",
        ),
    ] = "yaml",
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Overwrite existing config",
        ),
    ] = False,
    non_interactive: Annotated[
        bool,
        typer.Option(
            "--non-interactive",
            "-y",
            help="Use defaults without prompting",
        ),
    ] = False,
) -> None:
    """Initialize chronicle configuration.

    Creates a default configuration file and sections directory.
    Prompts for LLM provider configuration (LLM is required).
    """
    if format not in {"yaml", "toml"}:
        _logger.error(f"Invalid format: {format}. Use 'yaml' or 'toml'")
        raise typer.Exit(1)

    # Create .chronicle directory
    chronicle_dir = Path(".chronicle")
    chronicle_dir.mkdir(exist_ok=True)

    # Create sections directory
    sections_dir = chronicle_dir / "sections"
    sections_dir.mkdir(exist_ok=True)

    # Create config file
    config_file = chronicle_dir / f"config.{format}"

    if config_file.exists() and not force:
        _logger.error(f"Config already exists: {config_file}")
        _logger.info("Use --force to overwrite")
        raise typer.Exit(1)

    # LLM Configuration - prompt user for provider
    llm_provider = "ollama"
    llm_model = "llama3.2"
    llm_api_key: str | None = None
    llm_api_base = "http://localhost:11434"

    if not non_interactive:
        typer.echo(
            "\n🤖 LLM Configuration (required for generating documentation summaries)\n"
        )
        typer.echo("Available providers:")
        typer.echo("  1. Ollama (default - local/secure, no data leaves your machine)")
        typer.echo("  2. Claude (Anthropic API)")
        typer.echo("  3. Gemini (Google API)")
        typer.echo("  4. Bedrock (AWS)")

        provider_choice = typer.prompt(
            "\nSelect LLM provider [1-4]",
            default="1",
            show_default=True,
        )

        provider_map = {"1": "ollama", "2": "claude", "3": "gemini", "4": "bedrock"}
        llm_provider = provider_map.get(provider_choice, "ollama")

        if llm_provider == "ollama":
            llm_api_base = typer.prompt(
                "Ollama API base URL",
                default="http://localhost:11434",
                show_default=True,
            )
            llm_model = typer.prompt(
                "Ollama model",
                default="llama3.2",
                show_default=True,
            )
            typer.echo("\n💡 Make sure Ollama is running: ollama serve")

        elif llm_provider == "claude":
            llm_api_key = typer.prompt(
                "Anthropic API key (or set ANTHROPIC_API_KEY env var)",
                default="",
                hide_input=True,
            )
            if not llm_api_key:
                llm_api_key = "${ANTHROPIC_API_KEY}"
            llm_model = typer.prompt(
                "Claude model",
                default="claude-sonnet-4-20250514",
                show_default=True,
            )

        elif llm_provider == "gemini":
            llm_api_key = typer.prompt(
                "Google API key (or set GOOGLE_API_KEY env var)",
                default="",
                hide_input=True,
            )
            if not llm_api_key:
                llm_api_key = "${GOOGLE_API_KEY}"
            llm_model = typer.prompt(
                "Gemini model",
                default="gemini-1.5-pro",
                show_default=True,
            )

        elif llm_provider == "bedrock":
            llm_model = typer.prompt(
                "Bedrock model ID",
                default="anthropic.claude-3-sonnet-20240229-v1:0",
                show_default=True,
            )
            typer.echo(
                "\n💡 AWS credentials will be loaded from environment or ~/.aws/credentials"
            )

    # Generate config content
    if format == "yaml":
        config_content = _generate_config_yaml(
            llm_provider=llm_provider,
            llm_model=llm_model,
            llm_api_key=llm_api_key,
            llm_api_base=llm_api_base,
        )
    else:
        # TODO: Add TOML support
        _logger.error("TOML format not yet implemented")
        raise typer.Exit(1)

    config_file.write_text(config_content)
    _logger.info(f"Created config: {config_file}")

    # Create example section files
    overview_file = sections_dir / "overview.md"
    if not overview_file.exists():
        overview_file.write_text(
            "# System Overview\n\n"
            "<!-- Add your custom overview content here -->\n"
            "<!-- This will be merged with generated content -->\n"
        )
        _logger.info(f"Created example section: {overview_file}")

    typer.echo("\n✅ chronicle configuration initialized")
    typer.echo(f"   Config: {config_file}")
    typer.echo(f"   Sections: {sections_dir}/")
    raise typer.Exit(0)


# =============================================================================
# validate command
# =============================================================================


@app.command()
def validate(
    template: Annotated[
        Path,
        typer.Argument(
            help="Path to Jinja2 template to validate",
            exists=True,
            dir_okay=False,
        ),
    ],
) -> None:
    """Validate a Jinja2 template.

    Checks syntax and reports unsupported placeholders.
    """
    from jinja2 import Environment, TemplateSyntaxError

    _logger.info(f"Validating template: {template}")

    try:
        env = Environment()
        template_content = template.read_text()
        env.parse(template_content)

        _logger.info("Template syntax is valid")
        typer.echo(f"✅ Template is valid: {template}")
        raise typer.Exit(0)

    except TemplateSyntaxError as e:
        _logger.error(f"Template syntax error: {e.message}")
        typer.echo(f"❌ Template syntax error at line {e.lineno}: {e.message}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
