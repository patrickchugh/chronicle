"""Test fixtures for chronicle.

This package provides sample repositories and other test fixtures
for integration and end-to-end testing.

Sample Repositories:
- sample_repos/python_project: A Flask web application with pytest tests
"""

from pathlib import Path

# Path to fixtures directory
FIXTURES_DIR = Path(__file__).parent

# Path to sample repositories
SAMPLE_REPOS_DIR = FIXTURES_DIR / "sample_repos"

# Specific sample repository paths
PYTHON_PROJECT_PATH = SAMPLE_REPOS_DIR / "python_project"


def get_sample_repo(name: str) -> Path:
    """Get path to a sample repository.

    Args:
        name: Name of the sample repository

    Returns:
        Path to the sample repository

    Raises:
        ValueError: If repository doesn't exist
    """
    repo_path = SAMPLE_REPOS_DIR / name
    if not repo_path.exists():
        raise ValueError(f"Sample repository not found: {name}")
    return repo_path
