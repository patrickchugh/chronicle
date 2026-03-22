"""Unit tests for configuration system."""

from pathlib import Path

import pytest

from chronicle.config import (
    LLMConfig,
    SectionConfig,
    find_config_file,
    load_config_from_dict,
    substitute_env_vars,
)


class TestSubstituteEnvVars:
    """Tests for environment variable substitution."""

    def test_substitute_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test substituting env var in string."""
        monkeypatch.setenv("TEST_VAR", "test_value")

        result = substitute_env_vars("prefix_${TEST_VAR}_suffix")

        assert result == "prefix_test_value_suffix"

    def test_substitute_multiple_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test substituting multiple env vars."""
        monkeypatch.setenv("VAR1", "one")
        monkeypatch.setenv("VAR2", "two")

        result = substitute_env_vars("${VAR1} and ${VAR2}")

        assert result == "one and two"

    def test_substitute_in_dict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test substituting env vars in dictionary."""
        monkeypatch.setenv("API_KEY", "secret123")

        data = {"api_key": "${API_KEY}", "other": "value"}
        result = substitute_env_vars(data)

        assert result["api_key"] == "secret123"
        assert result["other"] == "value"

    def test_substitute_in_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test substituting env vars in list."""
        monkeypatch.setenv("ITEM", "value")

        data = ["static", "${ITEM}"]
        result = substitute_env_vars(data)

        assert result == ["static", "value"]

    def test_missing_env_var_raises(self) -> None:
        """Test that missing env var raises ValueError."""
        with pytest.raises(ValueError, match="Environment variable not set"):
            substitute_env_vars("${NONEXISTENT_VAR}")

    def test_passthrough_non_string(self) -> None:
        """Test that non-string values pass through unchanged."""
        assert substitute_env_vars(123) == 123
        assert substitute_env_vars(True) is True
        assert substitute_env_vars(None) is None


class TestFindConfigFile:
    """Tests for config file discovery."""

    def test_find_chronicle_config(self, tmp_path: Path) -> None:
        """Test finding .chronicle/config.yaml."""
        config_dir = tmp_path / ".chronicle"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"
        config_file.write_text("output:\n  path: test.md")

        result = find_config_file(tmp_path)

        assert result == config_file

    def test_find_root_config(self, tmp_path: Path) -> None:
        """Test finding chronicle.yaml at root."""
        config_file = tmp_path / "chronicle.yaml"
        config_file.write_text("output:\n  path: test.md")

        result = find_config_file(tmp_path)

        assert result == config_file

    def test_prefer_chronicle_dir_over_root(self, tmp_path: Path) -> None:
        """Test .chronicle/config.yaml is preferred over chronicle.yaml."""
        # Create both
        config_dir = tmp_path / ".chronicle"
        config_dir.mkdir()
        chronicle_config = config_dir / "config.yaml"
        chronicle_config.write_text("# preferred")

        root_config = tmp_path / "chronicle.yaml"
        root_config.write_text("# fallback")

        result = find_config_file(tmp_path)

        assert result == chronicle_config

    def test_no_config_returns_none(self, tmp_path: Path) -> None:
        """Test returns None when no config found."""
        result = find_config_file(tmp_path)

        assert result is None


class TestLoadConfigFromDict:
    """Tests for loading config from dictionary."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = load_config_from_dict({})

        assert config.output.path == "docs/SYSTEM.md"
        assert config.output.format == "markdown"
        assert config.tools.sbom == "syft"
        assert config.tools.diagrams == "terravision"
        # LLM is required with sensible defaults (Ollama for security)
        assert config.llm is not None
        assert config.llm.provider == "ollama"
        assert config.llm.model == "llama3.2"
        assert config.llm.enabled is True

    def test_custom_output(self) -> None:
        """Test custom output configuration."""
        config = load_config_from_dict(
            {
                "output": {
                    "path": "custom/path.md",
                    "format": "html",
                }
            }
        )

        assert config.output.path == "custom/path.md"
        assert config.output.format == "html"

    def test_llm_config(self) -> None:
        """Test LLM configuration."""
        config = load_config_from_dict(
            {
                "llm": {
                    "provider": "ollama",
                    "model": "llama2",
                    "temperature": 0,
                    "enabled": True,
                }
            }
        )

        assert config.llm is not None
        assert config.llm.provider == "ollama"
        assert config.llm.model == "llama2"
        assert config.llm.temperature == 0
        assert config.llm.enabled is True

    def test_sections_config(self) -> None:
        """Test sections configuration."""
        config = load_config_from_dict(
            {
                "sections": {
                    "overview": {
                        "file": ".chronicle/sections/overview.md",
                        "strategy": "prepend",
                    },
                    "security": {
                        "file": ".chronicle/sections/security.md",
                        "strategy": "append",
                    },
                }
            }
        )

        assert "overview" in config.sections
        assert config.sections["overview"].file == ".chronicle/sections/overview.md"
        assert config.sections["overview"].strategy == "prepend"


class TestLLMConfig:
    """Tests for LLM configuration validation."""

    def test_temperature_must_be_zero(self) -> None:
        """Test that non-zero temperature raises error (Principle II)."""
        with pytest.raises(ValueError, match="temperature must be 0"):
            LLMConfig(
                provider="ollama",
                model="llama2",
                temperature=0.7,
            )

    def test_invalid_provider(self) -> None:
        """Test that invalid provider raises error."""
        with pytest.raises(ValueError, match="Invalid LLM provider"):
            LLMConfig(
                provider="invalid",
                model="test",
                temperature=0,
            )

    def test_api_key_required_for_cloud(self) -> None:
        """Test that API key is required for cloud providers."""
        with pytest.raises(ValueError, match="API key required"):
            LLMConfig(
                provider="claude",
                model="claude-3-sonnet",
                temperature=0,
            )

    def test_ollama_defaults_api_base(self) -> None:
        """Test that Ollama defaults api_base."""
        config = LLMConfig(
            provider="ollama",
            model="llama2",
            temperature=0,
        )

        assert config.api_base == "http://localhost:11434"


class TestSectionConfig:
    """Tests for section configuration validation."""

    def test_invalid_strategy(self) -> None:
        """Test that invalid strategy raises error."""
        with pytest.raises(ValueError, match="Invalid merge strategy"):
            SectionConfig(
                file="test.md",
                strategy="invalid",
            )

    def test_valid_strategies(self) -> None:
        """Test valid merge strategies."""
        for strategy in ["prepend", "append", "replace"]:
            config = SectionConfig(file="test.md", strategy=strategy)
            assert config.strategy == strategy
