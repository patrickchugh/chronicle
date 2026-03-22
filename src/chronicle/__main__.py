"""Entry point for running chronicle as a module.

Usage:
    python -m chronicle [command] [options]

Example:
    python -m chronicle write --output docs/SYSTEM.md
    python -m chronicle check
"""

from chronicle.cli import app

if __name__ == "__main__":
    app()
