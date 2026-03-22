"""Unit tests for LLM preflight checks (T023j)."""

from unittest.mock import MagicMock, patch

from chronicle.utils.preflight import PreflightChecker, ToolCheck


class TestLiteLLMCheck:
    """Tests for check_litellm preflight check."""

    def test_litellm_available(self) -> None:
        """Test check_litellm when package is installed."""
        checker = PreflightChecker()

        with patch("importlib.util.find_spec") as mock_find_spec:
            mock_spec = MagicMock()
            mock_spec.origin = "/path/to/litellm/__init__.py"
            mock_find_spec.return_value = mock_spec

            with patch.dict("sys.modules", {"litellm": MagicMock(__version__="1.0.0")}):
                result = checker.check_litellm(required=True)

        assert result.available is True
        assert result.name == "litellm"
        assert result.required is True
        assert "Unified LLM interface" in result.message

    def test_litellm_not_available(self) -> None:
        """Test check_litellm when package is not installed."""
        checker = PreflightChecker()

        with patch("importlib.util.find_spec", return_value=None):
            result = checker.check_litellm(required=True)

        assert result.available is False
        assert result.name == "litellm"
        assert "pip install litellm" in result.message


class TestOllamaServerCheck:
    """Tests for check_ollama_server preflight check."""

    def test_ollama_server_available(self) -> None:
        """Test check_ollama_server when server is running."""
        checker = PreflightChecker()

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = checker.check_ollama_server("http://localhost:11434")

        assert result.available is True
        assert result.name == "ollama"
        assert result.path == "http://localhost:11434"
        assert "Local LLM server" in result.message

    def test_ollama_server_not_running(self) -> None:
        """Test check_ollama_server when server is not running."""
        import urllib.error

        checker = PreflightChecker()

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

            result = checker.check_ollama_server("http://localhost:11434")

        assert result.available is False
        assert result.name == "ollama"
        assert "not responding" in result.message
        assert "https://ollama.ai" in result.message

    def test_ollama_custom_api_base(self) -> None:
        """Test check_ollama_server with custom API base URL."""
        checker = PreflightChecker()

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_response

            result = checker.check_ollama_server("http://192.168.1.100:11434")

        assert result.path == "http://192.168.1.100:11434"


class TestLLMProviderCheck:
    """Tests for check_llm_provider preflight check."""

    def test_claude_with_api_key(self) -> None:
        """Test Claude provider check with API key (mocked connectivity)."""
        checker = PreflightChecker()

        with patch("litellm.completion") as mock_completion:
            # Mock successful API call
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="ok"))]
            mock_completion.return_value = mock_response

            result = checker.check_llm_provider(
                provider="claude",
                api_key="sk-ant-test-key",
            )

        assert result.available is True
        assert result.name == "claude"
        assert "Claude API verified" in result.message

    def test_claude_without_api_key(self) -> None:
        """Test Claude provider check without API key."""
        checker = PreflightChecker()

        result = checker.check_llm_provider(
            provider="claude",
            api_key=None,
        )

        assert result.available is False
        assert result.name == "claude"
        assert "API key required" in result.message
        assert "ANTHROPIC_API_KEY" in result.message

    def test_gemini_with_api_key(self) -> None:
        """Test Gemini provider check with API key (mocked connectivity)."""
        checker = PreflightChecker()

        with patch("litellm.completion") as mock_completion:
            # Mock successful API call
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="ok"))]
            mock_completion.return_value = mock_response

            result = checker.check_llm_provider(
                provider="gemini",
                api_key="test-google-key",
            )

        assert result.available is True
        assert result.name == "gemini"
        assert "Gemini API verified" in result.message

    def test_gemini_without_api_key(self) -> None:
        """Test Gemini provider check without API key."""
        checker = PreflightChecker()

        result = checker.check_llm_provider(
            provider="gemini",
            api_key=None,
        )

        assert result.available is False
        assert "GOOGLE_API_KEY" in result.message

    def test_ollama_provider_delegates_to_server_check(self) -> None:
        """Test Ollama provider check delegates to server check."""
        checker = PreflightChecker()

        with patch.object(checker, "check_ollama_server") as mock_check:
            mock_check.return_value = ToolCheck(
                name="ollama",
                available=True,
                message="test",
            )

            checker.check_llm_provider(
                provider="ollama",
                api_base="http://custom:11434",
            )

            mock_check.assert_called_once_with("http://custom:11434")

    def test_ollama_uses_default_api_base(self) -> None:
        """Test Ollama provider uses default API base when not specified."""
        checker = PreflightChecker()

        with patch.object(checker, "check_ollama_server") as mock_check:
            mock_check.return_value = ToolCheck(
                name="ollama",
                available=True,
                message="test",
            )

            checker.check_llm_provider(
                provider="ollama",
                api_base=None,
            )

            mock_check.assert_called_once_with("http://localhost:11434")

    def test_bedrock_delegates_to_bedrock_check(self) -> None:
        """Test Bedrock provider check delegates to bedrock check with configured model."""
        checker = PreflightChecker()

        with patch.object(checker, "check_bedrock") as mock_check:
            mock_check.return_value = ToolCheck(
                name="bedrock",
                available=True,
                message="test",
            )

            checker.check_llm_provider(
                provider="bedrock",
                model="us.anthropic.claude-sonnet-4-6",
            )

            # Model from config is passed through
            mock_check.assert_called_once_with(
                model="us.anthropic.claude-sonnet-4-6"
            )

    def test_unknown_provider(self) -> None:
        """Test unknown provider returns unavailable."""
        checker = PreflightChecker()

        result = checker.check_llm_provider(provider="unknown_provider")

        assert result.available is False
        assert "Unknown LLM provider" in result.message


class TestBedrockCheck:
    """Tests for check_bedrock preflight check."""

    def test_bedrock_with_env_credentials(self) -> None:
        """Test Bedrock check with environment variable credentials (mocked connectivity)."""
        checker = PreflightChecker()

        with (
            patch.dict(
                "os.environ",
                {
                    "AWS_ACCESS_KEY_ID": "test-key",
                    "AWS_SECRET_ACCESS_KEY": "test-secret",
                    "AWS_REGION": "us-west-2",
                },
            ),
            patch("litellm.completion") as mock_completion,
        ):
            # Mock successful API call
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="ok"))]
            mock_completion.return_value = mock_response

            result = checker.check_bedrock(model="us.anthropic.claude-sonnet-4-6")

        assert result.available is True
        assert result.name == "bedrock"
        assert "us-west-2" in result.message
        assert "env vars" in result.message

    def test_bedrock_without_credentials(self) -> None:
        """Test Bedrock check without credentials."""
        checker = PreflightChecker()

        with (
            patch.dict("os.environ", {}, clear=True),
            patch("pathlib.Path.exists", return_value=False),
        ):
            result = checker.check_bedrock(model="us.anthropic.claude-sonnet-4-6")

        assert result.available is False
        assert result.name == "bedrock"
        assert "AWS credentials required" in result.message

    def test_bedrock_with_credentials_file(self) -> None:
        """Test Bedrock check with credentials file (mocked connectivity)."""
        checker = PreflightChecker()

        with (
            patch.dict("os.environ", {}, clear=True),
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "pathlib.Path.read_text",
                return_value="[default]\naws_access_key_id=test",
            ),
            patch("litellm.completion") as mock_completion,
        ):
            # Mock successful API call
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="ok"))]
            mock_completion.return_value = mock_response

            result = checker.check_bedrock(model="us.anthropic.claude-sonnet-4-6")

        assert result.available is True
        assert "profile: default" in result.message


class TestCheckAllLLM:
    """Tests for check_all method LLM integration."""

    def test_check_all_includes_llm_checks(self) -> None:
        """Test check_all includes LLM checks when not skipped."""
        checker = PreflightChecker()

        with (
            patch.object(checker, "check_litellm") as mock_litellm,
            patch.object(checker, "check_llm_provider") as mock_provider,
            patch.object(checker, "check_git") as mock_git,
        ):
            mock_litellm.return_value = ToolCheck(
                name="litellm",
                available=True,
                message="test",
            )
            mock_provider.return_value = ToolCheck(
                name="claude",
                available=True,
                message="test",
            )
            mock_git.return_value = ToolCheck(
                name="git", available=True, message="test"
            )

            checker.check_all(
                skip_sbom=True,
                skip_architecture=True,
                skip_ast=True,
                skip_llm=False,
                llm_provider="claude",
                llm_api_key="test-key",
            )

            mock_litellm.assert_called_once_with(required=True)
            mock_provider.assert_called_once_with(
                provider="claude",
                api_key="test-key",
                api_base=None,
                model=None,
            )

    def test_check_all_skips_llm_when_flagged(self) -> None:
        """Test check_all skips LLM checks when skip_llm=True."""
        checker = PreflightChecker()

        with (
            patch.object(checker, "check_litellm") as mock_litellm,
            patch.object(checker, "check_llm_provider") as mock_provider,
            patch.object(checker, "check_git") as mock_git,
        ):
            mock_git.return_value = ToolCheck(
                name="git", available=True, message="test"
            )

            checker.check_all(
                skip_sbom=True,
                skip_architecture=True,
                skip_ast=True,
                skip_llm=True,
            )

            mock_litellm.assert_not_called()
            mock_provider.assert_not_called()
