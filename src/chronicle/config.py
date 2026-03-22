"""chronicle configuration system.

Configuration is primarily YAML-based with minimal CLI overrides (--output, --format, --ci).
Supports environment variable substitution (${VAR}) in config files.

Configuration file discovery (in priority order):
1. CLI --config argument
2. ./.chronicle/config.yaml
3. ./chronicle.yaml
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# =============================================================================
# Configuration Dataclasses
# =============================================================================


@dataclass
class OutputConfig:
    """Output configuration.

    Attributes:
        path: Output file path
        format: Output format (markdown, html, confluence)
    """

    path: str = "docs/SYSTEM.md"
    format: str = "markdown"


@dataclass
class ToolConfig:
    """Tool selection configuration (Principle V: Tool Agnosticism).

    Tools are auto-skipped if not applicable (no dependency files, no Terraform).

    Attributes:
        sbom: SBOM tool to use (syft, trivy)
        diagrams: Diagram tool to use (terravision)
        code_packager: Codebase compression tool (repomix)
    """

    sbom: str = "syft"
    diagrams: str = "terravision"
    code_packager: str = "repomix"


@dataclass
class LLMConfig:
    """LLM configuration.

    LLM is REQUIRED for generating human-readable documentation summaries.
    Ollama is the default provider for security-conscious enterprises (local processing).

    Attributes:
        provider: LLM provider (claude, gemini, ollama, bedrock)
        model: Model identifier
        api_key: API key (not required for Ollama)
        api_base: API base URL (required for Ollama)
        temperature: Temperature setting (MUST be 0 for reproducibility)
        max_tokens: Maximum response tokens
        enabled: Whether LLM summarization is enabled
    """

    provider: str = "ollama"
    model: str = "llama3.2"
    api_key: str | None = None
    api_base: str | None = None
    temperature: float = 0.0
    max_tokens: int = 4096
    enabled: bool = True

    def __post_init__(self) -> None:
        """Validate LLM configuration."""
        # Principle II: Reproducibility requires temperature=0
        if self.temperature != 0:
            raise ValueError(
                f"LLM temperature must be 0 for reproducibility (got {self.temperature})"
            )

        # Validate provider
        valid_providers = {"claude", "gemini", "ollama", "bedrock"}
        if self.provider not in valid_providers:
            raise ValueError(
                f"Invalid LLM provider: {self.provider}. Valid: {valid_providers}"
            )

        # API key required for cloud providers (except bedrock which uses AWS credentials)
        if self.provider in {"claude", "gemini"} and not self.api_key:
            raise ValueError(f"API key required for {self.provider}")

        # API base defaults for Ollama
        if self.provider == "ollama" and not self.api_base:
            self.api_base = "http://localhost:11434"

    @property
    def is_local(self) -> bool:
        """Return True if using local LLM (no data leaves machine)."""
        return self.provider == "ollama"


@dataclass
class SectionConfig:
    """Configuration for a human-authored section (Principle VI).

    Attributes:
        file: Path to markdown file with human content
        strategy: How to merge ("replace", "prepend", "append")
    """

    file: str
    strategy: str = "append"

    def __post_init__(self) -> None:
        """Validate section configuration."""
        valid_strategies = {"replace", "prepend", "append"}
        if self.strategy not in valid_strategies:
            raise ValueError(
                f"Invalid merge strategy: {self.strategy}. Valid: {valid_strategies}"
            )


@dataclass
class CIConfig:
    """CI/CD-specific configuration.

    Attributes:
        fail_on_warning: Exit with error if warnings occur
        json_output: Use JSON output format
        timeout: Timeout for external tools in seconds
    """

    fail_on_warning: bool = False
    json_output: bool = False
    timeout: int = 300


@dataclass
class chronicleConfig:
    """Top-level chronicle configuration.

    CLI provides only per-run overrides (--output, --format, --ci).

    Attributes:
        output: Output path and format
        tools: Tool selection (Principle V)
        llm: LLM settings (REQUIRED - Ollama default for security)
        sections: Human content sections (Principle VI)
        ci: CI/CD settings
    """

    output: OutputConfig = field(default_factory=OutputConfig)
    tools: ToolConfig = field(default_factory=ToolConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    sections: dict[str, SectionConfig] = field(default_factory=dict)
    ci: CIConfig = field(default_factory=CIConfig)

    # Runtime overrides (set by CLI)
    _config_path: Path | None = field(default=None, repr=False)

    @property
    def config_path(self) -> Path | None:
        """Get the path to the config file that was loaded."""
        return self._config_path


# =============================================================================
# Environment Variable Substitution
# =============================================================================


def substitute_env_vars(value: Any) -> Any:
    """Substitute environment variables in config values.

    Supports ${VAR} syntax for environment variable substitution.
    Example: ${ANTHROPIC_API_KEY} -> value of ANTHROPIC_API_KEY

    Args:
        value: Config value (string, dict, list, or other)

    Returns:
        Value with environment variables substituted
    """
    if isinstance(value, str):
        # Pattern: ${VAR_NAME}
        pattern = re.compile(r"\$\{([^}]+)\}")

        def replace_var(match: re.Match[str]) -> str:
            var_name = match.group(1)
            env_value = os.environ.get(var_name)
            if env_value is None:
                raise ValueError(f"Environment variable not set: {var_name}")
            return env_value

        return pattern.sub(replace_var, value)

    elif isinstance(value, dict):
        return {k: substitute_env_vars(v) for k, v in value.items()}

    elif isinstance(value, list):
        return [substitute_env_vars(v) for v in value]

    return value


# =============================================================================
# Config File Discovery
# =============================================================================


def find_config_file(start_path: Path | None = None) -> Path | None:
    """Find configuration file in standard locations.

    Search order:
    1. ./.chronicle/config.yaml
    2. ./chronicle.yaml

    Args:
        start_path: Starting directory for search (defaults to cwd)

    Returns:
        Path to config file if found, None otherwise
    """
    if start_path is None:
        start_path = Path.cwd()

    start_path = start_path.resolve()

    # Check standard locations
    candidates = [
        start_path / ".chronicle" / "config.yaml",
        start_path / "chronicle.yaml",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


# =============================================================================
# Config Loading
# =============================================================================


def load_config_from_dict(data: dict[str, Any]) -> chronicleConfig:
    """Load configuration from a dictionary.

    Args:
        data: Configuration dictionary

    Returns:
        chronicleConfig instance
    """
    # Apply environment variable substitution
    data = substitute_env_vars(data)

    config = chronicleConfig()

    # Output config
    if "output" in data:
        output_data = data["output"]
        config.output = OutputConfig(
            path=output_data.get("path", config.output.path),
            format=output_data.get("format", config.output.format),
        )

    # Tools config
    if "tools" in data:
        tools_data = data["tools"]
        config.tools = ToolConfig(
            sbom=tools_data.get("sbom", config.tools.sbom),
            diagrams=tools_data.get("diagrams", config.tools.diagrams),
        )

    # LLM config (always present - LLM is required)
    if "llm" in data:
        llm_data = data["llm"]
        config.llm = LLMConfig(
            provider=llm_data.get("provider", "ollama"),
            model=llm_data.get("model", "llama3.2"),
            api_key=llm_data.get("api_key"),
            api_base=llm_data.get("api_base"),
            temperature=llm_data.get("temperature", 0),
            max_tokens=llm_data.get("max_tokens", 4096),
            enabled=llm_data.get("enabled", True),
        )

    # Sections config
    if "sections" in data:
        for section_id, section_data in data["sections"].items():
            if isinstance(section_data, dict):
                config.sections[section_id] = SectionConfig(
                    file=section_data.get("file", ""),
                    strategy=section_data.get("strategy", "append"),
                )

    # CI config
    if "ci" in data:
        ci_data = data["ci"]
        config.ci = CIConfig(
            fail_on_warning=ci_data.get("fail_on_warning", False),
            json_output=ci_data.get("json_output", False),
            timeout=ci_data.get("timeout", 300),
        )

    return config


def load_config(
    config_path: Path | None = None,
    auto_discover: bool = True,
) -> chronicleConfig:
    """Load configuration from file.

    Args:
        config_path: Explicit path to config file
        auto_discover: Whether to search for config file if not specified

    Returns:
        chronicleConfig instance

    Raises:
        FileNotFoundError: If config_path specified but doesn't exist
    """
    # Find config file
    if config_path is not None:
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        found_path = config_path
    elif auto_discover:
        found_path = find_config_file()
    else:
        found_path = None

    # Load config
    if found_path is not None:
        with open(found_path) as f:
            data = yaml.safe_load(f) or {}
        config = load_config_from_dict(data)
        config._config_path = found_path
    else:
        config = chronicleConfig()

    return config


def create_default_config() -> str:
    """Create default configuration YAML content.

    Returns:
        YAML string with default configuration and comments
    """
    return """# chronicle Configuration
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
# Default: Ollama for security-conscious enterprises (no data leaves machine)
llm:
  provider: "ollama"     # ollama (local/secure), claude, gemini
  model: "llama3.2"      # Model to use
  # api_key: "${ANTHROPIC_API_KEY}"  # Required for claude/gemini
  api_base: "http://localhost:11434"  # Ollama server URL
  temperature: 0         # MUST be 0 for reproducibility (Principle II)
  max_tokens: 4096

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
