"""LLM prompt templates for documentation section summaries.

Provides structured prompts for generating section summaries from
deterministic analysis data. Follows Principle I (Deterministic-First)
by always basing summaries on concrete analysis results.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from chronicle.models.analysis import AnalysisResult


# System prompts for different documentation contexts
# Customize these to control LLM output style and content

# =============================================================================
# Negative Assertion Instruction (T085e)
# =============================================================================

NEGATIVE_ASSERTION_INSTRUCTION = """
CRITICAL: NO NEGATIVE ASSERTIONS

Do NOT include statements about what is NOT present or NOT detected:
- Do NOT say "not found", "not detected", "unable to determine"
- Do NOT say "none identified", "not determinable", "no X detected"
- Do NOT say "could not find", "missing", "absent"

If a section has no relevant content, simply output: N/A

WRONG: "No message queues were detected in this codebase."
WRONG: "Cloud provider: Not determinable from analysis"
WRONG: "Infrastructure details: Unable to determine"

RIGHT: Simply omit the section or output "N/A"

The reader should only see what EXISTS, not what doesn't exist.
"""

# Common rules applied to all sections - enforces factual, definitive language
_COMMON_RULES = """
CRITICAL WRITING RULES - YOU MUST FOLLOW THESE:

1. NEVER use hedging language. These phrases are BANNED:
   - "appears to be", "seems to", "likely", "probably", "possibly"
   - "may be used for", "could be", "might", "presumably"
   - "suggests that", "indicates that", "implies"
   - "potentially", "apparently", "presumably"

2. State detected facts DEFINITIVELY:
   WRONG: "The system appears to use AWS Lambda"
   RIGHT: "The system uses AWS Lambda"

3. If you cannot determine something from the provided data, DO NOT GUESS.
   Instead, add a final line: "Not determinable from analysis: [specific item]"

4. NEVER use vague filler phrases:
   BANNED: "various purposes", "multiple functions", "different operations"
   BANNED: "and more", "among others", "etc.", "and so on"

5. Use SPECIFIC names, counts, and values from the data provided.
   WRONG: "uses several AWS services"
   RIGHT: "uses 3 AWS services: Lambda, DynamoDB, API Gateway"
"""

SYSTEM_PROMPTS = {
    "overview": (
        "Write a 2-3 paragraph system overview for enterprise IT documentation.\n"
        + _COMMON_RULES
        + NEGATIVE_ASSERTION_INSTRUCTION
        + "\nSTRUCTURE:\n"
        "Paragraph 1: What the system IS (technologies, architecture pattern)\n"
        "Paragraph 2: Key components and their roles\n"
        "Paragraph 3 (if needed): Notable configurations or characteristics\n\n"
        "GOOD EXAMPLE:\n"
        "'This is a serverless application on AWS (us-east-1). The Lambda function "
        "bedrock_proxy (Node.js 20.x, 512MB) handles requests via API Gateway. "
        "Data is stored in DynamoDB table api_usage. CloudWatch monitors logs "
        "with 2 metric alarms configured.'\n\n"
        "BAD EXAMPLE:\n"
        "'This appears to be a cloud-native system that likely leverages various "
        "AWS services for different purposes and may include AI capabilities.'"
    ),
    "tech_stack": (
        "Document the detected technology stack.\n"
        + _COMMON_RULES
        + NEGATIVE_ASSERTION_INSTRUCTION
        + "\nINCLUDE:\n"
        "- Languages with exact file counts\n"
        "- Frameworks with versions (if detected)\n"
        "- Key dependencies by exact name\n\n"
        "GOOD EXAMPLE:\n"
        "'Languages: Python (1 file), JavaScript (1 file). "
        "Key npm packages: @aws-sdk/client-bedrock-runtime v3.0.0, "
        "@aws-sdk/client-dynamodb v3.0.0. Total: 483 packages.'\n\n"
        "BAD EXAMPLE:\n"
        "'Uses Python and JavaScript with various AWS-related dependencies "
        "for different purposes.'"
    ),
    "architecture": (
        "Document the cloud infrastructure architecture.\n"
        + _COMMON_RULES
        + NEGATIVE_ASSERTION_INSTRUCTION
        + "\nINCLUDE:\n"
        "- Each resource by its Terraform name\n"
        "- Specific configurations (memory, timeout, region)\n"
        "- The architectural pattern\n\n"
        "GOOD EXAMPLE:\n"
        "'Serverless architecture on AWS us-east-1:\n"
        "- Lambda: bedrock_proxy (Node.js 20.x, 512MB, 300s timeout)\n"
        "- API Gateway: api with /chat resource, prod stage\n"
        "- DynamoDB: api_usage table (PAY_PER_REQUEST, key: client_id)\n"
        "- CloudWatch: 2 alarms (cost_alert threshold:50, lambda_errors threshold:10)'\n\n"
        "BAD EXAMPLE:\n"
        "'This appears to be a serverless architecture that likely uses "
        "Lambda for compute and possibly DynamoDB for storage.'"
    ),
    "dependencies": (
        "Document the system dependencies from SBOM.\n"
        + _COMMON_RULES
        + NEGATIVE_ASSERTION_INSTRUCTION
        + "\nINCLUDE:\n"
        "- Direct dependency count (declared in manifest files)\n"
        "- Total package count including transitive dependencies\n"
        "- Ecosystem breakdown\n"
        "- Key direct dependencies by exact name\n\n"
        "GOOD EXAMPLE:\n"
        "'12 direct dependencies (483 total packages including transitive) "
        "across 4 ecosystems: npm (majority), go, terraform, github-action.\n"
        "Direct AWS SDK packages: @aws-sdk/client-bedrock-runtime, @aws-sdk/client-dynamodb.\n"
        "Direct utilities: uuid, express.'\n\n"
        "BAD EXAMPLE:\n"
        "'Dependencies include various AWS packages that are likely used for "
        "different cloud operations.'"
    ),
}


@dataclass
class PromptContext:
    """Context for constructing an LLM prompt.

    Attributes:
        section: Section name (overview, tech_stack, architecture, etc.)
        data: Structured data from deterministic analysis
        max_words: Target maximum words for the summary
    """

    section: str
    data: dict[str, Any]
    max_words: int = 200


@dataclass
class SubSectionPrompt:
    """Definition of a focused sub-section prompt (T065a).

    Sub-sections break documentation sections into focused questions
    for more consistent, higher-quality LLM output.

    Attributes:
        name: Sub-section identifier (e.g., "system_type")
        question: The focused question to answer
        max_words: Maximum words for the response
        facts_keys: Keys from data dict to include as facts
    """

    name: str
    question: str
    max_words: int = 50
    facts_keys: list[str] | None = None


@dataclass
class SectionDefinition:
    """Definition of a documentation section with sub-sections (T065b).

    Attributes:
        section_name: Name of the section (e.g., "overview")
        sub_sections: List of sub-section prompts to execute
        concatenation_strategy: How to join sub-answers ("newline", "paragraph", "bullet")
    """

    section_name: str
    sub_sections: list[SubSectionPrompt]
    concatenation_strategy: str = "paragraph"


# Sub-section definitions for each documentation section (T065c)
SECTION_DEFINITIONS: dict[str, SectionDefinition] = {
    # Overview Section Sub-Sections (T065d-f)
    "overview": SectionDefinition(
        section_name="overview",
        sub_sections=[
            SubSectionPrompt(
                name="system_type",
                question="What kind of system is this and what core technologies does it use?",
                max_words=60,
                facts_keys=[
                    "repository_name",
                    "languages",
                    "frameworks",
                    "cloud_providers",
                ],
            ),
            SubSectionPrompt(
                name="key_components",
                question="What are the main components/services and their roles?",
                max_words=80,
                facts_keys=["resources", "modules", "entry_points"],
            ),
            SubSectionPrompt(
                name="architecture_pattern",
                question="What architectural pattern does this system follow?",
                max_words=40,
                facts_keys=["cloud_providers", "resources", "frameworks"],
            ),
        ],
        concatenation_strategy="paragraph",
    ),
    # Tech Stack Section Sub-Sections (T065g-i)
    "tech_stack": SectionDefinition(
        section_name="tech_stack",
        sub_sections=[
            SubSectionPrompt(
                name="languages",
                question="What programming languages are used and in what proportion?",
                max_words=40,
                facts_keys=["languages"],
            ),
            SubSectionPrompt(
                name="frameworks_libraries",
                question="What key frameworks and libraries are used?",
                max_words=50,
                facts_keys=["frameworks", "key_dependencies"],
            ),
            SubSectionPrompt(
                name="package_summary",
                question="Summarize the dependency ecosystems and package counts.",
                max_words=30,
                facts_keys=["ecosystems", "total_packages", "direct_packages"],
            ),
        ],
        concatenation_strategy="paragraph",
    ),
    # Architecture Section Sub-Sections (T065j-l)
    "architecture": SectionDefinition(
        section_name="architecture",
        sub_sections=[
            SubSectionPrompt(
                name="infrastructure_overview",
                question="What cloud services and resources are provisioned?",
                max_words=60,
                facts_keys=["cloud_providers", "resources_by_type", "node_count"],
            ),
            SubSectionPrompt(
                name="data_flow",
                question="How do requests and data flow through the system?",
                max_words=60,
                facts_keys=["connections", "resources_by_type"],
            ),
            SubSectionPrompt(
                name="configuration",
                question="What key configuration values are set?",
                max_words=40,
                facts_keys=["terraform_variables"],
            ),
        ],
        concatenation_strategy="paragraph",
    ),
    # Dependencies Section Sub-Sections (T065m-n)
    "dependencies": SectionDefinition(
        section_name="dependencies",
        sub_sections=[
            SubSectionPrompt(
                name="ecosystem_breakdown",
                question="What package ecosystems are used and their package counts?",
                max_words=40,
                facts_keys=["ecosystems", "total_packages", "direct_packages"],
            ),
            SubSectionPrompt(
                name="key_packages",
                question="What are the most important direct dependency packages by name?",
                max_words=60,
                facts_keys=["direct_dependencies"],
            ),
        ],
        concatenation_strategy="paragraph",
    ),
}


def get_section_definition(section_name: str) -> SectionDefinition | None:
    """Get the section definition for structured prompting.

    Args:
        section_name: Name of the section

    Returns:
        SectionDefinition or None if not defined
    """
    return SECTION_DEFINITIONS.get(section_name)


def build_overview_prompt(result: "AnalysisResult") -> PromptContext:
    """Build prompt context for system overview section.

    Args:
        result: Complete analysis result

    Returns:
        PromptContext with overview data
    """
    # Collect key facts from analysis
    facts = []

    # Repository info
    facts.append(f"Repository: {result.repository_name}")

    # Technology stack
    if result.technology_stack:
        ts = result.technology_stack
        if ts.languages:
            langs = ", ".join(f"{lang.name}" for lang in ts.languages)
            facts.append(f"Languages: {langs}")
        if ts.frameworks:
            frameworks = ", ".join(f.name for f in ts.frameworks)
            facts.append(f"Frameworks: {frameworks}")
        if ts.dependencies:
            facts.append(f"Direct dependencies: {len(ts.dependencies)}")

    # SBOM summary
    if result.sbom:
        facts.append(f"Total packages (SBOM): {result.sbom.package_count}")
        if result.sbom.get_unique_ecosystems():
            facts.append(
                f"Package ecosystems: {', '.join(result.sbom.get_unique_ecosystems())}"
            )

    # Architecture summary
    if result.architecture and result.architecture.graph:
        graph = result.architecture.graph
        facts.append(f"Infrastructure resources: {graph.node_count}")
        if hasattr(result.architecture, "cloud_providers"):
            providers = result.architecture.cloud_providers
            if providers:
                facts.append(f"Cloud providers: {', '.join(providers)}")

    # Source analysis
    if result.source_analysis:
        sa = result.source_analysis
        facts.append(f"Source modules: {len(sa.modules)}")
        facts.append(f"Classes: {len(sa.classes)}")
        facts.append(f"Functions: {len(sa.functions)}")

    data = {
        "repository_name": result.repository_name,
        "facts": facts,
        "timestamp": result.timestamp.isoformat() if result.timestamp else None,
    }

    return PromptContext(section="overview", data=data, max_words=250)


def build_tech_stack_prompt(result: "AnalysisResult") -> PromptContext:
    """Build prompt context for technology stack section.

    Args:
        result: Complete analysis result

    Returns:
        PromptContext with tech stack data
    """
    data: dict[str, Any] = {"languages": [], "frameworks": [], "dependencies": []}

    if result.technology_stack:
        ts = result.technology_stack
        data["languages"] = [
            {"name": lang.name, "version": lang.version, "file_count": lang.file_count}
            for lang in ts.languages
        ]
        data["frameworks"] = [
            {"name": f.name, "version": f.version} for f in ts.frameworks
        ]
        data["dependencies"] = [
            {"name": d.name, "version": d.version, "ecosystem": d.ecosystem}
            for d in ts.dependencies[:20]  # Limit to top 20
        ]
        data["total_dependencies"] = len(ts.dependencies)

    return PromptContext(section="tech_stack", data=data, max_words=150)


def build_architecture_prompt(result: "AnalysisResult") -> PromptContext:
    """Build prompt context for architecture section.

    Args:
        result: Complete analysis result

    Returns:
        PromptContext with architecture data
    """
    data: dict[str, Any] = {
        "has_architecture": False,
        "resources": [],
        "providers": [],
        "connections": 0,
        "terraform_variables": {},
    }

    if result.architecture:
        arch = result.architecture
        data["has_architecture"] = True

        if arch.graph:
            data["node_count"] = arch.graph.node_count
            data["connections"] = arch.graph.connection_count

            # Group resources by type
            resources_by_type: dict[str, list[str]] = {}
            for _node_id, node in arch.graph.nodes.items():
                resource_type = node.type
                if resource_type not in resources_by_type:
                    resources_by_type[resource_type] = []
                resources_by_type[resource_type].append(node.name)

            data["resources_by_type"] = resources_by_type

        if hasattr(arch, "cloud_providers"):
            data["providers"] = arch.cloud_providers

        # Include terraform variables if available
        if arch.source and arch.source.metadata:
            tf_vars = arch.source.metadata.get("terraform_variables", {})
            data["terraform_variables"] = tf_vars

    return PromptContext(section="architecture", data=data, max_words=200)


def build_dependencies_prompt(result: "AnalysisResult") -> PromptContext:
    """Build prompt context for dependencies/SBOM section.

    Args:
        result: Complete analysis result

    Returns:
        PromptContext with SBOM data
    """
    data: dict[str, Any] = {
        "has_sbom": False,
        "total_packages": 0,
        "direct_packages": 0,
        "ecosystems": [],
        "direct_dependencies": [],
    }

    if result.sbom:
        sbom = result.sbom
        data["has_sbom"] = True
        data["total_packages"] = sbom.package_count
        data["direct_packages"] = sbom.direct_package_count
        data["ecosystems"] = sbom.get_unique_ecosystems()

        # Get direct dependencies (the meaningful ones for documentation)
        direct_deps = sbom.get_direct_packages()
        data["direct_dependencies"] = [
            {"name": p.name, "version": p.version, "ecosystem": p.ecosystem}
            for p in direct_deps[:20]  # Top 20 direct dependencies
        ]

    return PromptContext(section="dependencies", data=data, max_words=150)


def format_prompt(context: PromptContext) -> str:
    """Format a prompt from context data.

    Args:
        context: PromptContext with section and data

    Returns:
        Formatted prompt string for LLM
    """
    section = context.section
    data = context.data
    max_words = context.max_words

    # Build the prompt based on section type
    if section == "overview":
        facts_str = "\n".join(f"- {fact}" for fact in data.get("facts", []))
        prompt = (
            f"Based on the following analysis of '{data.get('repository_name', 'unknown')}', "
            f"write a system overview in approximately {max_words} words:\n\n"
            f"Key Facts:\n{facts_str}"
        )

    elif section == "tech_stack":
        langs = data.get("languages", [])
        frameworks = data.get("frameworks", [])
        deps = data.get("dependencies", [])

        langs_str = (
            ", ".join(f"{lang['name']}" for lang in langs) if langs else "None detected"
        )
        frameworks_str = (
            ", ".join(f"{f['name']}" for f in frameworks)
            if frameworks
            else "None detected"
        )
        deps_str = (
            ", ".join(f"{d['name']}" for d in deps[:10]) if deps else "None detected"
        )

        prompt = (
            f"Summarize the technology stack in approximately {max_words} words:\n\n"
            f"Languages: {langs_str}\n"
            f"Frameworks: {frameworks_str}\n"
            f"Key dependencies: {deps_str}\n"
            f"Total dependencies: {data.get('total_dependencies', 0)}"
        )

    elif section == "architecture":
        if not data.get("has_architecture"):
            return "No infrastructure-as-code detected in this repository."

        resources = data.get("resources_by_type", {})
        providers = data.get("providers", [])
        tf_vars = data.get("terraform_variables", {})

        resources_str = "\n".join(
            f"- {rtype}: {len(names)} resources" for rtype, names in resources.items()
        )
        providers_str = ", ".join(providers) if providers else "Unknown"
        vars_str = ", ".join(f"{k}={v}" for k, v in list(tf_vars.items())[:5])

        prompt = (
            f"Describe the cloud architecture in approximately {max_words} words:\n\n"
            f"Cloud Providers: {providers_str}\n"
            f"Total Resources: {data.get('node_count', 0)}\n"
            f"Connections: {data.get('connections', 0)}\n"
            f"Resources by Type:\n{resources_str}\n"
        )
        if vars_str:
            prompt += f"Configuration: {vars_str}"

    elif section == "dependencies":
        if not data.get("has_sbom"):
            return "No SBOM data available."

        ecosystems = data.get("ecosystems", [])
        direct_deps = data.get("direct_dependencies", [])
        direct_count = data.get("direct_packages", 0)
        total_count = data.get("total_packages", 0)

        ecosystems_str = ", ".join(ecosystems) if ecosystems else "None"
        deps_str = "\n".join(
            f"- {d['name']} ({d['ecosystem']})" for d in direct_deps[:15]
        )

        prompt = (
            f"Summarize the dependencies in approximately {max_words} words:\n\n"
            f"Direct Dependencies: {direct_count}\n"
            f"Total Packages (incl. transitive): {total_count}\n"
            f"Ecosystems: {ecosystems_str}\n"
            f"Direct Dependencies:\n{deps_str}"
        )

    else:
        prompt = f"Summarize the {section} section in approximately {max_words} words."

    return prompt


def get_system_prompt(section: str) -> str:
    """Get the system prompt for a section.

    Args:
        section: Section name

    Returns:
        System prompt string
    """
    return SYSTEM_PROMPTS.get(section, SYSTEM_PROMPTS["overview"])


# Placeholder text for when LLM is unavailable
PLACEHOLDER_SUMMARIES = {
    "overview": "*Overview summary will be generated when LLM is configured.*",
    "tech_stack": "*Technology stack summary will be generated when LLM is configured.*",
    "architecture": "*Architecture summary will be generated when LLM is configured.*",
    "dependencies": "*Dependencies summary will be generated when LLM is configured.*",
}


def get_placeholder(section: str) -> str:
    """Get placeholder text for a section when LLM is unavailable.

    Args:
        section: Section name

    Returns:
        Placeholder text
    """
    return PLACEHOLDER_SUMMARIES.get(
        section,
        f"*{section.replace('_', ' ').title()} summary pending LLM configuration.*",
    )


# =============================================================================
# Module Summary - REMOVED
# =============================================================================
# Module summary prompts removed - holistic overview provides module descriptions
# See "Core Components" in HolisticOverview for module responsibilities


# =============================================================================
# Holistic Overview Prompts (Phase 4g: Repomix Integration)
# =============================================================================

# System prompt for holistic codebase overview (T088a-d)
HOLISTIC_OVERVIEW_SYSTEM_PROMPT = """You are analyzing a compressed codebase for enterprise IT architecture documentation.

The codebase has been compressed using tree-sitter skeleton extraction, showing function signatures without implementation bodies. This allows you to understand the system's structure holistically.

Your analysis must be:
- SPECIFIC: Use actual class names, function names, and module names from the code
- DEFINITIVE: State facts with certainty. Code either IS something or it ISN'T - there's no "appears to be"
- CONCISE: Brief descriptions only, no filler

ABSOLUTELY BANNED - Never use these words/phrases:
- "appears to", "seems to", "likely", "probably", "possibly", "may", "might", "could"
- "not found", "not detected", "not determinable", "unable to determine", "none identified"
- "from the provided information", "from the analysis", "based on the code"
- Any phrase explaining what you CANNOT determine

CRITICAL RULE FOR MISSING INFORMATION:
- If you cannot determine something, use an EMPTY string or EMPTY array
- NEVER explain why something is missing
- NEVER say what was not found
- Example: If no cloud providers exist, use "external_dependencies": [] (empty array)
- Example: If architecture style is unclear, use "architecture_style": "" (empty string)

Focus on WHAT EXISTS:
1. What does this system DO? (purpose)
2. What pattern does it follow? (architecture_style - or empty if unclear)
3. What are the main modules/classes? (core_components)
4. How does data flow? (data_flow - or empty if unclear)
5. What patterns are used? (design_patterns - or empty array)
6. What external services/APIs does this connect to? (external_integrations - or empty array)
   Include: databases, caches, message queues, cloud services, LLM providers, HTTP APIs, storage
7. How do users interact? (entry_points)
"""

HOLISTIC_OVERVIEW_USER_PROMPT_TEMPLATE = """Analyze the following compressed codebase and provide a holistic overview.

Repository: {repository_name}
Languages: {languages}
Total Files: {file_count}

=== COMPRESSED CODEBASE (Function Signatures) ===
{compressed_content}
=== END CODEBASE ===

Provide your analysis in the following EXACT JSON format:
{{
    "purpose": "1-2 sentence description of what this system does",
    "architecture_style": "CLI Tool, Monolith, Microservices, Serverless, Event-Driven, or empty string if unclear",
    "core_components": [
        "ModuleName: what it does",
        "ClassName: what it does"
    ],
    "data_flow": "1-2 sentence description of how data flows, or empty string",
    "design_patterns": ["Pattern1", "Pattern2"],
    "external_integrations": [
        {{"name": "ServiceName", "type": "Database|Cache|Queue|LLM|HTTP API|Storage|Cloud", "purpose": "brief purpose"}}
    ],
    "entry_points": ["cli.main()", "handler()"]
}}

RULES:
- Use ACTUAL names from the code (e.g., "AnalysisPipeline: orchestrates analysis stages")
- For external_integrations, identify databases, caches, queues, LLM providers, HTTP clients, cloud services
- Use EMPTY string "" or EMPTY array [] for anything you cannot determine
- NEVER explain what is missing or why"""


def build_holistic_overview_prompt(
    repository_name: str,
    compressed_content: str,
    languages: list[str] | None = None,
    file_count: int = 0,
) -> str:
    """Build the user prompt for holistic codebase overview.

    Args:
        repository_name: Name of the repository
        compressed_content: Tree-sitter compressed codebase from Repomix
        languages: Detected programming languages
        file_count: Number of files in the codebase

    Returns:
        Formatted prompt string for LLM
    """
    languages_str = ", ".join(languages) if languages else "Not detected"

    # Truncate compressed content if too large (keep first ~50k chars)
    max_content_length = 50000
    if len(compressed_content) > max_content_length:
        compressed_content = (
            compressed_content[:max_content_length]
            + f"\n\n... [truncated, {len(compressed_content) - max_content_length} chars omitted]"
        )

    return HOLISTIC_OVERVIEW_USER_PROMPT_TEMPLATE.format(
        repository_name=repository_name,
        languages=languages_str,
        file_count=file_count,
        compressed_content=compressed_content,
    )
