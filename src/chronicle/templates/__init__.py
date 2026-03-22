"""chronicle template rendering (Principle II: Reproducibility).

This module provides Jinja2-based template rendering with deterministic output.
Templates are designed to produce identical output for identical input.
"""

from chronicle.templates.renderer import DocumentRenderer, SectionLoader

__all__ = ["DocumentRenderer", "SectionLoader"]
