# chronicle

Automated system documentation generator for Enterprise IT audit, architecture, security, and business stakeholders.

## Features

- Multi-language AST parsing (Python, JavaScript, TypeScript, Go, Java)
- Dependency file analysis (package.json, requirements.txt, pyproject.toml, go.mod, pom.xml)
- SBOM generation via Syft
- Architecture diagram extraction via Terravision
- Deterministic documentation generation
- Jinja2-based template rendering

## Installation

```bash
pip install chronicle
```

## Quick Start

```bash
# Initialize configuration
chronicle init

# Check tool availability
chronicle check

# Generate documentation
chronicle write --repo .
```

## Documentation

See [docs/](docs/) for detailed documentation.

## License

Mozilla Public License 2.0 (MPL-2.0)
