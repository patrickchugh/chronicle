"""Mermaid diagram generation for flow-based documentation.

Generates Mermaid flowcharts showing module relationships from import graphs.
"""

import logging
from collections import defaultdict

from chronicle.models.canonical.module import ImportGraph, ModuleFlowDiagram

logger = logging.getLogger(__name__)

# Maximum nodes before simplification
MAX_NODES_FULL_DETAIL = 15
MAX_NODES_MODULE_LEVEL = 30


class MermaidGenerator:
    """Generates Mermaid diagrams from import graphs and analysis data.

    Implements complexity management:
    - < 15 nodes: Full detail
    - 15-30 nodes: Group sub-modules
    - 30+ nodes: Show only top-level packages
    """

    # Node shapes for different module types
    NODE_SHAPES = {
        "cli": '{{"{name}"}}',  # Hexagon for CLI
        "api": '(["{name}"])',  # Stadium for API
        "models": '[["{name}"]]',  # Subroutine for models
        "services": '["{name}"]',  # Rectangle for services (default)
        "utils": '("{name}")',  # Rounded for utilities
        "default": '["{name}"]',  # Default rectangle
    }

    def __init__(self) -> None:
        """Initialize the Mermaid generator."""
        pass

    def generate_module_flowchart(
        self,
        import_graph: ImportGraph,
        title: str = "Module Dependencies",
    ) -> ModuleFlowDiagram:
        """Generate a Mermaid flowchart from an import graph.

        Args:
            import_graph: Import graph with nodes and edges
            title: Diagram title

        Returns:
            ModuleFlowDiagram with Mermaid syntax
        """
        nodes = import_graph.nodes
        edges = import_graph.edges

        if not nodes:
            return ModuleFlowDiagram(
                mermaid="flowchart TD\n    empty[No modules detected]",
                node_count=0,
                simplified=False,
                title=title,
            )

        # Determine simplification level
        simplified = False
        if len(nodes) > MAX_NODES_MODULE_LEVEL:
            # Collapse to top-level packages only
            nodes, edges = self._collapse_to_top_level(nodes, edges)
            simplified = True
        elif len(nodes) > MAX_NODES_FULL_DETAIL:
            # Group sub-modules
            nodes, edges = self._group_submodules(nodes, edges)
            simplified = True

        # Generate Mermaid syntax
        mermaid = self._generate_mermaid_syntax(nodes, edges, title)

        return ModuleFlowDiagram(
            mermaid=mermaid,
            node_count=len(nodes),
            simplified=simplified,
            title=title,
        )

    def _collapse_to_top_level(
        self,
        nodes: list[str],
        edges: list[tuple[str, str]],
    ) -> tuple[list[str], list[tuple[str, str]]]:
        """Collapse modules to show meaningful package structure.

        Uses adaptive depth: for the main package (most nodes), show
        2-level depth to reveal internal structure. Test packages are
        excluded entirely to focus on application architecture.

        Args:
            nodes: Original node names
            edges: Original edges

        Returns:
            Tuple of (collapsed_nodes, collapsed_edges)
        """
        # Packages to exclude from diagram (tests clutter the architecture view)
        excluded_packages = {"tests", "test", "spec", "specs", "__tests__"}

        # Count nodes per top-level package
        package_counts: dict[str, int] = defaultdict(int)
        for node in nodes:
            top_level = node.split("/")[0]
            package_counts[top_level] += 1

        # Identify the main package (the one with most nodes, excluding tests)
        main_packages = set()
        for pkg, count in package_counts.items():
            if pkg not in excluded_packages and count >= 3:
                main_packages.add(pkg)

        # Map each node to its collapsed form
        node_mapping: dict[str, str] = {}
        collapsed_nodes: set[str] = set()

        for node in nodes:
            parts = node.split("/")
            top_level = parts[0]

            # Skip test packages entirely
            if top_level in excluded_packages:
                continue

            # For main packages, show 2-level depth to reveal structure
            if top_level in main_packages and len(parts) >= 2:
                # Use first 2 levels (e.g., chronicle/analyzers, chronicle/models)
                collapsed = "/".join(parts[:2])
            else:
                # For small packages, just use top level
                collapsed = top_level

            node_mapping[node] = collapsed
            collapsed_nodes.add(collapsed)

        # Collapse edges (skip edges involving excluded packages)
        collapsed_edges: set[tuple[str, str]] = set()
        for source, target in edges:
            # Skip if either endpoint is a test package
            source_top = source.split("/")[0]
            target_top = target.split("/")[0]
            if source_top in excluded_packages or target_top in excluded_packages:
                continue

            collapsed_source = node_mapping.get(source)
            collapsed_target = node_mapping.get(target)
            # Skip self-loops and edges with unmapped nodes
            if (
                collapsed_source
                and collapsed_target
                and collapsed_source != collapsed_target
            ):
                collapsed_edges.add((collapsed_source, collapsed_target))

        return sorted(collapsed_nodes), list(collapsed_edges)

    def _group_submodules(
        self,
        nodes: list[str],
        edges: list[tuple[str, str]],
    ) -> tuple[list[str], list[tuple[str, str]]]:
        """Group sub-modules under their parent modules.

        Collapses modules with more than 2 levels of nesting.

        Args:
            nodes: Original node names
            edges: Original edges

        Returns:
            Tuple of (grouped_nodes, grouped_edges)
        """
        # Map nodes to 2-level depth
        node_mapping: dict[str, str] = {}
        grouped_nodes: set[str] = set()

        for node in nodes:
            parts = node.split("/")
            if len(parts) > 2:
                # Collapse to 2 levels
                grouped = "/".join(parts[:2])
            else:
                grouped = node
            node_mapping[node] = grouped
            grouped_nodes.add(grouped)

        # Group edges
        grouped_edges: set[tuple[str, str]] = set()
        for source, target in edges:
            grouped_source = node_mapping.get(source, source)
            grouped_target = node_mapping.get(target, target)
            if grouped_source != grouped_target:
                grouped_edges.add((grouped_source, grouped_target))

        return sorted(grouped_nodes), list(grouped_edges)

    def _generate_mermaid_syntax(
        self,
        nodes: list[str],
        edges: list[tuple[str, str]],
        title: str,
    ) -> str:
        """Generate Mermaid flowchart syntax.

        Args:
            nodes: Node names
            edges: Edge tuples
            title: Diagram title

        Returns:
            Mermaid flowchart syntax string
        """
        lines = [
            "%%{init: {'flowchart': {'curve': 'linear'}}}%%",
            "flowchart TD",
        ]

        # Add title as a comment
        lines.append(f"    %% {title}")
        lines.append("")

        # Create node ID mapping (sanitize names for Mermaid)
        # Filter out empty nodes first
        valid_nodes = [n for n in nodes if n and n.strip()]
        node_ids: dict[str, str] = {}
        for i, node in enumerate(valid_nodes):
            node_id = self._sanitize_node_id(node, i)
            node_ids[node] = node_id

        # Add node definitions with appropriate shapes
        for node in valid_nodes:
            node_id = node_ids[node]
            display_name = self._get_display_name(node)
            # Ensure display name is never empty
            if not display_name or not display_name.strip():
                display_name = node_id
            shape = self._get_node_shape(node, display_name)
            lines.append(f"    {node_id}{shape}")

        lines.append("")

        # Add edges (skip edges with missing or empty nodes)
        for source, target in edges:
            if not source or not source.strip() or not target or not target.strip():
                continue
            if source not in node_ids or target not in node_ids:
                continue
            source_id = node_ids[source]
            target_id = node_ids[target]
            lines.append(f"    {source_id} --> {target_id}")

        return "\n".join(lines)

    def _sanitize_node_id(self, node: str, index: int) -> str:
        """Create a valid Mermaid node ID from a module name.

        Args:
            node: Module name
            index: Unique index for disambiguation

        Returns:
            Valid Mermaid node ID
        """
        # Replace invalid characters
        sanitized = node.replace("/", "_").replace("-", "_").replace(".", "_")
        # Ensure it starts with a letter
        if sanitized and not sanitized[0].isalpha():
            sanitized = f"m{index}_{sanitized}"
        return sanitized or f"m{index}"

    def _get_display_name(self, node: str) -> str:
        """Get a display-friendly name for a node.

        Args:
            node: Module path

        Returns:
            Display name (never empty)
        """
        if not node or not node.strip():
            return "unnamed"

        # Use just the last part of the path for display
        parts = node.split("/")
        name = parts[-1] if parts else node

        # Ensure we have a valid name
        if not name or not name.strip():
            name = parts[0] if parts else "unnamed"

        # Escape special characters that break Mermaid
        # Mermaid doesn't handle quotes or brackets well in node labels
        name = name.replace('"', "'").replace("[", "(").replace("]", ")")

        return name if name else "unnamed"

    def _get_node_shape(self, node: str, display_name: str) -> str:
        """Determine the Mermaid shape for a node based on its type.

        Args:
            node: Module path
            display_name: Display name

        Returns:
            Mermaid shape syntax with display name
        """
        node_lower = node.lower()

        # Determine module type from name
        if "cli" in node_lower or "command" in node_lower:
            shape_template = self.NODE_SHAPES["cli"]
        elif "api" in node_lower or "endpoint" in node_lower or "route" in node_lower:
            shape_template = self.NODE_SHAPES["api"]
        elif "model" in node_lower or "schema" in node_lower or "entity" in node_lower:
            shape_template = self.NODE_SHAPES["models"]
        elif "util" in node_lower or "helper" in node_lower or "common" in node_lower:
            shape_template = self.NODE_SHAPES["utils"]
        elif "service" in node_lower or "handler" in node_lower:
            shape_template = self.NODE_SHAPES["services"]
        else:
            shape_template = self.NODE_SHAPES["default"]

        return shape_template.format(name=display_name)


def generate_module_flowchart(
    import_graph: ImportGraph,
    title: str = "Module Dependencies",
) -> ModuleFlowDiagram:
    """Generate a Mermaid flowchart from an import graph.

    Convenience function for diagram generation.

    Args:
        import_graph: Import graph with nodes and edges
        title: Diagram title

    Returns:
        ModuleFlowDiagram with Mermaid syntax
    """
    generator = MermaidGenerator()
    return generator.generate_module_flowchart(import_graph, title)
