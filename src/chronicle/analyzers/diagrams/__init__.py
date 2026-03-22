"""Diagram tool adapters (Principle V: Tool Agnosticism).

All diagram adapters output CanonicalArchitecture format.
"""

from chronicle.analyzers.diagrams.base import DiagramGenerator
from chronicle.analyzers.diagrams.terravision import TerravisionAdapter

__all__ = ["DiagramGenerator", "TerravisionAdapter"]
