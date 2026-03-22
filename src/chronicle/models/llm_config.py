"""LLM Configuration entity for chronicle.

Defines the configuration for LLM providers used in document summarization.
Supports multiple providers: Claude, Gemini, Ollama, and Bedrock.
"""

from dataclasses import dataclass, field

# Valid LLM providers
VALID_PROVIDERS = frozenset({"claude", "gemini", "ollama", "bedrock"})


@dataclass
class LLMConfig:
    """Configuration for LLM provider.

    Attributes:
        provider: LLM provider (claude, gemini, ollama, bedrock)
        model: Model identifier (e.g., "claude-3-sonnet", "gemini-pro")
        api_key: API key (not required for Ollama)
        api_base: API base URL (required for Ollama)
        temperature: Temperature setting (must be 0 for reproducibility)
        max_tokens: Maximum response tokens
        enabled: Whether LLM summarization is enabled
    """

    provider: str
    model: str
    api_key: str | None = None
    api_base: str | None = None
    temperature: float = field(default=0.0)
    max_tokens: int = field(default=4096)
    enabled: bool = field(default=True)

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        # Normalize provider to lowercase
        self.provider = self.provider.lower().strip()

        # Validate provider
        if self.provider not in VALID_PROVIDERS:
            raise ValueError(
                f"Invalid provider '{self.provider}'. "
                f"Must be one of: {sorted(VALID_PROVIDERS)}"
            )

        # Validate model is not empty
        if not self.model or not self.model.strip():
            raise ValueError("Model identifier cannot be empty")
        self.model = self.model.strip()

        # Validate temperature is 0 for reproducibility (Principle II)
        if self.temperature != 0.0:
            raise ValueError(
                f"Temperature must be 0 for reproducibility (Principle II). "
                f"Got: {self.temperature}"
            )

        # Validate max_tokens is positive
        if self.max_tokens <= 0:
            raise ValueError(f"max_tokens must be positive. Got: {self.max_tokens}")

        # Provider-specific validation
        if self.provider == "ollama":
            if not self.api_base:
                raise ValueError("api_base is required for Ollama provider")
        elif self.provider == "bedrock":
            # Bedrock uses AWS credentials from environment, not API key
            # AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN
            # Validation of actual credentials is done in preflight check
            pass
        elif self.provider in {"claude", "gemini"}:
            # Cloud providers require API key
            if not self.api_key:
                raise ValueError(f"api_key is required for {self.provider} provider")

    def validate(self) -> list[str]:
        """Validate configuration and return warnings.

        Returns:
            List of warning messages (empty if no warnings)
        """
        warnings: list[str] = []

        # Warn about very low max_tokens
        if self.max_tokens < 1000:
            warnings.append(
                f"max_tokens is set to {self.max_tokens}, which may truncate responses"
            )

        # Warn about non-standard Ollama base URL
        if (
            self.provider == "ollama"
            and self.api_base
            and not self.api_base.startswith(("http://", "https://"))
        ):
            warnings.append(
                f"api_base '{self.api_base}' does not start with http:// or https://"
            )

        return warnings

    def to_dict(self) -> dict[str, str | int | float | bool | None]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the configuration
        """
        return {
            "provider": self.provider,
            "model": self.model,
            "api_key": self.api_key,
            "api_base": self.api_base,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str | int | float | bool | None]) -> "LLMConfig":
        """Create LLMConfig from dictionary.

        Args:
            data: Dictionary with configuration values

        Returns:
            LLMConfig instance
        """
        return cls(
            provider=str(data.get("provider", "")),
            model=str(data.get("model", "")),
            api_key=data.get("api_key") if data.get("api_key") else None,  # type: ignore[arg-type]
            api_base=data.get("api_base") if data.get("api_base") else None,  # type: ignore[arg-type]
            temperature=float(data.get("temperature", 0.0)),  # type: ignore[arg-type]
            max_tokens=int(data.get("max_tokens", 4096)),  # type: ignore[arg-type]
            enabled=bool(data.get("enabled", True)),
        )

    def get_litellm_model_name(self) -> str:
        """Get the model name in LiteLLM format.

        Returns:
            Model name formatted for LiteLLM
        """
        # LiteLLM uses provider/model format for some providers
        if self.provider == "ollama":
            return f"ollama/{self.model}"
        elif self.provider == "bedrock":
            return f"bedrock/{self.model}"
        elif self.provider == "gemini":
            return f"gemini/{self.model}"
        else:
            # Claude uses anthropic/ prefix in LiteLLM
            return f"anthropic/{self.model}"
