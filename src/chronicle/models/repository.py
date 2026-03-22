"""Repository entity representing the source git repository being analyzed.

The Repository entity contains metadata about the git repository and
provides validation to ensure the path exists and is accessible.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Repository:
    """Source git repository being analyzed.

    Contains source files, infrastructure code, and dependency manifests.

    Attributes:
        path: Absolute path to repository root
        name: Repository name (derived from path or git remote)
        git_ref: Current git commit SHA or branch name
        detected_languages: Languages detected via file extensions and parsing

    Validation Rules:
        - path must exist and be a directory
        - path should contain a .git directory (warning if not)
        - detected_languages populated from file extension scanning
    """

    path: Path
    name: str
    git_ref: str | None = None
    detected_languages: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate repository path after initialization."""
        # Ensure path is a Path object
        if isinstance(self.path, str):
            self.path = Path(self.path)

        # Convert to absolute path
        self.path = self.path.resolve()

    def validate(self) -> list[str]:
        """Validate the repository configuration.

        Returns:
            List of validation warning messages (empty if valid)

        Raises:
            ValueError: If path does not exist or is not a directory
        """
        warnings: list[str] = []

        if not self.path.exists():
            raise ValueError(f"Repository path does not exist: {self.path}")

        if not self.path.is_dir():
            raise ValueError(f"Repository path is not a directory: {self.path}")

        git_dir = self.path / ".git"
        if not git_dir.exists():
            warnings.append(f"Not a git repository (no .git directory): {self.path}")

        return warnings

    @property
    def is_git_repo(self) -> bool:
        """Check if the path is a git repository."""
        return (self.path / ".git").exists()

    @classmethod
    def from_path(cls, path: Path | str, name: str | None = None) -> "Repository":
        """Create a Repository from a path.

        Args:
            path: Path to the repository root
            name: Optional name override (defaults to directory name)

        Returns:
            Repository instance
        """
        path = Path(path).resolve()
        if name is None:
            name = path.name

        return cls(path=path, name=name)
