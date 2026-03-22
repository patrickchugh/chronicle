"""chronicle - Automated System Documentation Generator.

chronicle generates comprehensive system documentation for Enterprise IT audit,
architecture, security, and business stakeholders. It runs in CI/CD pipelines
to ensure documentation stays current as systems change.

Core principles:
- Deterministic-First: All analysis uses deterministic methods before LLM
- Reproducibility: Same input produces semantically identical output
- Preflight Validation: All dependencies validated before processing
- CI/CD Compatibility: No interactive prompts, meaningful exit codes
- Tool Agnosticism: Pluggable tools via adapter pattern
- Human Annotation Persistence: User content merged with generated docs
"""

__version__ = "0.1.0"
__author__ = "chronicle Contributors"
