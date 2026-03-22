"""Config context collector for LLM analysis enhancement.

Reads key configuration and documentation files to provide additional
context for the LLM holistic overview analysis.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# File extensions/patterns that are documentation (reference only, may be outdated)
DOCUMENTATION_PATTERNS = {
    ".md",
    ".rst",
    ".txt",
    "README",
}

# File extensions that are authoritative config (source of truth for runtime)
CONFIG_EXTENSIONS = {
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".cfg",
    ".tf",
    ".py",  # setup.py is config
    "Dockerfile",
}


def _get_file_type_label(file_name: str) -> str:
    """Get the source-of-truth label for a file.

    Args:
        file_name: Name of the file

    Returns:
        Label indicating whether file is authoritative or reference-only
    """
    # Check for documentation patterns
    for pattern in DOCUMENTATION_PATTERNS:
        if file_name.endswith(pattern) or file_name == pattern:
            return "REFERENCE - may be outdated"

    # Check for config extensions
    for ext in CONFIG_EXTENSIONS:
        if file_name.endswith(ext) or file_name == ext:
            return "AUTHORITATIVE CONFIG"

    return "CONTEXT"


# Files to include for LLM context (in priority order)
CONFIG_FILES = [
    # Documentation
    "README.md",
    "README.rst",
    "README.txt",
    "README",
    # Python config
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    # JavaScript/Node config
    "package.json",
    # chronicle config
    ".chronicle/config.yaml",
    ".chronicle/config.yml",
    # Infrastructure
    "docker-compose.yml",
    "docker-compose.yaml",
    "Dockerfile",
    # CI/CD (may show integrations)
    ".github/workflows/ci.yml",
    ".github/workflows/ci.yaml",
    ".gitlab-ci.yml",
    # Environment (without secrets)
    ".env.example",
    ".env.template",
    # Terraform (first file only for context)
    "main.tf",
    "terraform/main.tf",
    "infra/main.tf",
]

# Maximum size per file (to avoid huge files)
MAX_FILE_SIZE = 50_000  # 50KB per file

# Maximum total context size
MAX_TOTAL_SIZE = 200_000  # 200KB total


def collect_config_context(repo_path: Path) -> str:
    """Collect configuration context from key files.

    Reads documentation and configuration files to provide additional
    context for LLM analysis. This helps the LLM understand:
    - What the project does (README)
    - Dependencies and their purposes (pyproject.toml, package.json)
    - Configured integrations (.chronicle/config.yaml, docker-compose.yml)
    - Infrastructure (Terraform, Dockerfile)

    Args:
        repo_path: Path to the repository root

    Returns:
        Formatted string with file contents, suitable for appending
        to the compressed codebase content
    """
    collected_files: list[tuple[str, str]] = []
    total_size = 0

    for file_pattern in CONFIG_FILES:
        file_path = repo_path / file_pattern

        if not file_path.exists():
            continue

        if not file_path.is_file():
            continue

        try:
            content = file_path.read_text(encoding="utf-8")

            # Skip if file is too large
            if len(content) > MAX_FILE_SIZE:
                logger.debug(
                    "Skipping %s (too large: %d bytes)",
                    file_pattern,
                    len(content),
                )
                continue

            # Check total size limit
            if total_size + len(content) > MAX_TOTAL_SIZE:
                logger.debug(
                    "Stopping config collection (total size limit reached)",
                )
                break

            collected_files.append((file_pattern, content))
            total_size += len(content)

            logger.debug(
                "Collected config file: %s (%d bytes)",
                file_pattern,
                len(content),
            )

        except Exception as e:
            logger.debug("Failed to read %s: %s", file_pattern, e)
            continue

    if not collected_files:
        return ""

    # Format as a context section with source-of-truth guidance
    lines = [
        "",
        "=" * 80,
        "CONFIGURATION AND DOCUMENTATION CONTEXT",
        "=" * 80,
        "",
        "The following files provide additional context about this project.",
        "",
        "SOURCE OF TRUTH PRECEDENCE (use this when analyzing):",
        "1. Code analysis (AST, imports) - highest authority",
        "2. Structured config (YAML, JSON, TOML) - authoritative for runtime behavior",
        "3. Documentation (README.md, *.md) - reference only, may be outdated",
        "",
        "IMPORTANT: Markdown documentation files may contain aspirational or outdated",
        "descriptions. When there is a conflict between what a .md file says vs what",
        "config files (YAML, JSON, TOML) or code shows, trust the config/code.",
        "",
    ]

    for file_name, content in collected_files:
        lines.append("-" * 40)
        file_type = _get_file_type_label(file_name)
        lines.append(f"File: {file_name} [{file_type}]")
        lines.append("-" * 40)
        lines.append(content.strip())
        lines.append("")

    logger.info(
        "Collected %d config files (%d bytes total)",
        len(collected_files),
        total_size,
    )

    return "\n".join(lines)
