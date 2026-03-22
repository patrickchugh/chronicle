"""Shared pytest fixtures for chronicle tests.

This module provides common fixtures used across unit, integration, and
contract tests. Fixtures are organized by category:
- Repository fixtures: Mock git repositories for testing
- Configuration fixtures: Test configs for various scenarios
- Analysis fixtures: Pre-built analysis results for testing renderers
"""

from pathlib import Path
from typing import Any

import pytest

# =============================================================================
# Path Fixtures
# =============================================================================


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_repos_dir(fixtures_dir: Path) -> Path:
    """Return the path to sample repository fixtures."""
    return fixtures_dir / "sample_repos"


@pytest.fixture
def sections_dir(fixtures_dir: Path) -> Path:
    """Return the path to human section fixtures."""
    return fixtures_dir / "sections"


# =============================================================================
# Temporary Directory Fixtures
# =============================================================================


@pytest.fixture
def temp_repo(tmp_path: Path) -> Path:
    """Create a temporary directory that mimics a git repository.

    Creates basic structure with .git directory marker.
    """
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    return tmp_path


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    """Create a temporary .chronicle configuration directory."""
    config_dir = tmp_path / ".chronicle"
    config_dir.mkdir()
    sections_dir = config_dir / "sections"
    sections_dir.mkdir()
    return config_dir


# =============================================================================
# Configuration Fixtures
# =============================================================================


@pytest.fixture
def minimal_config() -> dict[str, Any]:
    """Return a minimal valid chronicle configuration."""
    return {
        "output": {
            "path": "docs/SYSTEM.md",
            "format": "markdown",
        }
    }


@pytest.fixture
def full_config() -> dict[str, Any]:
    """Return a complete chronicle configuration with all options."""
    return {
        "output": {
            "path": "docs/SYSTEM.md",
            "format": "markdown",
        },
        "tools": {
            "sbom": "syft",
            "diagrams": "terravision",
        },
        "llm": {
            "provider": "ollama",
            "model": "llama2",
            "api_base": "http://localhost:11434",
            "temperature": 0,
            "max_tokens": 4096,
            "enabled": True,
        },
        "sections": {
            "overview": {
                "file": ".chronicle/sections/overview.md",
                "strategy": "prepend",
            },
            "security": {
                "file": ".chronicle/sections/security.md",
                "strategy": "append",
            },
        },
        "ci": {
            "fail_on_warning": False,
            "json_output": False,
        },
    }


# =============================================================================
# Sample Source Code Fixtures
# =============================================================================


@pytest.fixture
def python_source() -> str:
    """Return sample Python source code for AST parsing tests."""
    return '''"""Sample module for testing."""

from typing import Optional


class UserService:
    """Service for managing users."""

    def __init__(self, db_connection):
        self.db = db_connection

    def create_user(self, name: str, email: str) -> dict:
        """Create a new user."""
        return {"name": name, "email": email}

    def get_user(self, user_id: int) -> Optional[dict]:
        """Retrieve a user by ID."""
        return None


def main():
    """Entry point for the application."""
    print("Hello, World!")


if __name__ == "__main__":
    main()
'''


@pytest.fixture
def javascript_source() -> str:
    """Return sample JavaScript source code for AST parsing tests."""
    return """/**
 * Sample module for testing.
 */

class UserService {
    constructor(dbConnection) {
        this.db = dbConnection;
    }

    createUser(name, email) {
        return { name, email };
    }

    getUser(userId) {
        return null;
    }
}

function main() {
    console.log("Hello, World!");
}

module.exports = { UserService, main };
"""


@pytest.fixture
def typescript_source() -> str:
    """Return sample TypeScript source code for AST parsing tests."""
    return """/**
 * Sample module for testing.
 */

interface User {
    name: string;
    email: string;
}

class UserService {
    private db: any;

    constructor(dbConnection: any) {
        this.db = dbConnection;
    }

    createUser(name: string, email: string): User {
        return { name, email };
    }

    getUser(userId: number): User | null {
        return null;
    }
}

function main(): void {
    console.log("Hello, World!");
}

export { UserService, main };
"""


# =============================================================================
# Dependency File Fixtures
# =============================================================================


@pytest.fixture
def package_json() -> str:
    """Return sample package.json content."""
    return """{
  "name": "sample-project",
  "version": "1.0.0",
  "dependencies": {
    "express": "^4.18.0",
    "lodash": "^4.17.21"
  },
  "devDependencies": {
    "jest": "^29.0.0",
    "typescript": "^5.0.0"
  }
}"""


@pytest.fixture
def requirements_txt() -> str:
    """Return sample requirements.txt content."""
    return """# Production dependencies
fastapi>=0.100.0
uvicorn>=0.23.0
pydantic>=2.0.0

# Optional dependencies
redis>=4.0.0
"""


@pytest.fixture
def pyproject_toml() -> str:
    """Return sample pyproject.toml content."""
    return """[project]
name = "sample-project"
version = "1.0.0"
dependencies = [
    "fastapi>=0.100.0",
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "ruff>=0.1.0",
]
"""
