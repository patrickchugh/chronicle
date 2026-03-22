# Implementation Plan: chronicle - Automated System Documentation Generator

**Branch**: `001-system-doc-generator` | **Date**: 2026-01-31 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-chronicle-system-doc-generator/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

chronicle is an automated system documentation generator for enterprise IT audit, architecture, security, and business stakeholders. It runs in CI/CD pipelines, performing deterministic analysis first (AST parsing, Syft SBOM, Terravision diagrams), then using LLM to fill gaps and summarize sections into a Jinja2 template. Output must be reproducible across runs.

## Technical Context

**Language/Version**: Python 3.11+ (primary language for CLI, AST parsing, LLM integration)
**Primary Dependencies**:
- CLI: Typer + typer-config (type-safe CLI with config file support)
- AST Parsing: tree-sitter + tree-sitter-language-pack (multi-language support)
- Templating: Jinja2
- LLM: litellm (unified interface for Claude, Gemini, Ollama)
- External Tools: Syft (SBOM), Terravision (Terraform diagrams)

**Storage**: N/A (file-based I/O only, reads repository, writes documentation)
**Testing**: pytest with fixtures for repository mocking
**Target Platform**: Linux/macOS CI/CD environments (GitHub Actions, GitLab CI, Jenkins)
**Project Type**: Single CLI application
**Performance Goals**: Complete analysis of 100k LOC repository within 5 minutes (SC-001)
**Constraints**: Memory-efficient incremental processing for large repos, no interactive prompts
**Scale/Scope**: Single repository analysis per invocation, supports Python/JavaScript/Go/Java

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: ✅ PASS

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Deterministic-First | ✅ | Analyzers module runs before LLM module; LLM is supplementary |
| II. Reproducibility | ✅ | LLM config enforces temperature=0; VersionEntry tracks all changes |
| III. Preflight Validation | ✅ | `utils/preflight.py` validates tools before `chronicle write` proceeds |
| IV. CI/CD Compatibility | ✅ | No interactive prompts; exit codes 0/1/2; JSON output mode; env var support |
| V. Tool Agnosticism | ✅ | Adapters output canonical formats (`models/canonical/`); tools swappable via config |
| VI. Human Annotation Persistence | ✅ | `.chronicle/sections/` stores human markdown files; merge on regeneration |

**Quality Gates Alignment:**
- Deterministic Analysis: Unit tests with fixture comparison planned in `tests/unit/test_analyzers.py`
- Preflight Check: `chronicle check` command validates all external tools
- Exit Codes: CLI contract defines 0=success, 1=error, 2=warning
- Reproducibility: Integration test for consecutive run comparison in `tests/integration/test_full_pipeline.py`
- Canonical Format Compliance: All adapters must output validated canonical types; unit tests verify schema conformance
- Tool Abstraction: Interface compliance tests for analyzer adapters; new tools only need adapter implementation
- Human Content Merge: Integration test with human content fixtures in `tests/integration/test_sections.py`

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/chronicle/
├── __init__.py
├── __main__.py          # Entry point for python -m chronicle
├── cli.py               # CLI interface (Typer)
├── config.py            # Configuration loading and validation
├── models/
│   ├── __init__.py
│   ├── repository.py    # Repository entity
│   ├── analysis.py      # AnalysisResult entity
│   ├── template.py      # DocumentationTemplate entity
│   ├── llm_config.py    # LLMConfiguration entity
│   └── canonical/       # Canonical data formats (Principle V)
│       ├── __init__.py  # Exports all canonical types
│       ├── sbom.py      # CanonicalSBOM, CanonicalPackage, SBOMSource
│       ├── architecture.py  # CanonicalArchitecture, CanonicalGraph, NodeMetadata
│       └── ast.py       # CanonicalAST, CanonicalModule, CanonicalClass, etc.
├── analyzers/
│   ├── __init__.py
│   ├── base.py          # Abstract base interfaces (Principle V: Tool Agnosticism)
│   ├── registry.py      # Tool registry for pluggable analyzers
│   ├── ast_parser.py    # Multi-language AST parsing via tree-sitter
│   ├── dependency.py    # Dependency file parsing
│   ├── sbom/            # SBOM tool adapters (Principle V)
│   │   ├── __init__.py
│   │   ├── base.py      # SBOMAnalyzer interface
│   │   └── syft.py      # Syft adapter (default)
│   └── diagrams/        # Diagram tool adapters (Principle V)
│       ├── __init__.py
│       ├── base.py      # DiagramGenerator interface
│       └── terravision.py  # Terravision adapter (default)
├── llm/
│   ├── __init__.py
│   ├── client.py        # Unified LLM client via litellm
│   └── prompts.py       # Prompt templates for summaries
├── renderers/
│   ├── __init__.py
│   ├── jinja.py         # Jinja2 template rendering
│   ├── formats.py       # Output format converters (MD, HTML, Confluence)
│   └── sections.py      # Human section merger (Principle VI)
└── utils/
    ├── __init__.py
    ├── preflight.py     # External tool availability checks
    └── version.py       # Version history tracking

.chronicle/                 # User configuration directory
├── config.yaml          # All configuration (tools, LLM, sections)
└── sections/            # Human-authored content (Principle VI)
    ├── overview.md      # Merged with generated overview
    └── security.md      # Merged with generated security section

tests/
├── conftest.py          # Shared fixtures
├── unit/
│   ├── test_analyzers.py
│   ├── test_llm.py
│   └── test_renderers.py
├── integration/
│   ├── test_cli.py
│   ├── test_full_pipeline.py
│   └── test_sections.py     # Human section merging
└── fixtures/
    ├── sample_repos/        # Mock repositories for testing
    └── sections/            # Sample human section files
```

**Structure Decision**: Single CLI application structure. The `src/chronicle/` package contains all application code with clear separation between analyzers (deterministic), LLM integration, and renderers. Tests mirror the source structure with fixtures for mock repositories.

## Complexity Tracking

> **No constitution violations identified.** Structure follows single-project pattern.
