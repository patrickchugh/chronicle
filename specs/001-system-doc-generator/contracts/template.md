# Template Contract: Default Documentation Structure

**Date**: 2026-01-31
**Branch**: `001-system-doc-generator`

## Overview

This contract defines the default Jinja2 template structure for chronicle-generated documentation. The template is implemented at `src/chronicle/templates/default.md.j2`.

---

## Section Order

| # | Section | Content Source | Human Merge Support |
|---|---------|----------------|---------------------|
| 1 | Title & Metadata | Deterministic | No |
| 2 | Overview & Summary | LLM | Yes |
| 3 | Technology Stack | Deterministic | No |
| 4 | Architecture & Diagrams | Deterministic + LLM | Yes |
| 5 | Infrastructure | Deterministic (Terraform) | Yes |
| 6 | Data | Deterministic (ORM/Schema) + LLM | Yes |
| 7 | Security | Deterministic + LLM | Yes |
| 8 | Resilience & Operations | Deterministic + LLM | Yes |
| 9 | API Documentation | Deterministic (AST) + LLM | Yes |
| 10 | Build & Deployment | Deterministic (Config Files) | Yes |
| 11 | Testing | Deterministic (AST + Config) | Yes |
| 12 | Logging & Error Handling | Deterministic (AST) + LLM | Yes |
| 13 | Risks & Recommendations | LLM | Yes |
| 14 | Dependencies (SBOM) | Deterministic | No |
| 15 | Version History | Deterministic | No |

---

## Section Definitions

### 1. Title & Metadata

**Content Source**: Deterministic (repository data)

```markdown
# {{ repository.name }} - System Documentation

| Property | Value |
|----------|-------|
| Repository | {{ repository.url or repository.path }} |
| Branch | {{ repository.branch }} |
| Commit | {{ repository.commit_sha[:8] }} |
| Generated | {{ generated_at | datetime }} |
```

**Template Variables**:
- `repository.name` - Repository name
- `repository.url` - Remote URL (if available)
- `repository.path` - Local path
- `repository.branch` - Current branch
- `repository.commit_sha` - Full commit SHA
- `generated_at` - Generation timestamp (ISO 8601)

---

### 2. Overview & Summary

**Content Source**: LLM-generated summary
**Human Merge**: Yes (via `sections.overview` config)

```markdown
## Overview

{{ sections.overview.human_content if sections.overview.strategy == 'prepend' }}

{{ llm_summaries.overview }}

### Subcomponents

{% for component in source_analysis.components %}
- **{{ component.name }}** - {{ component.description }}
{% endfor %}

{{ sections.overview.human_content if sections.overview.strategy == 'append' }}
```

**LLM Prompt Context**:
- Repository metadata
- Technology stack summary
- Entry points detected
- Module/package structure
- Primary frameworks

**Purpose**: Provide a 2-3 paragraph executive summary of what the system does, its primary purpose, key technologies, and major subcomponents.

---

### 3. Technology Stack

**Content Source**: Deterministic (AST + dependency analysis)

```markdown
## Technology Stack

### Languages

| Language | Files | Lines of Code |
|----------|-------|---------------|
{% for lang in technology_stack.languages %}
| {{ lang.name }} | {{ lang.file_count }} | {{ lang.loc }} |
{% endfor %}

### Frameworks & Libraries

{% for framework in technology_stack.frameworks %}
- **{{ framework.name }}** ({{ framework.version }}) - {{ framework.category }}
{% endfor %}

### Runtime Dependencies

| Package | Version | License |
|---------|---------|---------|
{% for dep in technology_stack.dependencies[:20] %}
| {{ dep.name }} | {{ dep.version }} | {{ dep.license }} |
{% endfor %}
{% if technology_stack.dependencies | length > 20 %}
*... and {{ technology_stack.dependencies | length - 20 }} more (see SBOM section)*
{% endif %}
```

**Template Variables**:
- `technology_stack.languages[]` - Detected languages with stats
- `technology_stack.frameworks[]` - Detected frameworks
- `technology_stack.dependencies[]` - Direct dependencies

---

### 4. Architecture & Diagrams

**Content Source**: Deterministic (Terravision, AST) + LLM description
**Human Merge**: Yes (via `sections.architecture` config)

```markdown
## Architecture & Diagrams

{{ sections.architecture.human_content if sections.architecture.strategy == 'prepend' }}

{% if architecture.infrastructure_diagram.available %}
### Infrastructure Diagram

![Infrastructure Diagram]({{ architecture.infrastructure_diagram.path }})

*Generated from Terraform configuration using Terravision*
{% endif %}

{% if architecture.component_diagram.available %}
### Component Diagram

```mermaid
{{ architecture.component_diagram.mermaid }}
```

*Generated from code module analysis*
{% endif %}

{% if architecture.connectivity_diagram.available %}
### External Connectivity

```mermaid
{{ architecture.connectivity_diagram.mermaid }}
```
{% endif %}

### Architecture Description

{{ llm_summaries.architecture }}

{{ sections.architecture.human_content if sections.architecture.strategy == 'append' }}
```

**Diagram Types**:

| Diagram | Source | Format |
|---------|--------|--------|
| Infrastructure | Terravision (Terraform) | PNG/SVG |
| Component | AST module relationships | Mermaid |
| Connectivity | Terraform SGs + code API clients | Mermaid |

**Mermaid Generation** (from AST):
- Module import graph → component relationships
- Class hierarchies → class diagrams
- External service calls → connectivity diagram

**Template Variables**:
- `architecture.infrastructure_diagram.available` - Whether Terraform diagram was generated
- `architecture.infrastructure_diagram.path` - Relative path to diagram image
- `architecture.component_diagram.available` - Whether component diagram was generated
- `architecture.component_diagram.mermaid` - Mermaid diagram source
- `architecture.connectivity_diagram.available` - Whether connectivity diagram was generated
- `architecture.connectivity_diagram.mermaid` - Mermaid diagram source
- `llm_summaries.architecture` - LLM description of architecture

---

### 5. Infrastructure

**Content Source**: Deterministic (Terraform parsing)
**Human Merge**: Yes (via `sections.infrastructure` config)

```markdown
## Infrastructure

{{ sections.infrastructure.human_content if sections.infrastructure.strategy == 'prepend' }}

{% if infrastructure.available %}

### Compute Resources

| Resource | Type | Configuration |
|----------|------|---------------|
{% for resource in infrastructure.compute %}
| {{ resource.name }} | {{ resource.type }} | {{ resource.config_summary }} |
{% endfor %}

### Storage Resources

| Resource | Type | Configuration |
|----------|------|---------------|
{% for resource in infrastructure.storage %}
| {{ resource.name }} | {{ resource.type }} | {{ resource.config_summary }} |
{% endfor %}

### Networking

| Resource | Type | Configuration |
|----------|------|---------------|
{% for resource in infrastructure.networking %}
| {{ resource.name }} | {{ resource.type }} | {{ resource.config_summary }} |
{% endfor %}

### Cloud Services

| Service | Provider | Purpose |
|---------|----------|---------|
{% for service in infrastructure.services %}
| {{ service.name }} | {{ service.provider }} | {{ service.purpose }} |
{% endfor %}

{% else %}
*No Terraform configuration detected.*
{% endif %}

{{ sections.infrastructure.human_content if sections.infrastructure.strategy == 'append' }}
```

**Resource Categories**:

| Category | Terraform Resource Types |
|----------|-------------------------|
| Compute | `aws_instance`, `aws_ecs_*`, `aws_lambda_*`, `google_compute_*`, `azurerm_virtual_machine` |
| Storage | `aws_s3_*`, `aws_rds_*`, `aws_dynamodb_*`, `google_storage_*`, `azurerm_storage_*` |
| Networking | `aws_vpc`, `aws_subnet`, `aws_security_group`, `aws_lb_*`, `aws_route53_*` |
| Services | `aws_sqs_*`, `aws_sns_*`, `aws_cloudwatch_*`, managed services |

**Template Variables**:
- `infrastructure.available` - Whether Terraform was detected
- `infrastructure.compute[]` - Compute resources
- `infrastructure.storage[]` - Storage resources
- `infrastructure.networking[]` - Network resources
- `infrastructure.services[]` - Cloud services

---

### 6. Data

**Content Source**: Deterministic (ORM/Schema detection) + LLM
**Human Merge**: Yes (via `sections.data` config)

```markdown
## Data

{{ sections.data.human_content if sections.data.strategy == 'prepend' }}

{% if data.models %}
### Data Models

{% for model in data.models %}
#### {{ model.name }}
{% if model.table_name %}*Table: `{{ model.table_name }}`*{% endif %}

| Field | Type | Constraints |
|-------|------|-------------|
{% for field in model.fields %}
| {{ field.name }} | {{ field.type }} | {{ field.constraints | join(', ') }} |
{% endfor %}

{% endfor %}
{% endif %}

{% if data.stores %}
### Data Stores

| Store | Type | Purpose |
|-------|------|---------|
{% for store in data.stores %}
| {{ store.name }} | {{ store.type }} | {{ store.purpose }} |
{% endfor %}
{% endif %}

### Data Protection

{{ llm_summaries.data_protection }}

{{ sections.data.human_content if sections.data.strategy == 'append' }}
```

**Detection Sources**:

| ORM/Schema Type | Detection Method |
|-----------------|------------------|
| SQLAlchemy | AST: classes inheriting from `Base` with `Column` attributes |
| Django ORM | AST: classes inheriting from `models.Model` |
| Prisma | File: `schema.prisma` parsing |
| TypeORM | AST: classes with `@Entity()` decorator |
| SQL Migrations | File: `*.sql` in `migrations/` directories |

**Template Variables**:
- `data.models[]` - Detected data models
- `data.models[].name` - Model/entity name
- `data.models[].table_name` - Database table name
- `data.models[].fields[]` - Field definitions
- `data.stores[]` - Detected data stores (databases, caches)
- `llm_summaries.data_protection` - LLM analysis of data protection patterns

---

### 7. Security

**Content Source**: Deterministic (Terraform + code patterns) + LLM
**Human Merge**: Yes (via `sections.security` config)

```markdown
## Security

{{ sections.security.human_content if sections.security.strategy == 'prepend' }}

{% if security.iam %}
### IAM & Access Control

| Resource | Type | Permissions Summary |
|----------|------|---------------------|
{% for iam in security.iam %}
| {{ iam.name }} | {{ iam.type }} | {{ iam.permissions_summary }} |
{% endfor %}
{% endif %}

{% if security.auth_patterns %}
### Authentication Patterns

{% for pattern in security.auth_patterns %}
- **{{ pattern.type }}**: {{ pattern.description }} ({{ pattern.location }})
{% endfor %}
{% endif %}

{% if security.secrets_management %}
### Secret Management

| Pattern | Location | Notes |
|---------|----------|-------|
{% for secret in security.secrets_management %}
| {{ secret.pattern }} | {{ secret.location }} | {{ secret.notes }} |
{% endfor %}
{% endif %}

{% if sbom.vulnerabilities %}
### Dependency Vulnerabilities

| Package | Severity | CVE | Description |
|---------|----------|-----|-------------|
{% for vuln in sbom.vulnerabilities[:10] %}
| {{ vuln.package }} | {{ vuln.severity }} | {{ vuln.cve }} | {{ vuln.description }} |
{% endfor %}
{% if sbom.vulnerabilities | length > 10 %}
*... and {{ sbom.vulnerabilities | length - 10 }} more vulnerabilities*
{% endif %}
{% endif %}

### Security Analysis

{{ llm_summaries.security }}

{{ sections.security.human_content if sections.security.strategy == 'append' }}
```

**Detection Sources**:

| Security Aspect | Detection Source |
|-----------------|------------------|
| IAM Policies | Terraform: `aws_iam_*`, `google_*_iam_*` |
| Security Groups | Terraform: `aws_security_group`, ingress/egress rules |
| Auth Middleware | AST: JWT libraries, OAuth handlers, session middleware |
| Secret Management | AST: AWS Secrets Manager, HashiCorp Vault, env var patterns |
| Vulnerabilities | SBOM: CVE database lookup via Syft |

**Template Variables**:
- `security.iam[]` - IAM resources and policies
- `security.auth_patterns[]` - Detected authentication patterns
- `security.secrets_management[]` - Secret handling patterns
- `sbom.vulnerabilities[]` - Known CVEs in dependencies
- `llm_summaries.security` - LLM security analysis

---

### 8. Resilience & Operations

**Content Source**: Deterministic (Terraform + config patterns) + LLM
**Human Merge**: Yes (via `sections.resilience` config)

```markdown
## Resilience & Operations

{{ sections.resilience.human_content if sections.resilience.strategy == 'prepend' }}

{% if resilience.scalability %}
### Scalability

| Resource | Scaling Type | Configuration |
|----------|--------------|---------------|
{% for scale in resilience.scalability %}
| {{ scale.resource }} | {{ scale.type }} | {{ scale.config }} |
{% endfor %}
{% endif %}

{% if resilience.high_availability %}
### High Availability

| Feature | Configuration | Notes |
|---------|---------------|-------|
{% for ha in resilience.high_availability %}
| {{ ha.feature }} | {{ ha.config }} | {{ ha.notes }} |
{% endfor %}
{% endif %}

{% if resilience.observability %}
### Observability

| Tool | Type | Integration |
|------|------|-------------|
{% for obs in resilience.observability %}
| {{ obs.tool }} | {{ obs.type }} | {{ obs.integration }} |
{% endfor %}
{% endif %}

### Operational Analysis

{{ llm_summaries.resilience }}

{{ sections.resilience.human_content if sections.resilience.strategy == 'append' }}
```

**Detection Sources**:

| Resilience Aspect | Detection Source |
|-------------------|------------------|
| Auto-scaling | Terraform: `aws_autoscaling_*`, ECS service scaling |
| Multi-AZ | Terraform: availability zone configurations |
| Load Balancing | Terraform: `aws_lb_*`, `aws_elb` |
| Health Checks | Code: health check endpoints, liveness probes |
| Retry Patterns | AST: Polly, resilience4j, tenacity patterns |
| Observability | Dependencies: Prometheus, Datadog, OpenTelemetry, CloudWatch |

**Template Variables**:
- `resilience.scalability[]` - Auto-scaling configurations
- `resilience.high_availability[]` - HA features detected
- `resilience.observability[]` - Monitoring/logging tools
- `llm_summaries.resilience` - LLM operational analysis

---

### 9. API Documentation

**Content Source**: Deterministic (AST route/endpoint detection) + LLM
**Human Merge**: Yes (via `sections.api` config)

```markdown
## API Documentation

{{ sections.api.human_content if sections.api.strategy == 'prepend' }}

{% if api.endpoints %}
### Endpoints

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
{% for endpoint in api.endpoints %}
| {{ endpoint.method }} | `{{ endpoint.path }}` | {{ endpoint.handler }} | {{ endpoint.description }} |
{% endfor %}

{% for endpoint in api.endpoints %}
{% if endpoint.parameters or endpoint.request_body or endpoint.responses %}
#### {{ endpoint.method }} {{ endpoint.path }}

{% if endpoint.parameters %}
**Parameters:**
| Name | In | Type | Required | Description |
|------|-----|------|----------|-------------|
{% for param in endpoint.parameters %}
| {{ param.name }} | {{ param.location }} | {{ param.type }} | {{ param.required }} | {{ param.description }} |
{% endfor %}
{% endif %}

{% if endpoint.request_body %}
**Request Body:** `{{ endpoint.request_body.content_type }}`
```json
{{ endpoint.request_body.schema | tojson(indent=2) }}
```
{% endif %}

{% if endpoint.responses %}
**Responses:**
{% for response in endpoint.responses %}
- **{{ response.status }}**: {{ response.description }}
{% endfor %}
{% endif %}

{% endif %}
{% endfor %}
{% endif %}

{% if api.graphql %}
### GraphQL Schema

**Endpoint:** `{{ api.graphql.endpoint }}`

#### Queries
{% for query in api.graphql.queries %}
- `{{ query.name }}({{ query.args | join(', ') }})` → `{{ query.return_type }}`
{% endfor %}

#### Mutations
{% for mutation in api.graphql.mutations %}
- `{{ mutation.name }}({{ mutation.args | join(', ') }})` → `{{ mutation.return_type }}`
{% endfor %}
{% endif %}

{% if api.grpc %}
### gRPC Services

{% for service in api.grpc.services %}
#### {{ service.name }}

| Method | Request | Response | Streaming |
|--------|---------|----------|-----------|
{% for method in service.methods %}
| {{ method.name }} | {{ method.request }} | {{ method.response }} | {{ method.streaming }} |
{% endfor %}
{% endfor %}
{% endif %}

### API Analysis

{{ llm_summaries.api }}

{{ sections.api.human_content if sections.api.strategy == 'append' }}
```

**Detection Sources**:

| API Type | Detection Method |
|----------|------------------|
| REST (FastAPI) | AST: `@app.get()`, `@app.post()`, `@router.*` decorators |
| REST (Flask) | AST: `@app.route()`, `@blueprint.route()` decorators |
| REST (Express) | AST: `app.get()`, `router.post()` method calls |
| REST (Django) | File: `urls.py` + AST view functions |
| REST (Go) | AST: `http.HandleFunc()`, gorilla/mux, gin handlers |
| REST (Spring) | AST: `@GetMapping`, `@PostMapping`, `@RestController` |
| GraphQL | File: `*.graphql`, AST: schema definitions |
| gRPC | File: `*.proto` protobuf definitions |
| OpenAPI | File: `openapi.yaml`, `swagger.json` |

**Template Variables**:
- `api.endpoints[]` - Detected REST endpoints
- `api.endpoints[].method` - HTTP method
- `api.endpoints[].path` - URL path
- `api.endpoints[].handler` - Handler function/method
- `api.endpoints[].parameters[]` - Path/query/header parameters
- `api.endpoints[].request_body` - Request body schema
- `api.endpoints[].responses[]` - Response definitions
- `api.graphql` - GraphQL schema if detected
- `api.grpc` - gRPC services if detected
- `llm_summaries.api` - LLM API analysis

---

### 10. Build & Deployment

**Content Source**: Deterministic (Dockerfile, CI/CD configs, build scripts)
**Human Merge**: Yes (via `sections.build` config)

```markdown
## Build & Deployment

{{ sections.build.human_content if sections.build.strategy == 'prepend' }}

{% if build.containerization %}
### Containerization

{% for container in build.containerization %}
#### {{ container.file }}

| Property | Value |
|----------|-------|
| Base Image | `{{ container.base_image }}` |
| Stages | {{ container.stages | join(', ') if container.stages else 'Single stage' }} |
| Exposed Ports | {{ container.ports | join(', ') if container.ports else 'None' }} |
| Entry Point | `{{ container.entrypoint }}` |

{% endfor %}
{% endif %}

{% if build.ci_pipelines %}
### CI/CD Pipelines

{% for pipeline in build.ci_pipelines %}
#### {{ pipeline.platform }} ({{ pipeline.file }})

| Stage | Jobs |
|-------|------|
{% for stage in pipeline.stages %}
| {{ stage.name }} | {{ stage.jobs | join(', ') }} |
{% endfor %}

**Triggers:** {{ pipeline.triggers | join(', ') }}
{% endfor %}
{% endif %}

{% if build.scripts %}
### Build Scripts

| Script | Purpose | Command |
|--------|---------|---------|
{% for script in build.scripts %}
| {{ script.name }} | {{ script.purpose }} | `{{ script.command }}` |
{% endfor %}
{% endif %}

{% if build.package_managers %}
### Package Management

| Manager | Config File | Scripts |
|---------|-------------|---------|
{% for pm in build.package_managers %}
| {{ pm.name }} | `{{ pm.config_file }}` | {{ pm.scripts | join(', ') if pm.scripts else 'N/A' }} |
{% endfor %}
{% endif %}

{{ sections.build.human_content if sections.build.strategy == 'append' }}
```

**Detection Sources**:

| Component | Detection Method |
|-----------|------------------|
| Docker | File: `Dockerfile*`, `docker-compose*.yml` |
| GitHub Actions | File: `.github/workflows/*.yml` |
| GitLab CI | File: `.gitlab-ci.yml` |
| Jenkins | File: `Jenkinsfile` |
| CircleCI | File: `.circleci/config.yml` |
| Azure Pipelines | File: `azure-pipelines.yml` |
| Makefile | File: `Makefile`, `GNUmakefile` |
| npm scripts | File: `package.json` → scripts section |
| Python scripts | File: `pyproject.toml`, `setup.py` |
| Gradle | File: `build.gradle`, `build.gradle.kts` |
| Maven | File: `pom.xml` |

**Template Variables**:
- `build.containerization[]` - Container configurations
- `build.ci_pipelines[]` - CI/CD pipeline definitions
- `build.scripts[]` - Build scripts detected
- `build.package_managers[]` - Package manager configurations

---

### 11. Testing

**Content Source**: Deterministic (AST test detection + config files)
**Human Merge**: Yes (via `sections.testing` config)

```markdown
## Testing

{{ sections.testing.human_content if sections.testing.strategy == 'prepend' }}

{% if testing.summary %}
### Test Summary

| Metric | Value |
|--------|-------|
| Test Files | {{ testing.summary.test_files }} |
| Test Functions | {{ testing.summary.test_functions }} |
| Test Classes | {{ testing.summary.test_classes }} |
| Frameworks | {{ testing.summary.frameworks | join(', ') }} |
{% endif %}

{% if testing.frameworks %}
### Testing Frameworks

| Framework | Language | Config File | Test Pattern |
|-----------|----------|-------------|--------------|
{% for fw in testing.frameworks %}
| {{ fw.name }} | {{ fw.language }} | `{{ fw.config_file or 'N/A' }}` | `{{ fw.pattern }}` |
{% endfor %}
{% endif %}

{% if testing.test_structure %}
### Test Structure

{% for category in testing.test_structure %}
#### {{ category.type | title }} Tests

| File | Tests | Description |
|------|-------|-------------|
{% for file in category.files[:10] %}
| `{{ file.path }}` | {{ file.test_count }} | {{ file.description }} |
{% endfor %}
{% if category.files | length > 10 %}
*... and {{ category.files | length - 10 }} more {{ category.type }} test files*
{% endif %}
{% endfor %}
{% endif %}

{% if testing.coverage %}
### Code Coverage

| Metric | Value |
|--------|-------|
| Coverage Tool | {{ testing.coverage.tool }} |
| Configuration | `{{ testing.coverage.config_file }}` |
{% if testing.coverage.thresholds %}
| Line Threshold | {{ testing.coverage.thresholds.line }}% |
| Branch Threshold | {{ testing.coverage.thresholds.branch }}% |
{% endif %}
{% endif %}

{% if testing.fixtures %}
### Test Fixtures & Utilities

| Type | Location | Purpose |
|------|----------|---------|
{% for fixture in testing.fixtures %}
| {{ fixture.type }} | `{{ fixture.location }}` | {{ fixture.purpose }} |
{% endfor %}
{% endif %}

{{ sections.testing.human_content if sections.testing.strategy == 'append' }}
```

**Detection Sources**:

| Framework | Detection Method |
|-----------|------------------|
| pytest | File: `pytest.ini`, `pyproject.toml [tool.pytest]`, AST: `test_*.py` files |
| unittest | AST: classes inheriting `unittest.TestCase` |
| Jest | File: `jest.config.*`, `package.json [jest]`, AST: `*.test.js`, `*.spec.js` |
| Mocha | File: `.mocharc.*`, `package.json [mocha]` |
| Vitest | File: `vitest.config.*` |
| Go testing | AST: `*_test.go` files, `func Test*` functions |
| JUnit | AST: `@Test` annotations, File: `*Test.java` |
| Cypress | File: `cypress.config.*`, `cypress/` directory |
| Playwright | File: `playwright.config.*` |

**Template Variables**:
- `testing.summary` - Aggregate test statistics
- `testing.frameworks[]` - Detected testing frameworks
- `testing.test_structure[]` - Test files by category (unit, integration, e2e)
- `testing.coverage` - Coverage configuration if detected
- `testing.fixtures[]` - Test fixtures and utilities

---

### 12. Logging & Error Handling

**Content Source**: Deterministic (AST pattern detection) + LLM
**Human Merge**: Yes (via `sections.logging` config)

```markdown
## Logging & Error Handling

{{ sections.logging.human_content if sections.logging.strategy == 'prepend' }}

{% if logging.libraries %}
### Logging Libraries

| Library | Language | Configuration |
|---------|----------|---------------|
{% for lib in logging.libraries %}
| {{ lib.name }} | {{ lib.language }} | `{{ lib.config_file or 'Code-configured' }}` |
{% endfor %}
{% endif %}

{% if logging.patterns %}
### Logging Patterns

| Pattern | Files | Example |
|---------|-------|---------|
{% for pattern in logging.patterns %}
| {{ pattern.type }} | {{ pattern.file_count }} | `{{ pattern.example }}` |
{% endfor %}
{% endif %}

{% if logging.log_levels %}
### Log Level Usage

| Level | Occurrences | Primary Usage |
|-------|-------------|---------------|
{% for level in logging.log_levels %}
| {{ level.name | upper }} | {{ level.count }} | {{ level.usage }} |
{% endfor %}
{% endif %}

{% if error_handling.patterns %}
### Error Handling Patterns

| Pattern | Language | Occurrences |
|---------|----------|-------------|
{% for pattern in error_handling.patterns %}
| {{ pattern.type }} | {{ pattern.language }} | {{ pattern.count }} |
{% endfor %}
{% endif %}

{% if error_handling.custom_exceptions %}
### Custom Exceptions

| Exception | File | Purpose |
|-----------|------|---------|
{% for exc in error_handling.custom_exceptions %}
| `{{ exc.name }}` | `{{ exc.file }}` | {{ exc.purpose }} |
{% endfor %}
{% endif %}

{% if error_handling.error_boundaries %}
### Error Boundaries (React)

| Component | File | Fallback |
|-----------|------|----------|
{% for boundary in error_handling.error_boundaries %}
| `{{ boundary.name }}` | `{{ boundary.file }}` | {{ boundary.fallback }} |
{% endfor %}
{% endif %}

### Logging & Error Analysis

{{ llm_summaries.logging }}

{{ sections.logging.human_content if sections.logging.strategy == 'append' }}
```

**Detection Sources**:

| Component | Detection Method |
|-----------|------------------|
| Python logging | AST: `import logging`, `logging.getLogger()` |
| structlog | AST: `import structlog`, `structlog.get_logger()` |
| loguru | AST: `from loguru import logger` |
| winston | AST: `require('winston')`, `import winston` |
| pino | AST: `require('pino')`, `import pino` |
| log4j/slf4j | AST: `@Slf4j`, `LoggerFactory.getLogger()` |
| zap/zerolog | AST: `zap.NewLogger()`, `zerolog.New()` |
| Custom exceptions | AST: classes inheriting `Exception`, `Error` |
| Error boundaries | AST: React components with `componentDidCatch` or error boundary HOC |
| try/catch patterns | AST: try/except/catch blocks with analysis |

**Template Variables**:
- `logging.libraries[]` - Logging libraries detected
- `logging.patterns[]` - Logging patterns found
- `logging.log_levels[]` - Log level usage statistics
- `error_handling.patterns[]` - Error handling patterns
- `error_handling.custom_exceptions[]` - Custom exception classes
- `error_handling.error_boundaries[]` - React error boundaries
- `llm_summaries.logging` - LLM analysis of logging strategy

---

### 13. Risks & Recommendations

**Content Source**: LLM (based on all analysis)
**Human Merge**: Yes (via `sections.risks` config)

```markdown
## Risks & Recommendations

{{ sections.risks.human_content if sections.risks.strategy == 'prepend' }}

### Design Risks

{{ llm_summaries.design_risks }}

### Security Concerns

{{ llm_summaries.security_concerns }}

### Recommended Mitigations

{{ llm_summaries.mitigations }}

{{ sections.risks.human_content if sections.risks.strategy == 'append' }}
```

**LLM Prompt Context**:
- All deterministic analysis results
- Single points of failure detected
- Missing resilience patterns
- Security anti-patterns
- Dependency vulnerabilities
- Infrastructure gaps

**Template Variables**:
- `llm_summaries.design_risks` - Identified design risks
- `llm_summaries.security_concerns` - Security concerns
- `llm_summaries.mitigations` - Recommended mitigations

---

### 14. Dependencies (SBOM)

**Content Source**: Deterministic (Syft SBOM)

```markdown
## Software Bill of Materials

Generated by Syft {{ sbom.tool_version }}

### Summary

| Metric | Value |
|--------|-------|
| Total Packages | {{ sbom.packages | length }} |
| Direct Dependencies | {{ sbom.direct_count }} |
| Transitive Dependencies | {{ sbom.transitive_count }} |
| Known Vulnerabilities | {{ sbom.vulnerabilities | length }} |

### Package Inventory

| Package | Version | Type | License | PURL |
|---------|---------|------|---------|------|
{% for pkg in sbom.packages %}
| {{ pkg.name }} | {{ pkg.version }} | {{ pkg.type }} | {{ pkg.license }} | {{ pkg.purl }} |
{% endfor %}
```

**Template Variables**:
- `sbom.tool_version` - Syft version used
- `sbom.packages[]` - All packages with metadata
- `sbom.direct_count` - Direct dependency count
- `sbom.transitive_count` - Transitive dependency count
- `sbom.vulnerabilities[]` - Known CVEs

---

### 15. Version History

**Content Source**: Deterministic (git + chronicle tracking)

```markdown
## Version History

| Date | Author | Type | Description |
|------|--------|------|-------------|
{% for entry in version_history %}
| {{ entry.date }} | {{ entry.author }} | {{ entry.type }} | {{ entry.description }} |
{% endfor %}

---

*Documentation generated by [chronicle](https://github.com/your-org/chronicle) v{{ chronicle_version }}*

| Tool | Version |
|------|---------|
| chronicle | {{ chronicle_version }} |
| Syft | {{ tool_versions.syft }} |
| Terravision | {{ tool_versions.terravision }} |
| LLM | {{ llm_config.provider }}/{{ llm_config.model }} |
```

**Template Variables**:
- `version_history[]` - Document revision entries
- `chronicle_version` - chronicle CLI version
- `tool_versions.*` - External tool versions
- `llm_config.*` - LLM configuration used

---

## Human Section Merging (Principle VI)

Sections marked with "Human Merge: Yes" support content injection via `.chronicle/sections/*.md` files.

### Merge Strategies

| Strategy | Behavior |
|----------|----------|
| `prepend` | Human content appears before generated content |
| `append` | Human content appears after generated content |
| `replace` | Human content completely replaces generated content |

### Configuration Example

```yaml
sections:
  overview:
    file: ".chronicle/sections/overview.md"
    strategy: "prepend"
  architecture:
    file: ".chronicle/sections/architecture.md"
    strategy: "append"
  security:
    file: ".chronicle/sections/security.md"
    strategy: "append"
  data:
    file: ".chronicle/sections/data.md"
    strategy: "replace"  # Human-only data documentation
  api:
    file: ".chronicle/sections/api.md"
    strategy: "append"   # Add internal API notes
  build:
    file: ".chronicle/sections/build.md"
    strategy: "append"   # Add deployment notes
  testing:
    file: ".chronicle/sections/testing.md"
    strategy: "prepend"  # Testing strategy overview
  logging:
    file: ".chronicle/sections/logging.md"
    strategy: "append"
  risks:
    file: ".chronicle/sections/risks.md"
    strategy: "append"
```

---

## Conditional Rendering

Sections are conditionally rendered based on data availability. When a section is not applicable, it displays "N/A" or "Not applicable" rather than being omitted entirely. This ensures consistent document structure and makes it explicit what analysis was attempted.

| Section | Condition | Behavior |
|---------|-----------|----------|
| Infrastructure | No Terraform files | Shows "N/A - No Terraform configuration detected" |
| Data | No ORM/schema detected | Shows "N/A - No ORM models or database schemas detected" |
| Security | No security patterns found | Shows minimal section with "No security patterns automatically detected" |
| Resilience | No resilience patterns found | Shows "N/A - No resilience patterns detected" |
| API Documentation | No API endpoints detected | Shows "N/A - No API endpoints detected" |
| Build & Deployment | No build/CI files detected | Shows "N/A - No containerization or CI/CD configuration detected" |
| Testing | No test files detected | Shows "N/A - No test files or testing frameworks detected" |
| Logging | No logging patterns detected | Shows "N/A - No logging libraries or patterns detected" |
| Dependencies (SBOM) | No SBOM tool available | Shows "N/A - SBOM generation unavailable (Syft not installed)" |
| All LLM subsections | LLM unavailable | Shows "[Analysis not available - LLM not configured]" |

**N/A Rendering Example**:

```markdown
## API Documentation

*N/A - No API endpoints detected. This section will be populated if REST, GraphQL, or gRPC endpoints are detected in the codebase.*
```

---

## New Analyzers Required

This template structure requires the following analyzers:

| Analyzer | Purpose | Output |
|----------|---------|--------|
| `MermaidGenerator` | Generate component/connectivity diagrams | Mermaid source |
| `TerraformAnalyzer` | Categorize Terraform resources | Infrastructure model |
| `ORMDetector` | Detect ORM models and schema | Data model |
| `SecurityPatternScanner` | Detect auth, secrets, IAM patterns | Security findings |
| `ResilienceDetector` | Detect scaling, HA, observability | Resilience model |
| `APIEndpointDetector` | Detect REST, GraphQL, gRPC endpoints | API model |
| `BuildConfigAnalyzer` | Parse Dockerfile, CI/CD configs, build scripts | Build model |
| `TestDetector` | Detect test files, frameworks, coverage config | Testing model |
| `LoggingPatternScanner` | Detect logging libraries and error patterns | Logging model |

---

## Template Customization

Users can provide custom templates via `template.path` in config:

```yaml
template:
  path: "./my-template.md.j2"
```

Custom templates have access to all variables documented above. Use `chronicle validate TEMPLATE` to check syntax and placeholder validity.
