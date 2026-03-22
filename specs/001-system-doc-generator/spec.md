# Feature Specification: chronicle - Automated System Documentation Generator

**Feature Branch**: `001-chronicle-system-doc-generator`
**Created**: 2026-01-31
**Status**: Draft
**Input**: User description: "Create an automated system documentation generator for Enterprise IT audit, architecture, security and business stakeholders. chronicle runs in CI/CD pipelines to ensure documentation stays current as systems change. Uses deterministic analysis first (source code, Terraform, dependencies), then LLM to fill gaps and summarize sections in a template."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate Documentation from Repository (Priority: P1)

A DevOps engineer runs chronicle as part of their CI/CD pipeline to automatically generate up-to-date system documentation whenever code changes are merged.

**Why this priority**: This is the core value proposition - automatically generating documentation that stays current with system changes, eliminating manual documentation maintenance.

**Independent Test**: Can be fully tested by pointing chronicle at a sample repository and verifying it produces a complete documentation file with all detected components.

**Acceptance Scenarios**:

1. **Given** a git repository with source code, **When** the user runs chronicle CLI, **Then** a documentation file is generated containing detected components
2. **Given** a repository with Terraform files, **When** chronicle runs, **Then** the documentation includes cloud architecture diagrams
3. **Given** a repository with dependency files (package.json, requirements.txt, go.mod), **When** chronicle runs, **Then** the documentation includes a technology stack section
4. **Given** no LLM configuration is provided, **When** chronicle runs, **Then** deterministic analysis still produces useful documentation with placeholder summaries

---

### User Story 2 - Review Documentation for Audit Compliance (Priority: P2)

An IT auditor receives automatically generated system documentation that accurately describes the system architecture, dependencies, and technology stack to assess compliance.

**Why this priority**: Audit readiness is a primary enterprise use case that validates the accuracy and completeness of generated documentation.

**Independent Test**: Can be tested by generating documentation for a known system and verifying all security-relevant components (dependencies, infrastructure) are accurately documented.

**Acceptance Scenarios**:

1. **Given** generated documentation, **When** an auditor reviews it, **Then** all third-party dependencies are listed with version numbers
2. **Given** a system with cloud infrastructure, **When** documentation is generated, **Then** the architecture diagram accurately reflects the deployed resources
3. **Given** the same repository analyzed twice, **When** no changes occurred, **Then** the generated documentation is identical (reproducibility)

---

### User Story 3 - Configure LLM Backend for Summaries (Priority: P3) - IMPLEMENTED IN FOUNDATION

> **Note**: This user story is addressed by foundational Phase 2 infrastructure (tasks T023e-T023j) via LiteLLM unified interface. User must select their LLM provider (Ollama, Claude, Gemini, or Bedrock) during `chronicle init` - there is no default provider.

A security-conscious enterprise configures chronicle to use a local LLM (Ollama) to ensure no source code is sent to external services while still getting intelligent summaries.

**Why this priority**: Enterprise security requirements often mandate local processing, making LLM backend flexibility essential for adoption.

**Independent Test**: Can be tested by configuring different LLM backends and verifying summaries are generated without external network calls when using local LLM.

**Implementation Status**: Complete via LiteLLM in `src/chronicle/llm/client.py` with preflight validation in `src/chronicle/utils/preflight.py`.

**Acceptance Scenarios**:

1. **Given** chronicle configured with Ollama, **When** documentation is generated, **Then** no network requests are made to external LLM services
2. **Given** chronicle configured with Claude API, **When** documentation is generated, **Then** LLM summaries use the Claude service
3. **Given** chronicle configured with Gemini API, **When** documentation is generated, **Then** LLM summaries use the Gemini service
4. **Given** chronicle configured with AWS Bedrock, **When** documentation is generated, **Then** LLM summaries use the Bedrock service with detected AWS credentials
5. **Given** invalid LLM configuration, **When** chronicle runs, **Then** a clear error message indicates the configuration issue

---

### User Story 4 - Customize Documentation Template (Priority: P4)

A technical writer customizes the documentation template to match their organization's documentation standards before running chronicle.

**Why this priority**: Template customization enables enterprises to align generated documentation with their existing documentation standards.

**Independent Test**: Can be tested by providing a custom Jinja2 template and verifying the output matches the template structure.

**Acceptance Scenarios**:

1. **Given** a custom Jinja2 template, **When** chronicle runs, **Then** output follows the custom template structure
2. **Given** the default template, **When** chronicle runs, **Then** output follows the built-in template with all standard sections
3. **Given** a template with unsupported placeholders, **When** chronicle runs, **Then** unsupported placeholders remain visible with warnings

---

### User Story 5 - Export to Multiple Formats (Priority: P5)

A documentation manager exports generated documentation to different formats to publish on Confluence and SharePoint.

**Why this priority**: Multi-format export enables integration with existing enterprise documentation systems.

**Independent Test**: Can be tested by generating documentation and requesting different output formats, verifying each format is valid.

**Acceptance Scenarios**:

1. **Given** documentation content, **When** user requests Markdown output, **Then** valid Markdown file is produced
2. **Given** documentation content, **When** user requests Confluence-compatible format, **Then** output can be imported to Confluence
3. **Given** documentation content, **When** user requests HTML output, **Then** valid HTML file suitable for SharePoint is produced

---

### Edge Cases

- What happens when the repository contains no recognizable source code or dependency files? System produces minimal documentation with warning indicating no analyzable content found
- What happens when the user wants to augment the generated document to add clarity or insight? Human content is stored in separate markdown files (`.chronicle/sections/*.md`) referenced in config, merged with generated content using prepend/append/replace strategies per section
- What happens when the human input content conflicts with what the LLM summary states? User should be alerted of meaningful differences and told to address the conflicts before generating final document
- How does the system handle corrupted or invalid dependency files? System skips invalid files with warnings, continues processing valid files
- What happens when Terraform parsing fails? System logs error, continues without architecture diagram, notes absence in documentation
- How does the system handle very large repositories? System processes incrementally without running out of memory, with progress indication
- What happens when the LLM service is unavailable? Preflight check fails with clear error message and installation instructions. LLM is required for generating documentation summaries (provider configured via `chronicle init`)
- How does the system handle binary files or non-text content? System skips binary files automatically without error
- What happens when source code contains syntax errors? System uses best-effort parsing, notes parsing issues in output without failing

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a command-line interface executable from CI/CD pipelines
- **FR-002**: System MUST read and analyze files from a local git repository
- **FR-003**: System MUST parse source code files using AST parsing for Python, JavaScript, TypeScript, Go, and Java
- **FR-004**: System MUST detect and parse dependency files (package.json, requirements.txt, go.mod, pom.xml, build.gradle)
- **FR-005**: System MUST invoke Syft for comprehensive dependency scanning and SBOM generation
- **FR-006**: System MUST detect Terraform files and invoke Terravision to generate architecture diagrams
- **FR-007**: System MUST embed generated architecture diagrams (PNG/SVG) in the documentation
- **FR-008**: System MUST render documentation using Jinja2 templates with defined placeholders
- **FR-009**: System MUST support multiple output formats (Markdown at minimum)
- **FR-010**: System MUST support configurable LLM backends (Claude, Gemini, Ollama, AWS Bedrock)
- **FR-011**: System MUST use deterministic analysis before invoking LLM for any section
- **FR-012**: System MUST use temperature=0 and deterministic hyperparameters for LLM calls
- **FR-013**: System MUST produce identical output when run twice on an unchanged repository (see SC-005 for acceptable variations)
- **FR-014**: System MUST provide clear error messages when external tools (Syft, Terravision, Repomix) are unavailable
- **FR-015**: System MUST continue processing when individual analyzer sections fail (e.g., API detection, test detection), documenting failures in output. Note: Core dependencies (tree-sitter, Syft, Repomix, LLM) must pass preflight per Constitution III - this applies only to non-blocking analyzers that can be skipped via CLI flags
- **FR-016**: System MUST support configuration via command-line arguments and/or configuration file
- **FR-017**: System MUST exit with appropriate exit codes for CI/CD integration (0 for success, non-zero for failure)
- **FR-018**: System MUST use standardized log format: `[LEVEL] message` for human mode, `[LEVEL][HH:MM:SS] message` for verbose mode, and JSON lines `{"level":"...","ts":"...","msg":"..."}` for CI mode
- **FR-019**: System MUST generate Mermaid diagrams from AST analysis showing component relationships and external connectivity
- **FR-020**: System MUST categorize Terraform resources into compute, storage, networking, and services
- **FR-021**: System MUST detect ORM models (SQLAlchemy, Django, Prisma, TypeORM) and database schema definitions
- **FR-022**: System MUST detect security patterns including IAM policies, authentication middleware, and secret management
- **FR-023**: System MUST detect resilience patterns including auto-scaling, high availability, and observability tooling
- **FR-024**: System MUST use LLM to generate risk assessments and recommendations based on deterministic analysis
- **FR-025**: System MUST detect API endpoints from framework-specific patterns (FastAPI, Flask, Express, Django, Spring, Go HTTP handlers) and schema files (OpenAPI, GraphQL, protobuf)
- **FR-026**: System MUST detect build and deployment configurations including Dockerfiles, CI/CD pipelines (GitHub Actions, GitLab CI, Jenkins), and build scripts
- **FR-027**: System MUST detect test files, testing frameworks (pytest, Jest, JUnit, Go testing), and coverage configurations
- **FR-028**: System MUST detect logging libraries, logging patterns, and error handling patterns including custom exceptions
- **FR-029**: System MUST render sections as "N/A - [reason]" when applicable analysis yields no results, rather than omitting sections
- **FR-030**: System MUST use Repomix to compress the codebase into skeleton format (function signatures without implementation bodies) for holistic LLM analysis
- **FR-031**: System MUST exclude non-source directories from Repomix compression by default: tests/*, node_modules/*, dist/*, build/*, coverage/*, __pycache__/*, .venv/*, vendor/*, .git/*
- **FR-032**: System MUST generate a holistic system overview (purpose, architecture style, core components, data flow, design patterns) from the compressed codebase


### Key Entities

- **Repository**: The source git repository being analyzed; contains source files, infrastructure code, and dependency manifests
- **Documentation Template**: A Jinja2 template defining the structure and sections of the output document; contains placeholders populated by analysis
- **Analysis Result**: Structured data collected from deterministic analysis tools (AST parsing, Syft, dependency parsing); serves as input to template rendering
- **LLMConfig**: Settings specifying which LLM backend to use and connection parameters; includes provider type, API credentials, and model parameters
- **Architecture Diagram**: Visual representation of cloud infrastructure generated from Terraform; embedded as image in final documentation
- **Technology Stack**: Inventory of detected languages, frameworks, and dependencies; derived from dependency files and Syft scanning
- **Output Document**: The final rendered documentation in the specified format; contains all analyzed information and LLM-generated summaries

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Documentation generation completes within 5 minutes for repositories up to 100,000 lines of code
- **SC-002**: Generated documentation covers 100% of detected source code languages present in the repository
- **SC-003**: 100% of third-party dependencies are listed when dependency files are present and valid
- **SC-004**: Architecture diagrams are included whenever Terraform files are detected and Terravision is available
- **SC-005**: Two consecutive runs on the same unchanged repository produce near byte-identical output. Punctuation, or additional filler words like 'the' 'an' etc exempt. Meaning should be 100% the same.
- **SC-006**: System operates successfully in CI/CD pipelines without interactive prompts
- **SC-007**: Documentation MUST include all 15 sections defined in contracts/template.md. Sections render "N/A - [reason]" when analysis yields no results (per FR-029)
- **SC-008**: System handles missing external tools and checks for them at startup and exits gracefully saying required tools are not detected
- **SC-009**: Generated Markdown is valid and renders correctly in standard Markdown viewers
- **SC-010**: LLM-generated summaries accurately reflect the deterministic analysis data (no hallucinated components)
- **SC-011**: All documents generated must have a version history section, so it is clear when there are updates to it, along with a history so changes can be audited. Who made the change (Human or chronicle), on which date/time, pointing to which git repo to parse code from etc. should be clear with document template

## Assumptions

- Syft is available as an external tool and installed on the system where chronicle runs
- Terravision is available as an external tool for Terraform diagram generation
- tree-sitter and tree-sitter-language-pack are installed for AST parsing
- LiteLLM Python package is installed for unified LLM access
- Repomix is required for codebase compression (install via `npm install -g repomix` or use `npx repomix`)
- **LLM is REQUIRED**: User must select an LLM provider during `chronicle init` (Ollama, Claude, Gemini, or AWS Bedrock). No default is assumed.
- If Ollama is selected, Ollama server must be running locally at http://localhost:11434
- If Claude/Gemini is selected, valid API key must be configured
- If AWS Bedrock is selected, valid AWS credentials must be available
- Git repositories are accessible and have read permissions
- Source code files use standard file extensions for their respective languages (.py, .js, .ts, .go, .java)
- Terraform files follow standard naming conventions (.tf extension)
- CI/CD environments provide sufficient resources (memory, CPU) for analysis operations
- Preflight check before running any tools ensures all these assumptions are met before it starts

## Design Constraints

### No Fallback Implementations

**CRITICAL**: When a required dependency is unavailable, analysis MUST fail immediately with a clear error message. No degraded-mode or fallback parsing is permitted.

**Rationale**:
1. **Reproducibility**: Fallbacks produce inconsistent results depending on environment, violating SC-005
2. **Audit Integrity**: Enterprise IT audits require consistent, predictable output - partial results undermine trust
3. **Fail-Fast Principle**: Better to fail clearly during preflight than produce incomplete documentation
4. **Maintenance Burden**: Fallback code paths add complexity and are rarely as accurate as purpose-built tools

**Implementation**:
- `chronicle check` validates ALL required dependencies before ANY analysis begins
- Missing dependencies cause immediate exit with exit code 1 and installation instructions
- AST parsing requires tree-sitter (no regex fallback)
- SBOM generation requires Syft (no custom parsing fallback)
- Architecture diagrams require Terravision (no HCL regex fallback)
- Codebase compression requires Repomix (no custom skeleton fallback)
- LLM requires LiteLLM package + configured provider (Ollama, Claude, Gemini, or Bedrock - user must select during `chronicle init`)
- Users can skip specific analyzers via CLI flags (--skip-sbom, --skip-architecture) if tools are unavailable

### Source of Truth Precedence (Future Phases)

**IMPORTANT**: When chronicle collects context from multiple sources, deterministic facts SHALL take precedence over descriptive text.

**Precedence Order (highest to lowest)**:
1. **Code Analysis**: AST parsing, import analysis, actual code structure
2. **Structured Configuration**: YAML, JSON, TOML files (`.chronicle/config.yaml`, `pyproject.toml`, `package.json`)
3. **Dependency Manifests**: Lock files, SBOM output from Syft
4. **Descriptive Documentation**: Markdown files (README.md, docs/*.md)

**Rationale**:
- Markdown files often contain aspirational or outdated descriptions
- Structured config files are what the system actually uses at runtime
- Code is the ultimate truth of what the system does
- LLM receives all sources for context but deterministic analysis prevails for facts

**Future Implementation**:
- When LLM-generated content conflicts with deterministic analysis, flag the discrepancy
- User should be alerted to review and resolve conflicts before finalizing documentation
- Markdown content provides valuable context for LLM understanding but is not authoritative for technical facts

## Out of Scope

- Direct publishing to Confluence or SharePoint (outputs formats suitable for import)
- Version control of generated documentation (handled by Git as documentation will be checked into Git repo along with code) - however, the document should contain version history as a section
- Interactive editing of generated documentation
- Support for programming languages beyond Python, JavaScript, TypeScript, Go, and Java
- Cloud infrastructure diagrams for non-Terraform infrastructure-as-code (CloudFormation, Pulumi, etc.)
- Automatic deployment of documentation to hosting platforms
