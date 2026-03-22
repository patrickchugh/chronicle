"""Integration tests for pipeline LLM summarization (T060d).

Tests the integration of LLM summary generation into the analysis pipeline,
including placeholder handling and error scenarios.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chronicle.config import (
    CIConfig,
    LLMConfig,
    chronicleConfig,
    OutputConfig,
    ToolConfig,
)
from chronicle.llm.prompts import PLACEHOLDER_SUMMARIES
from chronicle.models import Repository
from chronicle.models.analysis import (
    AnalysisResult,
    AnalysisStatus,
    Dependency,
    Framework,
    LanguageInfo,
    TechnologyStack,
)
from chronicle.pipeline import AnalysisPipeline, PipelineOptions


class TestPipelineLLMSummarization:
    """Tests for LLM summarization in the pipeline."""

    @pytest.fixture
    def mock_config(self) -> chronicleConfig:
        """Create a real chronicleConfig with LLM enabled."""
        config = chronicleConfig(
            output=OutputConfig(),
            tools=ToolConfig(),
            llm=LLMConfig(
                provider="claude",
                model="claude-3-sonnet-20240229",
                api_key="test-api-key",
                enabled=True,
            ),
            ci=CIConfig(),
        )
        return config

    @pytest.fixture
    def mock_repository(self, tmp_path: Path) -> Repository:
        """Create a mock repository for testing."""
        # Create a minimal repository structure
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"')
        (tmp_path / "main.py").write_text("def main(): pass")

        return Repository(
            path=tmp_path,
            name="test-repo",
        )

    @pytest.fixture
    def mock_llm_response(self) -> MagicMock:
        """Create a mock LiteLLM response."""
        mock = MagicMock()
        mock.choices = [
            MagicMock(
                message=MagicMock(content="This is a generated summary."),
                finish_reason="stop",
            )
        ]
        mock.model = "claude-3-sonnet-20240229"
        mock.usage = MagicMock(prompt_tokens=50, completion_tokens=20, total_tokens=70)
        return mock

    def test_pipeline_skip_llm_uses_placeholders(
        self, mock_config: chronicleConfig, mock_repository: Repository
    ) -> None:
        """Test that --skip-llm flag applies placeholder summaries."""
        pipeline = AnalysisPipeline(config=mock_config)

        # Skip all other analyses to speed up test
        options = PipelineOptions(
            skip_sbom=True,
            skip_architecture=True,
            skip_ast=True,
            skip_dependencies=True,
            skip_llm=True,
        )

        result = pipeline.run(mock_repository, options)

        # All summaries should be placeholders
        assert "overview" in result.llm_summaries
        assert "tech_stack" in result.llm_summaries
        assert "architecture" in result.llm_summaries
        assert "dependencies" in result.llm_summaries

        # Verify placeholders are used
        for section, summary in result.llm_summaries.items():
            assert summary == PLACEHOLDER_SUMMARIES[section]

    def test_pipeline_llm_disabled_uses_placeholders(
        self, mock_repository: Repository
    ) -> None:
        """Test that disabled LLM config applies placeholder summaries."""
        # Create config with LLM disabled
        config = chronicleConfig(
            output=OutputConfig(),
            tools=ToolConfig(),
            llm=LLMConfig(
                provider="claude",
                model="claude-3-sonnet-20240229",
                api_key="test-api-key",
                enabled=False,  # LLM disabled
            ),
            ci=CIConfig(),
        )

        pipeline = AnalysisPipeline(config=config)

        options = PipelineOptions(
            skip_sbom=True,
            skip_architecture=True,
            skip_ast=True,
            skip_dependencies=True,
            skip_llm=False,  # LLM not skipped, but disabled in config
        )

        result = pipeline.run(mock_repository, options)

        # All summaries should be placeholders
        for section, summary in result.llm_summaries.items():
            assert summary == PLACEHOLDER_SUMMARIES[section]

    def test_pipeline_generates_llm_summaries(
        self,
        mock_config: chronicleConfig,
        mock_repository: Repository,
        mock_llm_response: MagicMock,
    ) -> None:
        """Test pipeline generates LLM summaries when enabled.

        With structured prompting, each section has multiple sub-sections.
        The mock response is used for each sub-section call, so the final
        summary is a concatenation of multiple responses joined by paragraph
        separator (double newline).

        Expected sub-section counts from SECTION_DEFINITIONS:
        - overview: 3 sub-sections
        - tech_stack: 3 sub-sections
        - architecture: 3 sub-sections
        - dependencies: 2 sub-sections
        """
        pipeline = AnalysisPipeline(config=mock_config)

        options = PipelineOptions(
            skip_sbom=True,
            skip_architecture=True,
            skip_ast=True,
            skip_dependencies=True,
            skip_llm=False,
        )

        with patch("litellm.completion", return_value=mock_llm_response):
            result = pipeline.run(mock_repository, options)

        # Expected concatenated outputs based on sub-section counts
        mock_text = "This is a generated summary."
        three_subsections = f"{mock_text}\n\n{mock_text}\n\n{mock_text}"
        two_subsections = f"{mock_text}\n\n{mock_text}"

        expected_summaries = {
            "overview": three_subsections,
            "tech_stack": three_subsections,
            "architecture": three_subsections,
            "dependencies": two_subsections,
        }

        # Verify exact match for each section
        for section, expected in expected_summaries.items():
            assert result.llm_summaries[section] == expected, (
                f"Section '{section}' mismatch.\n"
                f"Expected: {repr(expected)}\n"
                f"Got: {repr(result.llm_summaries[section])}"
            )

    def test_pipeline_llm_failure_marks_failed_status(
        self,
        mock_config: chronicleConfig,
        mock_repository: Repository,
    ) -> None:
        """Test pipeline marks failed status when LLM check_available fails."""
        pipeline = AnalysisPipeline(config=mock_config)

        options = PipelineOptions(
            skip_sbom=True,
            skip_architecture=True,
            skip_ast=True,
            skip_dependencies=True,
            skip_llm=False,
        )

        # Mock client creation succeeds but check_available fails
        with patch("litellm.completion") as mock_completion:
            # check_available makes a completion call internally
            mock_completion.side_effect = Exception("API error")
            result = pipeline.run(mock_repository, options)

        # Pipeline should be marked as failed
        assert result.status == AnalysisStatus.FAILED
        # Should have an LLM error
        llm_errors = [e for e in result.errors if e.component == "llm"]
        assert len(llm_errors) == 1
        assert "not available" in llm_errors[0].message

    def test_pipeline_llm_partial_subsection_failure_still_produces_content(
        self,
        mock_config: chronicleConfig,
        mock_repository: Repository,
    ) -> None:
        """Test that partial sub-section failures still produce content.

        With structured prompting, each section has multiple sub-sections.
        If some sub-sections fail but others succeed, we still get partial content.
        """
        pipeline = AnalysisPipeline(config=mock_config)

        options = PipelineOptions(
            skip_sbom=True,
            skip_architecture=True,
            skip_ast=True,
            skip_dependencies=True,
            skip_llm=False,
        )

        call_count = 0

        def mock_completion_with_failure(**kwargs: dict) -> MagicMock:
            nonlocal call_count
            call_count += 1
            # First call is check_available (succeeds)
            # Second call (first sub-section of overview) fails
            # Subsequent calls succeed
            if call_count == 2:
                raise Exception("API error for first overview sub-section")

            mock = MagicMock()
            mock.choices = [
                MagicMock(
                    message=MagicMock(content="Generated content"),
                    finish_reason="stop",
                )
            ]
            mock.model = "claude-3-sonnet-20240229"
            mock.usage = MagicMock(
                prompt_tokens=50, completion_tokens=20, total_tokens=70
            )
            return mock

        with patch("litellm.completion", side_effect=mock_completion_with_failure):
            result = pipeline.run(mock_repository, options)

        # Overview should still have content from successful sub-sections
        # (not a placeholder, since 2 out of 3 sub-sections succeeded)
        assert "Generated content" in result.llm_summaries["overview"]
        # Other sections should be fully generated
        assert "Generated content" in result.llm_summaries["tech_stack"]

    def test_pipeline_llm_all_subsections_fail_uses_placeholder(
        self,
        mock_config: chronicleConfig,
        mock_repository: Repository,
    ) -> None:
        """Test that when ALL sub-sections of a section fail, placeholder is used."""
        pipeline = AnalysisPipeline(config=mock_config)

        options = PipelineOptions(
            skip_sbom=True,
            skip_architecture=True,
            skip_ast=True,
            skip_dependencies=True,
            skip_llm=False,
        )

        call_count = 0

        def mock_completion_all_overview_fails(**kwargs: dict) -> MagicMock:
            nonlocal call_count
            call_count += 1
            # First call is check_available (succeeds)
            # Calls 2-4 are overview sub-sections (all fail)
            # Subsequent calls succeed
            if 2 <= call_count <= 4:
                raise Exception("API error for overview sub-section")

            mock = MagicMock()
            mock.choices = [
                MagicMock(
                    message=MagicMock(content="Generated content"),
                    finish_reason="stop",
                )
            ]
            mock.model = "claude-3-sonnet-20240229"
            mock.usage = MagicMock(
                prompt_tokens=50, completion_tokens=20, total_tokens=70
            )
            return mock

        with patch(
            "litellm.completion", side_effect=mock_completion_all_overview_fails
        ):
            result = pipeline.run(mock_repository, options)

        # Overview should be placeholder since ALL sub-sections failed
        assert result.llm_summaries["overview"].startswith("*")
        # Other sections should be generated
        assert "Generated content" in result.llm_summaries["tech_stack"]

    def test_pipeline_verbose_llm_logs_facts_and_responses(
        self,
        mock_config: chronicleConfig,
        mock_repository: Repository,
        mock_llm_response: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that verbose_llm=True logs facts and responses (T065ac).

        When verbose_llm is enabled, the pipeline should log:
        - The facts provided to each sub-section
        - The prompt sent to the LLM
        - The response received from the LLM
        """
        import logging

        pipeline = AnalysisPipeline(config=mock_config)

        options = PipelineOptions(
            skip_sbom=True,
            skip_architecture=True,
            skip_ast=True,
            skip_dependencies=True,
            skip_llm=False,
            verbose_llm=True,  # Enable verbose LLM logging
        )

        with caplog.at_level(logging.DEBUG, logger="chronicle.llm.client"):
            with patch("litellm.completion", return_value=mock_llm_response):
                pipeline.run(mock_repository, options)

        # Check that debug logs contain expected verbose output
        log_text = caplog.text

        # Should log sub-section prompts (DEBUG level includes "Facts:" in prompt)
        assert "prompt" in log_text.lower() or "facts" in log_text.lower()

        # Should log responses (either in DEBUG output or INFO summary)
        assert "response" in log_text.lower() or "tokens" in log_text.lower()

    def test_pipeline_llm_output_is_concatenation_of_subsections(
        self,
        mock_config: chronicleConfig,
        mock_repository: Repository,
    ) -> None:
        """Test that final output is concatenation of sub-section answers (T065ad).

        Each section's output should be the concatenated responses from its
        sub-sections, joined according to the section's concatenation strategy.
        """
        pipeline = AnalysisPipeline(config=mock_config)

        options = PipelineOptions(
            skip_sbom=True,
            skip_architecture=True,
            skip_ast=True,
            skip_dependencies=True,
            skip_llm=False,
        )

        # Create unique responses for each sub-section to verify concatenation
        call_count = 0
        subsection_responses = [
            "System type response.",
            "Key components response.",
            "Architecture pattern response.",
            "Languages response.",
            "Frameworks response.",
            "Package summary response.",
            "Infrastructure response.",
            "Data flow response.",
            "Configuration response.",
            "Ecosystem breakdown response.",
            "Key packages response.",
            "Module organization response.",
            "Key functions response.",
        ]

        def mock_completion_unique_responses(**kwargs: dict) -> MagicMock:
            nonlocal call_count
            call_count += 1

            # First call is check_available
            if call_count == 1:
                content = "ok"
            else:
                # Subsequent calls get unique responses
                idx = (call_count - 2) % len(subsection_responses)
                content = subsection_responses[idx]

            mock = MagicMock()
            mock.choices = [
                MagicMock(
                    message=MagicMock(content=content),
                    finish_reason="stop",
                )
            ]
            mock.model = "claude-3-sonnet-20240229"
            mock.usage = MagicMock(
                prompt_tokens=50, completion_tokens=20, total_tokens=70
            )
            return mock

        with patch("litellm.completion", side_effect=mock_completion_unique_responses):
            result = pipeline.run(mock_repository, options)

        # Verify overview has 3 concatenated responses (paragraph strategy = \n\n)
        overview = result.llm_summaries["overview"]
        assert "System type response." in overview
        assert "Key components response." in overview
        assert "Architecture pattern response." in overview
        # Paragraph strategy joins with double newline
        assert "\n\n" in overview

        # Verify dependencies has 2 concatenated responses
        deps = result.llm_summaries["dependencies"]
        assert "\n\n" in deps  # Paragraph strategy


class TestPipelineOptionsSkipLLM:
    """Tests for PipelineOptions.skip_llm behavior."""

    def test_pipeline_options_default_includes_llm(self) -> None:
        """Test PipelineOptions defaults to including LLM."""
        options = PipelineOptions()
        assert options.skip_llm is False

    def test_pipeline_options_skip_llm_can_be_set(self) -> None:
        """Test PipelineOptions skip_llm can be explicitly set."""
        options = PipelineOptions(skip_llm=True)
        assert options.skip_llm is True


class TestPipelineLLMWithFullAnalysis:
    """Tests for LLM summarization with full analysis context."""

    @pytest.fixture
    def full_result(self) -> AnalysisResult:
        """Create a full AnalysisResult with all analysis data."""
        result = AnalysisResult(
            repository_path=Path("/test/repo"),
            repository_name="full-test-repo",
            timestamp=datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC),
            status=AnalysisStatus.COMPLETED,
        )

        result.technology_stack = TechnologyStack(
            languages=[
                LanguageInfo(name="Python", version="3.11", file_count=50),
                LanguageInfo(name="TypeScript", version="5.0", file_count=30),
            ],
            frameworks=[
                Framework(name="FastAPI", version="0.100"),
                Framework(name="React", version="18.2"),
            ],
            dependencies=[
                Dependency(
                    name="pytest", ecosystem="pypi", source_file="pyproject.toml"
                ),
                Dependency(
                    name="boto3", ecosystem="pypi", source_file="pyproject.toml"
                ),
                Dependency(name="react", ecosystem="npm", source_file="package.json"),
            ],
        )

        return result

    def test_apply_placeholder_summaries_covers_all_sections(
        self, full_result: AnalysisResult
    ) -> None:
        """Test _apply_placeholder_summaries covers all expected sections."""
        # Simulate what the pipeline does
        sections = ["overview", "tech_stack", "architecture", "dependencies"]
        for section in sections:
            full_result.llm_summaries[section] = PLACEHOLDER_SUMMARIES[section]

        # All sections should have placeholders
        assert len(full_result.llm_summaries) == 4
        for section in sections:
            assert section in full_result.llm_summaries
            assert "LLM" in full_result.llm_summaries[section]


class TestPipelineLLMErrorMessages:
    """Tests for LLM-related error messages in pipeline."""

    def test_get_llm_help_message_ollama(self) -> None:
        """Test help message for Ollama."""
        pipeline = AnalysisPipeline()
        msg = pipeline._get_llm_help_message("ollama")
        assert "ollama serve" in msg

    def test_get_llm_help_message_claude(self) -> None:
        """Test help message for Claude."""
        pipeline = AnalysisPipeline()
        msg = pipeline._get_llm_help_message("claude")
        assert "ANTHROPIC_API_KEY" in msg

    def test_get_llm_help_message_gemini(self) -> None:
        """Test help message for Gemini."""
        pipeline = AnalysisPipeline()
        msg = pipeline._get_llm_help_message("gemini")
        assert "GOOGLE_API_KEY" in msg

    def test_get_llm_help_message_bedrock(self) -> None:
        """Test help message for Bedrock."""
        pipeline = AnalysisPipeline()
        msg = pipeline._get_llm_help_message("bedrock")
        assert "AWS" in msg
        assert "bedrock:InvokeModel" in msg

    def test_get_llm_help_message_unknown(self) -> None:
        """Test help message for unknown provider."""
        pipeline = AnalysisPipeline()
        msg = pipeline._get_llm_help_message("unknown")
        assert "chronicle init" in msg


class TestLLMSummariesInResult:
    """Tests for llm_summaries field in AnalysisResult."""

    def test_llm_summaries_default_empty(self) -> None:
        """Test llm_summaries defaults to empty dict."""
        result = AnalysisResult(
            repository_path=Path("/test"),
            repository_name="test",
        )
        assert result.llm_summaries == {}

    def test_llm_summaries_can_be_populated(self) -> None:
        """Test llm_summaries can be populated."""
        result = AnalysisResult(
            repository_path=Path("/test"),
            repository_name="test",
        )
        result.llm_summaries["overview"] = "Test overview summary"
        result.llm_summaries["tech_stack"] = "Test tech stack summary"

        assert result.llm_summaries["overview"] == "Test overview summary"
        assert len(result.llm_summaries) == 2

    def test_llm_summaries_placeholder_detection(self) -> None:
        """Test detecting placeholder vs generated summaries."""
        result = AnalysisResult(
            repository_path=Path("/test"),
            repository_name="test",
        )
        result.llm_summaries["overview"] = PLACEHOLDER_SUMMARIES["overview"]
        result.llm_summaries["tech_stack"] = "This is a real summary."

        # Placeholders start with *
        assert result.llm_summaries["overview"].startswith("*")
        assert not result.llm_summaries["tech_stack"].startswith("*")

        # Count generated summaries
        generated_count = sum(
            1 for s in result.llm_summaries.values() if not s.startswith("*")
        )
        assert generated_count == 1
