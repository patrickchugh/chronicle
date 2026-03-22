"""Unit tests for LLMConfig entity validation (T023m)."""

import pytest

from chronicle.models.llm_config import VALID_PROVIDERS, LLMConfig


class TestLLMConfig:
    """Tests for LLMConfig entity."""

    def test_create_claude_config(self) -> None:
        """Test creating a Claude provider configuration."""
        config = LLMConfig(
            provider="claude",
            model="claude-3-sonnet",
            api_key="test-key",
        )

        assert config.provider == "claude"
        assert config.model == "claude-3-sonnet"
        assert config.api_key == "test-key"
        assert config.temperature == 0.0
        assert config.max_tokens == 4096
        assert config.enabled is True

    def test_create_ollama_config(self) -> None:
        """Test creating an Ollama provider configuration."""
        config = LLMConfig(
            provider="ollama",
            model="llama2",
            api_base="http://localhost:11434",
        )

        assert config.provider == "ollama"
        assert config.model == "llama2"
        assert config.api_base == "http://localhost:11434"
        assert config.api_key is None

    def test_create_gemini_config(self) -> None:
        """Test creating a Gemini provider configuration."""
        config = LLMConfig(
            provider="gemini",
            model="gemini-pro",
            api_key="test-gemini-key",
        )

        assert config.provider == "gemini"
        assert config.model == "gemini-pro"
        assert config.api_key == "test-gemini-key"

    def test_create_bedrock_config(self) -> None:
        """Test creating a Bedrock provider configuration."""
        config = LLMConfig(
            provider="bedrock",
            model="anthropic.claude-v2",
            api_key="aws-key",
        )

        assert config.provider == "bedrock"
        assert config.model == "anthropic.claude-v2"

    def test_provider_normalized_to_lowercase(self) -> None:
        """Test provider is normalized to lowercase."""
        config = LLMConfig(
            provider="CLAUDE",
            model="claude-3-sonnet",
            api_key="test-key",
        )

        assert config.provider == "claude"

    def test_invalid_provider_raises_error(self) -> None:
        """Test invalid provider raises ValueError."""
        with pytest.raises(ValueError, match="Invalid provider"):
            LLMConfig(
                provider="invalid_provider",
                model="some-model",
                api_key="key",
            )

    def test_empty_model_raises_error(self) -> None:
        """Test empty model raises ValueError."""
        with pytest.raises(ValueError, match="Model identifier cannot be empty"):
            LLMConfig(
                provider="claude",
                model="",
                api_key="key",
            )

    def test_whitespace_model_raises_error(self) -> None:
        """Test whitespace-only model raises ValueError."""
        with pytest.raises(ValueError, match="Model identifier cannot be empty"):
            LLMConfig(
                provider="claude",
                model="   ",
                api_key="key",
            )

    def test_nonzero_temperature_raises_error(self) -> None:
        """Test non-zero temperature raises ValueError (Principle II)."""
        with pytest.raises(ValueError, match="Temperature must be 0"):
            LLMConfig(
                provider="claude",
                model="claude-3-sonnet",
                api_key="key",
                temperature=0.7,
            )

    def test_negative_max_tokens_raises_error(self) -> None:
        """Test negative max_tokens raises ValueError."""
        with pytest.raises(ValueError, match="max_tokens must be positive"):
            LLMConfig(
                provider="claude",
                model="claude-3-sonnet",
                api_key="key",
                max_tokens=-100,
            )

    def test_zero_max_tokens_raises_error(self) -> None:
        """Test zero max_tokens raises ValueError."""
        with pytest.raises(ValueError, match="max_tokens must be positive"):
            LLMConfig(
                provider="claude",
                model="claude-3-sonnet",
                api_key="key",
                max_tokens=0,
            )

    def test_ollama_without_api_base_raises_error(self) -> None:
        """Test Ollama provider without api_base raises ValueError."""
        with pytest.raises(ValueError, match="api_base is required for Ollama"):
            LLMConfig(
                provider="ollama",
                model="llama2",
            )

    def test_claude_without_api_key_raises_error(self) -> None:
        """Test Claude provider without api_key raises ValueError."""
        with pytest.raises(ValueError, match="api_key is required for claude"):
            LLMConfig(
                provider="claude",
                model="claude-3-sonnet",
            )

    def test_gemini_without_api_key_raises_error(self) -> None:
        """Test Gemini provider without api_key raises ValueError."""
        with pytest.raises(ValueError, match="api_key is required for gemini"):
            LLMConfig(
                provider="gemini",
                model="gemini-pro",
            )

    def test_validate_returns_warnings(self) -> None:
        """Test validate returns warnings for low max_tokens."""
        config = LLMConfig(
            provider="claude",
            model="claude-3-sonnet",
            api_key="key",
            max_tokens=500,
        )

        warnings = config.validate()

        assert len(warnings) == 1
        assert "max_tokens is set to 500" in warnings[0]

    def test_validate_warns_on_invalid_api_base_scheme(self) -> None:
        """Test validate warns on api_base without http/https."""
        config = LLMConfig(
            provider="ollama",
            model="llama2",
            api_base="localhost:11434",
        )

        warnings = config.validate()

        assert any("does not start with http" in w for w in warnings)

    def test_to_dict(self) -> None:
        """Test converting config to dictionary."""
        config = LLMConfig(
            provider="claude",
            model="claude-3-sonnet",
            api_key="test-key",
            max_tokens=2000,
        )

        data = config.to_dict()

        assert data["provider"] == "claude"
        assert data["model"] == "claude-3-sonnet"
        assert data["api_key"] == "test-key"
        assert data["temperature"] == 0.0
        assert data["max_tokens"] == 2000
        assert data["enabled"] is True

    def test_from_dict(self) -> None:
        """Test creating config from dictionary."""
        data = {
            "provider": "gemini",
            "model": "gemini-pro",
            "api_key": "test-key",
            "max_tokens": 3000,
        }

        config = LLMConfig.from_dict(data)

        assert config.provider == "gemini"
        assert config.model == "gemini-pro"
        assert config.api_key == "test-key"
        assert config.max_tokens == 3000

    def test_roundtrip_to_from_dict(self) -> None:
        """Test that to_dict/from_dict roundtrip preserves values."""
        original = LLMConfig(
            provider="ollama",
            model="codellama",
            api_base="http://localhost:11434",
            max_tokens=8192,
            enabled=False,
        )

        data = original.to_dict()
        restored = LLMConfig.from_dict(data)

        assert restored.provider == original.provider
        assert restored.model == original.model
        assert restored.api_base == original.api_base
        assert restored.max_tokens == original.max_tokens
        assert restored.enabled == original.enabled

    def test_get_litellm_model_name_claude(self) -> None:
        """Test LiteLLM model name for Claude."""
        config = LLMConfig(
            provider="claude",
            model="claude-3-sonnet",
            api_key="key",
        )

        assert config.get_litellm_model_name() == "anthropic/claude-3-sonnet"

    def test_get_litellm_model_name_ollama(self) -> None:
        """Test LiteLLM model name for Ollama."""
        config = LLMConfig(
            provider="ollama",
            model="llama2",
            api_base="http://localhost:11434",
        )

        assert config.get_litellm_model_name() == "ollama/llama2"

    def test_get_litellm_model_name_gemini(self) -> None:
        """Test LiteLLM model name for Gemini."""
        config = LLMConfig(
            provider="gemini",
            model="gemini-pro",
            api_key="key",
        )

        assert config.get_litellm_model_name() == "gemini/gemini-pro"

    def test_get_litellm_model_name_bedrock(self) -> None:
        """Test LiteLLM model name for Bedrock."""
        config = LLMConfig(
            provider="bedrock",
            model="anthropic.claude-v2",
            api_key="key",
        )

        assert config.get_litellm_model_name() == "bedrock/anthropic.claude-v2"

    def test_valid_providers_constant(self) -> None:
        """Test VALID_PROVIDERS contains expected values."""
        assert "claude" in VALID_PROVIDERS
        assert "gemini" in VALID_PROVIDERS
        assert "ollama" in VALID_PROVIDERS
        assert "bedrock" in VALID_PROVIDERS
        assert len(VALID_PROVIDERS) == 4
