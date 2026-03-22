# Quickstart: chronicle

**Date**: 2026-01-31
**Branch**: `001-system-doc-generator`

## Prerequisites

### Required

- Python 3.11+
- Git

### Optional (for full functionality)

- **Syft** - SBOM generation ([install guide](https://github.com/anchore/syft#installation))
- **Terravision** - Terraform diagrams ([install guide](https://github.com/patrickchugh/terravision))
- **Graphviz** - Required by Terravision for diagram rendering

### LLM Backend (choose one, optional)

- **Claude**: Requires `ANTHROPIC_API_KEY`
- **Gemini**: Requires `GOOGLE_API_KEY`
- **Ollama**: Local installation at http://localhost:11434

---

## Installation

```bash
# Install from PyPI (when published)
pip install chronicle

# Or install from source
git clone https://github.com/your-org/chronicle.git
cd chronicle
pip install -e .
```

---

## Basic Usage

### 1. Initialize configuration

```bash
cd /path/to/your/repo
chronicle init
```

This creates `.chronicle/config.yaml` with default settings.

### 2. Write documentation

```bash
chronicle write
```

Output: `./docs/system.md` (or as configured in YAML)

### 3. Write in CI/CD

```bash
chronicle write --ci
```

All settings (LLM, tools, output path) come from `.chronicle/config.yaml`.

---

## Verify Tool Availability

```bash
chronicle check
```

Example output:
```
✓ git: 2.43.0
✓ syft: 1.0.0
✓ terravision: 2.0.0
✓ graphviz: 9.0.0

All tools available. Ready to generate documentation.
```

---

## Configuration

All settings are managed in `.chronicle/config.yaml`. CLI flags are minimal and only for per-run overrides.

### Initialize configuration file

```bash
chronicle init
```

Creates `.chronicle/config.yaml` with default settings.

### Example configuration

```yaml
# Output settings
output:
  path: "./docs/system.md"
  format: "markdown"

# Tool selection (auto-skipped if not applicable)
tools:
  sbom: "syft"              # or: trivy
  diagrams: "terravision"   # default

# Human content sections (Principle VI)
# Add your own content to merge with generated docs
sections:
  overview:
    file: ".chronicle/sections/overview.md"
    strategy: "prepend"     # prepend | append | replace
  security:
    file: ".chronicle/sections/security.md"
    strategy: "append"

# LLM settings (optional - works without LLM)
llm:
  provider: "claude"         # or: gemini, ollama, bedrock
  model: "claude-3-5-sonnet-20241022"
  api_key: "${ANTHROPIC_API_KEY}"
  temperature: 0             # required for reproducibility
```

---

## Custom Templates

### Use a custom Jinja2 template

Add to `.chronicle/config.yaml`:

```yaml
template:
  path: "./my-template.md.j2"
```

Then run `chronicle write` as usual.

### Available template variables

| Variable | Type | Description |
|----------|------|-------------|
| `repository` | object | Repository metadata |
| `technology_stack` | object | Languages, frameworks, dependencies |
| `sbom` | object | Software Bill of Materials |
| `architecture_diagram` | object | Terraform diagram info |
| `source_analysis` | object | Code structure analysis (functions, classes, with explanations) |
| `llm_summaries` | object | LLM-generated section content |
| `function_explanations` | object | LLM-generated function behavior descriptions |
| `sections` | object | Human content for merging |
| `version_history` | list | Document version history |
| `generated_at` | datetime | Generation timestamp |

See the [Template Contract](contracts/template.md) for full variable documentation and default section structure.

---

## CI/CD Integration

Configuration is committed to the repo in `.chronicle/config.yaml`. CI just runs `chronicle write --ci`.

### GitHub Actions

```yaml
name: Write Documentation
on:
  push:
    branches: [main]

jobs:
  docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install chronicle
        run: pip install chronicle

      - name: Install Syft
        run: |
          curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin

      - name: Write documentation
        run: chronicle write --ci
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

      - name: Commit documentation
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add docs/
          git diff --staged --quiet || git commit -m "docs: update system documentation"
          git push
```

### GitLab CI

```yaml
write-docs:
  image: python:3.11
  script:
    - pip install chronicle
    - chronicle write --ci
  artifacts:
    paths:
      - docs/
  only:
    - main
```

---

## Troubleshooting

### "Syft not found" warning

chronicle continues without SBOM. Install Syft for dependency scanning:
```bash
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
```

### "Terravision not found" warning

chronicle continues without architecture diagrams. Install Terravision if you have Terraform files:
```bash
pip install terravision
```

### "LLM request failed"

Documentation is written with placeholder text for LLM sections. Check your API key and network connectivity. chronicle works without LLM—you'll just get deterministic analysis only.

### Large repository performance

For repositories over 100k lines, use verbose mode to monitor progress:
```bash
chronicle write --verbose
```

---

## Next Steps

- Read the [CLI Reference](contracts/cli.md) for all commands and options
- Review the [Template Contract](contracts/template.md) for default sections and variables
- Review the [Data Model](data-model.md) to understand output structure
- Customize the default template for your organization's standards
