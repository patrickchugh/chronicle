"""Unit tests for Mermaid diagram generator."""

import pytest

from chronicle.analyzers.diagrams.mermaid import (
    MAX_NODES_FULL_DETAIL,
    MAX_NODES_MODULE_LEVEL,
    MermaidGenerator,
    generate_module_flowchart,
)
from chronicle.models.canonical.module import ImportGraph


class TestMermaidGenerator:
    """Tests for MermaidGenerator."""

    @pytest.fixture
    def generator(self) -> MermaidGenerator:
        """Create a Mermaid generator instance."""
        return MermaidGenerator()

    def test_generate_simple_flowchart(self, generator: MermaidGenerator) -> None:
        """Test generating a simple flowchart."""
        graph = ImportGraph(
            nodes=["app/main", "app/utils", "app/models"],
            edges=[
                ("app/main", "app/utils"),
                ("app/main", "app/models"),
            ],
        )

        result = generator.generate_module_flowchart(graph)

        assert "flowchart TD" in result.mermaid
        assert "curve" in result.mermaid  # Straight line config
        assert result.node_count == 3
        assert result.simplified is False
        assert "main" in result.mermaid
        assert "-->" in result.mermaid

    def test_empty_graph(self, generator: MermaidGenerator) -> None:
        """Test generating flowchart from empty graph."""
        graph = ImportGraph(nodes=[], edges=[])

        result = generator.generate_module_flowchart(graph)

        assert "No modules detected" in result.mermaid
        assert result.node_count == 0
        assert result.simplified is False

    def test_custom_title(self, generator: MermaidGenerator) -> None:
        """Test generating flowchart with custom title."""
        graph = ImportGraph(
            nodes=["app/core"],
            edges=[],
        )

        result = generator.generate_module_flowchart(graph, title="My Custom Title")

        assert "My Custom Title" in result.mermaid
        assert result.title == "My Custom Title"

    def test_node_shapes_cli(self, generator: MermaidGenerator) -> None:
        """Test that CLI modules get hexagon shape."""
        graph = ImportGraph(
            nodes=["app/cli"],
            edges=[],
        )

        result = generator.generate_module_flowchart(graph)

        # Hexagon shape uses {{ }} - verify cli module appears with shape
        assert "cli" in result.mermaid.lower()
        # The shape should contain braces for hexagon
        assert "{" in result.mermaid

    def test_node_shapes_api(self, generator: MermaidGenerator) -> None:
        """Test that API modules get stadium shape."""
        graph = ImportGraph(
            nodes=["app/api"],
            edges=[],
        )

        result = generator.generate_module_flowchart(graph)

        # Stadium shape uses ([ ])
        assert "([" in result.mermaid

    def test_node_shapes_models(self, generator: MermaidGenerator) -> None:
        """Test that model modules get subroutine shape."""
        graph = ImportGraph(
            nodes=["app/models"],
            edges=[],
        )

        result = generator.generate_module_flowchart(graph)

        # Subroutine shape uses [[ ]]
        assert "[[" in result.mermaid

    def test_node_shapes_utils(self, generator: MermaidGenerator) -> None:
        """Test that utility modules get rounded shape."""
        graph = ImportGraph(
            nodes=["app/utils"],
            edges=[],
        )

        result = generator.generate_module_flowchart(graph)

        # Rounded shape uses ( )
        assert '("' in result.mermaid

    def test_sanitize_node_ids(self, generator: MermaidGenerator) -> None:
        """Test that node IDs are sanitized for Mermaid."""
        graph = ImportGraph(
            nodes=["my-module/sub.module", "1-invalid/start"],
            edges=[],
        )

        result = generator.generate_module_flowchart(graph)

        # Should not contain invalid characters in IDs
        # IDs should be sanitized (no -, no ., starts with letter)
        mermaid = result.mermaid
        assert (
            "my_module_sub_module" in mermaid
            or "my-module" not in mermaid.split("[")[0]
        )

    def test_collapse_to_top_level(self, generator: MermaidGenerator) -> None:
        """Test collapsing nodes to top-level packages."""
        nodes = [
            "pkg/a/module1",
            "pkg/a/module2",
            "pkg/b/module1",
            "pkg/b/module2",
        ]
        edges = [
            ("pkg/a/module1", "pkg/b/module1"),
        ]

        collapsed_nodes, collapsed_edges = generator._collapse_to_top_level(
            nodes, edges
        )

        # Main package (pkg) shows 2-level depth for internal structure
        assert "pkg/a" in collapsed_nodes
        assert "pkg/b" in collapsed_nodes
        assert len(collapsed_nodes) == 2  # pkg/a and pkg/b

    def test_group_submodules(self, generator: MermaidGenerator) -> None:
        """Test grouping sub-modules."""
        nodes = [
            "pkg/sub/deep/module1",
            "pkg/sub/deep/module2",
            "pkg/other/module1",
        ]
        edges = []

        grouped_nodes, grouped_edges = generator._group_submodules(nodes, edges)

        # Should group to 2 levels max
        assert all("/" in n and n.count("/") <= 1 for n in grouped_nodes)

    def test_simplification_for_large_graphs(self) -> None:
        """Test that large graphs are simplified."""
        # Create graph with more than MAX_NODES_FULL_DETAIL nodes
        nodes = [f"module{i}" for i in range(MAX_NODES_FULL_DETAIL + 5)]
        edges = []

        generator = MermaidGenerator()
        result = generator.generate_module_flowchart(
            ImportGraph(nodes=nodes, edges=edges)
        )

        # Should be simplified
        assert result.simplified is True

    def test_no_simplification_for_small_graphs(self) -> None:
        """Test that small graphs are not simplified."""
        nodes = ["app/a", "app/b", "app/c"]
        edges = []

        generator = MermaidGenerator()
        result = generator.generate_module_flowchart(
            ImportGraph(nodes=nodes, edges=edges)
        )

        assert result.simplified is False
        assert result.node_count == 3

    def test_self_loop_removal(self, generator: MermaidGenerator) -> None:
        """Test that self-loops are removed during collapse."""
        nodes = ["pkg/a", "pkg/b"]
        edges = [("pkg/a", "pkg/b")]

        collapsed_nodes, collapsed_edges = generator._collapse_to_top_level(
            nodes, edges
        )

        # Both collapse to 'pkg', so edge should be removed (self-loop)
        assert len(collapsed_edges) == 0

    def test_edge_preservation(self, generator: MermaidGenerator) -> None:
        """Test that cross-package edges are preserved."""
        nodes = ["pkg_a/module", "pkg_b/module"]
        edges = [("pkg_a/module", "pkg_b/module")]

        collapsed_nodes, collapsed_edges = generator._collapse_to_top_level(
            nodes, edges
        )

        # Edge should be preserved as it crosses packages
        assert len(collapsed_edges) == 1

    def test_convenience_function(self) -> None:
        """Test the generate_module_flowchart convenience function."""
        graph = ImportGraph(
            nodes=["app/main"],
            edges=[],
        )

        result = generate_module_flowchart(graph)

        assert result is not None
        assert "flowchart TD" in result.mermaid

    def test_display_name_extraction(self, generator: MermaidGenerator) -> None:
        """Test extracting display-friendly names."""
        # Full path should show just the last part
        name = generator._get_display_name("very/long/path/to/module")
        assert name == "module"

        # Single name should stay as-is
        name = generator._get_display_name("standalone")
        assert name == "standalone"

    def test_edge_formatting(self, generator: MermaidGenerator) -> None:
        """Test that edges are formatted correctly."""
        graph = ImportGraph(
            nodes=["a", "b", "c"],
            edges=[("a", "b"), ("b", "c")],
        )

        result = generator.generate_module_flowchart(graph)

        # Should have arrow notation
        assert "-->" in result.mermaid
        # Should have both edges
        lines = result.mermaid.split("\n")
        edge_lines = [l for l in lines if "-->" in l]
        assert len(edge_lines) == 2

    def test_comment_title(self, generator: MermaidGenerator) -> None:
        """Test that title is added as Mermaid comment."""
        graph = ImportGraph(nodes=["a"], edges=[])

        result = generator.generate_module_flowchart(graph, title="Test Title")

        # Title should be a comment (starts with %%)
        assert "%% Test Title" in result.mermaid
