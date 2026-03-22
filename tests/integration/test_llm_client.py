"""Integration tests for LLM client and backend connectivity (T060c).

Tests the LLMClient class with mocked LiteLLM responses to verify
correct integration behavior without making actual API calls.
"""

from unittest.mock import MagicMock, patch

import pytest

from chronicle.llm.client import LLMClient, LLMError, LLMResponse, create_client
from chronicle.models.llm_config import LLMConfig


class TestLLMClientCreation:
    """Tests for LLMClient creation and configuration."""

    def test_create_client_claude(self) -> None:
        """Test creating a Claude client."""
        config = LLMConfig(
            provider="claude",
            model="claude-3-sonnet-20240229",
            api_key="test-api-key",
        )

        client = create_client(config)

        assert client.config.provider == "claude"
        assert client.config.model == "claude-3-sonnet-20240229"

    def test_create_client_bedrock(self) -> None:
        """Test creating a Bedrock client."""
        config = LLMConfig(
            provider="bedrock",
            model="anthropic.claude-3-sonnet-20240229-v1:0",
        )

        client = create_client(config)

        assert client.config.provider == "bedrock"

    def test_create_client_ollama(self) -> None:
        """Test creating an Ollama client."""
        config = LLMConfig(
            provider="ollama",
            model="llama2",
            api_base="http://localhost:11434",
        )

        client = create_client(config)

        assert client.config.provider == "ollama"
        assert client.config.api_base == "http://localhost:11434"

    def test_create_client_disabled_raises_error(self) -> None:
        """Test creating client with disabled config raises error."""
        config = LLMConfig(
            provider="claude",
            model="claude-3-sonnet-20240229",
            api_key="test-api-key",
            enabled=False,
        )

        with pytest.raises(ValueError, match="LLM is disabled"):
            create_client(config)


class TestLLMClientCompletion:
    """Tests for LLMClient.complete method."""

    @pytest.fixture
    def mock_litellm_response(self) -> MagicMock:
        """Create a mock LiteLLM response."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(content="Test response content"),
                finish_reason="stop",
            )
        ]
        mock_response.model = "claude-3-sonnet-20240229"
        mock_response.usage = MagicMock(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        )
        return mock_response

    def test_complete_with_user_prompt_only(
        self, mock_litellm_response: MagicMock
    ) -> None:
        """Test completion with only user prompt."""
        config = LLMConfig(
            provider="claude",
            model="claude-3-sonnet-20240229",
            api_key="test-api-key",
        )
        client = LLMClient(config)

        with patch(
            "litellm.completion", return_value=mock_litellm_response
        ) as mock_call:
            response = client.complete("Hello, world!")

            mock_call.assert_called_once()
            call_kwargs = mock_call.call_args[1]
            assert len(call_kwargs["messages"]) == 1
            assert call_kwargs["messages"][0]["role"] == "user"
            assert call_kwargs["temperature"] == 0

        assert response.content == "Test response content"
        assert response.model == "claude-3-sonnet-20240229"
        assert response.finish_reason == "stop"

    def test_complete_with_system_prompt(
        self, mock_litellm_response: MagicMock
    ) -> None:
        """Test completion with system prompt."""
        config = LLMConfig(
            provider="claude",
            model="claude-3-sonnet-20240229",
            api_key="test-api-key",
        )
        client = LLMClient(config)

        with patch(
            "litellm.completion", return_value=mock_litellm_response
        ) as mock_call:
            response = client.complete(
                "Hello!",
                system_prompt="You are a helpful assistant.",
            )

            call_kwargs = mock_call.call_args[1]
            assert len(call_kwargs["messages"]) == 2
            assert call_kwargs["messages"][0]["role"] == "system"
            assert call_kwargs["messages"][1]["role"] == "user"

        assert response.content == "Test response content"

    def test_complete_respects_max_tokens_override(
        self, mock_litellm_response: MagicMock
    ) -> None:
        """Test completion respects max_tokens override."""
        config = LLMConfig(
            provider="claude",
            model="claude-3-sonnet-20240229",
            api_key="test-api-key",
            max_tokens=4096,
        )
        client = LLMClient(config)

        with patch(
            "litellm.completion", return_value=mock_litellm_response
        ) as mock_call:
            client.complete("Hello!", max_tokens=100)

            call_kwargs = mock_call.call_args[1]
            assert call_kwargs["max_tokens"] == 100

    def test_complete_uses_config_max_tokens_by_default(
        self, mock_litellm_response: MagicMock
    ) -> None:
        """Test completion uses config max_tokens when not overridden."""
        config = LLMConfig(
            provider="claude",
            model="claude-3-sonnet-20240229",
            api_key="test-api-key",
            max_tokens=2048,
        )
        client = LLMClient(config)

        with patch(
            "litellm.completion", return_value=mock_litellm_response
        ) as mock_call:
            client.complete("Hello!")

            call_kwargs = mock_call.call_args[1]
            assert call_kwargs["max_tokens"] == 2048

    def test_complete_returns_usage_stats(
        self, mock_litellm_response: MagicMock
    ) -> None:
        """Test completion returns token usage statistics."""
        config = LLMConfig(
            provider="claude",
            model="claude-3-sonnet-20240229",
            api_key="test-api-key",
        )
        client = LLMClient(config)

        with patch("litellm.completion", return_value=mock_litellm_response):
            response = client.complete("Hello!")

        assert response.usage["prompt_tokens"] == 10
        assert response.usage["completion_tokens"] == 5
        assert response.usage["total_tokens"] == 15


class TestLLMClientErrors:
    """Tests for LLMClient error handling."""

    def test_authentication_error(self) -> None:
        """Test authentication error is wrapped in LLMError."""
        import litellm

        config = LLMConfig(
            provider="claude",
            model="claude-3-sonnet-20240229",
            api_key="invalid-key",
        )
        client = LLMClient(config)

        with patch("litellm.completion") as mock_call:
            mock_call.side_effect = litellm.exceptions.AuthenticationError(
                message="Invalid API key",
                llm_provider="anthropic",
                model="claude-3-sonnet-20240229",
            )

            with pytest.raises(LLMError, match="Authentication failed"):
                client.complete("Hello!")

    def test_rate_limit_error(self) -> None:
        """Test rate limit error is wrapped in LLMError."""
        import litellm

        config = LLMConfig(
            provider="claude",
            model="claude-3-sonnet-20240229",
            api_key="test-key",
        )
        client = LLMClient(config)

        with patch("litellm.completion") as mock_call:
            mock_call.side_effect = litellm.exceptions.RateLimitError(
                message="Rate limit exceeded",
                llm_provider="anthropic",
                model="claude-3-sonnet-20240229",
            )

            with pytest.raises(LLMError, match="Rate limit exceeded"):
                client.complete("Hello!")

    def test_connection_error(self) -> None:
        """Test connection error is wrapped in LLMError."""
        import litellm

        config = LLMConfig(
            provider="ollama",
            model="llama2",
            api_base="http://localhost:11434",
        )
        client = LLMClient(config)

        with patch("litellm.completion") as mock_call:
            mock_call.side_effect = litellm.exceptions.APIConnectionError(
                message="Connection refused",
                llm_provider="ollama",
                model="llama2",
            )

            with pytest.raises(LLMError, match="Connection failed"):
                client.complete("Hello!")

    def test_generic_error(self) -> None:
        """Test generic exceptions are wrapped in LLMError."""
        config = LLMConfig(
            provider="claude",
            model="claude-3-sonnet-20240229",
            api_key="test-key",
        )
        client = LLMClient(config)

        with patch("litellm.completion") as mock_call:
            mock_call.side_effect = Exception("Unknown error")

            with pytest.raises(LLMError, match="LLM completion failed"):
                client.complete("Hello!")


class TestLLMClientSummarize:
    """Tests for LLMClient.summarize method."""

    @pytest.fixture
    def mock_litellm_response(self) -> MagicMock:
        """Create a mock LiteLLM response for summarization."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(content="This is a summary of the content."),
                finish_reason="stop",
            )
        ]
        mock_response.model = "claude-3-sonnet-20240229"
        mock_response.usage = MagicMock(
            prompt_tokens=50,
            completion_tokens=20,
            total_tokens=70,
        )
        return mock_response

    def test_summarize_returns_content(self, mock_litellm_response: MagicMock) -> None:
        """Test summarize returns the generated summary."""
        config = LLMConfig(
            provider="claude",
            model="claude-3-sonnet-20240229",
            api_key="test-key",
        )
        client = LLMClient(config)

        with patch("litellm.completion", return_value=mock_litellm_response):
            summary = client.summarize("Long content to summarize...")

        assert summary == "This is a summary of the content."

    def test_summarize_includes_context(self, mock_litellm_response: MagicMock) -> None:
        """Test summarize includes context in system prompt."""
        config = LLMConfig(
            provider="claude",
            model="claude-3-sonnet-20240229",
            api_key="test-key",
        )
        client = LLMClient(config)

        with patch(
            "litellm.completion", return_value=mock_litellm_response
        ) as mock_call:
            client.summarize("Content", context="architecture documentation")

            call_kwargs = mock_call.call_args[1]
            system_message = call_kwargs["messages"][0]["content"]
            assert "architecture documentation" in system_message

    def test_summarize_includes_max_length(
        self, mock_litellm_response: MagicMock
    ) -> None:
        """Test summarize includes max_length in prompt."""
        config = LLMConfig(
            provider="claude",
            model="claude-3-sonnet-20240229",
            api_key="test-key",
        )
        client = LLMClient(config)

        with patch(
            "litellm.completion", return_value=mock_litellm_response
        ) as mock_call:
            client.summarize("Content", max_length=200)

            call_kwargs = mock_call.call_args[1]
            system_message = call_kwargs["messages"][0]["content"]
            assert "200" in system_message


class TestLLMClientCheckAvailable:
    """Tests for LLMClient.check_available method."""

    def test_check_available_returns_true_on_success(self) -> None:
        """Test check_available returns True when API is reachable."""
        config = LLMConfig(
            provider="claude",
            model="claude-3-sonnet-20240229",
            api_key="test-key",
        )
        client = LLMClient(config)

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="ok"))]
        mock_response.model = "claude-3-sonnet-20240229"
        mock_response.usage = MagicMock(
            prompt_tokens=2, completion_tokens=1, total_tokens=3
        )

        with patch("litellm.completion", return_value=mock_response):
            assert client.check_available() is True

    def test_check_available_returns_false_on_error(self) -> None:
        """Test check_available returns False when API fails."""
        config = LLMConfig(
            provider="claude",
            model="claude-3-sonnet-20240229",
            api_key="invalid-key",
        )
        client = LLMClient(config)

        with patch("litellm.completion") as mock_call:
            mock_call.side_effect = Exception("API error")

            assert client.check_available() is False


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_response_creation(self) -> None:
        """Test LLMResponse can be created with all fields."""
        response = LLMResponse(
            content="Generated text",
            model="claude-3-sonnet",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            finish_reason="stop",
        )

        assert response.content == "Generated text"
        assert response.model == "claude-3-sonnet"
        assert response.usage["total_tokens"] == 15
        assert response.finish_reason == "stop"

    def test_response_finish_reason_optional(self) -> None:
        """Test finish_reason is optional."""
        response = LLMResponse(
            content="Text",
            model="model",
            usage={},
        )

        assert response.finish_reason is None


class TestProviderSpecificBehavior:
    """Tests for provider-specific LLM client behavior."""

    @pytest.fixture
    def mock_response(self) -> MagicMock:
        """Create standard mock response."""
        mock = MagicMock()
        mock.choices = [
            MagicMock(message=MagicMock(content="ok"), finish_reason="stop")
        ]
        mock.model = "test-model"
        mock.usage = MagicMock(prompt_tokens=5, completion_tokens=2, total_tokens=7)
        return mock

    def test_ollama_includes_api_base(self, mock_response: MagicMock) -> None:
        """Test Ollama client includes api_base in completion call."""
        config = LLMConfig(
            provider="ollama",
            model="llama2",
            api_base="http://localhost:11434",
        )
        client = LLMClient(config)

        with patch("litellm.completion", return_value=mock_response) as mock_call:
            client.complete("Hello")

            call_kwargs = mock_call.call_args[1]
            assert call_kwargs["api_base"] == "http://localhost:11434"
            assert call_kwargs["top_k"] == 1

    def test_bedrock_uses_bedrock_prefix(self, mock_response: MagicMock) -> None:
        """Test Bedrock client uses bedrock/ prefix for model."""
        config = LLMConfig(
            provider="bedrock",
            model="anthropic.claude-3-sonnet-20240229-v1:0",
        )
        client = LLMClient(config)

        with patch("litellm.completion", return_value=mock_response) as mock_call:
            client.complete("Hello")

            call_kwargs = mock_call.call_args[1]
            assert (
                call_kwargs["model"]
                == "bedrock/anthropic.claude-3-sonnet-20240229-v1:0"
            )

    def test_claude_uses_anthropic_prefix(self, mock_response: MagicMock) -> None:
        """Test Claude client uses anthropic/ prefix for model."""
        config = LLMConfig(
            provider="claude",
            model="claude-3-sonnet-20240229",
            api_key="test-key",
        )
        client = LLMClient(config)

        with patch("litellm.completion", return_value=mock_response) as mock_call:
            client.complete("Hello")

            call_kwargs = mock_call.call_args[1]
            assert call_kwargs["model"] == "anthropic/claude-3-sonnet-20240229"
            assert call_kwargs["top_k"] == 1

    def test_gemini_uses_gemini_prefix(self, mock_response: MagicMock) -> None:
        """Test Gemini client uses gemini/ prefix for model."""
        config = LLMConfig(
            provider="gemini",
            model="gemini-pro",
            api_key="test-key",
        )
        client = LLMClient(config)

        with patch("litellm.completion", return_value=mock_response) as mock_call:
            client.complete("Hello")

            call_kwargs = mock_call.call_args[1]
            assert call_kwargs["model"] == "gemini/gemini-pro"
