# CLI Contract: chronicle

**Date**: 2026-01-31
**Branch**: `001-system-doc-generator`

## Command Structure

```
chronicle [OPTIONS] COMMAND [ARGS]
```

## Global Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--config`, `-c` | PATH | None | Path to configuration file |
| `--verbose`, `-v` | FLAG | false | Enable verbose output |
| `--quiet`, `-q` | FLAG | false | Suppress non-error output |
| `--version` | FLAG | - | Show version and exit |
| `--help` | FLAG | - | Show help and exit |

---

## Commands

### `chronicle write`

Write system documentation for a repository.

```
chronicle write [OPTIONS] [REPOSITORY]
```

#### Arguments

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `REPOSITORY` | PATH | No | `.` | Path to repository to analyze |

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--output`, `-o` | PATH | from config | Output file path (overrides config for this run) |
| `--format`, `-f` | CHOICE | from config | Output format (overrides config for this run) |
| `--ci` | FLAG | false | CI/CD mode (no prompts, strict exit codes) |

> **Design Note**: All configuration (tools, LLM, human content) is in YAML. The tool auto-detects what to analyze based on repository contents. Missing tools produce warnings, not errors.

#### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success - documentation written |
| 1 | Error - fatal failure, no documentation produced |
| 2 | Warning - documentation written with warnings |

#### Examples

```bash
# Write docs using settings from .chronicle/config.yaml
chronicle write

# Override output path for this run
chronicle write --output ./docs/architecture.md

# CI/CD mode (uses config.yaml for all settings)
chronicle write --ci
```

---

### `chronicle check`

Verify external tool availability and configuration.

```
chronicle check [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--json` | FLAG | false | Output as JSON |

#### Output (JSON mode)

```json
{
  "syft": {
    "available": true,
    "version": "1.0.0",
    "path": "/usr/local/bin/syft"
  },
  "terravision": {
    "available": true,
    "version": "2.0.0",
    "path": "/usr/local/bin/terravision"
  },
  "git": {
    "available": true,
    "version": "2.43.0",
    "path": "/usr/bin/git"
  },
  "graphviz": {
    "available": true,
    "version": "9.0.0",
    "path": "/usr/local/bin/dot"
  }
}
```

#### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All required tools available |
| 1 | One or more required tools missing |

---

### `chronicle init`

Initialize chronicle configuration for a repository with interactive LLM provider setup.

```
chronicle init [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--force` | FLAG | false | Overwrite existing config |
| `--non-interactive` | FLAG | false | Skip interactive prompts, use defaults |

#### Interactive Flow

When run interactively (default), the command prompts:

1. **LLM Provider Selection**: User must choose Ollama, Claude, Gemini, or AWS Bedrock (no default)
2. **Credential Input**: Provider-specific credentials (API key or AWS credentials)
3. **Connectivity Test**: Validates provider connectivity/credentials
4. **Configuration Save**: Writes settings to `.chronicle/config.yaml`

```
$ chronicle init

Initializing chronicle configuration...

Select LLM provider:
  [1] Ollama (local - no data leaves machine)
  [2] Claude (Anthropic API)
  [3] Gemini (Google API)
  [4] AWS Bedrock
Choice: 4

AWS Bedrock requires AWS credentials configured via:
  - Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
  - AWS credentials file (~/.aws/credentials)
  - IAM role (when running on AWS)

Enter AWS region [us-east-1]: us-west-2
Enter Bedrock model ID [anthropic.claude-3-sonnet-20240229-v1:0]:
✓ AWS credentials detected

Created .chronicle/config.yaml
LLM provider: claude (claude-3-5-sonnet-20241022)

Run 'chronicle check' to verify all dependencies.
```

#### Behavior

Creates `.chronicle/config.yaml` with:
- Selected LLM provider and credentials
- Default output settings (./docs/system.md, markdown format)
- Default tool configuration (syft, terravision)

With `--non-interactive`, requires `--provider` flag or `chronicle_LLM_PROVIDER` environment variable (no default).

---

### `chronicle validate`

Validate a documentation template.

```
chronicle validate TEMPLATE
```

#### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `TEMPLATE` | PATH | Yes | Path to Jinja2 template file |

#### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Template is valid |
| 1 | Template has syntax errors |
| 2 | Template uses unsupported placeholders |

---

## Configuration File Schema

### chronicle.yaml

```yaml
# Output settings
output:
  path: "./docs/system.md"     # Output file path
  format: "markdown"           # markdown | html | confluence

# Template settings (optional)
template:
  path: null                   # Custom Jinja2 template path

# Tool selection (Principle V: Tool Agnosticism)
tools:
  sbom: "syft"                 # syft | trivy (auto-skipped if no dependency files)
  diagrams: "terravision"      # terravision (auto-skipped if no Terraform files)

# Human content sections (Principle VI: Human Annotation Persistence)
# Reference markdown files to merge with generated content
sections:
  overview:
    file: ".chronicle/sections/overview.md"
    strategy: "prepend"        # prepend | append | replace
  security:
    file: ".chronicle/sections/security.md"
    strategy: "append"

# LLM settings (optional - works without LLM)
llm:
  provider: "claude"           # claude | gemini | ollama | bedrock
  model: "claude-3-5-sonnet-20241022"
  api_key: "${ANTHROPIC_API_KEY}"
  temperature: 0               # Must be 0 for reproducibility
  # For AWS Bedrock:
  # provider: "bedrock"
  # model: "anthropic.claude-3-sonnet-20240229-v1:0"
  # aws_region: "us-east-1"   # Uses AWS credentials from env/profile

# CI/CD settings
ci:
  fail_on_warnings: false      # Exit code 1 for warnings
```

---

## Environment Variables

| Variable | Description | Used By |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Claude API key | LLM (claude) |
| `GOOGLE_API_KEY` | Gemini API key | LLM (gemini) |
| `OLLAMA_HOST` | Ollama API base URL | LLM (ollama) |
| `AWS_ACCESS_KEY_ID` | AWS access key for Bedrock | LLM (bedrock) |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key for Bedrock | LLM (bedrock) |
| `AWS_REGION` | AWS region for Bedrock (default: us-east-1) | LLM (bedrock) |
| `AWS_PROFILE` | AWS profile name (alternative to keys) | LLM (bedrock) |
| `CI` | Set to "true" in CI environments | Auto-enable CI mode |
| `chronicle_CONFIG` | Override config file path | Configuration loading |

---

## Output Formats

### Markdown (default)

Standard GitHub-flavored Markdown suitable for repository documentation.

### HTML

Self-contained HTML file with embedded styles, suitable for SharePoint or static hosting.

### Confluence

Confluence Storage Format (XHTML) compatible with Confluence REST API import.

---

## Error Output (stderr)

All errors are written to stderr in the following format:

```
[ERROR] Component: Message
[WARN] Component: Message
[INFO] Component: Message (only with --verbose)
```

In JSON mode (`--json` where applicable), errors are structured:

```json
{
  "level": "error",
  "component": "syft",
  "message": "Failed to generate SBOM",
  "details": "Command exited with code 1"
}
```
