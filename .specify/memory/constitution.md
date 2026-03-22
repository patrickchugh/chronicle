<!--
  SYNC IMPACT REPORT
  ==================
  Version change: 1.3.0 → 1.4.0 (LLM required, user must select provider)

  Modified principles:
  - I. Deterministic-First: LLM is REQUIRED. User must select provider during chronicle init (no default).
  - III. Preflight Validation: LLM provider must be configured via chronicle init before use.

  Added principles: None

  Added sections: None
  Removed sections: None

  Quality Gates added:
  - LLM Required: LLM must be available and produce valid summaries

  Templates validated:
  - .specify/templates/plan-template.md ✅ (Constitution Check section compatible)
  - .specify/templates/spec-template.md ✅ (no constitution-specific requirements)
  - .specify/templates/tasks-template.md ✅ (no constitution-specific requirements)

  Dependent artifacts to update:
  - specs/001-system-doc-generator/spec.md ✅ (LLM assumptions updated, no default)
  - specs/001-system-doc-generator/tasks.md ✅ (LLM in Phase 2 foundational)
  - specs/001-system-doc-generator/contracts/cli.md ✅ (chronicle init requires provider selection)
  - src/chronicle/config.py (LLM provider must be configured, no default)
  - src/chronicle/utils/preflight.py ✅ (LLM check added)

  Follow-up TODOs: None - all artifacts aligned
-->

# chronicle Constitution

## Core Principles

### I. Deterministic-First

All analysis MUST be performed using deterministic methods before any LLM invocation.

- Source code analysis via AST parsing MUST precede LLM summarization
- Dependency scanning via Syft MUST complete before LLM processing
- Infrastructure diagrams via Terravision MUST be generated before LLM descriptions
- LLM is REQUIRED for generating human-readable documentation summaries (deterministic analysis produces structured data, LLM produces prose)
- LLM transforms deterministic data into readable documentation; it never replaces the underlying analysis
- If deterministic analysis fails for a component, that failure MUST be documented in output rather than masked by LLM-generated content
- LLM provider must be selected during `chronicle init` (Ollama, Claude, Gemini, or AWS Bedrock). No default - user must explicitly choose based on their security and infrastructure requirements

**Rationale**: Deterministic analysis is auditable, reproducible, and verifiable. LLM output cannot be independently verified without the underlying deterministic data. Ollama option enables security-conscious enterprises to use chronicle without sending code to external services.

### II. Reproducibility

Given the same input repository state, chronicle MUST produce semantically identical output.

- All LLM calls MUST use `temperature=0` and other appropriate deterministic hyperparameters e.g. Top K etc
- Output documents MUST include version history with timestamps, git refs, and author attribution
- Minor variations in punctuation or filler words (the, an, a) are acceptable; meaning MUST be identical
- External tool versions SHOULD be captured in output metadata to explain any future differences
- No randomness or non-deterministic operations in the analysis pipeline

**Rationale**: Enterprise audit requires documentation that can be verified and compared across runs. Stakeholders must trust that changes in documentation reflect actual system changes.

### III. Preflight Validation

All external dependencies MUST be validated before analysis begins, not during processing.

- The `chronicle check` command MUST verify availability of ALL required tools:
  - git (version control)
  - tree-sitter + tree-sitter-language-pack (AST parsing)
  - Syft (SBOM generation)
  - Terravision + Graphviz (architecture diagrams)
  - LiteLLM (unified LLM interface)
  - LLM provider configured via `chronicle init`: Ollama (local server), Claude/Gemini (API key), or Bedrock (AWS credentials)
- Missing required tools MUST cause immediate exit with clear error message and installation instructions
- LLM is REQUIRED: User must configure provider via `chronicle init`. Ollama requires local server, Claude/Gemini require API keys, Bedrock requires AWS credentials
- No partial documentation: either all prerequisites pass and full docs are generated, or processing fails fast
- Users can skip specific analyzers via CLI flags (--skip-sbom, --skip-architecture) if tools are unavailable

**Rationale**: CI/CD pipelines require predictable behavior. Discovering a missing tool mid-analysis wastes resources and produces incomplete artifacts.

### IV. CI/CD Compatibility

chronicle MUST operate as a well-behaved CLI tool in automated environments.

- No interactive prompts: all configuration via CLI args, config files, or environment variables
- Exit codes MUST be meaningful: 0 = success, 1 = error, 2 = warnings
- All user-facing output MUST go to stdout; all errors and diagnostics MUST go to stderr
- JSON output mode MUST be available for machine parsing
- Timeout handling: long-running operations MUST respect configurable timeouts
- Environment variable substitution MUST be supported in config files (e.g., `${ANTHROPIC_API_KEY}`)

**Rationale**: chronicle runs unattended in CI/CD pipelines. It must integrate cleanly with existing automation infrastructure without special handling.

### V. Tool Agnosticism

chronicle MUST support pluggable tools for each analysis capability, enabling users to swap implementations.

- Each analysis capability (SBOM, diagrams, AST parsing) MUST be abstracted behind a common interface
- Tool configuration MUST be explicit in config files, not hardcoded (e.g., `sbom_tool: syft` or `sbom_tool: trivy`)
- Default tools SHOULD be provided, but alternatives MUST be configurable
- New tool integrations MUST implement the same interface as existing tools for that capability
- Tool-specific code MUST be isolated in adapter modules, not scattered throughout the codebase
- Multi-cloud support: infrastructure analyzers MUST NOT assume a single cloud provider
- **Canonical Data Formats**: All tool adapters MUST transform tool-specific output into canonical internal formats (`CanonicalSBOM`, `CanonicalArchitecture`, `CanonicalAST`)
- The rest of the codebase MUST only consume canonical formats, never tool-specific output
- Adding a new tool MUST NOT require changes outside the adapter module

**Rationale**: Enterprise environments have diverse toolchains. Mandating specific tools creates adoption friction. Canonical internal formats ensure that swapping tools requires only a new adapter—no changes to renderers, templates, or other components.

### VI. Human Annotation Persistence

User-provided content MUST be mergeable with generated documentation.

- Human sections MUST be defined in YAML config referencing markdown files
- Human markdown files (`.chronicle/sections/*.md`) MUST be merged with generated content
- Merge strategies (prepend, append, replace) MUST be configurable per section
- Human content files MUST NOT be modified by chronicle—they are user-owned
- Version history MUST distinguish between human-authored and chronicle-generated changes
- If a referenced section file is missing, chronicle MUST warn and continue without it

**Rationale**: Documentation often requires human insight that cannot be derived from code analysis. File-based sections keep human content cleanly separated and easy to edit.

## Quality Gates

These gates apply to all implementations and MUST be checked before merging:

| Gate | Requirement | Enforcement |
|------|-------------|-------------|
| Deterministic Analysis | All new analyzers MUST produce identical output for identical input | Unit test with fixture comparison |
| Preflight Check | New external dependencies MUST be added to `chronicle check` | Integration test verifies check coverage |
| Exit Codes | All error paths MUST set appropriate exit codes | CLI integration tests |
| No Interactive Prompts | All user input MUST come from args/config/env | CI test runs with `--ci` flag |
| Reproducibility | Two consecutive runs on same repo MUST produce semantically identical output | Integration test with diff analysis |
| Tool Abstraction | New tool integrations MUST implement capability interface | Interface compliance tests |
| Canonical Format Compliance | All adapters MUST output validated canonical types; no tool-specific data escapes adapters | Unit tests verify schema conformance |
| LLM Required | LLM provider must be configured via `chronicle init` and produce valid summaries | Preflight check + integration test |
| Section Merging | Human sections from config MUST merge correctly with generated content | Integration test with section files |

## Development Workflow

### Code Review Requirements

- All PRs MUST include verification that changes comply with Core Principles
- New analyzers MUST include deterministic output tests
- New CLI options MUST include `--ci` mode compatibility verification
- External tool integrations MUST include preflight check additions
- New tool integrations MUST implement the standard capability interface and output canonical formats
- New tool adapters MUST NOT expose tool-specific data structures outside the adapter module
- Changes affecting templates MUST verify human content preservation

### Testing Requirements

- Unit tests for all analyzers with fixture-based comparison
- Integration tests for CLI commands with exit code verification
- Reproducibility tests comparing consecutive runs
- CI mode tests ensuring no interactive prompts
- Interface compliance tests for tool adapters
- Canonical format schema validation tests for all adapter outputs
- Human content merge tests with conflict detection

## Governance

This constitution supersedes all other development practices for the chronicle project.

- **Amendments**: Changes to Core Principles require documentation of rationale and migration plan
- **Compliance**: All PRs and code reviews MUST verify adherence to Core Principles
- **Violations**: Any deviation from MUST requirements requires explicit justification in Complexity Tracking section of plan.md
- **Version Control**: Constitution changes follow semantic versioning (MAJOR.MINOR.PATCH)

**Version**: 1.4.0 | **Ratified**: 2026-01-31 | **Last Amended**: 2026-02-01
