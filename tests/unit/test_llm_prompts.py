"""Unit tests for LLM prompt templates and construction (T060a, T060b).

Tests the prompt templates, system prompts, placeholder text,
and prompt construction from AnalysisResult context.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from chronicle.llm.prompts import (
    PLACEHOLDER_SUMMARIES,
    SYSTEM_PROMPTS,
    PromptContext,
    build_architecture_prompt,
    build_dependencies_prompt,
    build_overview_prompt,
    build_tech_stack_prompt,
    format_prompt,
    get_placeholder,
    get_system_prompt,
)
from chronicle.models.analysis import (
    AnalysisResult,
    Dependency,
    Framework,
    LanguageInfo,
    TechnologyStack,
)


class TestSystemPrompts:
    """Tests for system prompt definitions."""

    def test_all_sections_have_system_prompts(self) -> None:
        """Test that all required sections have system prompts."""
        required_sections = [
            "overview",
            "tech_stack",
            "architecture",
            "dependencies",
        ]
        for section in required_sections:
            assert section in SYSTEM_PROMPTS
            assert len(SYSTEM_PROMPTS[section]) > 50  # Meaningful prompt length

    def test_system_prompts_contain_writing_rules(self) -> None:
        """Test that system prompts contain critical writing rules."""
        for section, prompt in SYSTEM_PROMPTS.items():
            assert (
                "CRITICAL WRITING RULES" in prompt
            ), f"Section '{section}' missing writing rules"

    def test_get_system_prompt_returns_correct_prompt(self) -> None:
        """Test get_system_prompt returns the correct prompt."""
        assert get_system_prompt("overview") == SYSTEM_PROMPTS["overview"]
        assert get_system_prompt("tech_stack") == SYSTEM_PROMPTS["tech_stack"]
        assert get_system_prompt("architecture") == SYSTEM_PROMPTS["architecture"]

    def test_get_system_prompt_defaults_to_overview(self) -> None:
        """Test get_system_prompt falls back to overview for unknown sections."""
        assert get_system_prompt("unknown_section") == SYSTEM_PROMPTS["overview"]


class TestPlaceholderSummaries:
    """Tests for placeholder text when LLM is unavailable."""

    def test_all_sections_have_placeholders(self) -> None:
        """Test that all sections have placeholder text."""
        required_sections = [
            "overview",
            "tech_stack",
            "architecture",
            "dependencies",
        ]
        for section in required_sections:
            assert section in PLACEHOLDER_SUMMARIES

    def test_placeholders_indicate_llm_needed(self) -> None:
        """Test that placeholders clearly indicate LLM is needed."""
        for placeholder in PLACEHOLDER_SUMMARIES.values():
            assert "LLM" in placeholder

    def test_get_placeholder_returns_correct_text(self) -> None:
        """Test get_placeholder returns the correct placeholder."""
        assert get_placeholder("overview") == PLACEHOLDER_SUMMARIES["overview"]
        assert get_placeholder("tech_stack") == PLACEHOLDER_SUMMARIES["tech_stack"]

    def test_get_placeholder_generates_for_unknown_section(self) -> None:
        """Test get_placeholder generates sensible placeholder for unknown sections."""
        placeholder = get_placeholder("custom_section")
        assert (
            "Custom Section" in placeholder or "custom section" in placeholder.lower()
        )
        assert "pending" in placeholder.lower()


class TestPromptContext:
    """Tests for PromptContext dataclass."""

    def test_prompt_context_creation(self) -> None:
        """Test PromptContext can be created with required fields."""
        context = PromptContext(section="overview", data={"key": "value"})
        assert context.section == "overview"
        assert context.data == {"key": "value"}
        assert context.max_words == 200  # Default

    def test_prompt_context_custom_max_words(self) -> None:
        """Test PromptContext accepts custom max_words."""
        context = PromptContext(section="tech_stack", data={}, max_words=100)
        assert context.max_words == 100


class TestBuildOverviewPrompt:
    """Tests for build_overview_prompt function."""

    @pytest.fixture
    def minimal_result(self) -> AnalysisResult:
        """Create a minimal AnalysisResult for testing."""
        return AnalysisResult(
            repository_path=Path("/test/repo"),
            repository_name="test-repo",
            timestamp=datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC),
        )

    @pytest.fixture
    def full_result(self) -> AnalysisResult:
        """Create a complete AnalysisResult for testing."""
        result = AnalysisResult(
            repository_path=Path("/test/repo"),
            repository_name="full-test-repo",
            timestamp=datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC),
        )
        result.technology_stack = TechnologyStack(
            languages=[
                LanguageInfo(name="Python", version="3.11", file_count=50),
                LanguageInfo(name="TypeScript", version="5.0", file_count=30),
            ],
            frameworks=[Framework(name="FastAPI"), Framework(name="React")],
            dependencies=[
                Dependency(
                    name="pytest", ecosystem="pypi", source_file="pyproject.toml"
                ),
                Dependency(
                    name="boto3", ecosystem="pypi", source_file="pyproject.toml"
                ),
            ],
        )
        return result

    def test_build_overview_prompt_minimal(
        self, minimal_result: AnalysisResult
    ) -> None:
        """Test building overview prompt with minimal data."""
        context = build_overview_prompt(minimal_result)

        assert context.section == "overview"
        assert context.max_words == 250
        assert "test-repo" in context.data["repository_name"]
        assert "Repository: test-repo" in context.data["facts"]

    def test_build_overview_prompt_with_tech_stack(
        self, full_result: AnalysisResult
    ) -> None:
        """Test building overview prompt includes technology stack."""
        context = build_overview_prompt(full_result)

        facts = context.data["facts"]
        assert any("Python" in f for f in facts)
        assert any("FastAPI" in f or "React" in f for f in facts)
        assert any("dependencies" in f.lower() for f in facts)

    def test_build_overview_prompt_includes_timestamp(
        self, minimal_result: AnalysisResult
    ) -> None:
        """Test build_overview_prompt includes timestamp."""
        context = build_overview_prompt(minimal_result)
        assert context.data["timestamp"] is not None


class TestBuildTechStackPrompt:
    """Tests for build_tech_stack_prompt function."""

    @pytest.fixture
    def result_with_stack(self) -> AnalysisResult:
        """Create AnalysisResult with technology stack."""
        result = AnalysisResult(
            repository_path=Path("/test/repo"),
            repository_name="tech-repo",
        )
        result.technology_stack = TechnologyStack(
            languages=[
                LanguageInfo(name="Python", version="3.11", file_count=50),
                LanguageInfo(name="Go", version="1.21", file_count=20),
            ],
            frameworks=[
                Framework(name="Django", version="4.2"),
                Framework(name="Gin", version="1.9"),
            ],
            dependencies=[
                Dependency(
                    name="requests", ecosystem="pypi", source_file="requirements.txt"
                ),
                Dependency(
                    name="boto3", ecosystem="pypi", source_file="requirements.txt"
                ),
            ],
        )
        return result

    def test_build_tech_stack_prompt_extracts_languages(
        self, result_with_stack: AnalysisResult
    ) -> None:
        """Test languages are extracted correctly."""
        context = build_tech_stack_prompt(result_with_stack)

        assert context.section == "tech_stack"
        assert len(context.data["languages"]) == 2
        assert context.data["languages"][0]["name"] == "Python"
        assert context.data["languages"][0]["version"] == "3.11"

    def test_build_tech_stack_prompt_extracts_frameworks(
        self, result_with_stack: AnalysisResult
    ) -> None:
        """Test frameworks are extracted correctly."""
        context = build_tech_stack_prompt(result_with_stack)

        assert len(context.data["frameworks"]) == 2
        assert context.data["frameworks"][0]["name"] == "Django"

    def test_build_tech_stack_prompt_limits_dependencies(
        self, result_with_stack: AnalysisResult
    ) -> None:
        """Test dependencies are limited to top 20."""
        # Add many dependencies
        result_with_stack.technology_stack.dependencies = [
            Dependency(
                name=f"pkg-{i}", ecosystem="pypi", source_file="requirements.txt"
            )
            for i in range(30)
        ]

        context = build_tech_stack_prompt(result_with_stack)

        assert len(context.data["dependencies"]) == 20
        assert context.data["total_dependencies"] == 30


class TestBuildArchitecturePrompt:
    """Tests for build_architecture_prompt function."""

    def test_build_architecture_prompt_no_architecture(self) -> None:
        """Test prompt when no architecture is available."""
        result = AnalysisResult(
            repository_path=Path("/test/repo"),
            repository_name="test-repo",
        )

        context = build_architecture_prompt(result)

        assert context.section == "architecture"
        assert context.data["has_architecture"] is False

    def test_build_architecture_prompt_with_graph(self) -> None:
        """Test prompt with architecture graph."""
        from dataclasses import dataclass, field as dc_field

        @dataclass
        class MockNode:
            type: str
            name: str

        @dataclass
        class MockGraph:
            node_count: int
            connection_count: int
            nodes: dict[str, MockNode] = dc_field(default_factory=dict)

        @dataclass
        class MockArchitecture:
            graph: MockGraph | None = None
            source: None = None
            cloud_providers: list[str] = dc_field(default_factory=list)

        result = AnalysisResult(
            repository_path=Path("/test/repo"),
            repository_name="test-repo",
        )
        result.architecture = MockArchitecture(
            graph=MockGraph(
                node_count=10,
                connection_count=5,
                nodes={
                    "1": MockNode(type="aws_instance", name="web-server"),
                    "2": MockNode(type="aws_instance", name="api-server"),
                    "3": MockNode(type="aws_rds", name="database"),
                },
            ),
            cloud_providers=["AWS"],
        )

        context = build_architecture_prompt(result)

        assert context.data["has_architecture"] is True
        assert context.data["node_count"] == 10
        assert context.data["connections"] == 5
        assert "aws_instance" in context.data["resources_by_type"]
        assert len(context.data["resources_by_type"]["aws_instance"]) == 2


class TestBuildDependenciesPrompt:
    """Tests for build_dependencies_prompt function."""

    def test_build_dependencies_prompt_no_sbom(self) -> None:
        """Test prompt when no SBOM is available."""
        result = AnalysisResult(
            repository_path=Path("/test/repo"),
            repository_name="test-repo",
        )

        context = build_dependencies_prompt(result)

        assert context.section == "dependencies"
        assert context.data["has_sbom"] is False
        assert context.data["total_packages"] == 0

    def test_build_dependencies_prompt_with_sbom(self) -> None:
        """Test prompt with SBOM data."""
        from dataclasses import dataclass, field as dc_field

        @dataclass
        class MockPackage:
            name: str
            version: str
            ecosystem: str
            is_direct: bool = True  # All test packages are direct

        @dataclass
        class MockSBOM:
            packages: list[MockPackage] = dc_field(default_factory=list)

            @property
            def package_count(self) -> int:
                return len(self.packages)

            @property
            def direct_package_count(self) -> int:
                return len(self.get_direct_packages())

            def get_unique_ecosystems(self) -> list[str]:
                return sorted(set(p.ecosystem for p in self.packages))

            def get_packages_by_ecosystem(self, ecosystem: str) -> list[MockPackage]:
                return [p for p in self.packages if p.ecosystem == ecosystem]

            def get_direct_packages(self) -> list[MockPackage]:
                return [p for p in self.packages if p.is_direct]

        result = AnalysisResult(
            repository_path=Path("/test/repo"),
            repository_name="test-repo",
        )
        result.sbom = MockSBOM(
            packages=[
                MockPackage(name="requests", version="2.31.0", ecosystem="pypi"),
                MockPackage(name="boto3", version="1.28.0", ecosystem="pypi"),
                MockPackage(name="react", version="18.2.0", ecosystem="npm"),
            ],
        )

        context = build_dependencies_prompt(result)

        assert context.data["has_sbom"] is True
        assert context.data["total_packages"] == 3  # 3 packages in mock
        assert context.data["direct_packages"] == 3  # All are direct
        assert "pypi" in context.data["ecosystems"]
        assert len(context.data["direct_dependencies"]) > 0


class TestFormatPrompt:
    """Tests for format_prompt function."""

    def test_format_overview_prompt(self) -> None:
        """Test formatting overview prompt."""
        context = PromptContext(
            section="overview",
            data={
                "repository_name": "test-repo",
                "facts": ["Repository: test-repo", "Languages: Python"],
            },
            max_words=250,
        )

        prompt = format_prompt(context)

        assert "test-repo" in prompt
        assert "250 words" in prompt
        assert "Key Facts:" in prompt
        assert "- Repository: test-repo" in prompt

    def test_format_tech_stack_prompt(self) -> None:
        """Test formatting tech stack prompt."""
        context = PromptContext(
            section="tech_stack",
            data={
                "languages": [{"name": "Python", "version": "3.11"}],
                "frameworks": [{"name": "FastAPI", "version": "0.100"}],
                "dependencies": [{"name": "boto3"}],
                "total_dependencies": 50,
            },
            max_words=150,
        )

        prompt = format_prompt(context)

        assert "Python" in prompt
        assert "FastAPI" in prompt
        assert "boto3" in prompt
        assert "50" in prompt

    def test_format_architecture_prompt_no_arch(self) -> None:
        """Test formatting architecture prompt with no architecture."""
        context = PromptContext(
            section="architecture",
            data={"has_architecture": False},
        )

        prompt = format_prompt(context)

        assert "No infrastructure-as-code" in prompt

    def test_format_architecture_prompt_with_arch(self) -> None:
        """Test formatting architecture prompt with architecture."""
        context = PromptContext(
            section="architecture",
            data={
                "has_architecture": True,
                "node_count": 10,
                "connections": 5,
                "resources_by_type": {"aws_instance": ["web", "api"]},
                "providers": ["AWS"],
                "terraform_variables": {"region": "us-west-2"},
            },
            max_words=200,
        )

        prompt = format_prompt(context)

        assert "AWS" in prompt
        assert "10" in prompt
        assert "aws_instance" in prompt

    def test_format_dependencies_prompt_no_sbom(self) -> None:
        """Test formatting dependencies prompt with no SBOM."""
        context = PromptContext(
            section="dependencies",
            data={"has_sbom": False},
        )

        prompt = format_prompt(context)

        assert "No SBOM data" in prompt

    def test_format_dependencies_prompt_with_sbom(self) -> None:
        """Test formatting dependencies prompt with SBOM."""
        context = PromptContext(
            section="dependencies",
            data={
                "has_sbom": True,
                "total_packages": 100,
                "direct_packages": 10,
                "ecosystems": ["pypi", "npm"],
                "direct_dependencies": [
                    {"name": "requests", "ecosystem": "pypi"},
                    {"name": "react", "ecosystem": "npm"},
                ],
            },
            max_words=150,
        )

        prompt = format_prompt(context)

        assert "100" in prompt  # Total packages
        assert "10" in prompt  # Direct packages
        assert "pypi" in prompt
        assert "requests" in prompt

    def test_format_unknown_section_prompt(self) -> None:
        """Test formatting unknown section uses generic format."""
        context = PromptContext(
            section="custom_section",
            data={},
            max_words=100,
        )

        prompt = format_prompt(context)

        assert "custom_section" in prompt
        assert "100 words" in prompt


class TestSubSectionPrompt:
    """Tests for SubSectionPrompt dataclass (T065aa)."""

    def test_subsection_prompt_creation(self) -> None:
        """Test SubSectionPrompt can be created with required fields."""
        from chronicle.llm.prompts import SubSectionPrompt

        prompt = SubSectionPrompt(
            name="system_type",
            question="What kind of system is this?",
        )

        assert prompt.name == "system_type"
        assert prompt.question == "What kind of system is this?"
        assert prompt.max_words == 50  # Default
        assert prompt.facts_keys is None  # Default

    def test_subsection_prompt_with_facts_keys(self) -> None:
        """Test SubSectionPrompt with custom facts_keys."""
        from chronicle.llm.prompts import SubSectionPrompt

        prompt = SubSectionPrompt(
            name="key_components",
            question="What are the main components?",
            max_words=80,
            facts_keys=["resources", "modules", "entry_points"],
        )

        assert prompt.max_words == 80
        assert prompt.facts_keys == ["resources", "modules", "entry_points"]


class TestSectionDefinition:
    """Tests for SectionDefinition dataclass (T065ab)."""

    def test_section_definition_creation(self) -> None:
        """Test SectionDefinition can be created."""
        from chronicle.llm.prompts import SectionDefinition, SubSectionPrompt

        section = SectionDefinition(
            section_name="overview",
            sub_sections=[
                SubSectionPrompt(name="intro", question="What is this?"),
                SubSectionPrompt(name="components", question="What components?"),
            ],
        )

        assert section.section_name == "overview"
        assert len(section.sub_sections) == 2
        assert section.concatenation_strategy == "paragraph"  # Default

    def test_section_definition_custom_strategy(self) -> None:
        """Test SectionDefinition with custom concatenation strategy."""
        from chronicle.llm.prompts import SectionDefinition, SubSectionPrompt

        section = SectionDefinition(
            section_name="dependencies",
            sub_sections=[
                SubSectionPrompt(name="ecosystems", question="What ecosystems?"),
            ],
            concatenation_strategy="bullet",
        )

        assert section.concatenation_strategy == "bullet"


class TestSectionDefinitions:
    """Tests for SECTION_DEFINITIONS constant (T065ac)."""

    def test_all_sections_have_definitions(self) -> None:
        """Test that all required sections have definitions."""
        from chronicle.llm.prompts import SECTION_DEFINITIONS

        required_sections = [
            "overview",
            "tech_stack",
            "architecture",
            "dependencies",
        ]

        for section in required_sections:
            assert section in SECTION_DEFINITIONS
            assert SECTION_DEFINITIONS[section].section_name == section

    def test_overview_section_has_subsections(self) -> None:
        """Test overview section has appropriate sub-sections."""
        from chronicle.llm.prompts import SECTION_DEFINITIONS

        overview = SECTION_DEFINITIONS["overview"]
        sub_names = [s.name for s in overview.sub_sections]

        assert "system_type" in sub_names
        assert "key_components" in sub_names
        assert "architecture_pattern" in sub_names

    def test_dependencies_section_has_subsections(self) -> None:
        """Test dependencies section has appropriate sub-sections."""
        from chronicle.llm.prompts import SECTION_DEFINITIONS

        deps = SECTION_DEFINITIONS["dependencies"]
        sub_names = [s.name for s in deps.sub_sections]

        assert "ecosystem_breakdown" in sub_names
        assert "key_packages" in sub_names

    def test_get_section_definition_returns_definition(self) -> None:
        """Test get_section_definition returns correct definition."""
        from chronicle.llm.prompts import get_section_definition

        section = get_section_definition("overview")
        assert section is not None
        assert section.section_name == "overview"

    def test_get_section_definition_returns_none_for_unknown(self) -> None:
        """Test get_section_definition returns None for unknown section."""
        from chronicle.llm.prompts import get_section_definition

        section = get_section_definition("unknown_section")
        assert section is None


class TestSubSectionResponse:
    """Tests for SubSectionResponse dataclass (T065ad)."""

    def test_subsection_response_creation(self) -> None:
        """Test SubSectionResponse can be created."""
        from chronicle.llm.client import SubSectionResponse

        response = SubSectionResponse(sub_section_name="system_type")

        assert response.sub_section_name == "system_type"
        assert response.facts_provided == {}
        assert response.prompt_sent == ""
        assert response.response_text == ""
        assert response.tokens_used == {}
        assert response.error is None

    def test_subsection_response_with_data(self) -> None:
        """Test SubSectionResponse with full data."""
        from chronicle.llm.client import SubSectionResponse

        response = SubSectionResponse(
            sub_section_name="key_components",
            facts_provided={"resources": ["lambda", "dynamodb"]},
            prompt_sent="What are the main components?",
            response_text="The system uses Lambda and DynamoDB.",
            tokens_used={
                "prompt_tokens": 50,
                "completion_tokens": 20,
                "total_tokens": 70,
            },
        )

        assert response.facts_provided == {"resources": ["lambda", "dynamodb"]}
        assert "Lambda" in response.response_text
        assert response.tokens_used["total_tokens"] == 70

    def test_subsection_response_with_error(self) -> None:
        """Test SubSectionResponse with error."""
        from chronicle.llm.client import SubSectionResponse

        response = SubSectionResponse(
            sub_section_name="failed_section",
            error="LLM call timed out",
        )

        assert response.error == "LLM call timed out"
        assert response.response_text == ""


class TestConcatenateSubsectionResponses:
    """Tests for concatenate_subsection_responses function (T065ae)."""

    def test_concatenate_paragraph_strategy(self) -> None:
        """Test paragraph concatenation strategy."""
        from chronicle.llm.client import (
            SubSectionResponse,
            concatenate_subsection_responses,
        )

        responses = [
            SubSectionResponse(
                sub_section_name="intro",
                response_text="This is the intro.",
            ),
            SubSectionResponse(
                sub_section_name="details",
                response_text="Here are the details.",
            ),
        ]

        result = concatenate_subsection_responses(responses, strategy="paragraph")

        assert "This is the intro." in result
        assert "Here are the details." in result
        assert "\n\n" in result  # Paragraph separator

    def test_concatenate_bullet_strategy(self) -> None:
        """Test bullet concatenation strategy."""
        from chronicle.llm.client import (
            SubSectionResponse,
            concatenate_subsection_responses,
        )

        responses = [
            SubSectionResponse(
                sub_section_name="item1",
                response_text="First item",
            ),
            SubSectionResponse(
                sub_section_name="item2",
                response_text="Second item",
            ),
        ]

        result = concatenate_subsection_responses(responses, strategy="bullet")

        assert "- First item" in result
        assert "- Second item" in result

    def test_concatenate_newline_strategy(self) -> None:
        """Test newline concatenation strategy."""
        from chronicle.llm.client import (
            SubSectionResponse,
            concatenate_subsection_responses,
        )

        responses = [
            SubSectionResponse(
                sub_section_name="line1",
                response_text="Line one",
            ),
            SubSectionResponse(
                sub_section_name="line2",
                response_text="Line two",
            ),
        ]

        result = concatenate_subsection_responses(responses, strategy="newline")

        assert "Line one\nLine two" in result

    def test_concatenate_filters_failed_responses(self) -> None:
        """Test that failed responses are filtered out."""
        from chronicle.llm.client import (
            SubSectionResponse,
            concatenate_subsection_responses,
        )

        responses = [
            SubSectionResponse(
                sub_section_name="success",
                response_text="This succeeded.",
            ),
            SubSectionResponse(
                sub_section_name="failed",
                response_text="",
                error="API error",
            ),
            SubSectionResponse(
                sub_section_name="also_success",
                response_text="This also succeeded.",
            ),
        ]

        result = concatenate_subsection_responses(responses, strategy="paragraph")

        assert "This succeeded." in result
        assert "This also succeeded." in result
        assert "API error" not in result

    def test_concatenate_returns_empty_for_all_failures(self) -> None:
        """Test empty result when all responses failed."""
        from chronicle.llm.client import (
            SubSectionResponse,
            concatenate_subsection_responses,
        )

        responses = [
            SubSectionResponse(sub_section_name="failed1", error="Error 1"),
            SubSectionResponse(sub_section_name="failed2", error="Error 2"),
        ]

        result = concatenate_subsection_responses(responses)

        assert result == ""


class TestFormatFacts:
    """Tests for _format_facts helper function (T065af)."""

    def test_format_simple_facts(self) -> None:
        """Test formatting simple string facts."""
        from chronicle.llm.client import _format_facts

        facts = {
            "repository_name": "test-repo",
            "node_count": 10,
        }

        result = _format_facts(facts)

        assert "- repository_name: test-repo" in result
        assert "- node_count: 10" in result

    def test_format_list_facts(self) -> None:
        """Test formatting list facts."""
        from chronicle.llm.client import _format_facts

        facts = {
            "ecosystems": ["npm", "pypi", "go"],
        }

        result = _format_facts(facts)

        assert "npm" in result
        assert "pypi" in result
        assert "go" in result

    def test_format_dict_list_facts(self) -> None:
        """Test formatting list of dict facts."""
        from chronicle.llm.client import _format_facts

        facts = {
            "languages": [
                {"name": "Python", "version": "3.11"},
                {"name": "Go", "version": "1.21"},
            ],
        }

        result = _format_facts(facts)

        assert "Python" in result
        assert "Go" in result

    def test_format_empty_facts(self) -> None:
        """Test formatting empty facts dict."""
        from chronicle.llm.client import _format_facts

        result = _format_facts({})

        assert "No specific facts available" in result


# =============================================================================
# Phase 4d: Code Explanation Tests - REMOVED
# =============================================================================
# Function/class explanation functionality was removed in favor of holistic
# overview from Repomix. See Phase 4g for holistic overview tests.
