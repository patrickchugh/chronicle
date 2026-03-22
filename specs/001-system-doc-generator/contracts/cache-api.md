# Cache API Contract

**Version**: 2.0
**Date**: 2026-02-01

## Overview

This contract defines the cache file format and API for chronicle's incremental documentation updates feature. The cache stores LLM-generated **module summaries** and **section summaries** to avoid redundant API calls on subsequent runs.

> **Note**: Version 2.0 caches module-level summaries (flow-based documentation) instead of function-level explanations. This aligns with Phase 4e which replaced function-by-function explanations with module-level documentation.

---

## Cache File Location

**Default**: `.chronicle/cache.json` in repository root

**Custom**: Override via `--cache-path PATH` CLI flag

**Behavior**:
- Cache file is automatically created on first run with LLM summaries
- Cache is updated after each successful run
- Missing cache file triggers full regeneration (graceful degradation)
- Corrupted cache file triggers full regeneration with warning

---

## Cache File Format

```json
{
  "version": "2.0",
  "chronicle_version": "0.1.0",
  "llm_model": "anthropic/claude-3-5-sonnet",
  "git_ref": "abc123def456789",
  "created_at": "2026-02-01T12:00:00Z",
  "updated_at": "2026-02-01T14:30:00Z",
  "modules": {
    "src/chronicle/analyzers": {
      "name": "analyzers",
      "path": "src/chronicle/analyzers",
      "responsibility": "Performs deterministic code analysis including AST parsing, dependency detection, and SBOM generation.",
      "created_at": "2026-02-01T12:00:00Z",
      "chronicle_version": "0.1.0"
    },
    "src/chronicle/llm": {
      "name": "llm",
      "path": "src/chronicle/llm",
      "responsibility": "Provides unified LLM access via LiteLLM for generating documentation summaries.",
      "created_at": "2026-02-01T12:00:00Z",
      "chronicle_version": "0.1.0"
    }
  },
  "section_summaries": {
    "overview": {
      "content": "chronicle is an automated system documentation generator...",
      "input_hash": "sha256:789abc...",
      "created_at": "2026-02-01T12:00:00Z",
      "chronicle_version": "0.1.0"
    },
    "tech_stack": {
      "content": "The system uses Python 3.11+ with tree-sitter for AST parsing...",
      "input_hash": "sha256:cde012...",
      "created_at": "2026-02-01T12:00:00Z",
      "chronicle_version": "0.1.0"
    }
  }
}
```

---

## Field Specifications

### Root Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| version | string | Yes | Cache format version (e.g., "2.0") |
| chronicle_version | string | Yes | chronicle version that created/updated the cache |
| llm_model | string | Yes | LLM model used for summaries |
| git_ref | string | Yes | Git commit SHA when cache was last updated |
| created_at | ISO 8601 | Yes | Initial cache creation timestamp |
| updated_at | ISO 8601 | Yes | Last cache update timestamp |
| modules | object | Yes | Module summary entries |
| section_summaries | object | Yes | Section summary entries |

### ModuleCacheEntry (modules values)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Module name (e.g., "analyzers") |
| path | string | Yes | Relative path from repo root |
| responsibility | string | Yes | LLM-generated 1-2 sentence module responsibility |
| created_at | ISO 8601 | Yes | When this entry was created |
| chronicle_version | string | Yes | chronicle version that generated this entry |

### SectionCacheEntry (section_summaries values)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| content | string | Yes | LLM-generated section content |
| input_hash | string | Yes | SHA-256 hash of input data used to generate this section |
| created_at | ISO 8601 | Yes | When this entry was created |
| chronicle_version | string | Yes | chronicle version that generated this entry |

---

## Cache Key Format

**Module entries** are keyed by module path: `{module_path}`

Examples:
- `src/chronicle/analyzers`
- `src/chronicle/llm`
- `src/chronicle/renderers`

**Section entries** are keyed by section name: `{section_name}`

Examples:
- `overview`
- `tech_stack`
- `architecture`

---

## Git Change Detection

Changed files are detected using git diff against the cached git_ref:

```bash
# Get all files changed since cache was created
git diff --name-only <cache.git_ref>

# This includes:
# - Committed changes since cache.git_ref
# - Staged changes (in index)
# - Unstaged changes (working tree modifications)
```

**Implementation**:
```python
import subprocess

def get_changed_files(cached_git_ref: str, repo_path: Path) -> set[str]:
    """Get files changed since the cached git ref."""
    result = subprocess.run(
        ["git", "diff", "--name-only", cached_git_ref],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return set(result.stdout.strip().split("\n")) if result.stdout.strip() else set()
```

**Non-Git Fallback**: If not a git repository, return empty set and trigger full regeneration.

---

## Cache Invalidation Rules

### Full Cache Invalidation

Discard entire cache when:

| Condition | Reason |
|-----------|--------|
| `cache.version != CURRENT_CACHE_VERSION` | Cache format changed |
| `cache.chronicle_version != __version__` | chronicle updated, prompts may differ |
| `cache.llm_model != config.llm.model` | Different model = different summaries |

### Module-Level Invalidation

Invalidate a module's cached summary when:

| Condition | Action |
|-----------|--------|
| Any file in module changed (via git diff) | Regenerate module summary |
| Module not in cache but exists | New module, generate summary |
| Module in cache but deleted | Remove from cache on next save |

### Section-Level Invalidation

Invalidate a section's cached content when:

| Condition | Action |
|-----------|--------|
| Section `input_hash` differs from current | Input data changed, regenerate |
| Section not in cache | New section, generate content |

---

## CLI Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--no-cache` | Disable cache, force full regeneration | false |
| `--clear-cache` | Delete existing cache before running | false |
| `--cache-path PATH` | Custom cache file location | `.chronicle/cache.json` |

---

## Logging

### Normal Mode

```
[INFO] Loaded cache (git_ref: abc123, 10 module summaries, 5 section summaries)
[INFO] 2 modules changed since last cache, regenerating summaries
[INFO] 8 module summaries reused from cache
```

### Verbose Mode

```
[INFO] Cache file: .chronicle/cache.json (created 2026-02-01)
[INFO] Loaded 10 module summaries + 5 section summaries (git_ref: abc123)
[INFO] Running git diff --name-only abc123...
[DEBUG] Changed files: src/chronicle/pipeline.py, src/chronicle/cli.py (5 total)
[DEBUG] Module src/chronicle/analyzers: unchanged (reusing cached summary)
[DEBUG] Module src/chronicle/llm: changed (regenerating summary)
[DEBUG] Module src/chronicle/renderers: changed (regenerating summary)
[INFO] Cache hit rate: 80% (8/10 module summaries reused)
[INFO] Generating 2 module summaries + 1 section summary
[INFO] Saved updated cache (git_ref: def456, 10 modules, 5 sections)
```

---

## Error Handling

| Error | Behavior |
|-------|----------|
| Cache file not found | Full regeneration, create new cache |
| Cache file corrupted (invalid JSON) | Warning, full regeneration, overwrite cache |
| Cache version mismatch | Info log, full regeneration |
| Not a git repository | Warning, full regeneration, no caching |
| Git diff failed | Warning, full regeneration |
| Permission denied writing cache | Warning, continue without caching |

---

## Performance Characteristics

### Overhead

| Operation | Typical Time |
|-----------|-------------|
| Load 1MB cache | ~10ms |
| `git diff --name-only` | ~5ms |
| Save 1MB cache | ~20ms |
| **Total cache overhead** | **<50ms** |

### Savings

| Scenario | LLM Calls Saved |
|----------|-----------------|
| No changes | 100% (all module + section summaries reused) |
| 1 module changed | ~90% (9/10 modules reused) |
| 2-3 modules changed | ~70-80% |

> **Note**: With flow-based documentation, the total LLM calls are ~10 (modules) + ~5 (sections) = ~15 calls vs ~200 function-level calls in v1.0. Even a full regeneration is 8x more efficient.

---

## Concurrency

**Behavior**: Simple file locking with graceful degradation

1. Acquire advisory lock on cache file before reading
2. If lock fails after 5 seconds: proceed without cache (log warning)
3. Release lock after writing

**Rationale**: chronicle typically runs once per commit in CI/CD. Graceful degradation ensures correctness (duplicate work, not corruption).

---

## Version History

| Version | Changes |
|---------|---------|
| 2.0 | Module-based caching (Phase 4e): Replaced function/class entries with module summaries and section summaries. Uses git diff exclusively for change detection (no content hashing). |
| 1.0 | Initial cache format (deprecated) |
