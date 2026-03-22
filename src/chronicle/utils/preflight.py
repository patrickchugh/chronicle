"""Preflight validation (Principle III: Preflight Validation).

All external dependencies MUST be validated before analysis begins, not during processing.
Missing required tools MUST cause immediate exit with clear error message.

NO FALLBACKS: If a required dependency is unavailable, analysis MUST fail immediately.
This prevents partial/degraded results and ensures consistent, reproducible output.
"""

import importlib.util
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ToolCheck:
    """Result of checking a single tool.

    Attributes:
        name: Tool name
        available: Whether tool is available
        version: Tool version if available
        required: Whether tool is required for this run
        path: Path to executable if available
        message: Status message (human-readable context)
    """

    name: str
    available: bool
    version: str | None = None
    required: bool = True
    path: str | None = None
    message: str = ""


@dataclass
class PreflightResult:
    """Result of preflight validation.

    Attributes:
        success: Whether all required tools are available
        checks: Individual tool check results
        errors: Error messages for missing required tools
        warnings: Warning messages for missing optional tools
    """

    success: bool = True
    checks: list[ToolCheck] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_check(self, check: ToolCheck) -> None:
        """Add a tool check result."""
        self.checks.append(check)

        if not check.available:
            if check.required:
                self.success = False
                self.errors.append(f"Required tool not found: {check.name}")
            else:
                self.warnings.append(f"Optional tool not found: {check.name}")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "success": self.success,
            "checks": [
                {
                    "name": c.name,
                    "available": c.available,
                    "version": c.version,
                    "required": c.required,
                    "path": c.path,
                    "message": c.message,
                }
                for c in self.checks
            ],
            "errors": self.errors,
            "warnings": self.warnings,
        }


class PreflightChecker:
    """Validates external tool availability before analysis.

    Usage:
        checker = PreflightChecker()
        result = checker.check_all(config)
        if not result.success:
            sys.exit(1)
    """

    def __init__(self, timeout: int = 10) -> None:
        """Initialize preflight checker.

        Args:
            timeout: Timeout in seconds for version checks
        """
        self.timeout = timeout

    def check_command_available(self, command: str) -> tuple[bool, str | None]:
        """Check if a command is available in PATH.

        Args:
            command: Command name to check

        Returns:
            Tuple of (available, path)
        """
        path = shutil.which(command)
        return path is not None, path

    def get_command_version(
        self,
        command: str,
        version_args: list[str] | None = None,
    ) -> str | None:
        """Get version string for a command.

        Args:
            command: Command to get version for
            version_args: Arguments to get version (default: ["--version"])

        Returns:
            Version string if available, None otherwise
        """
        if version_args is None:
            version_args = ["--version"]

        try:
            result = subprocess.run(
                [command, *version_args],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            if result.returncode == 0:
                # Return first line of output (usually contains version)
                output = result.stdout.strip() or result.stderr.strip()
                return output.split("\n")[0] if output else None
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return None

    def check_syft(self, required: bool = True) -> ToolCheck:
        """Check if Syft is available.

        Args:
            required: Whether Syft is required for this run

        Returns:
            ToolCheck result
        """
        available, path = self.check_command_available("syft")

        if available:
            version = self.get_command_version("syft", ["version"])
            return ToolCheck(
                name="syft",
                available=True,
                version=version,
                required=required,
                path=path,
                message="SBOM generator",
            )
        else:
            return ToolCheck(
                name="syft",
                available=False,
                required=required,
                message="Install from: https://github.com/anchore/syft",
            )

    def check_repomix(self, required: bool = True) -> ToolCheck:
        """Check if Repomix is available.

        Repomix compresses codebases into AI-friendly format for holistic analysis.
        Can be installed globally via npm or run via npx.

        Args:
            required: Whether Repomix is required for this run

        Returns:
            ToolCheck result
        """
        # First try global installation
        available, path = self.check_command_available("repomix")

        if available:
            version = self.get_command_version("repomix", ["--version"])
            return ToolCheck(
                name="repomix",
                available=True,
                version=version,
                required=required,
                path=path,
                message="Codebase compression tool for holistic LLM analysis",
            )

        # Try npx repomix
        npx_available, npx_path = self.check_command_available("npx")
        if npx_available:
            try:
                result = subprocess.run(
                    ["npx", "repomix", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )
                if result.returncode == 0:
                    version = result.stdout.strip().split("\n")[0]
                    return ToolCheck(
                        name="repomix",
                        available=True,
                        version=version,
                        required=required,
                        path="npx repomix",
                        message="Codebase compression tool (via npx)",
                    )
            except (subprocess.TimeoutExpired, Exception):
                pass

        return ToolCheck(
            name="repomix",
            available=False,
            required=required,
            message="Install via: npm install -g repomix (or use npx repomix)",
        )

    def check_terravision(self, required: bool = True) -> ToolCheck:
        """Check if Terravision is available.

        Args:
            required: Whether Terravision is required for this run

        Returns:
            ToolCheck result
        """
        available, path = self.check_command_available("terravision")

        if available:
            version = self.get_command_version("terravision")
            return ToolCheck(
                name="terravision",
                available=True,
                version=version,
                required=required,
                path=path,
                message="Terraform diagram generator",
            )
        else:
            return ToolCheck(
                name="terravision",
                available=False,
                required=required,
                message="Install from: https://github.com/patrickchugh/terravision",
            )

    def check_graphviz(self, required: bool = False) -> ToolCheck:
        """Check if Graphviz (dot) is available.

        Required for Terravision diagram rendering.

        Args:
            required: Whether Graphviz is required

        Returns:
            ToolCheck result
        """
        available, path = self.check_command_available("dot")

        if available:
            version = self.get_command_version("dot", ["-V"])
            return ToolCheck(
                name="graphviz",
                available=True,
                version=version,
                required=required,
                path=path,
                message="Diagram rendering engine",
            )
        else:
            return ToolCheck(
                name="graphviz",
                available=False,
                required=required,
                message="Required for diagram rendering. Install from: https://graphviz.org",
            )

    def check_git(self, required: bool = True) -> ToolCheck:
        """Check if Git is available.

        Args:
            required: Whether Git is required

        Returns:
            ToolCheck result
        """
        available, path = self.check_command_available("git")

        if available:
            version = self.get_command_version("git")
            return ToolCheck(
                name="git",
                available=True,
                version=version,
                required=required,
                path=path,
                message="Version control",
            )
        else:
            return ToolCheck(
                name="git",
                available=False,
                required=required,
                message="Install from: https://git-scm.com",
            )

    def check_tree_sitter(self, required: bool = True) -> ToolCheck:
        """Check if tree-sitter and tree-sitter-language-pack are available.

        Required for AST parsing. No fallback is provided per Principle III.

        Args:
            required: Whether tree-sitter is required

        Returns:
            ToolCheck result
        """
        # Check tree-sitter core
        ts_spec = importlib.util.find_spec("tree_sitter")
        if ts_spec is None:
            return ToolCheck(
                name="tree-sitter",
                available=False,
                required=required,
                message="Install with: pip install tree-sitter",
            )

        # Check tree-sitter-language-pack
        lang_pack_spec = importlib.util.find_spec("tree_sitter_language_pack")
        if lang_pack_spec is None:
            return ToolCheck(
                name="tree-sitter",
                available=False,
                required=required,
                message="Install with: pip install tree-sitter-language-pack",
            )

        # Get version and path
        version = None
        module_path = None
        try:
            import tree_sitter

            version = getattr(tree_sitter, "__version__", None)
            if ts_spec.origin:
                module_path = ts_spec.origin
        except ImportError:
            pass

        return ToolCheck(
            name="tree-sitter",
            available=True,
            version=version,
            required=required,
            path=module_path,
            message="AST parser (Python package)",
        )

    def check_litellm(self, required: bool = True) -> ToolCheck:
        """Check if LiteLLM package is available.

        LiteLLM provides unified access to multiple LLM providers.

        Args:
            required: Whether LiteLLM is required

        Returns:
            ToolCheck result
        """
        litellm_spec = importlib.util.find_spec("litellm")
        if litellm_spec is None:
            return ToolCheck(
                name="litellm",
                available=False,
                required=required,
                message="Install with: pip install litellm",
            )

        # Get version
        version = None
        module_path = None
        try:
            import litellm

            version = getattr(litellm, "__version__", None)
            if litellm_spec.origin:
                module_path = litellm_spec.origin
        except ImportError:
            pass

        return ToolCheck(
            name="litellm",
            available=True,
            version=version,
            required=required,
            path=module_path,
            message="Unified LLM interface (Python package)",
        )

    def check_ollama_server(self, api_base: str = "http://localhost:11434") -> ToolCheck:
        """Check if Ollama server is running and responding.

        Ollama is the default LLM provider for security-conscious enterprises
        as it keeps all data local. LiteLLM uses this server for ollama/* models.

        Args:
            api_base: Ollama API base URL

        Returns:
            ToolCheck result
        """
        import urllib.error
        import urllib.request

        try:
            # Check Ollama API endpoint
            url = f"{api_base}/api/tags"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    # Try to get version
                    version = None
                    try:
                        version_url = f"{api_base}/api/version"
                        version_req = urllib.request.Request(version_url, method="GET")
                        with urllib.request.urlopen(version_req, timeout=5) as ver_resp:
                            import json

                            data = json.loads(ver_resp.read().decode())
                            version = data.get("version")
                    except Exception:
                        pass

                    return ToolCheck(
                        name="ollama",
                        available=True,
                        version=version,
                        required=True,
                        path=api_base,
                        message="Local LLM server (secure - no data leaves machine)",
                    )
        except urllib.error.URLError:
            pass
        except Exception:
            pass

        return ToolCheck(
            name="ollama",
            available=False,
            required=True,
            message=f"Ollama not responding at {api_base}. Install from: https://ollama.ai",
        )

    def check_llm_provider(
        self,
        provider: str,
        api_key: str | None = None,
        api_base: str | None = None,
        model: str | None = None,
    ) -> ToolCheck:
        """Check if configured LLM provider is available.

        Uses LiteLLM as the unified interface. Performs actual API calls
        to verify connectivity, not just credential existence.

        Args:
            provider: LLM provider (ollama, claude, gemini, bedrock)
            api_key: API key for cloud providers
            api_base: API base URL (required for Ollama)
            model: Model to test with (provider-specific defaults used if not provided)

        Returns:
            ToolCheck result
        """
        if provider == "ollama":
            return self.check_ollama_server(api_base or "http://localhost:11434")

        if provider == "bedrock":
            # Default to Claude 3 Haiku on Bedrock for testing
            bedrock_model = model or "anthropic.claude-3-haiku-20240307-v1:0"
            return self.check_bedrock(model=bedrock_model)

        # For Claude and Gemini, verify API key and test connectivity
        if provider == "claude":
            if not api_key:
                return ToolCheck(
                    name="claude",
                    available=False,
                    required=True,
                    message="API key required. Set llm.api_key or ANTHROPIC_API_KEY env var",
                )
            return self._check_claude_connectivity(api_key, model)

        if provider == "gemini":
            if not api_key:
                return ToolCheck(
                    name="gemini",
                    available=False,
                    required=True,
                    message="API key required. Set llm.api_key or GOOGLE_API_KEY env var",
                )
            return self._check_gemini_connectivity(api_key, model)

        return ToolCheck(
            name=provider,
            available=False,
            required=True,
            message=f"Unknown LLM provider: {provider}",
        )

    def _check_claude_connectivity(
        self,
        api_key: str,
        model: str | None = None,
    ) -> ToolCheck:
        """Test actual connectivity to Claude API.

        Args:
            api_key: Anthropic API key
            model: Model to test with

        Returns:
            ToolCheck result
        """
        test_model = model or "claude-3-haiku-20240307"

        try:
            import litellm

            litellm.completion(
                model=f"anthropic/{test_model}",
                messages=[{"role": "user", "content": "Say ok"}],
                max_tokens=5,
                temperature=0,
                api_key=api_key,
            )

            return ToolCheck(
                name="claude",
                available=True,
                required=True,
                message=f"Anthropic Claude API verified (model: {test_model})",
            )

        except ImportError:
            return ToolCheck(
                name="claude",
                available=False,
                required=True,
                message="LiteLLM not installed. Install with: pip install litellm",
            )

        except Exception as e:
            error_msg = str(e)
            if "invalid_api_key" in error_msg.lower() or "authentication" in error_msg.lower():
                return ToolCheck(
                    name="claude",
                    available=False,
                    required=True,
                    message="Invalid API key. Check your ANTHROPIC_API_KEY.",
                )
            else:
                return ToolCheck(
                    name="claude",
                    available=False,
                    required=True,
                    message=f"Claude API connection failed: {error_msg}",
                )

    def _check_gemini_connectivity(
        self,
        api_key: str,
        model: str | None = None,
    ) -> ToolCheck:
        """Test actual connectivity to Gemini API.

        Args:
            api_key: Google API key
            model: Model to test with

        Returns:
            ToolCheck result
        """
        test_model = model or "gemini-1.5-flash"

        try:
            import litellm

            litellm.completion(
                model=f"gemini/{test_model}",
                messages=[{"role": "user", "content": "Say ok"}],
                max_tokens=5,
                temperature=0,
                api_key=api_key,
            )

            return ToolCheck(
                name="gemini",
                available=True,
                required=True,
                message=f"Google Gemini API verified (model: {test_model})",
            )

        except ImportError:
            return ToolCheck(
                name="gemini",
                available=False,
                required=True,
                message="LiteLLM not installed. Install with: pip install litellm",
            )

        except Exception as e:
            error_msg = str(e)
            if "invalid_api_key" in error_msg.lower() or "api key" in error_msg.lower():
                return ToolCheck(
                    name="gemini",
                    available=False,
                    required=True,
                    message="Invalid API key. Check your GOOGLE_API_KEY.",
                )
            else:
                return ToolCheck(
                    name="gemini",
                    available=False,
                    required=True,
                    message=f"Gemini API connection failed: {error_msg}",
                )

    def check_bedrock(self, model: str = "anthropic.claude-3-haiku-20240307-v1:0") -> ToolCheck:
        """Check if AWS Bedrock is available and accessible.

        Performs an actual API call to verify:
        1. AWS credentials are valid
        2. Bedrock service is accessible
        3. The specified model is available

        Args:
            model: Bedrock model ID to test with

        Returns:
            ToolCheck result
        """
        import os

        # First check if credentials are configured
        has_env_key = bool(os.environ.get("AWS_ACCESS_KEY_ID"))
        has_env_secret = bool(os.environ.get("AWS_SECRET_ACCESS_KEY"))
        aws_profile = os.environ.get("AWS_PROFILE")
        credentials_path = Path.home() / ".aws" / "credentials"

        has_file_creds = False
        if credentials_path.exists():
            try:
                content = credentials_path.read_text()
                has_file_creds = "[default]" in content or (
                    aws_profile and f"[{aws_profile}]" in content
                )
            except OSError:
                pass

        if not (has_env_key and has_env_secret) and not has_file_creds:
            return ToolCheck(
                name="bedrock",
                available=False,
                required=True,
                message=(
                    "AWS credentials required. Configure via:\n"
                    "  - Environment: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY\n"
                    "  - Credentials file: ~/.aws/credentials\n"
                    "  - IAM role (when running on AWS)"
                ),
            )

        # Credentials exist - now test actual connectivity
        region = os.environ.get(
            "AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        )

        try:
            import litellm

            # Make a minimal API call to verify connectivity
            # Using a very small prompt to minimize cost
            response = litellm.completion(
                model=f"bedrock/{model}",
                messages=[{"role": "user", "content": "Say ok"}],
                max_tokens=5,
                temperature=0,
            )

            # If we get here, Bedrock is working
            creds_source = "env vars" if (has_env_key and has_env_secret) else f"profile: {aws_profile or 'default'}"
            return ToolCheck(
                name="bedrock",
                available=True,
                required=True,
                message=f"AWS Bedrock verified (region: {region}, credentials: {creds_source})",
            )

        except ImportError:
            return ToolCheck(
                name="bedrock",
                available=False,
                required=True,
                message="LiteLLM not installed. Install with: pip install litellm",
            )

        except Exception as e:
            error_msg = str(e)

            # Provide helpful error messages based on common issues
            if "botocore" in error_msg or "boto3" in error_msg:
                return ToolCheck(
                    name="bedrock",
                    available=False,
                    required=True,
                    message=(
                        "AWS SDK not installed. Install with: pip install boto3\n"
                        "  (boto3 includes botocore, required for AWS Bedrock)"
                    ),
                )
            elif "AccessDeniedException" in error_msg:
                return ToolCheck(
                    name="bedrock",
                    available=False,
                    required=True,
                    message=(
                        f"AWS Bedrock access denied (region: {region}). "
                        "Ensure your IAM user/role has bedrock:InvokeModel permission "
                        f"and model {model} is enabled in your AWS account."
                    ),
                )
            elif "UnrecognizedClientException" in error_msg or "InvalidSignature" in error_msg:
                return ToolCheck(
                    name="bedrock",
                    available=False,
                    required=True,
                    message=(
                        f"AWS credentials invalid (region: {region}). "
                        "Verify AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are correct."
                    ),
                )
            elif "ResourceNotFoundException" in error_msg or "model" in error_msg.lower():
                return ToolCheck(
                    name="bedrock",
                    available=False,
                    required=True,
                    message=(
                        f"Bedrock model '{model}' not available in region {region}. "
                        "Enable the model in AWS Bedrock console or use a different region."
                    ),
                )
            elif "ExpiredToken" in error_msg:
                return ToolCheck(
                    name="bedrock",
                    available=False,
                    required=True,
                    message=(
                        "AWS session token expired. "
                        "Refresh your credentials with 'aws sso login' or regenerate temporary credentials."
                    ),
                )
            else:
                return ToolCheck(
                    name="bedrock",
                    available=False,
                    required=True,
                    message=f"AWS Bedrock connection failed: {error_msg}",
                )

    def check_terraform_files(self, repo_path: Path) -> bool:
        """Check if repository contains Terraform files.

        Args:
            repo_path: Path to repository

        Returns:
            True if Terraform files exist
        """
        return any(repo_path.glob("**/*.tf"))

    def check_all(
        self,
        repo_path: Path | None = None,
        sbom_tool: str = "syft",
        diagram_tool: str = "terravision",
        code_packager: str = "repomix",
        llm_provider: str = "ollama",
        llm_api_key: str | None = None,
        llm_api_base: str | None = None,
        llm_model: str | None = None,
        skip_sbom: bool = False,
        skip_architecture: bool = False,
        skip_ast: bool = False,
        skip_llm: bool = False,
        skip_repomix: bool = False,
    ) -> PreflightResult:
        """Run all preflight checks.

        Per Principle III: Preflight Validation, all required dependencies must
        be validated before analysis begins. No fallbacks are provided.

        Args:
            repo_path: Repository path (for context-aware checks)
            sbom_tool: Configured SBOM tool
            diagram_tool: Configured diagram tool
            code_packager: Configured codebase compression tool (repomix)
            llm_provider: LLM provider (ollama, claude, gemini, bedrock)
            llm_api_key: API key for cloud LLM providers
            llm_api_base: API base URL for Ollama
            llm_model: LLM model to test with
            skip_sbom: Whether SBOM generation will be skipped
            skip_architecture: Whether architecture analysis will be skipped
            skip_ast: Whether AST analysis will be skipped
            skip_llm: Whether LLM validation will be skipped
            skip_repomix: Whether Repomix compression will be skipped

        Returns:
            PreflightResult with all check results
        """
        result = PreflightResult()

        # Git is always required
        result.add_check(self.check_git(required=True))

        # tree-sitter is required for AST parsing (no fallback)
        if not skip_ast:
            result.add_check(self.check_tree_sitter(required=True))

        # SBOM tool
        if not skip_sbom and sbom_tool == "syft":
            result.add_check(self.check_syft(required=True))

        # Repomix for codebase compression (required for holistic LLM analysis)
        if not skip_repomix:
            result.add_check(self.check_repomix(required=True))

        # Diagram tool - always required unless explicitly skipped
        if not skip_architecture:
            if diagram_tool == "terravision":
                result.add_check(self.check_terravision(required=True))
                result.add_check(self.check_graphviz(required=True))

        # LLM - required for generating documentation summaries
        # Uses LiteLLM as unified interface (per research.md)
        if not skip_llm:
            # First check LiteLLM package is installed
            result.add_check(self.check_litellm(required=True))

            # Then check provider-specific requirements with actual connectivity test
            result.add_check(
                self.check_llm_provider(
                    provider=llm_provider,
                    api_key=llm_api_key,
                    api_base=llm_api_base,
                    model=llm_model,
                )
            )

        return result
