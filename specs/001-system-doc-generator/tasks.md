# Tasks: chronicle - Automated System Documentation Generator

**Input**: Design documents from `/specs/001-system-doc-generator/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md, contracts/template.md, quickstart.md

**Tests**: Tests are included based on constitution quality gates (deterministic output, reproducibility, interface compliance).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Based on plan.md structure:
- Source code: `src/chronicle/`
- Tests: `tests/`
- Configuration: `.chronicle/`

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Create project structure and install dependencies

- [x] T001 Create project directory structure per plan.md in src/chronicle/
- [x] T002 Initialize Python project with pyproject.toml (Python 3.11+, dependencies: typer, typer-config, tree-sitter, tree-sitter-language-pack, litellm, jinja2, pyyaml)
- [x] T003 [P] Create src/chronicle/__init__.py with version info
- [x] T004 [P] Create src/chronicle/__main__.py entry point for `python -m chronicle`
- [x] T005 [P] Create tests/conftest.py with shared pytest fixtures
- [x] T006 [P] Configure ruff for linting and formatting in pyproject.toml

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**Critical**: No user story work can begin until this phase is complete

### Core Models

- [x] T007 [P] Create src/chronicle/models/__init__.py exporting all models
- [x] T008 [P] Implement Repository entity in src/chronicle/models/repository.py
- [x] T009 [P] Implement AnalysisError entity in src/chronicle/models/analysis.py
- [x] T010 [P] Implement VersionEntry entity in src/chronicle/models/analysis.py

### Canonical Data Formats (Principle V: Tool Agnosticism)

- [x] T011 [P] Create src/chronicle/models/canonical/__init__.py exporting all canonical types
- [x] T012 [P] Implement CanonicalSBOM, CanonicalPackage, SBOMSource in src/chronicle/models/canonical/sbom.py
- [x] T013 [P] Implement CanonicalArchitecture, CanonicalGraph, NodeMetadata, RenderedImage, ArchitectureSource in src/chronicle/models/canonical/architecture.py
- [x] T014 [P] Implement CanonicalAST, CanonicalModule, CanonicalClass, CanonicalFunction, CanonicalEntryPoint, ASTSource in src/chronicle/models/canonical/ast.py

### Tool Adapter Interfaces (Principle V: Tool Agnosticism)

- [x] T015 [P] Implement abstract ToolAdapter base class in src/chronicle/analyzers/base.py
- [x] T016 [P] Implement SBOMAdapter abstract interface in src/chronicle/analyzers/sbom/base.py
- [x] T017 [P] Implement DiagramGenerator abstract interface in src/chronicle/analyzers/diagrams/base.py
- [x] T018 [P] Implement ToolRegistry in src/chronicle/analyzers/registry.py

### Configuration System

- [x] T019 Implement chronicleConfig, OutputConfig, ToolConfig, SectionConfig dataclasses in src/chronicle/config.py
- [x] T020 [P] Implement YAML config loading with env var substitution (${VAR}) in src/chronicle/config.py
- [x] T021 [P] Implement config file discovery (.chronicle/config.yaml, chronicle.yaml) in src/chronicle/config.py

### Utility Infrastructure

- [x] T022 [P] Implement preflight tool checker in src/chronicle/utils/preflight.py (Principle III)
- [x] T023 [P] Implement version history tracking in src/chronicle/utils/version.py

### Logging System (FR-018)

- [x] T023b [P] Implement logging formatter with three modes (human, verbose, JSON) in src/chronicle/utils/logging.py
- [x] T023c [P] Add colored output for human mode (INFO=green, WARNING=yellow, ERROR=red, disabled when not TTY) in src/chronicle/utils/logging.py
- [x] T023d [P] Configure logging integration with CLI (--verbose, --quiet, --ci flags) in src/chronicle/cli.py

### LLM Infrastructure (configured via chronicle init)

- [x] T023e [P] Implement LLMConfig entity in src/chronicle/models/llm_config.py
- [x] T023f [P] Add LiteLLM preflight check in src/chronicle/utils/preflight.py
- [x] T023g [P] Add Ollama server connectivity check in src/chronicle/utils/preflight.py
- [x] T023k [P] Create src/chronicle/llm/__init__.py package module exporting client and prompts
- [x] T023h Implement unified LLM client wrapper using LiteLLM in src/chronicle/llm/client.py
- [x] T023i [P] Add Claude/Gemini/Bedrock credential validation in src/chronicle/utils/preflight.py
- [x] T023j Unit test for LLM preflight checks in tests/unit/test_preflight.py

### CLI Framework

- [x] T024 Create Typer app structure in src/chronicle/cli.py with global options (--config, --verbose, --quiet, --version)

### Foundational Tests

- [x] T025 [P] Unit test for Repository entity in tests/unit/test_models.py
- [x] T026 [P] Unit test for config loading in tests/unit/test_config.py
- [x] T027 [P] Unit test for canonical format validation in tests/unit/test_canonical.py
- [x] T023l [P] Unit test for ToolRegistry (registration, retrieval, error handling) in tests/unit/test_registry.py
- [x] T023m [P] Unit test for LLMConfig entity validation (temperature=0, provider, api_key requirements) in tests/unit/test_llm_config.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Generate Documentation from Repository (Priority: P1) MVP

**Goal**: DevOps engineer runs chronicle in CI/CD pipeline to automatically generate up-to-date system documentation

**Independent Test**: Point chronicle at a sample repository and verify it produces a complete documentation file with all detected components

### Implementation for User Story 1

#### AST Parsing (Deterministic Analysis)

- [x] T028 [P] [US1] Create tree-sitter parser wrapper in src/chronicle/analyzers/ast_parser.py
- [x] T029 [US1] Implement Python AST extraction (modules, classes, functions) in src/chronicle/analyzers/ast_parser.py
- [x] T030 [P] [US1] Implement JavaScript AST extraction in src/chronicle/analyzers/ast_parser.py
- [x] T030b [P] [US1] Implement TypeScript AST extraction in src/chronicle/analyzers/ast_parser.py
- [x] T031 [P] [US1] Implement Go AST extraction in src/chronicle/analyzers/ast_parser.py
- [x] T032 [P] [US1] Implement Java AST extraction in src/chronicle/analyzers/ast_parser.py
- [x] T033 [US1] Implement CanonicalAST output from parser in src/chronicle/analyzers/ast_parser.py

#### Dependency Parsing

- [x] T034 [P] [US1] Implement dependency file parser for package.json in src/chronicle/analyzers/dependency.py
- [x] T035 [P] [US1] Implement dependency file parser for requirements.txt/pyproject.toml in src/chronicle/analyzers/dependency.py
- [x] T036 [P] [US1] Implement dependency file parser for go.mod in src/chronicle/analyzers/dependency.py
- [x] T037 [P] [US1] Implement dependency file parser for pom.xml/build.gradle in src/chronicle/analyzers/dependency.py
- [x] T038 [US1] Create TechnologyStack entity from parsed dependencies in src/chronicle/models/analysis.py

#### SBOM Integration (Syft Adapter)

- [x] T039 [US1] Implement SyftAdapter in src/chronicle/analyzers/sbom/syft.py
- [x] T040 [US1] Transform Syft JSON output to CanonicalSBOM in src/chronicle/analyzers/sbom/syft.py
- [x] T041 [US1] Register SyftAdapter in ToolRegistry in src/chronicle/analyzers/registry.py

#### Terraform Diagram Integration (Terravision Adapter)

- [x] T042 [US1] Implement TerravisionAdapter in src/chronicle/analyzers/diagrams/terravision.py
- [x] T043 [US1] Transform Terravision output to CanonicalArchitecture in src/chronicle/analyzers/diagrams/terravision.py
- [x] T044 [US1] Register TerravisionAdapter in ToolRegistry in src/chronicle/analyzers/registry.py

#### Analysis Pipeline

- [x] T045 [US1] Implement AnalysisResult aggregation in src/chronicle/models/analysis.py
- [x] T046 [US1] Create analysis orchestrator that runs all deterministic analyzers in src/chronicle/pipeline.py

#### Template Rendering

- [x] T048 [US1] Implement Jinja2 renderer in src/chronicle/templates/renderer.py
- [x] T049 [US1] Create default Markdown template in src/chronicle/templates/SYSTEM.md.j2 (basic sections; LLM/advanced sections pending future phases)
- [x] T050 [US1] Implement OutputDocument generation with version history in src/chronicle/templates/renderer.py

#### CLI Command: write

- [x] T051 [US1] Implement `chronicle write` command in src/chronicle/cli.py
- [x] T052 [US1] Add --output, --format, --ci flags to write command in src/chronicle/cli.py
- [x] T053 [US1] Implement exit codes (0=success, 1=error, 2=warning) in src/chronicle/cli.py

#### CLI Command: check (Principle III: Preflight Validation)

- [x] T054 [US1] Implement `chronicle check` command in src/chronicle/cli.py
- [x] T055 [US1] Add --json flag for machine-readable output in src/chronicle/cli.py

#### LLM Summary Generation (Required per spec assumptions - LLM is REQUIRED)

- [x] T055a [US1] Create prompt templates for section summaries (overview, tech stack, architecture) in src/chronicle/llm/prompts.py
- [x] T055b [US1] Implement prompt construction from AnalysisResult context in src/chronicle/llm/prompts.py
- [x] T055c [US1] Integrate LLM summaries into analysis pipeline (after deterministic analysis) in src/chronicle/pipeline.py
- [x] T055d [US1] Add LLM summary placeholders in template when LLM unavailable in src/chronicle/templates/renderer.py
- [x] T055e [US1] Add --skip-llm flag to bypass LLM summaries for testing in src/chronicle/cli.py

### Tests for User Story 1

- [x] T056 [P] [US1] Create sample Python repository fixture in tests/fixtures/sample_repos/python_project/
- [x] T057 [P] [US1] Unit test for AST parser determinism in tests/unit/test_ast_parser.py
- [x] T058 [P] [US1] Unit test for dependency parsing in tests/unit/test_dependency_parser.py
- [x] T059 [US1] Integration test for `chronicle write` on sample repo in tests/integration/test_cli.py
- [x] T060 [US1] Integration test for preflight check in tests/integration/test_cli.py
- [x] T060a [P] [US1] Unit test for LLM prompt templates in tests/unit/test_llm_prompts.py
- [x] T060b [P] [US1] Unit test for prompt construction from AnalysisResult in tests/unit/test_llm_prompts.py
- [x] T060c [US1] Integration test for LLM backend connectivity (configured provider) in tests/integration/test_llm_client.py
- [x] T060d [US1] Integration test for documentation with LLM summaries in tests/integration/test_llm_client.py

**Checkpoint**: User Story 1 complete - chronicle can generate documentation from a repository with LLM summaries

---

## Phase 4: User Story 2 - Review Documentation for Audit Compliance (Priority: P2)

**Goal**: IT auditor receives accurate system documentation with all dependencies and architecture for compliance assessment

**Independent Test**: Generate documentation for a known system and verify all security-relevant components are accurately documented

### Implementation for User Story 2

#### Reproducibility (Principle II)

- [x] T061 [US2] Add external tool version capture to AnalysisResult metadata in src/chronicle/models/analysis.py
- [x] T062 [US2] Ensure all output includes git ref and timestamps in src/chronicle/templates/SYSTEM.md.j2
- [x] T063 [US2] Implement output comparison utility for reproducibility testing in src/chronicle/utils/version.py

#### SBOM Completeness

- [x] T064 [US2] Add license information extraction to CanonicalPackage in src/chronicle/models/canonical/sbom.py
- [x] T065 [US2] Add PURL (Package URL) standardized identifier to CanonicalPackage in src/chronicle/models/canonical/sbom.py

#### Version History (SC-011)

- [x] T066 [US2] Implement version history section in default template in src/chronicle/templates/SYSTEM.md.j2
- [x] T067 [US2] Add author attribution (Human vs chronicle) to VersionEntry in src/chronicle/models/analysis.py

### Tests for User Story 2

- [x] T068 [P] [US2] Reproducibility test: consecutive runs produce identical output in tests/integration/test_full_pipeline.py
- [x] T069 [P] [US2] Unit test for SBOM completeness (all deps with versions) in tests/integration/test_full_pipeline.py
- [x] T070 [US2] Integration test for version history section in tests/integration/test_full_pipeline.py

**Checkpoint**: User Story 2 complete - Documentation is audit-ready with full dependency listing and version history

---

## Phase 4b: Production Dependencies Refinement

**Goal**: Refine the Production Dependencies section to show only direct/meaningful dependencies instead of all transitive sub-packages

**Problem Statement**: The current implementation lists ALL packages from Syft (483 in the example), including transitive dependencies like `@smithy/*`, `@aws-crypto/*` that are pulled in automatically by npm. This creates a long, noisy list that adds little value for documentation purposes.

**Solution**: Distinguish between direct dependencies (explicitly declared in package.json, requirements.txt, etc.) and transitive dependencies (pulled in automatically). Show only direct dependencies in the main documentation table with a summary of total package count.

### Implementation

#### Update Data Model

- [x] T064a [P] [US2] Add `is_direct` boolean field to CanonicalPackage in src/chronicle/models/canonical/sbom.py
- [x] T064b [P] [US2] Add helper methods to CanonicalSBOM: `get_direct_packages()` and `get_transitive_packages()` in src/chronicle/models/canonical/sbom.py
- [x] T064c [P] [US2] Add `direct_package_count` property to CanonicalSBOM in src/chronicle/models/canonical/sbom.py

#### Cross-Reference Direct Dependencies

- [x] T064d [US2] Create DirectDependencyResolver class in src/chronicle/analyzers/dependency.py that parses manifest files and returns set of direct dependency names
- [x] T064e [US2] Update SyftAdapter to cross-reference packages with DirectDependencyResolver and set `is_direct=True` for packages declared in manifest files in src/chronicle/analyzers/sbom/syft.py
- [x] T064f [P] [US2] Handle scope prefixes for npm packages (match `@aws-sdk/client-dynamodb` to `@aws-sdk/client-dynamodb` in package.json) in src/chronicle/analyzers/dependency.py

#### Update Template Rendering

- [x] T064g [US2] Update SYSTEM.md.j2 template to only show direct dependencies in Production Dependencies table in src/chronicle/templates/SYSTEM.md.j2
- [x] T064h [US2] Add SBOM summary statistics to template (total packages, direct packages, ecosystems) in src/chronicle/templates/SYSTEM.md.j2
- [x] T064i [P] [US2] Add "See full SBOM for complete list including transitive dependencies" note to template in src/chronicle/templates/SYSTEM.md.j2

#### Update LLM Prompts

- [x] T064j [US2] Update dependencies prompt to focus on direct dependencies and mention total package count in src/chronicle/llm/prompts.py

#### Tests

- [x] T064k [P] [US2] Unit test for CanonicalPackage.is_direct field in tests/unit/test_canonical.py
- [x] T064l [P] [US2] Unit test for DirectDependencyResolver parsing package.json in tests/unit/test_dependency_parser.py
- [x] T064m [P] [US2] Unit test for DirectDependencyResolver parsing requirements.txt in tests/unit/test_dependency_parser.py
- [x] T064n [P] [US2] Unit test for SyftAdapter cross-referencing with DirectDependencyResolver in tests/unit/test_sbom_adapter.py (covered in test_dependency_parser.py)
- [x] T064o [US2] Integration test verifying template shows only direct dependencies in tests/integration/test_full_pipeline.py (covered in test_canonical.py)

**Checkpoint**: Production Dependencies section now shows only direct/meaningful dependencies with clear summary statistics

---

## Phase 4c: Structured LLM Prompting and Debug Logging

**Goal**: Improve LLM prompting to produce more standardized, consistent summaries by breaking sections into focused sub-questions, and add verbose logging for debugging.

**Problem Statement**: Current prompts ask LLM to generate entire sections at once, resulting in variable quality and style. Additionally, there's no visibility into what data is sent to the LLM or what responses are received during debugging.

**Solution**:
1. Break each documentation section into 2-4 focused sub-questions
2. Make separate LLM calls for each sub-question
3. Concatenate sub-answers into final section content
4. Add verbose logging showing facts given to LLM and responses received

### Implementation

#### Define Sub-Section Structure

- [x] T065a [P] [US1] Create SubSectionPrompt dataclass in src/chronicle/llm/prompts.py with fields: name, question, max_words, facts_template
- [x] T065b [P] [US1] Create SectionDefinition dataclass in src/chronicle/llm/prompts.py with fields: section_name, sub_sections, concatenation_strategy
- [x] T065c [US1] Define SECTION_DEFINITIONS dict mapping section names to SectionDefinition in src/chronicle/llm/prompts.py

#### Overview Sub-Sections

- [x] T065d [US1] Define Overview sub-section 1: "System Type and Technologies" - What kind of system is this and what core technologies does it use? in src/chronicle/llm/prompts.py
- [x] T065e [P] [US1] Define Overview sub-section 2: "Key Components" - What are the main components/services and their roles? in src/chronicle/llm/prompts.py
- [x] T065f [P] [US1] Define Overview sub-section 3: "Architecture Pattern" - What architectural pattern does this follow? in src/chronicle/llm/prompts.py

#### Tech Stack Sub-Sections

- [x] T065g [US1] Define Tech Stack sub-section 1: "Languages" - What programming languages are used and in what proportion? in src/chronicle/llm/prompts.py
- [x] T065h [P] [US1] Define Tech Stack sub-section 2: "Frameworks and Libraries" - What key frameworks and libraries are used? in src/chronicle/llm/prompts.py
- [x] T065i [P] [US1] Define Tech Stack sub-section 3: "Package Summary" - Summarize the dependency ecosystems and counts in src/chronicle/llm/prompts.py

#### Architecture Sub-Sections

- [x] T065j [US1] Define Architecture sub-section 1: "Infrastructure Overview" - What cloud services/resources are provisioned? in src/chronicle/llm/prompts.py
- [x] T065k [P] [US1] Define Architecture sub-section 2: "Data Flow" - How do requests/data flow through the system? in src/chronicle/llm/prompts.py
- [x] T065l [P] [US1] Define Architecture sub-section 3: "Configuration" - What key configuration values are set? in src/chronicle/llm/prompts.py

#### Dependencies Sub-Sections

- [x] T065m [US1] Define Dependencies sub-section 1: "Ecosystem Breakdown" - What package ecosystems are used and their counts? in src/chronicle/llm/prompts.py
- [x] T065n [P] [US1] Define Dependencies sub-section 2: "Key Packages" - What are the most important packages by name? in src/chronicle/llm/prompts.py

#### Code Structure Sub-Sections

- [x] T065o [US1] Define Code Structure sub-section 1: "Module Organization" - How is the code organized into modules? in src/chronicle/llm/prompts.py
- [x] T065p [P] [US1] Define Code Structure sub-section 2: "Key Functions and Entry Points" - What are the main functions and entry points? in src/chronicle/llm/prompts.py

#### Multi-Call Prompting Engine

- [x] T065q [US1] Implement generate_section_summary() in src/chronicle/llm/client.py that iterates over sub-sections and makes multiple LLM calls
- [x] T065r [US1] Implement concatenate_subsection_responses() in src/chronicle/llm/client.py to join sub-answers into final section
- [x] T065s [US1] Add SubSectionResponse dataclass tracking: sub_section_name, facts_provided, prompt_sent, response_text, tokens_used in src/chronicle/llm/client.py

#### Verbose Debug Logging

- [x] T065t [US1] Add debug logging in generate_section_summary() to log facts provided for each sub-section in src/chronicle/llm/client.py
- [x] T065u [P] [US1] Add debug logging to log the complete prompt sent to LLM for each sub-section in src/chronicle/llm/client.py
- [x] T065v [P] [US1] Add debug logging to log the LLM response text for each sub-section in src/chronicle/llm/client.py
- [x] T065w [P] [US1] Add info logging showing final concatenated section summary in src/chronicle/llm/client.py

#### Update Pipeline Integration

- [x] T065x [US1] Update pipeline.py to use new generate_section_summary() instead of single-call approach in src/chronicle/pipeline.py
- [x] T065y [US1] Update build_*_prompt() functions to return facts for each sub-section in src/chronicle/llm/prompts.py (implemented via _build_section_data in pipeline.py)

#### Tests

- [x] T065z [P] [US1] Unit test for SubSectionPrompt and SectionDefinition dataclasses in tests/unit/test_llm_prompts.py
- [x] T065aa [P] [US1] Unit test for SubSectionResponse and _format_facts in tests/unit/test_llm_prompts.py
- [x] T065ab [P] [US1] Unit test for concatenate_subsection_responses() in tests/unit/test_llm_prompts.py
- [x] T065ac [US1] Integration test verifying verbose mode logs facts and responses in tests/integration/test_pipeline_llm.py
- [x] T065ad [US1] Integration test verifying final output is concatenation of sub-section answers in tests/integration/test_pipeline_llm.py

**Checkpoint**: LLM prompting now uses structured sub-sections for consistent output, with full debug logging support

---

## Phase 4d: Code Explanation Feature (Priority: P1 Enhancement)

**Goal**: Add functionality to read source code and explain what each function/class does, transforming chronicle from structural documentation (names, parameters) to behavioral documentation (purpose, responsibilities, data flow)

**Independent Test**: Generate documentation for a sample repository and verify the Function Reference section contains LLM-generated explanations for each function

**Dependencies**: Builds on Phase 4c (Structured LLM Prompting) patterns

### Data Model Extensions

#### Extend CanonicalFunction

- [x] T071a [P] [US1] Add `docstring: str | None` field to CanonicalFunction in src/chronicle/models/canonical/ast.py
- [x] T071b [P] [US1] Add `return_type: str | None` field to CanonicalFunction in src/chronicle/models/canonical/ast.py
- [x] T071c [P] [US1] Add `source_snippet: str | None` field to CanonicalFunction (first 5 lines of body) in src/chronicle/models/canonical/ast.py
- [x] T071d [P] [US1] Add `description: str | None` field to CanonicalFunction (LLM-generated) in src/chronicle/models/canonical/ast.py

#### Extend CanonicalClass

- [x] T071e [P] [US1] Add `docstring: str | None` field to CanonicalClass in src/chronicle/models/canonical/ast.py
- [x] T071f [P] [US1] Add `description: str | None` field to CanonicalClass (LLM-generated) in src/chronicle/models/canonical/ast.py

### AST Parser: Docstring Extraction

#### Python Docstring Extraction

- [x] T072a [US1] Implement Python docstring extraction (first statement string in function body) in src/chronicle/analyzers/ast_parser.py
- [x] T072b [US1] Implement Python class docstring extraction in src/chronicle/analyzers/ast_parser.py
- [x] T072c [P] [US1] Extract Python return type annotations in src/chronicle/analyzers/ast_parser.py

#### JavaScript/TypeScript JSDoc Extraction

- [x] T072d [P] [US1] Implement JSDoc comment extraction (/** before function) for JavaScript in src/chronicle/analyzers/ast_parser.py
- [x] T072e [P] [US1] Implement JSDoc comment extraction for TypeScript in src/chronicle/analyzers/ast_parser.py
- [x] T072f [P] [US1] Extract TypeScript return type annotations in src/chronicle/analyzers/ast_parser.py

#### Go Comment Extraction

- [x] T072g [P] [US1] Implement Go doc comment extraction (// lines before func) in src/chronicle/analyzers/ast_parser.py

#### Java Javadoc Extraction

- [x] T072h [P] [US1] Implement Javadoc comment extraction (/** before method) in src/chronicle/analyzers/ast_parser.py

#### Source Snippet Extraction

- [x] T072i [US1] Implement source snippet extraction (first 5 lines of function body) for all languages in src/chronicle/analyzers/ast_parser.py

### LLM Prompts: Function Explanations

#### Prompt Templates

- [x] T073a [US1] Create FUNCTION_EXPLANATION_SYSTEM_PROMPT in src/chronicle/llm/prompts.py (enterprise doc style, no speculation)
- [x] T073b [US1] Create function explanation user prompt template (numbered list format) in src/chronicle/llm/prompts.py
- [x] T073c [P] [US1] Create class explanation prompt template in src/chronicle/llm/prompts.py

#### Batching Strategy

- [x] T073d [US1] Implement FunctionBatch dataclass (max 20 functions per batch) in src/chronicle/llm/client.py
- [x] T073e [US1] Implement batch_functions_by_file() to group functions for LLM calls in src/chronicle/llm/client.py
- [x] T073f [US1] Implement generate_function_explanations() that processes batches in src/chronicle/llm/client.py

#### Response Parsing

- [x] T073g [US1] Implement parse_numbered_explanations() to extract explanations from LLM response in src/chronicle/llm/client.py
- [x] T073h [P] [US1] Handle malformed LLM responses gracefully (partial parsing, placeholders) in src/chronicle/llm/client.py

### Pipeline Integration

- [x] T074a [US1] Add code explanation step to pipeline (after AST parsing, before template rendering) in src/chronicle/pipeline.py
- [x] T074b [US1] Integrate function explanations into AnalysisResult in src/chronicle/pipeline.py
- [x] T074c [P] [US1] Add --skip-explanations flag to bypass function explanation generation in src/chronicle/cli.py
- [x] T074d [P] [US1] Add explanation progress logging (batch X/Y) in src/chronicle/pipeline.py

### Template Updates

- [x] T075a [US1] Add "Function Reference" subsection to Code Structure section in src/chronicle/templates/SYSTEM.md.j2
- [x] T075b [US1] Group function explanations by file in template in src/chronicle/templates/SYSTEM.md.j2
- [x] T075c [P] [US1] Add class explanations to Code Structure section in src/chronicle/templates/SYSTEM.md.j2
- [x] T075d [P] [US1] Handle missing explanations with placeholder text in template in src/chronicle/templates/SYSTEM.md.j2

### Tests

- [x] T076a [P] [US1] Unit test for CanonicalFunction new fields in tests/unit/test_canonical.py
- [x] T076b [P] [US1] Unit test for CanonicalClass new fields in tests/unit/test_canonical.py
- [x] T076c [P] [US1] Unit test for Python docstring extraction in tests/unit/test_ast_parser.py
- [x] T076d [P] [US1] Unit test for JSDoc extraction in tests/unit/test_ast_parser.py
- [x] T076e [P] [US1] Unit test for Go comment extraction in tests/unit/test_ast_parser.py
- [x] T076f [P] [US1] Unit test for source snippet extraction in tests/unit/test_ast_parser.py
- [x] T076g [P] [US1] Unit test for function explanation prompt construction in tests/unit/test_llm_prompts.py
- [x] T076h [P] [US1] Unit test for batch_functions_by_file() in tests/unit/test_llm_prompts.py
- [x] T076i [P] [US1] Unit test for parse_numbered_explanations() in tests/unit/test_llm_prompts.py
- [x] T076j [US1] Integration test for full explanation generation pipeline in tests/integration/test_pipeline_llm.py
- [x] T076k [US1] Integration test for Function Reference section in output in tests/integration/test_full_pipeline.py

**Checkpoint**: Code explanation feature complete - documentation now includes LLM-generated function/class explanations

> **⚠️ DEPRECATION NOTICE**: Phase 4d (function-by-function explanations) is being replaced by Phase 4e (flow-based documentation). The function-by-function approach generated too much detail for the target audience (enterprise architects, auditors). See research.md R14-R17 for rationale.

---

## Phase 4e: Flow-Based Code Documentation (Priority: P1 - Replaces 4d)

**Goal**: Replace function-by-function explanations with flow-based documentation showing module responsibilities, system flow diagrams, and entry points only.

**Rationale**: Enterprise IT audit and architecture stakeholders need to understand system flow, not individual function behavior. This approach reduces LLM calls by 90% (10 module summaries vs 200 function explanations).

**Independent Test**: Generate documentation and verify Code Structure section shows module overview table, system flow diagram, and entry points (not individual functions).

**Design Documents**: See [research.md](research.md) R14-R17, [plan.md](plan.md) Code Structure Documentation Strategy

### Data Model: Module Summary

- [x] T077a [P] [US1] Create CanonicalModule dataclass in src/chronicle/models/canonical/module.py with fields: name, path, files, classes, functions, imports, description
- [x] T077b [P] [US1] Create ModuleSummary dataclass in src/chronicle/models/canonical/module.py with fields: name, path, responsibility (LLM-generated), key_classes, key_functions
- [x] T077c [P] [US1] Create EntryPoint dataclass in src/chronicle/models/canonical/module.py with fields: name, type (cli/api/handler), location, description
- [x] T077d [US1] Add modules: list[ModuleSummary] field to AnalysisResult in src/chronicle/models/analysis.py
- [x] T077e [US1] Add entry_points: list[EntryPoint] field to AnalysisResult in src/chronicle/models/analysis.py

### Module Detection

- [x] T078a [US1] Implement detect_modules() in src/chronicle/analyzers/module_detector.py that groups files by package/directory
- [x] T078b [P] [US1] Add Python module detection (directories with __init__.py) in src/chronicle/analyzers/module_detector.py
- [x] T078c [P] [US1] Add JavaScript/TypeScript module detection (directories with index.js/ts) in src/chronicle/analyzers/module_detector.py
- [x] T078d [P] [US1] Add Go module detection (directories as packages) in src/chronicle/analyzers/module_detector.py
- [x] T078e [US1] Aggregate functions/classes per module from existing AST analysis in src/chronicle/analyzers/module_detector.py

### Import Graph Analysis

- [x] T079a [US1] Implement build_import_graph() in src/chronicle/analyzers/import_graph.py that extracts imports from AST
- [x] T079b [P] [US1] Extract Python imports (import x, from x import y) in src/chronicle/analyzers/import_graph.py
- [x] T079c [P] [US1] Extract JavaScript/TypeScript imports (import/require) in src/chronicle/analyzers/import_graph.py
- [x] T079d [P] [US1] Extract Go imports in src/chronicle/analyzers/import_graph.py
- [x] T079e [US1] Filter to internal modules only (exclude external packages) in src/chronicle/analyzers/import_graph.py
- [x] T079f [US1] Build directed graph: importing_module → imported_module in src/chronicle/analyzers/import_graph.py

### Mermaid Diagram Generation

- [x] T080a [US1] Implement generate_module_flowchart() in src/chronicle/analyzers/diagrams/mermaid.py
- [x] T080b [US1] Convert import graph to Mermaid flowchart syntax in src/chronicle/analyzers/diagrams/mermaid.py
- [x] T080c [US1] Implement complexity reducer: group sub-modules when >15 nodes in src/chronicle/analyzers/diagrams/mermaid.py
- [x] T080d [P] [US1] Add node styling (different shapes for CLI, services, models) in src/chronicle/analyzers/diagrams/mermaid.py

### Entry Point Detection

- [x] T081a [US1] Implement detect_entry_points() in src/chronicle/analyzers/entry_points.py
- [x] T081b [P] [US1] Detect Typer CLI commands (@app.command decorators) in src/chronicle/analyzers/entry_points.py
- [x] T081c [P] [US1] Detect FastAPI/Flask endpoints (@app.get/post/route) in src/chronicle/analyzers/entry_points.py
- [x] T081d [P] [US1] Detect main functions (if __name__ == "__main__") in src/chronicle/analyzers/entry_points.py
- [x] T081e [P] [US1] Detect Express.js endpoints (app.get, router.post) in src/chronicle/analyzers/entry_points.py

### External Integration Detection

- [x] T082a [US1] Implement detect_external_integrations() in src/chronicle/analyzers/integrations.py
- [x] T082b [P] [US1] Detect HTTP client calls (requests, httpx, fetch, axios) in src/chronicle/analyzers/integrations.py
- [x] T082c [P] [US1] Detect database calls (SQLAlchemy, Django ORM, Prisma) in src/chronicle/analyzers/integrations.py
- [x] T082d [P] [US1] Detect message queue calls (boto3 SQS, Kafka) in src/chronicle/analyzers/integrations.py
- [x] T082e [US1] Create ExternalIntegration dataclass with fields: name, type, library, locations in src/chronicle/models/canonical/module.py

### LLM: Module Summaries

- [x] T083a [US1] Create MODULE_SUMMARY_PROMPT template in src/chronicle/llm/prompts.py
- [x] T083b [US1] Implement generate_module_summaries() in src/chronicle/llm/client.py (one LLM call per module)
- [x] T083c [US1] Build prompt context: module name, files, key classes/functions, imports in src/chronicle/llm/prompts.py
- [x] T083d [P] [US1] Handle modules with no code (config-only, assets) gracefully in src/chronicle/llm/client.py

### Pipeline Integration

- [x] T084a [US1] Add module detection step to pipeline (after AST parsing) in src/chronicle/pipeline.py
- [x] T084b [US1] Add import graph analysis step in src/chronicle/pipeline.py
- [x] T084c [US1] Add entry point detection step in src/chronicle/pipeline.py
- [x] T084d [US1] Add module summary generation step (LLM) in src/chronicle/pipeline.py
- [x] T084e [US1] Add Mermaid diagram generation step in src/chronicle/pipeline.py
- [x] T084f [P] [US1] Remove function-by-function explanation step from pipeline in src/chronicle/pipeline.py

### Template Updates

- [x] T084g [US1] Replace "Function Reference" with "Module Overview" in src/chronicle/templates/SYSTEM.md.j2
- [x] T084h [US1] Add module responsibility table to template in src/chronicle/templates/SYSTEM.md.j2
- [x] T084i [US1] Add system flow diagram (Mermaid) to template in src/chronicle/templates/SYSTEM.md.j2
- [x] T084j [US1] Add entry points table to template in src/chronicle/templates/SYSTEM.md.j2
- [x] T084k [P] [US1] Add external integrations section to template in src/chronicle/templates/SYSTEM.md.j2

### Tests

- [x] T084l [P] [US1] Unit test for CanonicalModule and ModuleSummary in tests/unit/test_canonical.py
- [x] T084m [P] [US1] Unit test for detect_modules() in tests/unit/test_module_detector.py
- [x] T084n [P] [US1] Unit test for build_import_graph() in tests/unit/test_import_graph.py
- [x] T084o [P] [US1] Unit test for generate_module_flowchart() in tests/unit/test_mermaid.py
- [x] T084p [P] [US1] Unit test for detect_entry_points() in tests/unit/test_entry_points.py
- [x] T084q [P] [US1] Unit test for detect_external_integrations() in tests/unit/test_integrations.py
- [x] T084r [US1] Integration test: Code Structure section shows modules not functions in tests/integration/test_full_pipeline.py
- [x] T084s [US1] Integration test: Mermaid diagram renders in output in tests/integration/test_full_pipeline.py

**Checkpoint**: Flow-based documentation complete - Code Structure shows module overview, system flow diagram, and entry points

---

## Phase 4f: LLM Output Quality - No Negative Assertions (Priority: P1)

**Goal**: Remove unhelpful "not found" and "unable to determine" statements from LLM output. If something doesn't exist, omit it entirely rather than stating its absence.

**Problem Statement**: Current LLM output includes filler text like:
- "Not determinable from analysis: specific AWS services or frameworks used."
- "No Terraform detected"
- "Infrastructure details: Unable to determine from codebase"

These statements add no value and clutter the documentation.

**Design Documents**: See [research.md](research.md) R18

### Prompt Updates

- [ ] T085a [P] [US1] Add "no negative assertions" instruction block to OVERVIEW_PROMPT in src/chronicle/llm/prompts.py
- [ ] T085b [P] [US1] Add "no negative assertions" instruction block to TECH_STACK_PROMPT in src/chronicle/llm/prompts.py
- [ ] T085c [P] [US1] Add "no negative assertions" instruction block to ARCHITECTURE_PROMPT in src/chronicle/llm/prompts.py
- [ ] T085d [P] [US1] Add "no negative assertions" instruction block to MODULE_SUMMARY_PROMPT in src/chronicle/llm/prompts.py
- [ ] T085e [US1] Create NEGATIVE_ASSERTION_INSTRUCTION constant with standard text block in src/chronicle/llm/prompts.py

Standard instruction block:
```
IMPORTANT: Only include information that IS present in the codebase.
- Do NOT say "not found", "not detected", "unable to determine", "none identified"
- If a section has no relevant content, output "N/A"
- If a field cannot be determined, output "N/A"
- Keep sections visible with "N/A" so users know the analysis ran
```

### Template Conditional Rendering

- [ ] T085f [US1] Add Jinja2 conditionals to SYSTEM.md.j2 to show "N/A" for empty Infrastructure section in src/chronicle/templates/SYSTEM.md.j2
- [ ] T085g [P] [US1] Add Jinja2 conditionals to show "N/A" for empty External Integrations section in src/chronicle/templates/SYSTEM.md.j2
- [ ] T085h [P] [US1] Add Jinja2 conditionals to show "N/A" for empty Cloud Services section in src/chronicle/templates/SYSTEM.md.j2

### Post-Processing Filter (Safety Net)

- [ ] T085i [US1] Implement replace_negative_assertions() in src/chronicle/renderers/filters.py
- [ ] T085j [US1] Define NEGATIVE_PATTERNS list: ["not detected", "not found", "unable to determine", "none identified", "not determinable", "no .* detected"] in src/chronicle/renderers/filters.py
- [ ] T085k [US1] Filter replaces lines containing negative patterns with "N/A" in src/chronicle/renderers/filters.py
- [ ] T085l [US1] Filter replaces empty section content (header with no content) with "N/A" in src/chronicle/renderers/filters.py
- [ ] T085m [US1] Integrate replace_negative_assertions() into render pipeline in src/chronicle/pipeline.py

### Tests

- [ ] T085n [P] [US1] Unit test: prompts include "no negative assertions" instruction in tests/unit/test_llm_prompts.py
- [ ] T085o [P] [US1] Unit test: replace_negative_assertions() replaces known patterns with "N/A" in tests/unit/test_filters.py
- [ ] T085p [P] [US1] Unit test: replace_negative_assertions() replaces empty sections with "N/A" in tests/unit/test_filters.py
- [ ] T085q [US1] Integration test: output contains no "not detected" phrases (only "N/A") in tests/integration/test_full_pipeline.py

**Checkpoint**: LLM output no longer contains unhelpful "not found" statements - absence is communicated through "N/A"

---

## Phase 4g: Repomix Integration for Holistic Codebase Summarization (Priority: P1 - CRITICAL)

**Goal**: Integrate Repomix to compress the codebase into an LLM-friendly format, enabling holistic system understanding with a single LLM call instead of granular module-by-module summaries.

**Problem Statement**: The current flow-based documentation (Phase 4e) is still too granular. Module-by-module analysis lacks holistic system understanding. Enterprise stakeholders need:
- "What does this system do overall?"
- "What are the major architectural patterns?"
- "How does the system fit together as a whole?"

**Design Documents**: See [research.md](research.md) R19-R21

**Why Before Phase 5**: This fundamentally changes how we generate high-level documentation. Must be integrated before template customization (Phase 5) to ensure templates reference the correct data structure.

### Preflight Check

- [ ] T086a [P] [US1] Add check_repomix() method to PreflightChecker in src/chronicle/utils/preflight.py
- [ ] T086b [US1] Check for `repomix` or `npx repomix` availability in src/chronicle/utils/preflight.py
- [ ] T086c [US1] Repomix is REQUIRED - preflight fails with installation instructions if unavailable in src/chronicle/utils/preflight.py
- [ ] T086d [P] [US1] Unit test for check_repomix() in tests/unit/test_preflight.py

### Repomix Adapter

- [ ] T087a [P] [US1] Create RepomixAdapter class in src/chronicle/analyzers/repomix.py
- [ ] T087b [US1] Implement compress_codebase() method that invokes `repomix --compress --style markdown --stdout` in src/chronicle/analyzers/repomix.py
- [ ] T087c [US1] Add default exclude patterns in src/chronicle/analyzers/repomix.py: tests/*, test/*, __tests__/*, *.test.*, *.spec.*, node_modules/*, .git/*, dist/*, build/*, coverage/*, *.min.js, *.bundle.js, vendor/*, __pycache__/*, .venv/*, venv/*, .env
- [ ] T087d [US1] Add configurable exclude patterns from chronicleConfig in src/chronicle/analyzers/repomix.py
- [ ] T087e [US1] Handle timeout (default 300s) for large repositories in src/chronicle/analyzers/repomix.py
- [ ] T087f [US1] Return RepomixOutput dataclass with compressed_content, file_count, token_count in src/chronicle/analyzers/repomix.py

### RepomixOutput Data Model

- [ ] T087g [P] [US1] Create RepomixOutput dataclass in src/chronicle/models/canonical/repomix.py
- [ ] T087h [US1] Fields: compressed_content (str), file_count (int), token_count (int), directory_structure (str) in src/chronicle/models/canonical/repomix.py
- [ ] T087i [US1] Add repomix_output: RepomixOutput | None field to AnalysisResult in src/chronicle/models/analysis.py

### LLM Prompt for Holistic Overview

- [ ] T088a [P] [US1] Create HOLISTIC_OVERVIEW_PROMPT template in src/chronicle/llm/prompts.py
- [ ] T088b [US1] Prompt asks for: System Purpose, Architecture Style, Core Components, Data Flow, External Integrations, Key Design Patterns in src/chronicle/llm/prompts.py
- [ ] T088c [US1] Include "no negative assertions" instruction block in prompt in src/chronicle/llm/prompts.py
- [ ] T088d [US1] Create HolisticOverviewContext dataclass for prompt context in src/chronicle/llm/prompts.py

### LLM Client Extension

- [ ] T089a [US1] Add generate_holistic_overview() method to OraishaLLMClient in src/chronicle/llm/client.py
- [ ] T089b [US1] Method takes RepomixOutput and returns structured HolisticOverview in src/chronicle/llm/client.py
- [ ] T089c [US1] Handle large compressed output by chunking if needed (>100k tokens) in src/chronicle/llm/client.py
- [ ] T089d [P] [US1] Raise error if Repomix output is missing (required dependency) in src/chronicle/llm/client.py

### HolisticOverview Data Model

- [ ] T089e [P] [US1] Create HolisticOverview dataclass in src/chronicle/models/canonical/overview.py
- [ ] T089f [US1] Fields: system_purpose (str), architecture_style (str), core_components (list[str]), data_flow (str), external_integrations (list[str]), design_patterns (list[str]) in src/chronicle/models/canonical/overview.py
- [ ] T089g [US1] Add holistic_overview: HolisticOverview | None field to AnalysisResult in src/chronicle/models/analysis.py

### Pipeline Integration

- [ ] T090a [US1] Add Stage 1b: Repomix compression (after preflight, before AST parsing) in src/chronicle/pipeline.py
- [ ] T090b [US1] Add Stage 7b: Holistic overview generation (after module summaries) in src/chronicle/pipeline.py
- [ ] T090c [US1] Repomix stage is mandatory (no --skip-repomix flag) in src/chronicle/pipeline.py
- [ ] T090d [US1] If Repomix fails, abort pipeline with clear error message in src/chronicle/pipeline.py

### Template Updates

- [ ] T091a [US1] Update Overview section in SYSTEM.md.j2 to use holistic_overview.system_purpose in src/chronicle/templates/SYSTEM.md.j2
- [ ] T091b [US1] Add Architecture Style field to Overview section in src/chronicle/templates/SYSTEM.md.j2
- [ ] T091c [US1] Add Core Components list to Overview section in src/chronicle/templates/SYSTEM.md.j2
- [ ] T091d [US1] Add Design Patterns section to template in src/chronicle/templates/SYSTEM.md.j2
- [ ] T091e [US1] Template requires holistic_overview (no fallback - Repomix is required) in src/chronicle/templates/SYSTEM.md.j2

### Configuration

- [ ] T092a [US1] Add repomix section to chronicleConfig in src/chronicle/config.py
- [ ] T092b [US1] Configuration options: exclude_patterns (list[str]), timeout (int) in src/chronicle/config.py (no 'enabled' - Repomix is required)
- [ ] T092c [US1] Add repomix config to default .chronicle/config.yaml template in src/chronicle/cli.py

### Tests

- [ ] T093a [P] [US1] Unit test: RepomixAdapter.compress_codebase() invokes CLI correctly in tests/unit/test_repomix.py
- [ ] T093b [P] [US1] Unit test: RepomixAdapter raises error when repomix unavailable in tests/unit/test_repomix.py
- [ ] T093c [P] [US1] Unit test: RepomixAdapter applies exclude patterns in tests/unit/test_repomix.py
- [ ] T093d [P] [US1] Unit test: generate_holistic_overview() returns structured data in tests/unit/test_llm_client.py
- [ ] T093e [P] [US1] Unit test: HolisticOverview dataclass serialization in tests/unit/test_models.py
- [ ] T093f [US1] Integration test: Pipeline runs Repomix stage successfully in tests/integration/test_repomix.py
- [ ] T093g [US1] Integration test: Template renders holistic overview content in tests/integration/test_repomix.py
- [ ] T093h [US1] Integration test: Pipeline fails with clear error when Repomix unavailable in tests/integration/test_repomix.py

**Checkpoint**: Holistic overview section generated from compressed codebase - single LLM call provides system-wide understanding

---

## Phase 5: User Story 4 - Customize Documentation Template (Priority: P4)

**Goal**: Technical writer customizes documentation template to match organization standards

**Independent Test**: Provide custom Jinja2 template and verify output matches template structure

### Implementation for User Story 4

#### Template System

- [ ] T085 [US4] Implement custom template loading from config path in src/chronicle/renderers/jinja.py
- [ ] T086 [US4] Create template placeholder documentation in src/chronicle/templates/README.md
- [ ] T087 [US4] Implement unsupported placeholder warning (not error) in src/chronicle/renderers/jinja.py

#### CLI Command: init

- [ ] T088 [US4] Implement `chronicle init` command structure in src/chronicle/cli.py
- [ ] T089 [US4] Add --force flag to overwrite existing config in src/chronicle/cli.py
- [ ] T090 [US4] Create default config template at .chronicle/config.yaml in src/chronicle/cli.py

#### Interactive LLM Provider Setup (chronicle init)

- [ ] T090a [US4] Add interactive LLM provider selection prompt (Ollama/Claude/Gemini/Bedrock) in src/chronicle/cli.py
- [ ] T090b [US4] Prompt for API key input when user selects Claude or Gemini in src/chronicle/cli.py
- [ ] T090c [US4] Validate API key format (non-empty, appropriate prefix) in src/chronicle/cli.py
- [ ] T090d [US4] Test Ollama connectivity when selected (http://localhost:11434) in src/chronicle/cli.py
- [ ] T090e [US4] Save LLM provider and credentials to .chronicle/config.yaml in src/chronicle/cli.py
- [ ] T090f [US4] Add --non-interactive flag to skip prompts (for scripted init) in src/chronicle/cli.py
- [ ] T090g [P] [US4] Unit test for interactive LLM provider selection flow in tests/unit/test_cli.py

#### AWS Bedrock Support (chronicle init)

- [ ] T090h [US4] Add AWS Bedrock as LLM provider option in interactive prompt in src/chronicle/cli.py
- [ ] T090i [US4] Detect AWS credentials (env vars, ~/.aws/credentials, IAM role) in src/chronicle/cli.py
- [ ] T090j [US4] Prompt for AWS region and Bedrock model ID when Bedrock selected in src/chronicle/cli.py
- [x] T090k [US4] Add check_bedrock() method to PreflightChecker in src/chronicle/utils/preflight.py
- [x] T090l [P] [US4] Unit test for Bedrock credential detection in tests/unit/test_preflight_llm.py

#### CLI Command: validate

- [ ] T091 [US4] Implement `chronicle validate TEMPLATE` command in src/chronicle/cli.py
- [ ] T092 [US4] Check Jinja2 syntax and placeholder validity in src/chronicle/cli.py

### Tests for User Story 4

- [ ] T093 [P] [US4] Unit test for custom template rendering in tests/unit/test_renderers.py
- [ ] T094 [P] [US4] Unit test for template validation in tests/unit/test_renderers.py
- [ ] T095 [US4] Integration test for `chronicle init` command in tests/integration/test_cli.py

**Checkpoint**: User Story 4 complete - Custom templates work with validation

---

## Phase 6: User Story 5 - Export to Multiple Formats (Priority: P5)

**Goal**: Documentation manager exports to Markdown, HTML, and Confluence formats

**Independent Test**: Generate documentation and request different output formats, verify each is valid

### Implementation for User Story 5

#### Format Converters

- [ ] T096 [P] [US5] Implement Markdown output (default, already exists) in src/chronicle/renderers/formats.py
- [ ] T097 [P] [US5] Implement HTML output with embedded styles in src/chronicle/renderers/formats.py
- [ ] T098 [P] [US5] Implement Confluence Storage Format (XHTML) output in src/chronicle/renderers/formats.py

#### Human Section Merging (Principle VI)

- [ ] T099 [US5] Implement SectionMerger with prepend/append/replace strategies in src/chronicle/renderers/sections.py
- [ ] T100 [US5] Load human sections from .chronicle/sections/*.md per config in src/chronicle/renderers/sections.py
- [ ] T101 [US5] Integrate section merging into render pipeline in src/chronicle/renderers/jinja.py
- [ ] T102 [US5] Warn on missing section files (not error) in src/chronicle/renderers/sections.py

#### Conflict Detection (Edge Case: Human/LLM Conflict per spec.md)

- [ ] T102a [US5] Implement conflict detector comparing human section content with LLM summary in src/chronicle/renderers/sections.py
- [ ] T102b [US5] Define conflict severity levels (info, warning, error) based on semantic similarity in src/chronicle/renderers/sections.py
- [ ] T102c [US5] Warn user of meaningful semantic differences between human and LLM content in src/chronicle/renderers/sections.py
- [ ] T102d [P] [US5] Add --strict-conflicts flag to fail on conflicts (default: warn only) in src/chronicle/cli.py
- [ ] T102e [P] [US5] Unit test for conflict detection with matching content (no conflict) in tests/unit/test_sections.py
- [ ] T102f [P] [US5] Unit test for conflict detection with contradictory content (conflict) in tests/unit/test_sections.py

### Tests for User Story 5

- [ ] T103 [P] [US5] Unit test for HTML format validity in tests/unit/test_renderers.py
- [ ] T104 [P] [US5] Unit test for Confluence format validity in tests/unit/test_renderers.py
- [ ] T105 [US5] Integration test for human section merging in tests/integration/test_sections.py

**Checkpoint**: User Story 5 complete - All output formats work with human section merging

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

### Error Handling & Edge Cases

- [ ] T106 [P] Handle empty/invalid dependency files gracefully in src/chronicle/analyzers/dependency.py
- [ ] T107 [P] Handle Terraform parsing failures with warning in src/chronicle/analyzers/diagrams/terravision.py
- [ ] T108 [P] Handle syntax errors in source code with best-effort parsing in src/chronicle/analyzers/ast_parser.py
- [ ] T109 [P] Skip binary files automatically in src/chronicle/analyzers/ast_parser.py

### Performance (SC-001: 100k LOC in 5 minutes)

- [ ] T110 Implement incremental file processing for large repos in src/chronicle/analyzers/__init__.py
- [ ] T111 Add --verbose progress indication in src/chronicle/cli.py
- [ ] T111b Create large repo fixture (100k LOC) and benchmark test verifying <5 min completion in tests/integration/test_performance.py

### CI/CD Compatibility (Principle IV)

- [ ] T112 [P] Ensure all output to stdout, errors to stderr in src/chronicle/cli.py
- [ ] T113 [P] Auto-detect CI environment (CI=true) for --ci mode in src/chronicle/cli.py
- [ ] T114 [P] Implement configurable timeouts for external tools in src/chronicle/utils/preflight.py

### Quality Gates

- [ ] T115 Run full test suite and fix failures
- [ ] T116 Run linter (ruff) and fix issues
- [ ] T117 Validate quickstart.md scenarios work end-to-end

---

## Phase 8: Extended Analyzers (Priority: P6)

**Goal**: Implement extended analysis capabilities for comprehensive enterprise documentation

**Independent Test**: Generate documentation with all extended sections populated

### Mermaid Diagram Generation (FR-019)

- [ ] T118 [P] Implement MermaidGenerator base class in src/chronicle/analyzers/diagrams/mermaid.py
- [ ] T119 [P] Generate component diagram from AST module import graph in src/chronicle/analyzers/diagrams/mermaid.py
- [ ] T120 [P] Generate connectivity diagram from external service detection in src/chronicle/analyzers/diagrams/mermaid.py
- [ ] T121 [P] Add CanonicalMermaidDiagram model in src/chronicle/models/canonical/mermaid.py
- [ ] T122 [P] Unit test for Mermaid diagram generation in tests/unit/test_mermaid.py

### Data Flow Diagram Generation (FR-019 Extension)

#### Data Model

- [ ] T122a [P] Implement CanonicalDataFlow model in src/chronicle/models/canonical/data_flow.py
- [ ] T122b [P] Implement EntryPointFlow model in src/chronicle/models/canonical/data_flow.py
- [ ] T122c [P] Implement CallChain model in src/chronicle/models/canonical/data_flow.py
- [ ] T122d [P] Implement ExternalServiceCall model in src/chronicle/models/canonical/data_flow.py
- [ ] T122e [P] Implement MermaidDiagram model in src/chronicle/models/canonical/data_flow.py

#### Entry Point Detection

- [ ] T122f Implement entry point detector for FastAPI (@app.get, @app.post) in src/chronicle/analyzers/data_flow.py
- [ ] T122g [P] Implement entry point detector for Flask (@app.route) in src/chronicle/analyzers/data_flow.py
- [ ] T122h [P] Implement entry point detector for Express.js (app.get, router.post) in src/chronicle/analyzers/data_flow.py
- [ ] T122i [P] Implement entry point detector for Django views in src/chronicle/analyzers/data_flow.py
- [ ] T122j [P] Implement entry point detector for Go HTTP handlers in src/chronicle/analyzers/data_flow.py

#### Call Graph Extraction

- [ ] T122k Implement call graph builder from AST (function call tracking) in src/chronicle/analyzers/data_flow.py
- [ ] T122l Implement call chain extraction from entry points with depth limit in src/chronicle/analyzers/data_flow.py

#### External Service Detection

- [ ] T122m [P] Detect HTTP client calls (requests, httpx, fetch, axios) in src/chronicle/analyzers/data_flow.py
- [ ] T122n [P] Detect database calls (SQLAlchemy, Django ORM, Prisma) in src/chronicle/analyzers/data_flow.py
- [ ] T122o [P] Detect message queue calls (boto3 SQS, Kafka, RabbitMQ) in src/chronicle/analyzers/data_flow.py
- [ ] T122p [P] Detect cache calls (Redis, Memcached) in src/chronicle/analyzers/data_flow.py
- [ ] T122q Classify external service calls by type (http, database, queue, cache) in src/chronicle/analyzers/data_flow.py

#### Diagram Generation

- [ ] T122r Implement sequence diagram generator for request flows in src/chronicle/analyzers/diagrams/mermaid.py
- [ ] T122s Implement flowchart generator for component connectivity in src/chronicle/analyzers/diagrams/mermaid.py
- [ ] T122t Implement complexity reducer (auto-simplify at 40+ nodes) in src/chronicle/analyzers/diagrams/mermaid.py
- [ ] T122u [P] Implement subgraph clustering for large diagrams in src/chronicle/analyzers/diagrams/mermaid.py

#### Pipeline Integration

- [ ] T122v Add data flow analysis step to pipeline in src/chronicle/pipeline.py
- [ ] T122w Add --skip-data-flow flag to CLI in src/chronicle/cli.py
- [ ] T122x Add data flow diagrams to SYSTEM.md.j2 template in src/chronicle/templates/SYSTEM.md.j2

#### Tests

- [ ] T122y [P] Unit test for entry point detection (all frameworks) in tests/unit/test_data_flow.py
- [ ] T122z [P] Unit test for call graph extraction in tests/unit/test_data_flow.py
- [ ] T122aa [P] Unit test for external service detection in tests/unit/test_data_flow.py
- [ ] T122ab [P] Unit test for sequence diagram generation in tests/unit/test_mermaid.py
- [ ] T122ac [P] Unit test for complexity reduction in tests/unit/test_mermaid.py
- [ ] T122ad Integration test for data flow diagrams in output in tests/integration/test_full_pipeline.py

### Infrastructure Analysis (FR-020)

- [ ] T123 [P] Implement TerraformAnalyzer for resource categorization in src/chronicle/analyzers/infrastructure/terraform.py
- [ ] T124 [P] Add resource type mappings (compute, storage, networking, services) in src/chronicle/analyzers/infrastructure/terraform.py
- [ ] T125 [P] Add CanonicalInfrastructure model in src/chronicle/models/canonical/infrastructure.py
- [ ] T126 [P] Unit test for Terraform resource categorization in tests/unit/test_infrastructure.py

### Data Model Detection (FR-021)

- [ ] T127 [P] Implement ORMDetector base class in src/chronicle/analyzers/data/orm_detector.py
- [ ] T128 [P] Detect SQLAlchemy models (Base inheritance, Column attributes) in src/chronicle/analyzers/data/orm_detector.py
- [ ] T129 [P] Detect Django models (models.Model inheritance) in src/chronicle/analyzers/data/orm_detector.py
- [ ] T130 [P] Detect Prisma schemas (schema.prisma file parsing) in src/chronicle/analyzers/data/orm_detector.py
- [ ] T131 [P] Detect TypeORM entities (@Entity decorator) in src/chronicle/analyzers/data/orm_detector.py
- [ ] T132 [P] Add CanonicalData model in src/chronicle/models/canonical/data.py
- [ ] T133 [P] Unit test for ORM detection in tests/unit/test_orm_detector.py

### Security Pattern Detection (FR-022)

- [ ] T134 [P] Implement SecurityPatternScanner in src/chronicle/analyzers/security/scanner.py
- [ ] T135 [P] Detect IAM resources from Terraform in src/chronicle/analyzers/security/scanner.py
- [ ] T136 [P] Detect authentication patterns (JWT, OAuth, session) from AST in src/chronicle/analyzers/security/scanner.py
- [ ] T137 [P] Detect secret management patterns (Secrets Manager, Vault, env vars) in src/chronicle/analyzers/security/scanner.py
- [ ] T138 [P] Extract security group rules from Terraform in src/chronicle/analyzers/security/scanner.py
- [ ] T139 [P] Add CanonicalSecurity model in src/chronicle/models/canonical/security.py
- [ ] T140 [P] Unit test for security pattern detection in tests/unit/test_security_scanner.py

### Resilience Pattern Detection (FR-023)

- [ ] T141 [P] Implement ResilienceDetector in src/chronicle/analyzers/resilience/detector.py
- [ ] T142 [P] Detect auto-scaling configurations from Terraform in src/chronicle/analyzers/resilience/detector.py
- [ ] T143 [P] Detect HA patterns (multi-AZ, load balancing) from Terraform in src/chronicle/analyzers/resilience/detector.py
- [ ] T144 [P] Detect observability tools from dependencies in src/chronicle/analyzers/resilience/detector.py
- [ ] T145 [P] Detect retry/circuit breaker patterns from AST in src/chronicle/analyzers/resilience/detector.py
- [ ] T146 [P] Add CanonicalResilience model in src/chronicle/models/canonical/resilience.py
- [ ] T147 [P] Unit test for resilience pattern detection in tests/unit/test_resilience_detector.py

### Risk Assessment LLM Integration (FR-024)

- [ ] T148 Create risk assessment prompt templates in src/chronicle/llm/prompts.py
- [ ] T149 Implement design risk analysis from all deterministic data in src/chronicle/llm/prompts.py
- [ ] T150 Implement security concern analysis in src/chronicle/llm/prompts.py
- [ ] T151 Implement mitigation recommendation generation in src/chronicle/llm/prompts.py
- [ ] T152 [P] Unit test for risk assessment prompts in tests/unit/test_llm_prompts.py

### Extended Template Integration

- [ ] T153 Update default template with extended sections in src/chronicle/templates/default.md.j2
- [ ] T154 Add extended section variables to template context in src/chronicle/renderers/jinja.py
- [ ] T155 Integration test for extended documentation output in tests/integration/test_extended_docs.py

**Checkpoint**: Extended analyzers complete - full enterprise documentation with all sections

---

## Phase 9: Documentation Completeness Analyzers (Priority: P7)

**Goal**: Detect API documentation, build/deployment, testing, and logging patterns for comprehensive documentation

**Independent Test**: Generate documentation with API, Build, Testing, and Logging sections populated

### API Endpoint Detection (FR-025)

- [ ] T156 [P] Implement APIEndpointDetector base class in src/chronicle/analyzers/api/detector.py
- [ ] T157 [P] Detect FastAPI endpoints (@app.get, @router.post, etc.) in src/chronicle/analyzers/api/detector.py
- [ ] T158 [P] Detect Flask endpoints (@app.route, @blueprint.route) in src/chronicle/analyzers/api/detector.py
- [ ] T159 [P] Detect Express.js endpoints (app.get, router.post) in src/chronicle/analyzers/api/detector.py
- [ ] T160 [P] Detect Django URL patterns (urls.py parsing) in src/chronicle/analyzers/api/detector.py
- [ ] T161 [P] Detect Spring endpoints (@GetMapping, @PostMapping, @RestController) in src/chronicle/analyzers/api/detector.py
- [ ] T162 [P] Detect Go HTTP handlers (http.HandleFunc, gorilla/mux, gin) in src/chronicle/analyzers/api/detector.py
- [ ] T163 [P] Parse OpenAPI/Swagger specifications (openapi.yaml, swagger.json) in src/chronicle/analyzers/api/openapi.py
- [ ] T164 [P] Parse GraphQL schemas (*.graphql files, schema definitions) in src/chronicle/analyzers/api/graphql.py
- [ ] T165 [P] Parse protobuf definitions for gRPC (*.proto files) in src/chronicle/analyzers/api/grpc.py
- [ ] T166 [P] Add CanonicalAPI model in src/chronicle/models/canonical/api.py
- [ ] T167 [P] Unit test for API endpoint detection in tests/unit/test_api_detector.py

### Build Configuration Analysis (FR-026)

- [ ] T168 [P] Implement BuildConfigAnalyzer base class in src/chronicle/analyzers/build/analyzer.py
- [ ] T169 [P] Parse Dockerfile (base image, stages, ports, entrypoint) in src/chronicle/analyzers/build/docker.py
- [ ] T170 [P] Parse docker-compose.yml files in src/chronicle/analyzers/build/docker.py
- [ ] T171 [P] Parse GitHub Actions workflows (.github/workflows/*.yml) in src/chronicle/analyzers/build/ci.py
- [ ] T172 [P] Parse GitLab CI configuration (.gitlab-ci.yml) in src/chronicle/analyzers/build/ci.py
- [ ] T173 [P] Parse Jenkinsfile in src/chronicle/analyzers/build/ci.py
- [ ] T174 [P] Parse CircleCI configuration (.circleci/config.yml) in src/chronicle/analyzers/build/ci.py
- [ ] T175 [P] Parse Azure Pipelines (azure-pipelines.yml) in src/chronicle/analyzers/build/ci.py
- [ ] T176 [P] Parse Makefile targets in src/chronicle/analyzers/build/scripts.py
- [ ] T177 [P] Extract npm/yarn scripts from package.json in src/chronicle/analyzers/build/scripts.py
- [ ] T178 [P] Extract Python scripts from pyproject.toml in src/chronicle/analyzers/build/scripts.py
- [ ] T179 [P] Add CanonicalBuild model in src/chronicle/models/canonical/build.py
- [ ] T180 [P] Unit test for build configuration analysis in tests/unit/test_build_analyzer.py

### Test Detection (FR-027)

- [ ] T181 [P] Implement TestDetector base class in src/chronicle/analyzers/testing/detector.py
- [ ] T182 [P] Detect pytest tests (test_*.py, pytest.ini, pyproject.toml) in src/chronicle/analyzers/testing/detector.py
- [ ] T183 [P] Detect unittest tests (TestCase inheritance) in src/chronicle/analyzers/testing/detector.py
- [ ] T184 [P] Detect Jest tests (*.test.js, *.spec.js, jest.config.*) in src/chronicle/analyzers/testing/detector.py
- [ ] T185 [P] Detect Mocha/Vitest tests in src/chronicle/analyzers/testing/detector.py
- [ ] T186 [P] Detect Go tests (*_test.go, func Test*) in src/chronicle/analyzers/testing/detector.py
- [ ] T187 [P] Detect JUnit tests (@Test annotation, *Test.java) in src/chronicle/analyzers/testing/detector.py
- [ ] T188 [P] Detect Cypress/Playwright E2E tests in src/chronicle/analyzers/testing/detector.py
- [ ] T189 [P] Parse coverage configuration (coverage.py, istanbul, nyc) in src/chronicle/analyzers/testing/coverage.py
- [ ] T190 [P] Detect test fixtures (conftest.py, factories, mocks) in src/chronicle/analyzers/testing/detector.py
- [ ] T191 [P] Categorize tests by type (unit, integration, e2e) in src/chronicle/analyzers/testing/detector.py
- [ ] T192 [P] Add CanonicalTesting model in src/chronicle/models/canonical/testing.py
- [ ] T193 [P] Unit test for test detection in tests/unit/test_test_detector.py

### Logging Pattern Detection (FR-028)

- [ ] T194 [P] Implement LoggingPatternScanner base class in src/chronicle/analyzers/logging/scanner.py
- [ ] T195 [P] Detect Python logging libraries (logging, structlog, loguru) in src/chronicle/analyzers/logging/scanner.py
- [ ] T196 [P] Detect Node.js logging libraries (winston, pino, bunyan) in src/chronicle/analyzers/logging/scanner.py
- [ ] T197 [P] Detect Java logging (log4j, slf4j, logback) in src/chronicle/analyzers/logging/scanner.py
- [ ] T198 [P] Detect Go logging (zap, zerolog, logrus) in src/chronicle/analyzers/logging/scanner.py
- [ ] T199 [P] Analyze log level usage patterns in src/chronicle/analyzers/logging/scanner.py
- [ ] T200 [P] Detect custom exception classes in src/chronicle/analyzers/logging/errors.py
- [ ] T201 [P] Detect React error boundaries in src/chronicle/analyzers/logging/errors.py
- [ ] T202 [P] Detect error middleware patterns in src/chronicle/analyzers/logging/errors.py
- [ ] T203 [P] Analyze try/catch/except patterns in src/chronicle/analyzers/logging/errors.py
- [ ] T204 [P] Add CanonicalLogging model in src/chronicle/models/canonical/logging.py
- [ ] T205 [P] Unit test for logging pattern detection in tests/unit/test_logging_scanner.py

### N/A Rendering (FR-029)

- [ ] T206 Implement N/A rendering for all sections when analysis yields no results in src/chronicle/renderers/jinja.py
- [ ] T207 [P] Unit test for N/A section rendering in tests/unit/test_renderers.py

### Phase 9 Template Integration

- [ ] T208 Update default template with API, Build, Testing, Logging sections in src/chronicle/templates/default.md.j2
- [ ] T209 Add new section variables to template context in src/chronicle/renderers/jinja.py
- [ ] T210 Add human merge support for new sections in src/chronicle/renderers/sections.py
- [ ] T211 Integration test for documentation completeness sections in tests/integration/test_completeness_docs.py

**Checkpoint**: Documentation completeness analyzers complete - API, build, testing, and logging sections populated

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 -> P2 -> P4 -> P5)
- **Dependency Refinement (Phase 4b)**: Depends on Phase 3 (US1) SBOM integration - refines how dependencies are displayed
- **Structured LLM Prompting (Phase 4c)**: Depends on Phase 3 (US1) LLM integration - refines prompting for consistent output
- **Code Explanation (Phase 4d)**: Depends on Phase 4c (Structured LLM Prompting) - adds function/class explanations
- **Polish (Phase 7)**: Depends on all desired user stories being complete
- **Extended Analyzers (Phase 8)**: Depends on Phase 3 (US1) - extends core analysis pipeline
- **Completeness Analyzers (Phase 9)**: Depends on Phase 3 (US1) - extends core analysis pipeline with API, build, testing, and logging detection

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational - Builds on US1 analysis output but independently testable
- **User Story 4 (P4)**: Can start after Foundational - Independent template system
- **User Story 5 (P5)**: Can start after Foundational - Independent format converters, section merging integrates with rendering

Note: User Story 3 (LLM Backend Configuration) was removed - LLM provider support is already implemented via LiteLLM in Phase 2 Foundational.

### Within Each User Story

- Models before services/adapters
- Adapters before pipeline integration
- Pipeline before CLI commands
- Core implementation before tests
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models and canonical formats marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1 AST Parsing

```bash
# Launch all language parsers in parallel after T028 (base parser):
Task: T030 "Implement JavaScript AST extraction in src/chronicle/analyzers/ast_parser.py"
Task: T031 "Implement Go AST extraction in src/chronicle/analyzers/ast_parser.py"
Task: T032 "Implement Java AST extraction in src/chronicle/analyzers/ast_parser.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - includes LLM infrastructure)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready - chronicle generates full docs with LLM summaries

### Incremental Delivery

1. Complete Setup + Foundational (includes LLM via LiteLLM) -> Foundation ready
2. Add User Story 1 -> Test independently -> Deploy/Demo (MVP with summaries!)
3. Add User Story 2 -> Test independently -> Deploy/Demo (audit compliance)
4. Add User Story 4 -> Test independently -> Deploy/Demo (custom templates)
5. Add User Story 5 -> Test independently -> Deploy/Demo (multi-format export)
6. Each story adds value without breaking previous stories

Note: User Story 3 (LLM providers) is complete - providers work via LiteLLM configuration.

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (LLM infrastructure via LiteLLM)
2. Once Foundational is done:
   - Developer A: User Story 1 (core pipeline + doc generation)
   - Developer B: User Story 4 (template system)
   - Developer C: User Story 5 (multi-format export, section merging)
3. Stories complete and integrate independently

---

## Summary

| Metric | Count |
|--------|-------|
| **Total Tasks** | 366 |
| **Phase 1 (Setup)** | 6 |
| **Phase 2 (Foundational)** | 33 |
| **Phase 3 (US1 - Generate Docs)** | 43 |
| **Phase 4 (US2 - Audit Compliance)** | 10 |
| **Phase 4b (Dependency Refinement)** | 15 |
| **Phase 4c (Structured LLM Prompting)** | 30 |
| **Phase 4d (Code Explanation)** | 36 (DEPRECATED) |
| **Phase 4e (Flow-Based Documentation)** | 43 |
| **Phase 4f (Output Quality)** | 17 |
| **Phase 5 (US4 - Custom Templates)** | 23 |
| **Phase 6 (US5 - Multi-Format + Sections)** | 16 |
| **Phase 7 (Polish)** | 13 |
| **Phase 8 (Extended Analyzers)** | 68 |
| **Phase 9 (Completeness Analyzers)** | 56 |
| **Parallelizable [P] Tasks** | 237 |

Note: User Story 3 (LLM Backend) removed - provider support already implemented via LiteLLM.

**MVP Scope**: Phases 1-3 (82 tasks) delivers core documentation generation with LLM summaries (user-selected provider)

**Phase 3 MVP includes**:
- Deterministic analysis (AST, dependencies, SBOM, architecture diagrams)
- LLM summary generation using user-selected provider (Ollama, Claude, Gemini, or Bedrock)
- Integration tests for LLM backend connectivity

**Extended Scope**:
- Phase 4b refines dependency display to show only direct dependencies with SBOM summary
- Phase 4c adds structured sub-section prompting and verbose debug logging for LLM
- Phase 4d (DEPRECATED) - replaced by Phase 4e
- Phase 4e adds flow-based documentation with module summaries, system flow diagrams, and entry points (replaces function-by-function explanations)
- Phase 4f removes "not found" and "unable to determine" statements - replaced with "N/A" for clarity
- Phase 8 adds enterprise features (infrastructure categorization, data models, security analysis, resilience patterns, risk assessment, **data flow diagrams**)
- Phase 9 adds documentation completeness (API endpoints, build/deployment, testing, logging/error handling)

**Constitution Compliance**:
- Principle I (Deterministic-First): All analyzers run before LLM; LLM generates prose summaries after deterministic data is collected
- Principle II (Reproducibility): Version tracking, temperature=0 (Foundational, US2)
- Principle III (Preflight Validation): `chronicle check` includes LLM validation (Foundational, US1)
- Principle IV (CI/CD Compatibility): Exit codes, no prompts, env vars (US1, Phase 7 Polish)
- Principle V (Tool Agnosticism): Canonical formats, adapter interfaces, LiteLLM unified interface (Foundational)
- Principle VI (Human Annotation Persistence): Section merging with conflict detection (Phase 6 US5)

---

## Phase 10: Incremental Documentation Updates (Caching) (Priority: P3)

**Goal**: Reduce LLM API calls for subsequent documentation runs by caching module summaries and using git to detect changed files.

**Independent Test**: Run chronicle twice on same repo; verify second run makes no LLM calls for unchanged modules

**Dependencies**: Requires Phase 4e (Flow-Based Documentation) to be complete - caches module summaries generated there

**Design Documents**: See [plan.md](plan.md), [research.md](research.md) (R10-R13), [contracts/cache-api.md](contracts/cache-api.md)

> **Note**: With flow-based documentation (Phase 4e), caching provides less dramatic savings since we generate ~10 module summaries vs ~200 function explanations. However, caching is still valuable for: (1) large codebases with many modules, (2) section summaries (overview, tech stack, etc.), (3) avoiding redundant API calls during development.

### Phase 10a: Setup (Cache Module)

**Purpose**: Create cache module directory structure

- [ ] T212 Create cache module directory structure at src/chronicle/cache/
- [ ] T213 [P] Create src/chronicle/cache/__init__.py with module exports

### Phase 10b: Cache Data Model

**Purpose**: Implement core cache data structures per contracts/cache-api.md

- [ ] T214 [P] Implement ModuleCacheEntry dataclass in src/chronicle/cache/models.py with fields: name, path, responsibility, created_at, chronicle_version
- [ ] T215 [P] Implement AnalysisCache dataclass in src/chronicle/cache/models.py with fields: version, chronicle_version, llm_model, git_ref, created_at, updated_at, modules dict, section_summaries dict
- [ ] T216 Implement cache JSON serialization in src/chronicle/cache/models.py (to_dict/from_dict methods with ISO 8601 datetime handling)
- [ ] T217 Add cache format version constant (CACHE_VERSION = "2.0") in src/chronicle/cache/models.py

### Phase 10c: Git Change Detection

**Purpose**: Implement git-based file change detection per research.md R10

- [ ] T218 Implement get_current_git_ref() function in src/chronicle/cache/git_utils.py to get current HEAD commit SHA
- [ ] T219 Implement get_changed_files(cached_git_ref: str, repo_path: Path) -> set[str] in src/chronicle/cache/git_utils.py using git diff --name-only
- [ ] T220 Implement is_git_repository(path: Path) -> bool helper in src/chronicle/cache/git_utils.py
- [ ] T221 Add error handling for git command failures (subprocess.CalledProcessError) with graceful fallback to full regeneration

### Phase 10d: Cache Manager

**Purpose**: Implement CacheManager class per plan.md specification

- [ ] T222 Create CacheManager class skeleton in src/chronicle/cache/manager.py with __init__(cache_path: Path, repo_path: Path)
- [ ] T223 Implement CacheManager.load() method to load cache from disk, handling missing/corrupted files gracefully
- [ ] T224 Implement CacheManager.save() method to write cache to disk with atomic write (write to temp, rename)
- [ ] T225 Implement CacheManager.should_invalidate_all() method checking chronicle_version, llm_model, cache format version
- [ ] T226 Implement CacheManager.get_changed_files() method that calls git_utils and caches result
- [ ] T227 Implement CacheManager.is_file_changed(file_path: str) -> bool method
- [ ] T228 Implement CacheManager.get_explanation(file_path: str, line: int, name: str) -> str | None method
- [ ] T229 Implement CacheManager.store_explanation(file_path: str, line: int, name: str, signature: str, explanation: str) method for both functions and classes
- [ ] T230 Implement CacheManager.clear() method to delete cache file
- [ ] T231 Add advisory file locking with 5-second timeout per contracts/cache-api.md concurrency section
- [ ] T232 Update src/chronicle/cache/__init__.py exports with CacheManager, CacheEntry, AnalysisCache

### Phase 10e: Pipeline Integration

**Purpose**: Integrate caching into the documentation generation pipeline

- [ ] T233 Add cache_manager: CacheManager | None field to pipeline context/state in src/chronicle/pipeline.py
- [ ] T234 Initialize CacheManager in pipeline startup in src/chronicle/pipeline.py
- [ ] T235 Add cache loading step at pipeline start with logging: "[INFO] Loaded cache (git_ref: xxx, N function explanations)" in src/chronicle/pipeline.py
- [ ] T236 Modify function explanation generation to check cache first via cache_manager.get_explanation() in src/chronicle/pipeline.py
- [ ] T237 Modify class explanation generation to check cache first via cache_manager.get_explanation() in src/chronicle/pipeline.py
- [ ] T238 Add cache storage after each LLM explanation call via cache_manager.store_explanation() in src/chronicle/pipeline.py
- [ ] T239 Update cache git_ref to current HEAD after pipeline completes in src/chronicle/pipeline.py
- [ ] T240 Add cache save step at pipeline end with logging: "[INFO] Saved cache (git_ref: xxx, N entries)" in src/chronicle/pipeline.py
- [ ] T241 Add cache hit/miss statistics logging: "[INFO] Cache hit rate: X% (N/M explanations reused)" in src/chronicle/pipeline.py

### Phase 10f: CLI Integration

**Purpose**: Add cache-related CLI flags per plan.md specification

- [ ] T242 Add --no-cache flag to CLI (disables cache, forces full regeneration) in src/chronicle/cli.py
- [ ] T243 Add --clear-cache flag to CLI (deletes existing cache before running) in src/chronicle/cli.py
- [ ] T244 Add --cache-path PATH flag to CLI (custom cache file location, default: .chronicle/cache.json) in src/chronicle/cli.py
- [ ] T245 Pass cache flags through to pipeline initialization in src/chronicle/cli.py
- [ ] T246 Add cache statistics to CLI verbose output (changed files count, cache hit rate) in src/chronicle/cli.py

### Phase 10g: Testing

**Purpose**: Comprehensive test coverage for cache functionality

#### Unit Tests

- [ ] T247 [P] Unit tests for CacheEntry serialization in tests/unit/test_cache_models.py
- [ ] T248 [P] Unit tests for AnalysisCache serialization in tests/unit/test_cache_models.py
- [ ] T249 [P] Unit tests for cache version validation in tests/unit/test_cache_models.py
- [ ] T250 [P] Unit tests for get_changed_files() in tests/unit/test_git_utils.py (mock git subprocess)
- [ ] T251 [P] Unit tests for is_git_repository() in tests/unit/test_git_utils.py
- [ ] T252 Unit tests for CacheManager.load() with valid/invalid/missing cache in tests/unit/test_cache_manager.py
- [ ] T253 Unit tests for CacheManager.save() with atomic write verification in tests/unit/test_cache_manager.py
- [ ] T254 Unit tests for CacheManager.should_invalidate_all() scenarios in tests/unit/test_cache_manager.py
- [ ] T255 Unit tests for CacheManager.get_explanation() and store_explanation() in tests/unit/test_cache_manager.py

#### Integration Tests

- [ ] T256 Integration test: initial run creates cache file in tests/integration/test_incremental.py
- [ ] T257 Integration test: unchanged files use cached explanations (mock LLM not called) in tests/integration/test_incremental.py
- [ ] T258 Integration test: changed files regenerate explanations (mock LLM called) in tests/integration/test_incremental.py
- [ ] T259 Integration test: --no-cache flag bypasses cache entirely in tests/integration/test_incremental.py
- [ ] T260 Integration test: --clear-cache flag deletes cache before running in tests/integration/test_incremental.py
- [ ] T261 Integration test: corrupted cache triggers full regeneration with warning in tests/integration/test_incremental.py
- [ ] T262 Integration test: non-git repository skips caching gracefully in tests/integration/test_incremental.py

### Phase 10h: Polish & Documentation

**Purpose**: Final cleanup and documentation

- [ ] T263 Add cache-related logging per contracts/cache-api.md logging section (normal + verbose modes) in src/chronicle/utils/logging.py
- [ ] T264 Update quickstart.md with cache CLI flags documentation
- [ ] T265 Add .chronicle/cache.json to .gitignore template (optional - users can choose to commit or ignore)
- [ ] T266 Run full test suite to verify no regressions
- [ ] T267 Test cache with chronicle's own codebase (42 functions, 158 classes) to verify 90%+ LLM call reduction

**Checkpoint**: Incremental documentation updates complete - subsequent runs use cached explanations for unchanged files

---

### Phase 10 Dependencies

```
Phase 10a (Setup) ───────────────────────────────────┐
                                                     │
Phase 10b (Data Model) ──┬───────────────────────────┼──> Phase 10d (Cache Manager)
                         │                           │
Phase 10c (Git Detection)┘                           │
                                                     │
Phase 10d (Cache Manager) ───────────────────────────┼──> Phase 10e (Pipeline Integration)
                                                     │
                                                     ├──> Phase 10f (CLI Integration)
                                                     │
Phase 10e + 10f ─────────────────────────────────────┼──> Phase 10g (Testing)
                                                     │
Phase 10g (Testing) ─────────────────────────────────┴──> Phase 10h (Polish)
```

### Phase 10 Parallel Opportunities

Within Phase 10b:
```
T214 (CacheEntry) ─┬─> T216 (serialization)
T215 (AnalysisCache) ─┘
```

Within Phase 10c:
```
T218 (get_current_git_ref)  ─┬─> T221 (error handling)
T219 (get_changed_files)    ─┤
T220 (is_git_repository)    ─┘
```

Phases 10e and 10f can run in parallel once Phase 10d is complete.

Unit tests in Phase 10g (T247-T251) can all run in parallel.

### Expected Impact After Phase 10

| Scenario | Before (LLM calls) | After (LLM calls) | Reduction |
|----------|-------------------|-------------------|-----------|
| Initial run | 200 | 200 | 0% |
| No changes | 200 | 0 | 100% |
| 1 file edited | 200 | ~10 | 95% |
| 5 files edited | 200 | ~50 | 75% |

---

## Updated Summary (with Phase 10)

| Metric | Count |
|--------|-------|
| **Total Tasks** | 405 |
| **Phase 10 (Incremental Updates)** | 56 |
| **Phase 10 Parallelizable [P] Tasks** | 9 |

**Phase 10 Notes**:
- Cache file location: `.chronicle/cache.json` (default)
- Cache key format: `{file_path}:{line}:{name}`
- Git change detection: `git diff --name-only <cached_git_ref>`
- Full invalidation triggers: chronicle_version, llm_model, cache format version changes
- Non-git repos: Skip caching, full regeneration with warning
- Corrupted cache: Warning + full regeneration (graceful degradation)
