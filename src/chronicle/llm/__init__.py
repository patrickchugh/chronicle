"""LLM integration module for chronicle.

Provides unified LLM client wrapper using LiteLLM for multi-provider support.
Supports Claude, Gemini, Ollama, and Bedrock providers.

Principle II (Reproducibility): Temperature is fixed at 0 for deterministic outputs.
Principle III (Preflight Validation): Provider credentials validated before use.
"""

from chronicle.llm.client import (
    LLMClient,
    LLMError,
    LLMResponse,
    SubSectionResponse,
    concatenate_subsection_responses,
    create_client,
    generate_section_summary,
)
from chronicle.llm.prompts import (
    PLACEHOLDER_SUMMARIES,
    SECTION_DEFINITIONS,
    SYSTEM_PROMPTS,
    PromptContext,
    SectionDefinition,
    SubSectionPrompt,
    build_architecture_prompt,
    build_dependencies_prompt,
    build_overview_prompt,
    build_tech_stack_prompt,
    format_prompt,
    get_placeholder,
    get_section_definition,
    get_system_prompt,
)
from chronicle.models.llm_config import VALID_PROVIDERS, LLMConfig

__all__ = [
    "LLMClient",
    "LLMConfig",
    "LLMError",
    "LLMResponse",
    "PLACEHOLDER_SUMMARIES",
    "PromptContext",
    "SECTION_DEFINITIONS",
    "SYSTEM_PROMPTS",
    "SectionDefinition",
    "SubSectionPrompt",
    "SubSectionResponse",
    "VALID_PROVIDERS",
    "build_architecture_prompt",
    "build_dependencies_prompt",
    "build_overview_prompt",
    "build_tech_stack_prompt",
    "concatenate_subsection_responses",
    "create_client",
    "format_prompt",
    "generate_section_summary",
    "get_placeholder",
    "get_section_definition",
    "get_system_prompt",
]
