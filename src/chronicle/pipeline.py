"""Analysis pipeline orchestrator (Principle I: Deterministic-First).

Coordinates all deterministic analyzers and collects results before any LLM invocation.
"""

import logging
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from chronicle.analyzers import (
    ASTParser,
    DependencyParser,
    DirectDependencyResolver,
    ToolExecutionError,
    ToolNotAvailableError,
    get_registry,
    setup_default_adapters,
)
from chronicle.analyzers.diagrams.mermaid import generate_module_flowchart
from chronicle.analyzers.entry_points import detect_entry_points
from chronicle.analyzers.import_graph import build_import_graph
from chronicle.analyzers.integrations import detect_external_integrations
from chronicle.analyzers.config_context import collect_config_context
from chronicle.analyzers.module_detector import detect_modules
from chronicle.config import chronicleConfig
from chronicle.llm import (
    LLMError,
    create_client,
    generate_section_summary,
    get_placeholder,
    get_section_definition,
    get_system_prompt,
)
from chronicle.models import AnalysisError, Repository
from chronicle.models.analysis import (
    AnalysisResult,
    AnalysisStatus,
    Dependency,
    LanguageInfo,
)
from chronicle.models.canonical import CanonicalAST, CanonicalSBOM
from chronicle.models.llm_config import LLMConfig as LLMConfigModel

logger = logging.getLogger(__name__)


@dataclass
class PipelineOptions:
    """Options for controlling pipeline execution.

    Attributes:
        skip_sbom: Skip SBOM generation
        skip_architecture: Skip architecture diagram generation
        skip_ast: Skip AST parsing
        skip_dependencies: Skip dependency file parsing
        skip_llm: Skip LLM summary generation
        skip_flow_docs: Skip flow-based documentation generation (T084)
        skip_repomix: Skip Repomix codebase compression (T090)
        fail_fast: Stop on first error (otherwise continue and collect errors)
        exclude_patterns: File patterns to exclude from analysis
        verbose_llm: Enable verbose LLM logging (prompts and responses)
    """

    skip_sbom: bool = False
    skip_architecture: bool = False
    skip_ast: bool = False
    skip_dependencies: bool = False
    skip_llm: bool = False
    skip_flow_docs: bool = False  # T084: bypass flow-based documentation
    skip_repomix: bool = False  # T090: bypass Repomix codebase compression
    fail_fast: bool = False
    exclude_patterns: list[str] = field(default_factory=list)
    verbose_llm: bool = False  # Debug logging only - logs full prompts/responses


class AnalysisPipeline:
    """Orchestrates all deterministic analyzers in sequence.

    This pipeline implements Principle I (Deterministic-First) by running
    all deterministic analysis before any LLM invocation.

    The pipeline sequence:
    1. Dependency file parsing (package.json, requirements.txt, etc.)
    2. AST parsing (tree-sitter or fallback)
    3. SBOM generation (Syft)
    4. Architecture extraction (Terravision)

    All results are collected into AnalysisResult for template rendering.
    """

    def __init__(self, config: chronicleConfig | None = None) -> None:
        """Initialize the analysis pipeline.

        Args:
            config: chronicle configuration (uses defaults if None)
        """
        self.config = config
        self._ast_parser = ASTParser()
        self._dependency_parser = DependencyParser()

        # Set up tool registry with default adapters
        setup_default_adapters()
        self._registry = get_registry()

    def run(
        self,
        repository: Repository,
        options: PipelineOptions | None = None,
    ) -> AnalysisResult:
        """Execute the full analysis pipeline.

        Args:
            repository: Repository to analyze
            options: Pipeline execution options

        Returns:
            AnalysisResult with all collected data

        Raises:
            ValueError: If repository validation fails
        """
        options = options or PipelineOptions()

        # Validate repository
        warnings = repository.validate()
        for warning in warnings:
            logger.warning("Repository warning: %s", warning)

        # Initialize result
        result = AnalysisResult(
            repository_path=repository.path,
            repository_name=repository.name,
            timestamp=datetime.now(UTC),
            status=AnalysisStatus.RUNNING,
            git_ref=self._get_git_ref(repository.path),
        )

        logger.info("Starting analysis pipeline for %s", repository.name)

        try:
            # Stage 1: Dependency parsing
            if not options.skip_dependencies:
                self._run_dependency_analysis(repository, result, options)

            # Stage 1b: Repomix codebase compression (T090)
            if not options.skip_repomix:
                self._run_repomix_compression(repository, result, options)
            else:
                logger.info(
                    "Stage 1b: Skipping Repomix compression (--skip-repomix flag)"
                )

            # Stage 2: AST parsing
            if not options.skip_ast:
                self._run_ast_analysis(repository, result, options)

            # Stage 2b: Flow-based documentation (T084)
            if not options.skip_flow_docs and not options.skip_ast:
                self._run_flow_documentation(repository, result, options)

            # Stage 3: SBOM generation
            if not options.skip_sbom:
                self._run_sbom_analysis(repository, result, options)

            # Stage 4: Architecture extraction
            if not options.skip_architecture:
                self._run_architecture_analysis(repository, result, options)

            # Stage 5: LLM Summary Generation (Principle I: after all deterministic analysis)
            if not options.skip_llm:
                self._run_llm_summarization(result, options)
            else:
                # Apply placeholder summaries when LLM is explicitly skipped
                logger.info("Stage 5: Skipping LLM summaries (--skip-llm flag)")
                self._apply_placeholder_summaries(result)

            # Stage 6: Removed - function/class explanations replaced by holistic overview
            # Repomix provides system-wide understanding, making granular explanations redundant

            # Stage 7: Removed - module summaries replaced by holistic overview
            # The holistic overview's "Core Components" already describes module responsibilities

            # Stage 8: Holistic Overview Generation (T090)
            # Generates system-wide overview from compressed codebase
            if (
                not options.skip_repomix
                and not options.skip_llm
                and result.compressed_codebase
            ):
                self._run_holistic_overview(result, options)
            elif options.skip_repomix:
                logger.info("Stage 8: Skipping holistic overview (--skip-repomix flag)")

            # Mark complete (even with recoverable errors)
            if result.has_errors() and any(not e.recoverable for e in result.errors):
                result.status = AnalysisStatus.FAILED
            else:
                result.status = AnalysisStatus.COMPLETED

        except Exception as e:
            logger.error("Pipeline failed: %s", e)
            result.status = AnalysisStatus.FAILED
            result.add_error(
                AnalysisError(
                    component="pipeline",
                    message=str(e),
                    recoverable=False,
                )
            )

        logger.info(
            "Analysis complete: %s (%d errors)",
            result.status.value,
            len(result.errors),
        )

        return result

    def _run_dependency_analysis(
        self,
        repository: Repository,
        result: AnalysisResult,
        options: PipelineOptions,
    ) -> None:
        """Run dependency file parsing.

        Args:
            repository: Repository to analyze
            result: Result object to update
            options: Pipeline options
        """
        logger.info("Stage 1: Parsing dependency files")

        try:
            tech_stack = self._dependency_parser.parse_directory(repository.path)

            # Merge into result
            result.technology_stack = tech_stack

            logger.info(
                "Found %d languages, %d frameworks, %d dependencies",
                len(tech_stack.languages),
                len(tech_stack.frameworks),
                len(tech_stack.dependencies),
            )

        except Exception as e:
            error = AnalysisError(
                component="dependency",
                message=f"Dependency parsing failed: {e}",
                recoverable=True,
            )
            result.add_error(error)
            logger.warning("Dependency parsing failed: %s", e)

            if options.fail_fast:
                raise

    def _run_ast_analysis(
        self,
        repository: Repository,
        result: AnalysisResult,
        options: PipelineOptions,
    ) -> None:
        """Run AST parsing for source code analysis.

        Args:
            repository: Repository to analyze
            result: Result object to update
            options: Pipeline options
        """
        logger.info("Stage 2: Parsing source code AST")

        try:
            ast_result = self._ast_parser.parse_directory(
                repository.path,
                exclude_patterns=options.exclude_patterns or None,
            )

            result.source_analysis = ast_result

            # Update language info from AST
            self._update_languages_from_ast(result, ast_result)

            logger.info(
                "Parsed %d modules, %d classes, %d functions",
                ast_result.module_count,
                ast_result.class_count,
                ast_result.function_count,
            )

        except Exception as e:
            error = AnalysisError(
                component="ast",
                message=f"AST parsing failed: {e}",
                recoverable=True,
            )
            result.add_error(error)
            logger.warning("AST parsing failed: %s", e)

            if options.fail_fast:
                raise

    def _run_flow_documentation(
        self,
        repository: Repository,
        result: AnalysisResult,
        options: PipelineOptions,
    ) -> None:
        """Run flow-based documentation analysis (T084).

        Generates module-level documentation including:
        - Module detection and grouping
        - Import graph analysis
        - Entry point detection
        - External integration detection
        - Mermaid diagram generation

        Args:
            repository: Repository to analyze
            result: Result object to update
            options: Pipeline options
        """
        logger.info("Stage 2b: Generating flow-based documentation")

        repo_path = repository.path

        # Detect modules
        try:
            detected_modules = detect_modules(repo_path)
            logger.info("Detected %d modules", len(detected_modules))
        except Exception as e:
            error = AnalysisError(
                component="flow_docs",
                message=f"Module detection failed: {e}",
                recoverable=True,
            )
            result.add_error(error)
            logger.warning("Module detection failed: %s", e)
            detected_modules = []

            if options.fail_fast:
                raise

        # Build import graph (requires AST result)
        import_graph = None
        if result.source_analysis:
            try:
                import_graph = build_import_graph(
                    repo_path,
                    result.source_analysis,
                    detected_modules,
                )
                logger.info(
                    "Built import graph: %d nodes, %d edges",
                    len(import_graph.nodes),
                    len(import_graph.edges),
                )
            except Exception as e:
                error = AnalysisError(
                    component="flow_docs",
                    message=f"Import graph building failed: {e}",
                    recoverable=True,
                )
                result.add_error(error)
                logger.warning("Import graph building failed: %s", e)

                if options.fail_fast:
                    raise

        # Detect entry points
        try:
            entry_points = detect_entry_points(repo_path)
            result.entry_points = entry_points
            logger.info("Detected %d entry points", len(entry_points))
        except Exception as e:
            error = AnalysisError(
                component="flow_docs",
                message=f"Entry point detection failed: {e}",
                recoverable=True,
            )
            result.add_error(error)
            logger.warning("Entry point detection failed: %s", e)

            if options.fail_fast:
                raise

        # Detect external integrations
        try:
            integrations = detect_external_integrations(repo_path)
            result.external_integrations = integrations
            logger.info("Detected %d external integrations", len(integrations))
        except Exception as e:
            error = AnalysisError(
                component="flow_docs",
                message=f"External integration detection failed: {e}",
                recoverable=True,
            )
            result.add_error(error)
            logger.warning("External integration detection failed: %s", e)

            if options.fail_fast:
                raise

        # Generate Mermaid diagram
        if import_graph:
            try:
                module_diagram = generate_module_flowchart(
                    import_graph,
                    title=f"{repository.name} Module Dependencies",
                )
                result.module_flow_diagram = module_diagram
                logger.info(
                    "Generated module flowchart: %d nodes, simplified=%s",
                    module_diagram.node_count,
                    module_diagram.simplified,
                )
            except Exception as e:
                error = AnalysisError(
                    component="flow_docs",
                    message=f"Mermaid diagram generation failed: {e}",
                    recoverable=True,
                )
                result.add_error(error)
                logger.warning("Mermaid diagram generation failed: %s", e)

                if options.fail_fast:
                    raise

        # Store detected modules (to be enriched with LLM summaries later)
        # Convert CanonicalModule to ModuleSummary placeholders
        from chronicle.models.canonical.module import ModuleSummary

        module_summaries = []
        for module in detected_modules:
            module_summaries.append(
                ModuleSummary(
                    name=module.name,
                    path=module.path,
                    language=module.language,
                    responsibility="",  # Will be filled by LLM
                    key_classes=module.classes[:5] if module.classes else [],
                    key_functions=module.functions[:5] if module.functions else [],
                    file_count=len(module.files) if module.files else 0,
                )
            )
        result.modules = module_summaries

    def _run_sbom_analysis(
        self,
        repository: Repository,
        result: AnalysisResult,
        options: PipelineOptions,
    ) -> None:
        """Run SBOM generation.

        Args:
            repository: Repository to analyze
            result: Result object to update
            options: Pipeline options
        """
        logger.info("Stage 3: Generating SBOM")

        tool_name = self.config.tools.sbom if self.config else "syft"

        try:
            # Create DirectDependencyResolver to mark direct dependencies
            dependency_resolver = DirectDependencyResolver()

            # Get adapter from registry - we need to handle syft specially
            # to pass the dependency resolver
            if tool_name == "syft":
                from chronicle.analyzers.sbom.syft import SyftAdapter

                adapter = SyftAdapter(
                    name="syft",
                    dependency_resolver=dependency_resolver,
                )
            else:
                adapter = self._registry.get_sbom_adapter(tool_name)

            result.tool_versions["sbom"] = adapter.version or "unknown"

            sbom = adapter.execute(repository.path)
            result.sbom = sbom

            # Merge SBOM data into technology stack
            self._merge_sbom_data(result, sbom)

            logger.info(
                "SBOM: %d packages (%d direct, %s)",
                sbom.package_count,
                sbom.direct_package_count,
                ", ".join(sbom.get_unique_ecosystems()),
            )

        except ToolNotAvailableError as e:
            error = AnalysisError(
                component="sbom",
                message=str(e),
                recoverable=True,
            )
            result.add_error(error)
            logger.warning("SBOM tool not available: %s", e)

        except ToolExecutionError as e:
            error = AnalysisError(
                component="sbom",
                message=str(e),
                recoverable=True,
            )
            result.add_error(error)
            logger.warning("SBOM generation failed: %s", e)

            if options.fail_fast:
                raise

        except Exception as e:
            error = AnalysisError(
                component="sbom",
                message=f"Unexpected SBOM error: {e}",
                recoverable=True,
            )
            result.add_error(error)
            logger.warning("SBOM generation failed: %s", e)

            if options.fail_fast:
                raise

    def _run_architecture_analysis(
        self,
        repository: Repository,
        result: AnalysisResult,
        options: PipelineOptions,
    ) -> None:
        """Run architecture diagram generation.

        Args:
            repository: Repository to analyze
            result: Result object to update
            options: Pipeline options
        """
        logger.info("Stage 4: Extracting architecture")

        tool_name = self.config.tools.diagrams if self.config else "terravision"

        try:
            adapter = self._registry.get_diagram_adapter(tool_name)
            result.tool_versions["diagrams"] = adapter.version or "unknown"

            architecture = adapter.execute(repository.path)
            result.architecture = architecture

            logger.info(
                "Architecture: %d nodes, %d connections (%s)",
                architecture.graph.node_count,
                architecture.graph.connection_count,
                ", ".join(architecture.cloud_providers) or "no cloud",
            )

        except ToolNotAvailableError as e:
            error = AnalysisError(
                component="architecture",
                message=str(e),
                recoverable=True,
            )
            result.add_error(error)
            logger.warning("Diagram tool not available: %s", e)

        except ToolExecutionError as e:
            error = AnalysisError(
                component="architecture",
                message=str(e),
                recoverable=True,
            )
            result.add_error(error)
            logger.warning("Architecture extraction failed: %s", e)

            if options.fail_fast:
                raise

        except Exception as e:
            error = AnalysisError(
                component="architecture",
                message=f"Unexpected architecture error: {e}",
                recoverable=True,
            )
            result.add_error(error)
            logger.warning("Architecture extraction failed: %s", e)

            if options.fail_fast:
                raise

    def _run_llm_summarization(
        self,
        result: AnalysisResult,
        options: PipelineOptions,  # noqa: ARG002
    ) -> None:
        """Run LLM summary generation for documentation sections.

        Implements Principle I: Only runs after all deterministic analysis.
        Implements Principle II: Uses temperature=0 for reproducibility.

        Args:
            result: Analysis result with deterministic data
            options: Pipeline options
        """
        logger.info("Stage 5: Generating LLM summaries")

        # Check if LLM is configured
        if not self.config or not self.config.llm.enabled:
            logger.info("LLM disabled, using placeholder summaries")
            self._apply_placeholder_summaries(result)
            return

        # Create LLM client
        # Note: LLM is REQUIRED per spec. Preflight check should have validated availability.
        # If we reach here without skip_llm, LLM must be available.
        try:
            # Convert config LLMConfig to models.llm_config.LLMConfig
            llm_config = LLMConfigModel(
                provider=self.config.llm.provider,
                model=self.config.llm.model,
                api_key=self.config.llm.api_key,
                api_base=self.config.llm.api_base,
                max_tokens=self.config.llm.max_tokens,
            )
            client = create_client(llm_config)
        except (ValueError, LLMError) as e:
            # LLM client creation failed - this is a fatal error
            error = AnalysisError(
                component="llm",
                message=f"Failed to create LLM client: {e}",
                recoverable=False,  # LLM is required
            )
            result.add_error(error)
            logger.error("LLM client creation failed: %s", e)
            raise ValueError(f"LLM is required but client creation failed: {e}") from e

        # Check LLM availability
        if not client.check_available():
            # LLM not available - this is a fatal error
            provider = self.config.llm.provider
            help_msg = self._get_llm_help_message(provider)
            error = AnalysisError(
                component="llm",
                message=f"LLM provider {provider} is not available. {help_msg}",
                recoverable=False,  # LLM is required
            )
            result.add_error(error)
            logger.error(
                "LLM provider %s not available. %s",
                provider,
                help_msg,
            )
            raise ValueError(
                f"LLM is required but provider {provider} is not available. {help_msg}"
            )

        # Generate summaries using structured multi-call prompting
        self._run_structured_prompting(client, result, options)

        sections = ["overview", "tech_stack", "architecture", "dependencies"]
        logger.info(
            "LLM summarization complete: %d/%d sections generated",
            sum(1 for s in result.llm_summaries.values() if not s.startswith("*")),
            len(sections),
        )

    def _run_structured_prompting(
        self,
        client,
        result: AnalysisResult,
        options: PipelineOptions,
    ) -> None:
        """Run structured multi-call prompting strategy (T065x-y).

        Breaks each section into focused sub-section calls for better quality.

        Args:
            client: LLM client
            result: Analysis result to update
            options: Pipeline options (for verbose logging)
        """
        sections = ["overview", "tech_stack", "architecture", "dependencies"]

        for section_name in sections:
            section_def = get_section_definition(section_name)

            if not section_def:
                # Fall back to placeholder if no definition
                logger.warning("No section definition for %s", section_name)
                result.llm_summaries[section_name] = get_placeholder(section_name)
                continue

            try:
                # Build data dict from analysis result
                data = self._build_section_data(result, section_name)

                # Get system prompt
                system_prompt = get_system_prompt(section_name)

                # Generate using structured prompting
                summary, responses = generate_section_summary(
                    client=client,
                    section_def=section_def,
                    data=data,
                    system_prompt=system_prompt,
                    verbose=options.verbose_llm,
                )

                if summary:
                    result.llm_summaries[section_name] = summary
                    logger.info(
                        "Generated %s summary via structured prompting (%d sub-sections, %d chars)",
                        section_name,
                        len(responses),
                        len(summary),
                    )
                else:
                    result.llm_summaries[section_name] = get_placeholder(section_name)
                    logger.warning(
                        "Structured prompting produced empty summary for %s",
                        section_name,
                    )

            except LLMError as e:
                logger.warning(
                    "Structured prompting failed for %s: %s - using placeholder",
                    section_name,
                    e,
                )
                result.llm_summaries[section_name] = get_placeholder(section_name)

            except Exception as e:
                logger.warning(
                    "Unexpected error in structured prompting for %s: %s - using placeholder",
                    section_name,
                    e,
                )
                result.llm_summaries[section_name] = get_placeholder(section_name)

    def _build_section_data(self, result: AnalysisResult, section_name: str) -> dict:
        """Build data dictionary for structured prompting.

        Args:
            result: Analysis result
            section_name: Section to build data for

        Returns:
            Data dictionary with relevant facts
        """
        data: dict = {}

        # Common data
        data["repository_name"] = result.repository_name

        # Technology stack
        if result.technology_stack:
            ts = result.technology_stack
            data["languages"] = [
                {"name": l.name, "version": l.version, "file_count": l.file_count}
                for l in ts.languages
            ]
            data["frameworks"] = [
                {"name": f.name, "version": f.version} for f in ts.frameworks
            ]
            data["key_dependencies"] = [
                {"name": d.name, "version": d.version, "ecosystem": d.ecosystem}
                for d in ts.dependencies[:15]
            ]

        # SBOM data
        if result.sbom:
            data["total_packages"] = result.sbom.package_count
            data["direct_packages"] = result.sbom.direct_package_count
            data["ecosystems"] = result.sbom.get_unique_ecosystems()
            data["direct_dependencies"] = [
                {"name": p.name, "version": p.version, "ecosystem": p.ecosystem}
                for p in result.sbom.get_direct_packages()[:20]
            ]

        # Architecture data
        if result.architecture and result.architecture.graph:
            graph = result.architecture.graph
            data["cloud_providers"] = result.architecture.cloud_providers
            data["node_count"] = graph.node_count
            data["connections"] = graph.connection_count

            # Resources by type
            resources_by_type: dict[str, list[str]] = {}
            for _node_id, node in graph.nodes.items():
                if node.type not in resources_by_type:
                    resources_by_type[node.type] = []
                resources_by_type[node.type].append(node.name)
            data["resources_by_type"] = resources_by_type
            data["resources"] = [
                {"id": node_id, "type": node.type, "name": node.name}
                for node_id, node in list(graph.nodes.items())[:20]
            ]

            # Terraform variables if available
            if result.architecture.source and result.architecture.source.metadata:
                tf_vars = result.architecture.source.metadata.get(
                    "terraform_variables", {}
                )
                data["terraform_variables"] = tf_vars

        # Source analysis
        if result.source_analysis:
            sa = result.source_analysis
            data["modules"] = [
                {"path": m.path, "language": m.language, "imports": len(m.imports)}
                for m in sa.modules[:15]
            ]
            data["total_modules"] = len(sa.modules)
            data["classes"] = [
                {
                    "name": c.name,
                    "file": c.file,
                    "methods": len(c.methods) if c.methods else 0,
                }
                for c in sa.classes[:10]
            ]
            data["functions"] = [
                {"name": f.name, "file": f.file, "is_async": f.is_async}
                for f in sa.functions[:10]
            ]
            data["entry_points"] = [
                {"name": e.name, "type": e.type} for e in sa.entry_points
            ]

        return data

    def _apply_placeholder_summaries(self, result: AnalysisResult) -> None:
        """Apply placeholder text for all sections when LLM is unavailable.

        Args:
            result: Analysis result to update
        """
        sections = ["overview", "tech_stack", "architecture", "dependencies"]
        for section in sections:
            result.llm_summaries[section] = get_placeholder(section)

    def _get_llm_help_message(self, provider: str) -> str:
        """Get provider-specific help message for LLM connectivity issues.

        Args:
            provider: LLM provider name

        Returns:
            Help message string
        """
        help_messages = {
            "ollama": "Ensure Ollama is running with 'ollama serve' and the model is pulled.",
            "claude": "Verify your ANTHROPIC_API_KEY is valid. Run 'chronicle check' to diagnose.",
            "gemini": "Verify your GOOGLE_API_KEY is valid. Run 'chronicle check' to diagnose.",
            "bedrock": (
                "Verify AWS credentials and Bedrock access. Check:\n"
                "  1. AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set\n"
                "  2. Your IAM role has bedrock:InvokeModel permission\n"
                "  3. The model is enabled in your AWS Bedrock console\n"
                "  4. AWS_REGION is set to a Bedrock-supported region"
            ),
        }
        return help_messages.get(
            provider,
            f"Run 'chronicle init' to configure a different LLM provider.",
        )

    def _get_git_ref(self, repo_path: Path) -> str | None:
        """Get current git commit SHA.

        Args:
            repo_path: Repository path

        Returns:
            Git commit SHA or None if not a git repo
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=str(repo_path),
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return None

    def _update_languages_from_ast(
        self,
        result: AnalysisResult,
        ast: CanonicalAST,
    ) -> None:
        """Update language info from AST parsing results.

        Args:
            result: Analysis result to update
            ast: AST parsing result
        """
        # Count files per language
        language_files: dict[str, int] = {}
        for module in ast.modules:
            lang = module.language
            language_files[lang] = language_files.get(lang, 0) + 1

        # Update or add language info
        existing_langs = {lang.name for lang in result.technology_stack.languages}

        for lang_name, file_count in language_files.items():
            if lang_name in existing_langs:
                # Update file count
                for lang_info in result.technology_stack.languages:
                    if lang_info.name == lang_name:
                        lang_info.file_count = file_count
                        break
            else:
                # Add new language
                result.technology_stack.languages.append(
                    LanguageInfo(name=lang_name, file_count=file_count)
                )

    def _merge_sbom_data(
        self,
        result: AnalysisResult,
        sbom: CanonicalSBOM,
    ) -> None:
        """Merge SBOM package data into technology stack.

        Enriches dependency info with license data from SBOM.

        Args:
            result: Analysis result to update
            sbom: SBOM data to merge
        """
        # Build lookup of existing dependencies
        existing_deps = {
            (d.name, d.ecosystem): d for d in result.technology_stack.dependencies
        }

        for pkg in sbom.packages:
            key = (pkg.name, pkg.ecosystem)
            if key in existing_deps:
                # Enrich with license info
                if pkg.license and not existing_deps[key].license:
                    existing_deps[key].license = pkg.license
            else:
                # Add new dependency from SBOM
                result.technology_stack.dependencies.append(
                    Dependency(
                        name=pkg.name,
                        ecosystem=pkg.ecosystem,
                        version=pkg.version,
                        license=pkg.license,
                        source_file=pkg.source_file or "SBOM",
                    )
                )

    # _run_module_summaries removed - holistic overview provides module descriptions

    def _run_repomix_compression(
        self,
        repository: Repository,
        result: AnalysisResult,
        options: PipelineOptions,
    ) -> None:
        """Stage 1b: Compress codebase using Repomix (T090a-b).

        Uses tree-sitter skeleton extraction for holistic LLM analysis.

        Args:
            repository: Repository to analyze
            result: Analysis result to populate
            options: Pipeline options
        """
        logger.info("Stage 1b: Compressing codebase with Repomix")

        try:
            from chronicle.analyzers.repomix import RepomixAdapter

            # Get additional exclude patterns from config
            additional_excludes = (
                options.exclude_patterns if options.exclude_patterns else None
            )

            adapter = RepomixAdapter()
            compressed = adapter.compress(
                repo_path=repository.path,
                additional_excludes=additional_excludes,
            )

            result.compressed_codebase = compressed

            # Record tool version
            version = adapter.get_version()
            if version:
                result.tool_versions["repomix"] = version

            logger.info(
                "Codebase compressed: %d files, %d tokens, %d chars",
                compressed.file_count,
                compressed.token_count,
                len(compressed.compressed_content),
            )

        except Exception as e:
            error = AnalysisError(
                component="repomix",
                message=f"Repomix compression failed: {e}",
                recoverable=True,  # Repomix is optional for basic documentation
            )
            result.add_error(error)
            logger.warning("Repomix compression failed: %s", e)

    def _run_holistic_overview(
        self,
        result: AnalysisResult,
        options: PipelineOptions,
    ) -> None:
        """Stage 8: Generate holistic overview from compressed codebase (T090c-d).

        Uses single LLM call with Repomix-compressed content for system-wide understanding.

        Args:
            result: Analysis result with compressed_codebase
            options: Pipeline options
        """
        logger.info("Stage 8: Generating holistic overview")

        if not result.compressed_codebase:
            logger.info(
                "No compressed codebase available, skipping holistic overview",
            )
            return

        if not self.config or not self.config.llm.enabled:
            logger.info("LLM disabled, skipping holistic overview")
            return

        # Create LLM client
        try:
            llm_config = LLMConfigModel(
                provider=self.config.llm.provider,
                model=self.config.llm.model,
                api_key=self.config.llm.api_key,
                api_base=self.config.llm.api_base,
                max_tokens=self.config.llm.max_tokens,
            )
            client = create_client(llm_config)
        except (ValueError, LLMError) as e:
            error = AnalysisError(
                component="holistic_overview",
                message=f"Failed to create LLM client for holistic overview: {e}",
                recoverable=True,
            )
            result.add_error(error)
            logger.warning("Holistic overview generation skipped: %s", e)
            return

        # Get languages from technology stack
        languages = []
        if result.technology_stack and result.technology_stack.languages:
            languages = [lang.name for lang in result.technology_stack.languages]

        # Collect config context (README, pyproject.toml, config files, etc.)
        # This gives the LLM additional context about integrations and dependencies
        config_context = collect_config_context(result.repository_path)

        # Combine compressed code with config context
        enhanced_content = result.compressed_codebase.compressed_content
        if config_context:
            enhanced_content = enhanced_content + "\n" + config_context

        try:
            from chronicle.llm.client import generate_holistic_overview

            overview = generate_holistic_overview(
                client=client,
                compressed_content=enhanced_content,
                repository_name=result.repository_name,
                languages=languages,
                file_count=result.compressed_codebase.file_count,
                verbose=options.verbose_llm,
            )

            result.holistic_overview = overview

            logger.info(
                "Holistic overview generated: purpose=%d chars, %d components",
                len(overview.purpose),
                len(overview.core_components),
            )

        except LLMError as e:
            error = AnalysisError(
                component="holistic_overview",
                message=f"Holistic overview generation failed: {e}",
                recoverable=True,
            )
            result.add_error(error)
            logger.warning("Holistic overview generation failed: %s", e)
