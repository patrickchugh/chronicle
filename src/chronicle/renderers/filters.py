"""Jinja2 filters for post-processing rendered output.

This module provides filters that clean up LLM output and ensure
consistent presentation of missing or unavailable data.
"""

import re

# Patterns that indicate negative assertions (what is NOT present)
# These should be replaced with simple "N/A" per FR-029
NEGATIVE_PATTERNS: list[str] = [
    # Direct negative statements
    r"not detected",
    r"not found",
    r"unable to determine",
    r"none identified",
    r"not determinable",
    r"no\s+\w+\s+detected",
    r"could not find",
    r"could not determine",
    r"no\s+\w+\s+found",
    r"nothing\s+\w+\s+detected",
    r"nothing\s+\w+\s+found",
    r"not available",
    r"not present",
    r"none found",
    r"none detected",
    r"cannot be determined",
    r"is not determinable",
    r"are not determinable",
    # Hedging language (banned per FR-029)
    r"appears? to be",
    r"seems? to be",
    r"seems? to",
    r"likely\s+\w+",
    r"probably\s+\w+",
    r"possibly\s+\w+",
    r"may be used",
    r"could be\s+\w+",
    r"might be\s+\w+",
    # Negative assertions in longer sentences
    r"no\s+\w+\s+(?:providers?|frameworks?|patterns?)\s+(?:are|is)\s+determinable",
    r"the\s+\w+\s+(?:pattern|style)\s+is\s+not\s+determinable",
    r"from the (?:provided|available) information",
    r"from the analysis",
]

# Compiled regex for efficiency
_NEGATIVE_PATTERN_RE = re.compile(
    "|".join(f"({p})" for p in NEGATIVE_PATTERNS),
    re.IGNORECASE,
)


def replace_negative_assertions(text: str) -> str:
    """Remove negative assertion statements from text.

    This filter ensures that LLM-generated text does not contain unhelpful
    statements about what was NOT found or NOT detected. Lines containing
    negative assertions are simply removed.

    Args:
        text: The text to process (typically LLM output).

    Returns:
        Text with negative assertion lines removed. Empty if all lines removed.

    Examples:
        >>> replace_negative_assertions("No dependencies detected.")
        ''
        >>> replace_negative_assertions("The system uses Python 3.11.")
        'The system uses Python 3.11.'
    """
    if not text or not text.strip():
        return ""

    lines = text.split("\n")
    result_lines: list[str] = []

    for line in lines:
        stripped = line.strip()

        # Skip empty lines but preserve them for formatting
        if not stripped:
            result_lines.append(line)
            continue

        # Check if the entire line is essentially a negative assertion
        # (starts with * and contains negative pattern = italicized placeholder)
        if stripped.startswith("*") and stripped.endswith("*"):
            inner = stripped[1:-1]
            if _NEGATIVE_PATTERN_RE.search(inner):
                # Skip this line entirely
                continue

        # Check if line contains a negative pattern
        if _NEGATIVE_PATTERN_RE.search(stripped):
            # Skip lines that contain negative assertions
            continue

        result_lines.append(line)

    result = "\n".join(result_lines)

    # Clean up excessive blank lines
    result = re.sub(r"\n{3,}", "\n\n", result)

    return result.strip()


def is_empty_section(content: str) -> bool:
    """Check if section content is effectively empty.

    Args:
        content: Section content to check.

    Returns:
        True if the content is empty or only contains whitespace/N/A.
    """
    if not content:
        return True

    stripped = content.strip()
    if not stripped:
        return True

    # Check if it's just "N/A" possibly with whitespace
    return stripped.upper() == "N/A"
