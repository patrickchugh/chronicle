"""Unified LLM client wrapper using LiteLLM.

Provides a consistent interface for multiple LLM providers.
Enforces Principle II (Reproducibility) by fixing temperature at 0.
"""

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import litellm

from chronicle.models.llm_config import LLMConfig

if TYPE_CHECKING:
    from chronicle.llm.prompts import (
        SectionDefinition,
        SubSectionPrompt,
    )

logger = logging.getLogger(__name__)


@dataclass
class SubSectionResponse:
    """Response from a sub-section LLM call (T065s).

    Tracks all details of a sub-section prompt for debugging and audit.

    Attributes:
        sub_section_name: Name of the sub-section (e.g., "system_type")
        facts_provided: The facts/data included in the prompt
        prompt_sent: The full prompt text sent to the LLM
        response_text: The LLM's response text
        tokens_used: Token usage statistics
        error: Error message if the call failed
    """

    sub_section_name: str
    facts_provided: dict[str, Any] = field(default_factory=dict)
    prompt_sent: str = ""
    response_text: str = ""
    tokens_used: dict[str, int] = field(default_factory=dict)
    error: str | None = None


@dataclass
class LLMResponse:
    """Response from LLM completion.

    Attributes:
        content: Generated text content
        model: Model that generated the response
        usage: Token usage statistics
        finish_reason: Reason for completion (stop, length, etc.)
    """

    content: str
    model: str
    usage: dict[str, int]
    finish_reason: str | None = None


class LLMClient:
    """Unified LLM client using LiteLLM.

    Supports multiple providers through a single interface:
    - Claude (Anthropic)
    - Gemini (Google)
    - Ollama (local)
    - Bedrock (AWS)

    Principle II: Temperature is enforced at 0 for reproducibility.
    """

    def __init__(self, config: LLMConfig) -> None:
        """Initialize LLM client with configuration.

        Args:
            config: LLM configuration with provider, model, and credentials
        """
        self.config = config
        self._setup_provider()

    def _setup_provider(self) -> None:
        """Configure LiteLLM for the specified provider."""
        # Set API key if provided
        if self.config.api_key:
            if self.config.provider == "claude":
                litellm.anthropic_key = self.config.api_key
            elif self.config.provider == "gemini":
                litellm.google_api_key = self.config.api_key

        # Set API base for Ollama
        if self.config.provider == "ollama" and self.config.api_base:
            litellm.api_base = self.config.api_base

    def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate a completion from the LLM.

        Args:
            prompt: User prompt for the LLM
            system_prompt: Optional system prompt
            max_tokens: Override max_tokens from config

        Returns:
            LLMResponse with generated content

        Raises:
            LLMError: If the completion fails
        """
        messages: list[dict[str, str]] = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        try:
            # Principle II: Reproducibility - use deterministic sampling
            # temperature=0 selects highest probability token
            # top_k=1 provides defense-in-depth (only consider top token)
            completion_kwargs: dict = {
                "model": self.config.get_litellm_model_name(),
                "messages": messages,
                "temperature": 0,
                "max_tokens": max_tokens or self.config.max_tokens,
                "api_key": self.config.api_key,
            }

            # Add provider-specific parameters
            if self.config.provider == "ollama":
                completion_kwargs["api_base"] = self.config.api_base
                completion_kwargs["top_k"] = 1
            elif self.config.provider in {"claude", "gemini"}:
                completion_kwargs["top_k"] = 1

            response = litellm.completion(**completion_kwargs)

            # Extract response content
            choice = response.choices[0]
            content = choice.message.content or ""

            # Build usage dict
            usage = {}
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens or 0,
                    "completion_tokens": response.usage.completion_tokens or 0,
                    "total_tokens": response.usage.total_tokens or 0,
                }

            return LLMResponse(
                content=content,
                model=response.model or self.config.model,
                usage=usage,
                finish_reason=choice.finish_reason,
            )

        except litellm.exceptions.AuthenticationError as e:
            raise LLMError(
                f"Authentication failed for {self.config.provider}: {e}"
            ) from e
        except litellm.exceptions.RateLimitError as e:
            raise LLMError(
                f"Rate limit exceeded for {self.config.provider}: {e}"
            ) from e
        except litellm.exceptions.APIConnectionError as e:
            raise LLMError(f"Connection failed to {self.config.provider}: {e}") from e
        except Exception as e:
            raise LLMError(f"LLM completion failed: {e}") from e

    def summarize(
        self,
        content: str,
        context: str = "technical documentation",
        max_length: int = 500,
    ) -> str:
        """Generate a summary of the provided content.

        Args:
            content: Content to summarize
            context: Context for the summary (e.g., "technical documentation")
            max_length: Approximate maximum length in words

        Returns:
            Generated summary text

        Raises:
            LLMError: If summarization fails
        """
        system_prompt = (
            f"You are a technical writer creating {context}. "
            f"Generate concise, accurate summaries in approximately {max_length} words or less. "
            "Focus on key information relevant to system documentation, architecture, "
            "and security analysis. Use clear, professional language."
        )

        prompt = f"Summarize the following content:\n\n{content}"

        response = self.complete(prompt, system_prompt=system_prompt)
        return response.content

    def check_available(self) -> bool:
        """Check if the LLM provider is available.

        Performs a minimal API call to verify connectivity.

        Returns:
            True if provider is reachable and credentials are valid
        """
        try:
            # Use a minimal prompt to test connectivity
            self.complete("Say 'ok'", max_tokens=10)
            return True
        except LLMError:
            return False


class LLMError(Exception):
    """Exception raised for LLM-related errors."""

    pass


def create_client(config: LLMConfig) -> LLMClient:
    """Create an LLM client from configuration.

    Factory function for creating LLM clients.

    Args:
        config: LLM configuration

    Returns:
        Configured LLMClient instance

    Raises:
        ValueError: If LLM is disabled in config
    """
    if not config.enabled:
        raise ValueError("LLM is disabled in configuration")

    return LLMClient(config)


def concatenate_subsection_responses(
    responses: list[SubSectionResponse],
    strategy: str = "paragraph",
) -> str:
    """Concatenate sub-section responses into final section text (T065r).

    Args:
        responses: List of SubSectionResponse objects
        strategy: Concatenation strategy ("paragraph", "newline", "bullet")

    Returns:
        Concatenated section text
    """
    # Filter out failed responses
    successful = [r for r in responses if r.response_text and not r.error]

    if not successful:
        logger.warning("No successful sub-section responses to concatenate")
        return ""

    texts = [r.response_text.strip() for r in successful]

    if strategy == "paragraph":
        # Join with double newline for paragraphs
        result = "\n\n".join(texts)
    elif strategy == "bullet":
        # Format as bullet points
        result = "\n".join(f"- {text}" for text in texts)
    else:  # "newline" or default
        result = "\n".join(texts)

    logger.debug(
        "Concatenated %d sub-sections using '%s' strategy (%d chars)",
        len(successful),
        strategy,
        len(result),
    )

    return result


def generate_section_summary(
    client: LLMClient,
    section_def: "SectionDefinition",
    data: dict[str, Any],
    system_prompt: str,
    verbose: bool = False,
) -> tuple[str, list[SubSectionResponse]]:
    """Generate a section summary using structured multi-call prompting (T065q).

    Iterates over sub-sections, makes focused LLM calls for each, and
    concatenates the results.

    Args:
        client: LLM client to use for calls
        section_def: Section definition with sub-sections
        data: Analysis data to extract facts from
        system_prompt: System prompt for the LLM
        verbose: If True, log detailed prompt/response info

    Returns:
        Tuple of (concatenated summary text, list of SubSectionResponse)
    """
    from chronicle.llm.prompts import _COMMON_RULES

    responses: list[SubSectionResponse] = []

    logger.info(
        "Generating '%s' section with %d sub-sections",
        section_def.section_name,
        len(section_def.sub_sections),
    )

    for sub_section in section_def.sub_sections:
        response = _call_subsection(
            client=client,
            sub_section=sub_section,
            data=data,
            system_prompt=system_prompt,
            common_rules=_COMMON_RULES,
            verbose=verbose,
        )
        responses.append(response)

    # Concatenate successful responses
    summary = concatenate_subsection_responses(
        responses,
        strategy=section_def.concatenation_strategy,
    )

    # Log summary statistics
    total_tokens = sum(r.tokens_used.get("total_tokens", 0) for r in responses)
    success_count = sum(1 for r in responses if not r.error)
    failed_count = len(responses) - success_count

    # Warn user about partial failures
    if 0 < failed_count < len(responses):
        failed_names = [r.sub_section_name for r in responses if r.error]
        logger.warning(
            "Section '%s' has partial content: %d/%d sub-sections failed (%s). "
            "Output may be incomplete.",
            section_def.section_name,
            failed_count,
            len(responses),
            ", ".join(failed_names),
        )

    logger.info(
        "Section '%s' complete: %d/%d sub-sections successful, %d total tokens",
        section_def.section_name,
        success_count,
        len(responses),
        total_tokens,
    )

    return summary, responses


def _call_subsection(
    client: LLMClient,
    sub_section: "SubSectionPrompt",
    data: dict[str, Any],
    system_prompt: str,
    common_rules: str,
    verbose: bool = False,
) -> SubSectionResponse:
    """Make a single LLM call for a sub-section.

    Args:
        client: LLM client
        sub_section: Sub-section definition
        data: Analysis data
        system_prompt: Base system prompt
        common_rules: Common writing rules to include
        verbose: Enable verbose logging

    Returns:
        SubSectionResponse with results
    """
    response = SubSectionResponse(sub_section_name=sub_section.name)

    # Extract relevant facts based on facts_keys
    facts: dict[str, Any] = {}
    if sub_section.facts_keys:
        for key in sub_section.facts_keys:
            if key in data:
                facts[key] = data[key]

    response.facts_provided = facts

    # Build the focused prompt
    facts_str = _format_facts(facts)
    prompt = (
        f"Answer this specific question in {sub_section.max_words} words or less:\n\n"
        f"Question: {sub_section.question}\n\n"
        f"Facts:\n{facts_str}\n\n"
        f"Answer concisely and factually based ONLY on the facts above."
    )
    response.prompt_sent = prompt

    # Enhanced system prompt with common rules
    enhanced_system = f"{system_prompt}\n{common_rules}"

    if verbose:
        logger.debug(
            "Sub-section '%s' prompt:\n%s\n---\nFacts: %s",
            sub_section.name,
            prompt,
            facts,
        )

    try:
        llm_response = client.complete(
            prompt=prompt,
            system_prompt=enhanced_system,
            max_tokens=sub_section.max_words * 2,  # Approximate tokens from words
        )

        response.response_text = llm_response.content
        response.tokens_used = llm_response.usage

        if verbose:
            logger.debug(
                "Sub-section '%s' response (%d tokens):\n%s",
                sub_section.name,
                llm_response.usage.get("total_tokens", 0),
                llm_response.content,
            )
        else:
            logger.debug(
                "Sub-section '%s': %d tokens, %d chars",
                sub_section.name,
                llm_response.usage.get("total_tokens", 0),
                len(llm_response.content),
            )

    except LLMError as e:
        response.error = str(e)
        logger.warning("Sub-section '%s' failed: %s", sub_section.name, e)

    return response


def _format_facts(facts: dict[str, Any]) -> str:
    """Format facts dictionary for prompt inclusion.

    Args:
        facts: Dictionary of facts

    Returns:
        Formatted string representation
    """
    if not facts:
        return "No specific facts available."

    lines = []
    for key, value in facts.items():
        if isinstance(value, list):
            if value and isinstance(value[0], dict):
                # List of dicts - format each item
                items = [_format_dict_item(item) for item in value[:10]]
                lines.append(f"- {key}: {', '.join(items)}")
            else:
                # Simple list
                lines.append(f"- {key}: {', '.join(str(v) for v in value[:10])}")
        elif isinstance(value, dict):
            # Nested dict
            items = [f"{k}={v}" for k, v in list(value.items())[:5]]
            lines.append(f"- {key}: {', '.join(items)}")
        else:
            lines.append(f"- {key}: {value}")

    return "\n".join(lines)


def _format_dict_item(item: dict[str, Any]) -> str:
    """Format a single dict item for display.

    Args:
        item: Dictionary item

    Returns:
        Formatted string
    """
    if "name" in item:
        name = item["name"]
        version = item.get("version", "")
        if version:
            return f"{name} v{version}"
        return name
    # Fall back to first key-value pair
    if item:
        key, value = next(iter(item.items()))
        return f"{key}={value}"
    return str(item)


# =============================================================================
# Module Summary Generation - REMOVED
# =============================================================================
# generate_module_summaries removed - holistic overview provides module descriptions


# =============================================================================
# Holistic Overview Generation (Phase 4g: Repomix Integration)
# =============================================================================


def generate_holistic_overview(
    client: LLMClient,
    compressed_content: str,
    repository_name: str,
    languages: list[str] | None = None,
    file_count: int = 0,
    verbose: bool = False,
) -> "HolisticOverview":
    """Generate a holistic overview from compressed codebase (T089a-d).

    Makes a single LLM call with the Repomix-compressed codebase to generate
    a system-wide understanding.

    Args:
        client: LLM client to use
        compressed_content: Tree-sitter compressed codebase from Repomix
        repository_name: Name of the repository
        languages: Detected programming languages
        file_count: Number of files in the codebase
        verbose: Enable verbose logging

    Returns:
        HolisticOverview with system-wide analysis
    """
    import json

    from chronicle.llm.prompts import (
        HOLISTIC_OVERVIEW_SYSTEM_PROMPT,
        build_holistic_overview_prompt,
    )
    from chronicle.models.canonical import HolisticOverview

    logger.info(
        "Generating holistic overview for %s (%d chars compressed)",
        repository_name,
        len(compressed_content),
    )

    # Build the prompt
    prompt = build_holistic_overview_prompt(
        repository_name=repository_name,
        compressed_content=compressed_content,
        languages=languages,
        file_count=file_count,
    )

    if verbose:
        logger.debug("Holistic overview prompt:\n%s", prompt[:2000])

    try:
        # Make LLM call with larger token budget for comprehensive analysis
        response = client.complete(
            prompt=prompt,
            system_prompt=HOLISTIC_OVERVIEW_SYSTEM_PROMPT,
            max_tokens=2000,
        )

        if verbose:
            logger.debug(
                "Holistic overview response (%d tokens):\n%s",
                response.usage.get("total_tokens", 0),
                response.content,
            )

        # Parse JSON response
        overview = _parse_holistic_overview_response(
            response.content,
            response.content,  # raw_response
        )

        logger.info(
            "Generated holistic overview: purpose=%d chars, %d components",
            len(overview.purpose),
            len(overview.core_components),
        )

        # Log detected integrations for visibility
        if overview.external_integrations:
            integration_names = [i.name for i in overview.external_integrations]
            logger.info(
                "LLM detected integrations: %s",
                ", ".join(integration_names),
            )
        else:
            logger.debug("LLM detected no external integrations")

        return overview

    except LLMError as e:
        logger.error("Holistic overview generation failed: %s", e)
        return HolisticOverview(
            purpose="",
            raw_response=f"Error: {e}",
        )


def _parse_holistic_overview_response(
    response_text: str,
    raw_response: str,
) -> "HolisticOverview":
    """Parse LLM response into HolisticOverview dataclass.

    Args:
        response_text: LLM response text (should be JSON)
        raw_response: Original raw response for storage

    Returns:
        HolisticOverview populated from parsed JSON
    """
    import json
    import re

    from chronicle.models.canonical import HolisticOverview
    from chronicle.models.canonical.compressed import ExternalIntegrationInfo

    # Try to extract JSON from response (may have markdown code blocks)
    json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Try to find JSON object directly
        json_match = re.search(r"\{[\s\S]*\}", response_text)
        if json_match:
            json_str = json_match.group(0)
        else:
            logger.warning("Could not find JSON in holistic overview response")
            return HolisticOverview(
                purpose=response_text[:500] if response_text else "",
                raw_response=raw_response,
            )

    try:
        data = json.loads(json_str)

        # Parse external_integrations as structured objects
        external_integrations: list[ExternalIntegrationInfo] = []
        for item in data.get("external_integrations", []):
            if isinstance(item, dict):
                external_integrations.append(
                    ExternalIntegrationInfo(
                        name=item.get("name", ""),
                        type=item.get("type", ""),
                        purpose=item.get("purpose", ""),
                    )
                )
            elif isinstance(item, str):
                # Backwards compatibility: simple string becomes name
                external_integrations.append(
                    ExternalIntegrationInfo(name=item, type="", purpose="")
                )

        return HolisticOverview(
            purpose=data.get("purpose", ""),
            architecture_style=data.get("architecture_style", ""),
            core_components=data.get("core_components", []),
            data_flow=data.get("data_flow", ""),
            design_patterns=data.get("design_patterns", []),
            external_integrations=external_integrations,
            entry_points=data.get("entry_points", []),
            raw_response=raw_response,
        )

    except json.JSONDecodeError as e:
        logger.warning("Failed to parse holistic overview JSON: %s", e)
        return HolisticOverview(
            purpose=response_text[:500] if response_text else "",
            raw_response=raw_response,
        )


# Import HolisticOverview for type hints
if TYPE_CHECKING:
    from chronicle.models.canonical import HolisticOverview
