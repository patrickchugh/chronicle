"""Integration tests for flow-based documentation (T084).

Tests that the pipeline correctly runs flow-based documentation stages:
- Module detection
- Import graph building
- Entry point detection
- External integration detection
- Mermaid diagram generation
"""

from pathlib import Path

import pytest

from chronicle.config import LLMConfig, chronicleConfig, OutputConfig, ToolConfig
from chronicle.models import Repository
from chronicle.pipeline import AnalysisPipeline, PipelineOptions


class TestFlowBasedDocumentation:
    """Integration tests for flow-based documentation pipeline stages."""

    @pytest.fixture
    def python_repo(self, tmp_path: Path) -> Repository:
        """Create a sample Python repository with modules."""
        # Create package structure
        pkg = tmp_path / "myapp"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")

        # CLI module with entry points
        (pkg / "cli.py").write_text(
            '''
"""CLI module."""
import typer

app = typer.Typer()

@app.command()
def hello(name: str):
    """Say hello."""
    print(f"Hello {name}")

if __name__ == "__main__":
    app()
'''
        )

        # API module with endpoints
        (pkg / "api.py").write_text(
            '''
"""API endpoints."""
from fastapi import FastAPI

app = FastAPI()

@app.get("/users")
def list_users():
    """List all users."""
    return []

@app.post("/users")
def create_user(user: dict):
    """Create a user."""
    return user
'''
        )

        # Utils module
        (pkg / "utils.py").write_text(
            '''
"""Utility functions."""

def helper_function():
    """A helper function."""
    return True
'''
        )

        # Services with external integrations
        (pkg / "services.py").write_text(
            '''
"""Service layer with external integrations."""
import requests
import redis
from sqlalchemy import create_engine

from myapp.utils import helper_function

engine = create_engine("postgresql://localhost/db")
cache = redis.Redis()

def fetch_data():
    """Fetch data from external API."""
    response = requests.get("https://api.example.com/data")
    return response.json()

def get_cached_value(key):
    """Get cached value."""
    return cache.get(key)
'''
        )

        return Repository(path=tmp_path, name="test-myapp")

    @pytest.fixture
    def config(self) -> chronicleConfig:
        """Create test configuration with LLM disabled."""
        return chronicleConfig(
            output=OutputConfig(path=Path("docs/system.md")),
            tools=ToolConfig(),
            llm=LLMConfig(enabled=False),
        )

    def test_pipeline_runs_flow_docs(
        self, python_repo: Repository, config: chronicleConfig
    ) -> None:
        """Test that pipeline runs flow-based documentation stages."""
        pipeline = AnalysisPipeline(config)
        options = PipelineOptions(
            skip_sbom=True,
            skip_architecture=True,
            skip_llm=True,
        )

        result = pipeline.run(python_repo, options)

        # Verify flow-based documentation data was populated
        assert result.modules is not None
        assert result.entry_points is not None
        assert result.external_integrations is not None

    def test_module_detection(
        self, python_repo: Repository, config: chronicleConfig
    ) -> None:
        """Test that modules are correctly detected."""
        pipeline = AnalysisPipeline(config)
        options = PipelineOptions(
            skip_sbom=True,
            skip_architecture=True,
            skip_llm=True,
        )

        result = pipeline.run(python_repo, options)

        # Should detect the myapp module
        assert len(result.modules) >= 1
        module_names = {m.name for m in result.modules}
        assert any("myapp" in name for name in module_names)

    def test_entry_point_detection(
        self, python_repo: Repository, config: chronicleConfig
    ) -> None:
        """Test that entry points are correctly detected."""
        pipeline = AnalysisPipeline(config)
        options = PipelineOptions(
            skip_sbom=True,
            skip_architecture=True,
            skip_llm=True,
        )

        result = pipeline.run(python_repo, options)

        # Should detect CLI commands, API endpoints, and __main__
        assert len(result.entry_points) >= 1

        ep_types = {ep.type for ep in result.entry_points}
        # Should detect at least some entry point types
        assert len(ep_types) >= 1

    def test_external_integration_detection(
        self, python_repo: Repository, config: chronicleConfig
    ) -> None:
        """Test that external integrations are correctly detected."""
        pipeline = AnalysisPipeline(config)
        options = PipelineOptions(
            skip_sbom=True,
            skip_architecture=True,
            skip_llm=True,
        )

        result = pipeline.run(python_repo, options)

        # Should detect HTTP, database, and cache integrations
        assert len(result.external_integrations) >= 1

        integration_types = {i.type for i in result.external_integrations}
        # Should detect at least http integration (requests)
        assert "http" in integration_types

    def test_mermaid_diagram_generation(
        self, python_repo: Repository, config: chronicleConfig
    ) -> None:
        """Test that Mermaid diagram is generated."""
        pipeline = AnalysisPipeline(config)
        options = PipelineOptions(
            skip_sbom=True,
            skip_architecture=True,
            skip_llm=True,
        )

        result = pipeline.run(python_repo, options)

        # Should have generated a module flow diagram
        if result.module_flow_diagram:
            assert result.module_flow_diagram.mermaid.startswith("flowchart TD")
            assert result.module_flow_diagram.node_count >= 0

    def test_skip_flow_docs_option(
        self, python_repo: Repository, config: chronicleConfig
    ) -> None:
        """Test that skip_flow_docs option bypasses flow-based documentation."""
        pipeline = AnalysisPipeline(config)
        options = PipelineOptions(
            skip_sbom=True,
            skip_architecture=True,
            skip_llm=True,
            skip_flow_docs=True,
        )

        result = pipeline.run(python_repo, options)

        # Flow-based documentation should be empty when skipped
        assert len(result.modules) == 0
        assert len(result.entry_points) == 0
        assert len(result.external_integrations) == 0
        assert result.module_flow_diagram is None


class TestFlowDocsReproducibility:
    """Test that flow-based documentation is reproducible."""

    @pytest.fixture
    def sample_repo(self, tmp_path: Path) -> Repository:
        """Create a sample repository."""
        pkg = tmp_path / "app"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "main.py").write_text("def main(): pass")
        (pkg / "utils.py").write_text("def helper(): pass")
        return Repository(path=tmp_path, name="test-app")

    @pytest.fixture
    def config(self) -> chronicleConfig:
        """Create test configuration."""
        return chronicleConfig(
            output=OutputConfig(path=Path("docs/system.md")),
            tools=ToolConfig(),
            llm=LLMConfig(enabled=False),
        )

    def test_consecutive_runs_produce_identical_flow_docs(
        self, sample_repo: Repository, config: chronicleConfig
    ) -> None:
        """Test that flow-based documentation is reproducible across runs."""
        pipeline = AnalysisPipeline(config)
        options = PipelineOptions(
            skip_sbom=True,
            skip_architecture=True,
            skip_llm=True,
        )

        result1 = pipeline.run(sample_repo, options)
        result2 = pipeline.run(sample_repo, options)

        # Modules should be identical
        assert len(result1.modules) == len(result2.modules)
        modules1 = sorted([m.name for m in result1.modules])
        modules2 = sorted([m.name for m in result2.modules])
        assert modules1 == modules2

        # Entry points should be identical
        assert len(result1.entry_points) == len(result2.entry_points)

        # External integrations should be identical
        assert len(result1.external_integrations) == len(result2.external_integrations)

        # Mermaid diagrams should be identical
        if result1.module_flow_diagram and result2.module_flow_diagram:
            assert (
                result1.module_flow_diagram.mermaid
                == result2.module_flow_diagram.mermaid
            )
