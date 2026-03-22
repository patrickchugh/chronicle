"""Dependency file parsing.

Parses dependency files to extract technology stack information:
- package.json (JavaScript/TypeScript)
- requirements.txt, pyproject.toml (Python)
- go.mod (Go)
- pom.xml, build.gradle (Java)

All output is used to populate TechnologyStack entity.
"""

import json
import re
from pathlib import Path

from chronicle.models.analysis import (
    Dependency,
    Framework,
    LanguageInfo,
    TechnologyStack,
)
from chronicle.utils.logging import get_logger

_logger = get_logger()

# Known frameworks by ecosystem
KNOWN_FRAMEWORKS: dict[str, dict[str, str]] = {
    "npm": {
        "express": "Express.js",
        "fastify": "Fastify",
        "koa": "Koa",
        "next": "Next.js",
        "react": "React",
        "vue": "Vue.js",
        "angular": "Angular",
        "svelte": "Svelte",
        "nestjs": "NestJS",
        "@nestjs/core": "NestJS",
    },
    "pypi": {
        "fastapi": "FastAPI",
        "flask": "Flask",
        "django": "Django",
        "starlette": "Starlette",
        "tornado": "Tornado",
        "pyramid": "Pyramid",
        "aiohttp": "aiohttp",
    },
    "go": {
        "github.com/gin-gonic/gin": "Gin",
        "github.com/labstack/echo": "Echo",
        "github.com/gofiber/fiber": "Fiber",
        "github.com/gorilla/mux": "Gorilla Mux",
    },
    "maven": {
        "org.springframework.boot": "Spring Boot",
        "org.springframework": "Spring Framework",
        "io.quarkus": "Quarkus",
        "io.micronaut": "Micronaut",
    },
}


class DependencyParser:
    """Parses dependency files to extract technology stack."""

    def __init__(self) -> None:
        """Initialize the dependency parser."""
        pass

    def parse_directory(self, directory: Path) -> TechnologyStack:
        """Parse all dependency files in a directory.

        Args:
            directory: Root directory to scan

        Returns:
            TechnologyStack with all detected dependencies
        """
        stack = TechnologyStack()
        languages_detected: dict[str, LanguageInfo] = {}

        # Scan for each file type
        parsers = [
            ("package.json", self._parse_package_json),
            ("requirements.txt", self._parse_requirements_txt),
            ("pyproject.toml", self._parse_pyproject_toml),
            ("go.mod", self._parse_go_mod),
            ("pom.xml", self._parse_pom_xml),
            ("build.gradle", self._parse_build_gradle),
        ]

        for filename, parser in parsers:
            file_path = directory / filename
            if file_path.exists():
                try:
                    deps, dev_deps, lang_info, frameworks = parser(file_path)
                    stack.dependencies.extend(deps)
                    stack.dev_dependencies.extend(dev_deps)

                    if lang_info and lang_info.name not in languages_detected:
                        languages_detected[lang_info.name] = lang_info

                    stack.frameworks.extend(frameworks)

                    _logger.debug(
                        f"Parsed {filename}: {len(deps)} deps, {len(dev_deps)} dev deps"
                    )
                except Exception as e:
                    _logger.warning(f"Failed to parse {file_path}: {e}")

        # Also check nested package.json files (monorepos)
        for pkg_json in directory.rglob("package.json"):
            if pkg_json.parent != directory and "node_modules" not in str(pkg_json):
                try:
                    deps, dev_deps, lang_info, frameworks = self._parse_package_json(
                        pkg_json
                    )
                    stack.dependencies.extend(deps)
                    stack.dev_dependencies.extend(dev_deps)
                    stack.frameworks.extend(frameworks)
                except Exception as e:
                    _logger.debug(f"Failed to parse nested {pkg_json}: {e}")

        stack.languages = list(languages_detected.values())
        return stack

    # =========================================================================
    # package.json (JavaScript/TypeScript)
    # =========================================================================

    def _parse_package_json(
        self, file_path: Path
    ) -> tuple[
        list[Dependency], list[Dependency], LanguageInfo | None, list[Framework]
    ]:
        """Parse package.json file.

        Args:
            file_path: Path to package.json

        Returns:
            Tuple of (dependencies, dev_dependencies, language_info, frameworks)
        """
        deps: list[Dependency] = []
        dev_deps: list[Dependency] = []
        frameworks: list[Framework] = []

        content = file_path.read_text(encoding="utf-8")
        data = json.loads(content)

        # Determine language (check for TypeScript)
        has_typescript = (
            "typescript" in data.get("devDependencies", {})
            or "typescript" in data.get("dependencies", {})
            or file_path.parent.joinpath("tsconfig.json").exists()
        )

        lang = LanguageInfo(
            name="TypeScript" if has_typescript else "JavaScript",
            version=None,
        )

        # Parse dependencies
        for name, version in data.get("dependencies", {}).items():
            dep = Dependency(
                name=name,
                version=self._clean_version(version),
                ecosystem="npm",
                source_file=str(file_path),
            )
            deps.append(dep)

            # Check for known frameworks
            if name in KNOWN_FRAMEWORKS.get("npm", {}):
                frameworks.append(
                    Framework(
                        name=KNOWN_FRAMEWORKS["npm"][name],
                        version=self._clean_version(version),
                        language=lang.name,
                    )
                )

        # Parse devDependencies
        for name, version in data.get("devDependencies", {}).items():
            dev_deps.append(
                Dependency(
                    name=name,
                    version=self._clean_version(version),
                    ecosystem="npm",
                    source_file=str(file_path),
                )
            )

        return deps, dev_deps, lang, frameworks

    # =========================================================================
    # requirements.txt (Python)
    # =========================================================================

    def _parse_requirements_txt(
        self, file_path: Path
    ) -> tuple[
        list[Dependency], list[Dependency], LanguageInfo | None, list[Framework]
    ]:
        """Parse requirements.txt file.

        Args:
            file_path: Path to requirements.txt

        Returns:
            Tuple of (dependencies, dev_dependencies, language_info, frameworks)
        """
        deps: list[Dependency] = []
        frameworks: list[Framework] = []

        lang = LanguageInfo(name="Python", version=None)

        content = file_path.read_text(encoding="utf-8")

        for line in content.split("\n"):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue

            # Parse package==version or package>=version etc.
            match = re.match(r"^([a-zA-Z0-9_-]+)(?:[<>=!]+(.+))?", line)
            if match:
                name = match.group(1).lower()
                version = match.group(2)

                dep = Dependency(
                    name=name,
                    version=version,
                    ecosystem="pypi",
                    source_file=str(file_path),
                )
                deps.append(dep)

                # Check for known frameworks
                if name in KNOWN_FRAMEWORKS.get("pypi", {}):
                    frameworks.append(
                        Framework(
                            name=KNOWN_FRAMEWORKS["pypi"][name],
                            version=version,
                            language="Python",
                        )
                    )

        return deps, [], lang, frameworks

    # =========================================================================
    # pyproject.toml (Python)
    # =========================================================================

    def _parse_pyproject_toml(
        self, file_path: Path
    ) -> tuple[
        list[Dependency], list[Dependency], LanguageInfo | None, list[Framework]
    ]:
        """Parse pyproject.toml file.

        Args:
            file_path: Path to pyproject.toml

        Returns:
            Tuple of (dependencies, dev_dependencies, language_info, frameworks)
        """
        deps: list[Dependency] = []
        dev_deps: list[Dependency] = []
        frameworks: list[Framework] = []

        content = file_path.read_text(encoding="utf-8")

        # Get Python version
        python_version = None
        version_match = re.search(r'requires-python\s*=\s*"([^"]+)"', content)
        if version_match:
            python_version = version_match.group(1)

        lang = LanguageInfo(name="Python", version=python_version)

        # Parse dependencies from [project] section
        deps_section = re.search(
            r"\[project\].*?dependencies\s*=\s*\[(.*?)\]", content, re.DOTALL
        )
        if deps_section:
            deps_content = deps_section.group(1)
            for line in deps_content.split("\n"):
                line = line.strip().strip(",").strip('"').strip("'")
                if line:
                    match = re.match(r"^([a-zA-Z0-9_-]+)(?:[<>=!]+(.+))?", line)
                    if match:
                        name = match.group(1).lower()
                        version = match.group(2)
                        deps.append(
                            Dependency(
                                name=name,
                                version=version,
                                ecosystem="pypi",
                                source_file=str(file_path),
                            )
                        )

                        if name in KNOWN_FRAMEWORKS.get("pypi", {}):
                            frameworks.append(
                                Framework(
                                    name=KNOWN_FRAMEWORKS["pypi"][name],
                                    version=version,
                                    language="Python",
                                )
                            )

        # Parse optional-dependencies (dev)
        dev_section = re.search(
            r"\[project\.optional-dependencies\].*?dev\s*=\s*\[(.*?)\]",
            content,
            re.DOTALL,
        )
        if dev_section:
            dev_content = dev_section.group(1)
            for line in dev_content.split("\n"):
                line = line.strip().strip(",").strip('"').strip("'")
                if line:
                    match = re.match(r"^([a-zA-Z0-9_-]+)(?:[<>=!]+(.+))?", line)
                    if match:
                        name = match.group(1).lower()
                        version = match.group(2)
                        dev_deps.append(
                            Dependency(
                                name=name,
                                version=version,
                                ecosystem="pypi",
                                source_file=str(file_path),
                            )
                        )

        return deps, dev_deps, lang, frameworks

    # =========================================================================
    # go.mod (Go)
    # =========================================================================

    def _parse_go_mod(
        self, file_path: Path
    ) -> tuple[
        list[Dependency], list[Dependency], LanguageInfo | None, list[Framework]
    ]:
        """Parse go.mod file.

        Args:
            file_path: Path to go.mod

        Returns:
            Tuple of (dependencies, dev_dependencies, language_info, frameworks)
        """
        deps: list[Dependency] = []
        frameworks: list[Framework] = []

        content = file_path.read_text(encoding="utf-8")

        # Get Go version
        go_version = None
        version_match = re.search(r"^go\s+(\d+\.\d+)", content, re.MULTILINE)
        if version_match:
            go_version = version_match.group(1)

        lang = LanguageInfo(name="Go", version=go_version)

        # Parse require block
        require_block = re.search(r"require\s*\((.*?)\)", content, re.DOTALL)
        if require_block:
            for line in require_block.group(1).split("\n"):
                line = line.strip()
                if line and not line.startswith("//"):
                    parts = line.split()
                    if len(parts) >= 2:
                        name = parts[0]
                        version = parts[1]
                        deps.append(
                            Dependency(
                                name=name,
                                version=version,
                                ecosystem="go",
                                source_file=str(file_path),
                            )
                        )

                        # Check for known frameworks
                        for framework_pkg, framework_name in KNOWN_FRAMEWORKS.get(
                            "go", {}
                        ).items():
                            if framework_pkg in name:
                                frameworks.append(
                                    Framework(
                                        name=framework_name,
                                        version=version,
                                        language="Go",
                                    )
                                )
                                break

        # Also check for single-line requires
        for match in re.finditer(r"^require\s+(\S+)\s+(\S+)", content, re.MULTILINE):
            name = match.group(1)
            version = match.group(2)
            if not any(d.name == name for d in deps):
                deps.append(
                    Dependency(
                        name=name,
                        version=version,
                        ecosystem="go",
                        source_file=str(file_path),
                    )
                )

        return deps, [], lang, frameworks

    # =========================================================================
    # pom.xml (Java/Maven)
    # =========================================================================

    def _parse_pom_xml(
        self, file_path: Path
    ) -> tuple[
        list[Dependency], list[Dependency], LanguageInfo | None, list[Framework]
    ]:
        """Parse pom.xml file (Maven).

        Args:
            file_path: Path to pom.xml

        Returns:
            Tuple of (dependencies, dev_dependencies, language_info, frameworks)
        """
        deps: list[Dependency] = []
        dev_deps: list[Dependency] = []
        frameworks: list[Framework] = []

        content = file_path.read_text(encoding="utf-8")

        # Get Java version
        java_version = None
        version_match = re.search(
            r"<java\.version>([^<]+)</java\.version>", content
        ) or re.search(
            r"<maven\.compiler\.source>([^<]+)</maven\.compiler\.source>", content
        )
        if version_match:
            java_version = version_match.group(1)

        lang = LanguageInfo(name="Java", version=java_version)

        # Parse dependencies
        for dep_match in re.finditer(
            r"<dependency>\s*"
            r"<groupId>([^<]+)</groupId>\s*"
            r"<artifactId>([^<]+)</artifactId>\s*"
            r"(?:<version>([^<]+)</version>)?\s*"
            r"(?:<scope>([^<]+)</scope>)?",
            content,
            re.DOTALL,
        ):
            group_id = dep_match.group(1)
            artifact_id = dep_match.group(2)
            version = dep_match.group(3)
            scope = dep_match.group(4)

            name = f"{group_id}:{artifact_id}"
            dep = Dependency(
                name=name,
                version=version,
                ecosystem="maven",
                source_file=str(file_path),
            )

            if scope == "test":
                dev_deps.append(dep)
            else:
                deps.append(dep)

                # Check for known frameworks
                for framework_pkg, framework_name in KNOWN_FRAMEWORKS.get(
                    "maven", {}
                ).items():
                    if framework_pkg in group_id:
                        if not any(f.name == framework_name for f in frameworks):
                            frameworks.append(
                                Framework(
                                    name=framework_name,
                                    version=version,
                                    language="Java",
                                )
                            )
                        break

        return deps, dev_deps, lang, frameworks

    # =========================================================================
    # build.gradle (Java/Gradle)
    # =========================================================================

    def _parse_build_gradle(
        self, file_path: Path
    ) -> tuple[
        list[Dependency], list[Dependency], LanguageInfo | None, list[Framework]
    ]:
        """Parse build.gradle file.

        Args:
            file_path: Path to build.gradle

        Returns:
            Tuple of (dependencies, dev_dependencies, language_info, frameworks)
        """
        deps: list[Dependency] = []
        dev_deps: list[Dependency] = []
        frameworks: list[Framework] = []

        content = file_path.read_text(encoding="utf-8")

        lang = LanguageInfo(name="Java", version=None)

        # Parse implementation/compile dependencies
        for match in re.finditer(
            r"(?:implementation|compile)\s+['\"]([^'\"]+)['\"]", content
        ):
            dep_string = match.group(1)
            parts = dep_string.split(":")
            if len(parts) >= 2:
                name = f"{parts[0]}:{parts[1]}"
                version = parts[2] if len(parts) > 2 else None
                deps.append(
                    Dependency(
                        name=name,
                        version=version,
                        ecosystem="maven",
                        source_file=str(file_path),
                    )
                )

                # Check for known frameworks
                for framework_pkg, framework_name in KNOWN_FRAMEWORKS.get(
                    "maven", {}
                ).items():
                    if framework_pkg in parts[0]:
                        if not any(f.name == framework_name for f in frameworks):
                            frameworks.append(
                                Framework(
                                    name=framework_name,
                                    version=version,
                                    language="Java",
                                )
                            )
                        break

        # Parse test dependencies
        for match in re.finditer(r"testImplementation\s+['\"]([^'\"]+)['\"]", content):
            dep_string = match.group(1)
            parts = dep_string.split(":")
            if len(parts) >= 2:
                name = f"{parts[0]}:{parts[1]}"
                version = parts[2] if len(parts) > 2 else None
                dev_deps.append(
                    Dependency(
                        name=name,
                        version=version,
                        ecosystem="maven",
                        source_file=str(file_path),
                    )
                )

        return deps, dev_deps, lang, frameworks

    # =========================================================================
    # Utilities
    # =========================================================================

    def _clean_version(self, version: str | None) -> str | None:
        """Clean version string by removing semver prefixes."""
        if version is None:
            return None

        # Remove common prefixes
        version = version.strip()
        if version.startswith("^") or version.startswith("~"):
            version = version[1:]
        if version.startswith(">=") or version.startswith("<="):
            version = version[2:]
        if (
            version.startswith(">")
            or version.startswith("<")
            or version.startswith("=")
        ):
            version = version[1:]

        return version if version else None


class DirectDependencyResolver:
    """Resolves direct dependencies from manifest files.

    Used to distinguish between direct dependencies (declared in manifest files
    like package.json, requirements.txt) and transitive dependencies (pulled in
    automatically by package managers).

    This is used by SBOM adapters to mark packages with is_direct=True when they
    appear in manifest files.
    """

    def __init__(self) -> None:
        """Initialize the resolver."""
        self._direct_deps: dict[str, set[str]] = {}  # ecosystem -> set of names

    def resolve_from_directory(self, directory: Path) -> None:
        """Scan a directory and collect all direct dependency names.

        Args:
            directory: Root directory to scan for manifest files
        """
        self._direct_deps = {
            "npm": set(),
            "pypi": set(),
            "go": set(),
            "maven": set(),
        }

        # Parse each manifest file type
        self._parse_package_json(directory)
        self._parse_requirements_txt(directory)
        self._parse_pyproject_toml(directory)
        self._parse_go_mod(directory)
        self._parse_pom_xml(directory)
        self._parse_build_gradle(directory)

        # Also check nested package.json files (monorepos)
        for pkg_json in directory.rglob("package.json"):
            if pkg_json.parent != directory and "node_modules" not in str(pkg_json):
                self._parse_package_json_file(pkg_json)

        _logger.debug(
            f"DirectDependencyResolver found: npm={len(self._direct_deps['npm'])}, "
            f"pypi={len(self._direct_deps['pypi'])}, go={len(self._direct_deps['go'])}, "
            f"maven={len(self._direct_deps['maven'])}"
        )

    def is_direct(self, name: str, ecosystem: str) -> bool:
        """Check if a package is a direct dependency.

        Args:
            name: Package name to check
            ecosystem: Package ecosystem (npm, pypi, go, maven)

        Returns:
            True if the package is declared in a manifest file
        """
        if ecosystem not in self._direct_deps:
            return False

        direct_names = self._direct_deps[ecosystem]

        # Direct match
        if name in direct_names:
            return True

        # For npm: normalize and try matching
        if ecosystem == "npm":
            return self._match_npm_package(name, direct_names)

        # For pypi: case-insensitive, normalize underscores/hyphens
        if ecosystem == "pypi":
            normalized = self._normalize_pypi_name(name)
            return any(
                self._normalize_pypi_name(direct_name) == normalized
                for direct_name in direct_names
            )

        return False

    def get_direct_dependencies(self, ecosystem: str) -> set[str]:
        """Get all direct dependency names for an ecosystem.

        Args:
            ecosystem: Package ecosystem (npm, pypi, go, maven)

        Returns:
            Set of direct dependency names
        """
        return self._direct_deps.get(ecosystem, set())

    def _match_npm_package(self, name: str, direct_names: set[str]) -> bool:
        """Match npm package name against direct dependencies.

        Handles scoped packages like @aws-sdk/client-dynamodb.

        Args:
            name: Package name from SBOM
            direct_names: Set of direct dependency names from package.json

        Returns:
            True if the package matches a direct dependency
        """
        # Exact match
        if name in direct_names:
            return True

        # For scoped packages, check if any direct dependency matches
        # e.g., @aws-sdk/client-dynamodb should match @aws-sdk/client-dynamodb
        if name.startswith("@"):
            return name in direct_names

        return False

    def _normalize_pypi_name(self, name: str) -> str:
        """Normalize PyPI package name for comparison.

        PyPI package names are case-insensitive and treat hyphens/underscores as equivalent.
        """
        return name.lower().replace("-", "_").replace(".", "_")

    def _parse_package_json(self, directory: Path) -> None:
        """Parse root package.json."""
        file_path = directory / "package.json"
        if file_path.exists():
            self._parse_package_json_file(file_path)

    def _parse_package_json_file(self, file_path: Path) -> None:
        """Parse a package.json file and extract dependency names."""
        try:
            content = file_path.read_text(encoding="utf-8")
            data = json.loads(content)

            # Both dependencies and devDependencies are direct dependencies
            for name in data.get("dependencies", {}).keys():
                self._direct_deps["npm"].add(name)

            for name in data.get("devDependencies", {}).keys():
                self._direct_deps["npm"].add(name)

        except Exception as e:
            _logger.debug(f"Failed to parse {file_path} for direct deps: {e}")

    def _parse_requirements_txt(self, directory: Path) -> None:
        """Parse requirements.txt."""
        file_path = directory / "requirements.txt"
        if not file_path.exists():
            return

        try:
            content = file_path.read_text(encoding="utf-8")
            for line in content.split("\n"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                match = re.match(r"^([a-zA-Z0-9_.-]+)", line)
                if match:
                    self._direct_deps["pypi"].add(match.group(1).lower())

        except Exception as e:
            _logger.debug(f"Failed to parse {file_path} for direct deps: {e}")

    def _parse_pyproject_toml(self, directory: Path) -> None:
        """Parse pyproject.toml."""
        file_path = directory / "pyproject.toml"
        if not file_path.exists():
            return

        try:
            content = file_path.read_text(encoding="utf-8")

            # Parse dependencies from [project] section
            deps_section = re.search(
                r"\[project\].*?dependencies\s*=\s*\[(.*?)\]", content, re.DOTALL
            )
            if deps_section:
                deps_content = deps_section.group(1)
                for line in deps_content.split("\n"):
                    line = line.strip().strip(",").strip('"').strip("'")
                    if line:
                        match = re.match(r"^([a-zA-Z0-9_.-]+)", line)
                        if match:
                            self._direct_deps["pypi"].add(match.group(1).lower())

            # Parse optional-dependencies (dev)
            dev_section = re.search(
                r"\[project\.optional-dependencies\].*?dev\s*=\s*\[(.*?)\]",
                content,
                re.DOTALL,
            )
            if dev_section:
                dev_content = dev_section.group(1)
                for line in dev_content.split("\n"):
                    line = line.strip().strip(",").strip('"').strip("'")
                    if line:
                        match = re.match(r"^([a-zA-Z0-9_.-]+)", line)
                        if match:
                            self._direct_deps["pypi"].add(match.group(1).lower())

        except Exception as e:
            _logger.debug(f"Failed to parse {file_path} for direct deps: {e}")

    def _parse_go_mod(self, directory: Path) -> None:
        """Parse go.mod."""
        file_path = directory / "go.mod"
        if not file_path.exists():
            return

        try:
            content = file_path.read_text(encoding="utf-8")

            # Parse require block
            require_block = re.search(r"require\s*\((.*?)\)", content, re.DOTALL)
            if require_block:
                for line in require_block.group(1).split("\n"):
                    line = line.strip()
                    if line and not line.startswith("//"):
                        parts = line.split()
                        if parts:
                            self._direct_deps["go"].add(parts[0])

            # Also check for single-line requires
            for match in re.finditer(r"^require\s+(\S+)", content, re.MULTILINE):
                self._direct_deps["go"].add(match.group(1))

        except Exception as e:
            _logger.debug(f"Failed to parse {file_path} for direct deps: {e}")

    def _parse_pom_xml(self, directory: Path) -> None:
        """Parse pom.xml."""
        file_path = directory / "pom.xml"
        if not file_path.exists():
            return

        try:
            content = file_path.read_text(encoding="utf-8")

            for dep_match in re.finditer(
                r"<dependency>\s*"
                r"<groupId>([^<]+)</groupId>\s*"
                r"<artifactId>([^<]+)</artifactId>",
                content,
                re.DOTALL,
            ):
                group_id = dep_match.group(1)
                artifact_id = dep_match.group(2)
                name = f"{group_id}:{artifact_id}"
                self._direct_deps["maven"].add(name)

        except Exception as e:
            _logger.debug(f"Failed to parse {file_path} for direct deps: {e}")

    def _parse_build_gradle(self, directory: Path) -> None:
        """Parse build.gradle."""
        file_path = directory / "build.gradle"
        if not file_path.exists():
            return

        try:
            content = file_path.read_text(encoding="utf-8")

            for match in re.finditer(
                r"(?:implementation|compile|testImplementation)\s+['\"]([^'\"]+)['\"]",
                content,
            ):
                dep_string = match.group(1)
                parts = dep_string.split(":")
                if len(parts) >= 2:
                    name = f"{parts[0]}:{parts[1]}"
                    self._direct_deps["maven"].add(name)

        except Exception as e:
            _logger.debug(f"Failed to parse {file_path} for direct deps: {e}")
