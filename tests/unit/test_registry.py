"""Unit tests for ToolRegistry (T023l)."""

import pytest

from chronicle.analyzers.base import ToolNotAvailableError
from chronicle.analyzers.diagrams.base import DiagramGenerator
from chronicle.analyzers.registry import (
    ToolRegistry,
    get_registry,
    reset_registry,
)
from chronicle.analyzers.sbom.base import SBOMAdapter


class MockSBOMAdapter(SBOMAdapter):
    """Mock SBOM adapter for testing."""

    def check_available(self) -> bool:
        return True

    def get_version(self) -> str | None:
        return "1.0.0"

    def execute(self, _input_path) -> dict:
        return {}

    def get_supported_ecosystems(self) -> list[str]:
        return ["npm", "pypi"]


class MockSBOMAdapterUnavailable(SBOMAdapter):
    """Mock SBOM adapter that is unavailable."""

    def check_available(self) -> bool:
        return False

    def get_version(self) -> str | None:
        return None

    def execute(self, _input_path) -> dict:
        return {}

    def get_supported_ecosystems(self) -> list[str]:
        return []


class MockDiagramGenerator(DiagramGenerator):
    """Mock diagram generator for testing."""

    def check_available(self) -> bool:
        return True

    def get_version(self) -> str | None:
        return "1.0.0"

    def execute(self, _input_path) -> dict:
        return {}

    def get_supported_sources(self) -> list[str]:
        return ["terraform"]

    def get_supported_providers(self) -> list[str]:
        return ["aws"]


class MockDiagramGeneratorUnavailable(DiagramGenerator):
    """Mock diagram generator that is unavailable."""

    def check_available(self) -> bool:
        return False

    def get_version(self) -> str | None:
        return None

    def execute(self, _input_path) -> dict:
        return {}

    def get_supported_sources(self) -> list[str]:
        return []

    def get_supported_providers(self) -> list[str]:
        return []


class TestToolRegistry:
    """Tests for ToolRegistry class."""

    def test_register_sbom_adapter(self) -> None:
        """Test registering an SBOM adapter."""
        registry = ToolRegistry()

        registry.register_sbom_adapter("mock", MockSBOMAdapter)

        assert "mock" in registry.list_sbom_adapters()

    def test_register_sbom_adapter_as_default(self) -> None:
        """Test registering an SBOM adapter as default."""
        registry = ToolRegistry()

        registry.register_sbom_adapter("mock", MockSBOMAdapter, is_default=True)

        # Should be able to get without specifying name
        adapter = registry.get_sbom_adapter()
        assert isinstance(adapter, MockSBOMAdapter)

    def test_register_diagram_adapter(self) -> None:
        """Test registering a diagram adapter."""
        registry = ToolRegistry()

        registry.register_diagram_adapter("mock", MockDiagramGenerator)

        assert "mock" in registry.list_diagram_adapters()

    def test_register_diagram_adapter_as_default(self) -> None:
        """Test registering a diagram adapter as default."""
        registry = ToolRegistry()

        registry.register_diagram_adapter("mock", MockDiagramGenerator, is_default=True)

        # Should be able to get without specifying name
        adapter = registry.get_diagram_adapter()
        assert isinstance(adapter, MockDiagramGenerator)

    def test_get_sbom_adapter_by_name(self) -> None:
        """Test getting an SBOM adapter by name."""
        registry = ToolRegistry()
        registry.register_sbom_adapter("mock", MockSBOMAdapter)

        adapter = registry.get_sbom_adapter("mock")

        assert isinstance(adapter, MockSBOMAdapter)
        assert adapter.name == "mock"

    def test_get_sbom_adapter_not_found(self) -> None:
        """Test getting an unregistered SBOM adapter raises error."""
        registry = ToolRegistry()

        with pytest.raises(ToolNotAvailableError) as exc_info:
            registry.get_sbom_adapter("nonexistent")

        assert "nonexistent" in str(exc_info.value)
        assert "not registered" in str(exc_info.value)

    def test_get_sbom_adapter_no_default(self) -> None:
        """Test getting SBOM adapter without name or default raises error."""
        registry = ToolRegistry()

        with pytest.raises(ToolNotAvailableError) as exc_info:
            registry.get_sbom_adapter()

        assert "No SBOM tool configured" in str(exc_info.value)

    def test_get_diagram_adapter_by_name(self) -> None:
        """Test getting a diagram adapter by name."""
        registry = ToolRegistry()
        registry.register_diagram_adapter("mock", MockDiagramGenerator)

        adapter = registry.get_diagram_adapter("mock")

        assert isinstance(adapter, MockDiagramGenerator)
        assert adapter.name == "mock"

    def test_get_diagram_adapter_not_found(self) -> None:
        """Test getting an unregistered diagram adapter raises error."""
        registry = ToolRegistry()

        with pytest.raises(ToolNotAvailableError) as exc_info:
            registry.get_diagram_adapter("nonexistent")

        assert "nonexistent" in str(exc_info.value)
        assert "not registered" in str(exc_info.value)

    def test_get_diagram_adapter_no_default(self) -> None:
        """Test getting diagram adapter without name or default raises error."""
        registry = ToolRegistry()

        with pytest.raises(ToolNotAvailableError) as exc_info:
            registry.get_diagram_adapter()

        assert "No diagram tool configured" in str(exc_info.value)

    def test_list_sbom_adapters(self) -> None:
        """Test listing registered SBOM adapters."""
        registry = ToolRegistry()
        registry.register_sbom_adapter("mock1", MockSBOMAdapter)
        registry.register_sbom_adapter("mock2", MockSBOMAdapter)

        adapters = registry.list_sbom_adapters()

        assert len(adapters) == 2
        assert "mock1" in adapters
        assert "mock2" in adapters

    def test_list_diagram_adapters(self) -> None:
        """Test listing registered diagram adapters."""
        registry = ToolRegistry()
        registry.register_diagram_adapter("mock1", MockDiagramGenerator)
        registry.register_diagram_adapter("mock2", MockDiagramGenerator)

        adapters = registry.list_diagram_adapters()

        assert len(adapters) == 2
        assert "mock1" in adapters
        assert "mock2" in adapters

    def test_get_available_tools(self) -> None:
        """Test getting all available tools by capability."""
        registry = ToolRegistry()
        registry.register_sbom_adapter("sbom1", MockSBOMAdapter)
        registry.register_diagram_adapter("diag1", MockDiagramGenerator)

        tools = registry.get_available_tools()

        assert "sbom" in tools
        assert "diagram" in tools
        assert "sbom1" in tools["sbom"]
        assert "diag1" in tools["diagram"]

    def test_check_tool_availability(self) -> None:
        """Test checking availability of all registered tools."""
        registry = ToolRegistry()
        registry.register_sbom_adapter("available", MockSBOMAdapter)
        registry.register_sbom_adapter("unavailable", MockSBOMAdapterUnavailable)
        registry.register_diagram_adapter("available", MockDiagramGenerator)
        registry.register_diagram_adapter(
            "unavailable", MockDiagramGeneratorUnavailable
        )

        availability = registry.check_tool_availability()

        assert availability["sbom"]["available"] is True
        assert availability["sbom"]["unavailable"] is False
        assert availability["diagram"]["available"] is True
        assert availability["diagram"]["unavailable"] is False

    def test_get_metadata(self) -> None:
        """Test getting registry metadata."""
        registry = ToolRegistry()
        registry.register_sbom_adapter("syft", MockSBOMAdapter, is_default=True)
        registry.register_diagram_adapter(
            "terravision", MockDiagramGenerator, is_default=True
        )

        metadata = registry.get_metadata()

        assert "syft" in metadata["sbom_adapters"]
        assert "terravision" in metadata["diagram_adapters"]
        assert metadata["default_sbom"] == "syft"
        assert metadata["default_diagram"] == "terravision"


class TestGlobalRegistry:
    """Tests for global registry functions."""

    def test_get_registry_returns_singleton(self) -> None:
        """Test get_registry returns the same instance."""
        reset_registry()

        registry1 = get_registry()
        registry2 = get_registry()

        assert registry1 is registry2

    def test_reset_registry(self) -> None:
        """Test reset_registry clears the global registry."""
        reset_registry()

        registry1 = get_registry()
        registry1.register_sbom_adapter("test", MockSBOMAdapter)

        reset_registry()

        registry2 = get_registry()

        assert "test" not in registry2.list_sbom_adapters()
        assert registry1 is not registry2

    def test_get_registry_creates_new_if_none(self) -> None:
        """Test get_registry creates a new registry if none exists."""
        reset_registry()

        registry = get_registry()

        assert isinstance(registry, ToolRegistry)
        assert len(registry.list_sbom_adapters()) == 0
        assert len(registry.list_diagram_adapters()) == 0
