# chronicle Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-31

## Active Technologies
- Python 3.11+ (primary language for CLI, AST parsing, LLM integration) + ree-sitter (AST), LiteLLM (LLM), Jinja2 (templates) (001-system-doc-generator)
- N/A (stateless analysis) (001-system-doc-generator)
- Python 3.11+ (existing codebase) + hashlib (stdlib), json (stdlib), pathlib (stdlib), git integration (existing) (001-system-doc-generator)
- `.chronicle/cache.json` - JSON cache file in repository (001-system-doc-generator)

- Python 3.11+ (primary language for CLI, AST parsing, LLM integration) (001-system-doc-generator)

## Project Structure

```text
src/
tests/
```

## Commands

 pytest
 ruff check .
 uv run chronicle

## Code Style

Python 3.11+ (primary language for CLI, AST parsing, LLM integration): Follow standard conventions

## Recent Changes
- 001-system-doc-generator: Added Python 3.11+ (existing codebase) + hashlib (stdlib), json (stdlib), pathlib (stdlib), git integration (existing)
- 001-system-doc-generator: Added Python 3.11+ (primary language for CLI, AST parsing, LLM integration) + ree-sitter (AST), LiteLLM (LLM), Jinja2 (templates)

- 001-system-doc-generator: Added Python 3.11+ (primary language for CLI, AST parsing, LLM integration)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
