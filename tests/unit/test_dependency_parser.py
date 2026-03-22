"""Unit tests for dependency parser."""

from pathlib import Path

import pytest

from chronicle.analyzers.dependency import DependencyParser, DirectDependencyResolver


class TestDependencyParser:
    """Tests for DependencyParser."""

    @pytest.fixture
    def parser(self) -> DependencyParser:
        """Create a dependency parser instance."""
        return DependencyParser()

    def test_parse_package_json(self, parser: DependencyParser, tmp_path: Path) -> None:
        """Test parsing package.json."""
        pkg_json = tmp_path / "package.json"
        pkg_json.write_text(
            """{
    "name": "test-project",
    "version": "1.0.0",
    "dependencies": {
        "express": "^4.18.0",
        "lodash": "4.17.21"
    },
    "devDependencies": {
        "jest": "^29.0.0",
        "typescript": "^5.0.0"
    }
}"""
        )

        result = parser.parse_directory(tmp_path)

        assert len(result.languages) >= 1  # JavaScript/TypeScript detected
        assert len(result.dependencies) == 2
        assert len(result.dev_dependencies) == 2

        dep_names = [d.name for d in result.dependencies]
        assert "express" in dep_names
        assert "lodash" in dep_names

    def test_parse_requirements_txt(
        self, parser: DependencyParser, tmp_path: Path
    ) -> None:
        """Test parsing requirements.txt."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text(
            """
# Production dependencies
flask==2.3.0
sqlalchemy>=2.0
requests

# Comment line
-e git+https://github.com/user/repo.git#egg=package
"""
        )

        result = parser.parse_directory(tmp_path)

        assert len(result.languages) >= 1  # Python detected
        assert len(result.dependencies) >= 3

        dep_names = [d.name for d in result.dependencies]
        assert "flask" in dep_names
        assert "sqlalchemy" in dep_names
        assert "requests" in dep_names

    def test_parse_pyproject_toml(
        self, parser: DependencyParser, tmp_path: Path
    ) -> None:
        """Test parsing pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[project]
name = "test-project"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "typer>=0.9.0",
    "rich>=13.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "ruff>=0.1.0",
]
"""
        )

        result = parser.parse_directory(tmp_path)

        # Check Python version detected (uses capitalized name)
        py_lang = next(
            (l for l in result.languages if l.name.lower() == "python"), None
        )
        assert py_lang is not None
        assert "3.11" in (py_lang.version or "")

        assert len(result.dependencies) >= 2
        dep_names = [d.name for d in result.dependencies]
        assert "typer" in dep_names
        assert "rich" in dep_names

    def test_parse_go_mod(self, parser: DependencyParser, tmp_path: Path) -> None:
        """Test parsing go.mod."""
        go_mod = tmp_path / "go.mod"
        go_mod.write_text(
            """
module github.com/user/project

go 1.21

require (
    github.com/gin-gonic/gin v1.9.0
    github.com/spf13/cobra v1.7.0
)

require (
    golang.org/x/text v0.12.0 // indirect
)
"""
        )

        result = parser.parse_directory(tmp_path)

        # Check Go version detected (uses capitalized name)
        go_lang = next((l for l in result.languages if l.name.lower() == "go"), None)
        assert go_lang is not None
        assert go_lang.version == "1.21"

        dep_names = [d.name for d in result.dependencies]
        assert "github.com/gin-gonic/gin" in dep_names
        assert "github.com/spf13/cobra" in dep_names

    def test_parse_pom_xml(self, parser: DependencyParser, tmp_path: Path) -> None:
        """Test parsing pom.xml."""
        pom = tmp_path / "pom.xml"
        pom.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<project>
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>test-project</artifactId>
    <version>1.0.0</version>

    <properties>
        <maven.compiler.source>17</maven.compiler.source>
        <maven.compiler.target>17</maven.compiler.target>
    </properties>

    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter</artifactId>
            <version>3.1.0</version>
        </dependency>
        <dependency>
            <groupId>junit</groupId>
            <artifactId>junit</artifactId>
            <version>4.13.2</version>
            <scope>test</scope>
        </dependency>
    </dependencies>
</project>"""
        )

        result = parser.parse_directory(tmp_path)

        # Check Java version detected (uses capitalized name)
        java_lang = next(
            (l for l in result.languages if l.name.lower() == "java"), None
        )
        assert java_lang is not None
        assert java_lang.version == "17"

        dep_names = [d.name for d in result.dependencies]
        # Maven may include groupId:artifactId format
        assert any("spring-boot-starter" in name for name in dep_names)

        dev_dep_names = [d.name for d in result.dev_dependencies]
        assert any("junit" in name for name in dev_dep_names)

    def test_parse_build_gradle(self, parser: DependencyParser, tmp_path: Path) -> None:
        """Test parsing build.gradle."""
        gradle = tmp_path / "build.gradle"
        gradle.write_text(
            """
plugins {
    id 'java'
    id 'org.springframework.boot' version '3.1.0'
}

sourceCompatibility = '17'

dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-web:3.1.0'
    implementation 'com.google.guava:guava:32.0.0-jre'
    testImplementation 'org.junit.jupiter:junit-jupiter:5.9.0'
}
"""
        )

        result = parser.parse_directory(tmp_path)

        dep_names = [d.name for d in result.dependencies]
        # Gradle may include full coordinates or just artifact name
        assert any("spring-boot-starter-web" in name for name in dep_names)
        assert any("guava" in name for name in dep_names)

    def test_framework_detection(
        self, parser: DependencyParser, tmp_path: Path
    ) -> None:
        """Test framework detection from dependencies."""
        pkg_json = tmp_path / "package.json"
        pkg_json.write_text(
            """{
    "dependencies": {
        "react": "^18.0.0",
        "react-dom": "^18.0.0",
        "next": "^13.0.0"
    }
}"""
        )

        result = parser.parse_directory(tmp_path)

        fw_names = [f.name.lower() for f in result.frameworks]
        assert "react" in fw_names
        assert "next.js" in fw_names

    def test_python_framework_detection(
        self, parser: DependencyParser, tmp_path: Path
    ) -> None:
        """Test Python framework detection."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text(
            """
fastapi>=0.100.0
uvicorn>=0.22.0
django>=4.0.0
"""
        )

        result = parser.parse_directory(tmp_path)

        fw_names = [f.name.lower() for f in result.frameworks]
        # At least FastAPI should be detected as a framework
        assert "fastapi" in fw_names

    def test_empty_directory(self, parser: DependencyParser, tmp_path: Path) -> None:
        """Test parsing an empty directory."""
        result = parser.parse_directory(tmp_path)

        assert len(result.languages) == 0
        assert len(result.frameworks) == 0
        assert len(result.dependencies) == 0

    def test_to_dict(self, parser: DependencyParser, tmp_path: Path) -> None:
        """Test converting result to dictionary."""
        pkg_json = tmp_path / "package.json"
        pkg_json.write_text(
            """{
    "dependencies": {"express": "^4.18.0"}
}"""
        )

        result = parser.parse_directory(tmp_path)
        data = result.to_dict()

        assert "languages" in data
        assert "frameworks" in data
        assert "dependencies" in data
        assert "dev_dependencies" in data


class TestDirectDependencyResolver:
    """Tests for DirectDependencyResolver (T064l, T064m)."""

    @pytest.fixture
    def resolver(self) -> DirectDependencyResolver:
        """Create a DirectDependencyResolver instance."""
        return DirectDependencyResolver()

    def test_parse_package_json(
        self, resolver: DirectDependencyResolver, tmp_path: Path
    ) -> None:
        """Test parsing package.json for direct deps (T064l)."""
        pkg_json = tmp_path / "package.json"
        pkg_json.write_text(
            """{
    "name": "test-project",
    "dependencies": {
        "express": "^4.18.0",
        "@aws-sdk/client-dynamodb": "^3.0.0"
    },
    "devDependencies": {
        "jest": "^29.0.0"
    }
}"""
        )

        resolver.resolve_from_directory(tmp_path)

        # Production dependencies should be direct
        assert resolver.is_direct("express", "npm")
        assert resolver.is_direct("@aws-sdk/client-dynamodb", "npm")

        # Dev dependencies should also be direct (they're declared in manifest)
        assert resolver.is_direct("jest", "npm")

        # Transitive dependencies should not be direct
        assert not resolver.is_direct("accepts", "npm")
        assert not resolver.is_direct("@smithy/types", "npm")

    def test_parse_requirements_txt(
        self, resolver: DirectDependencyResolver, tmp_path: Path
    ) -> None:
        """Test parsing requirements.txt for direct deps (T064m)."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text(
            """
# Dependencies
flask==2.3.0
sqlalchemy>=2.0
requests
boto3==1.28.0
"""
        )

        resolver.resolve_from_directory(tmp_path)

        # All listed packages are direct
        assert resolver.is_direct("flask", "pypi")
        assert resolver.is_direct("sqlalchemy", "pypi")
        assert resolver.is_direct("requests", "pypi")
        assert resolver.is_direct("boto3", "pypi")

        # Transitive dependencies are not direct
        assert not resolver.is_direct("werkzeug", "pypi")
        assert not resolver.is_direct("botocore", "pypi")

    def test_pypi_name_normalization(
        self, resolver: DirectDependencyResolver, tmp_path: Path
    ) -> None:
        """Test PyPI package name normalization."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text(
            """
Flask
SQLAlchemy
aws-cdk-lib
"""
        )

        resolver.resolve_from_directory(tmp_path)

        # Case-insensitive
        assert resolver.is_direct("flask", "pypi")
        assert resolver.is_direct("FLASK", "pypi")

        # Hyphen/underscore normalization
        assert resolver.is_direct("aws_cdk_lib", "pypi")
        assert resolver.is_direct("aws-cdk-lib", "pypi")

    def test_npm_scoped_packages(
        self, resolver: DirectDependencyResolver, tmp_path: Path
    ) -> None:
        """Test npm scoped package handling (T064f)."""
        pkg_json = tmp_path / "package.json"
        pkg_json.write_text(
            """{
    "dependencies": {
        "@aws-sdk/client-dynamodb": "^3.0.0",
        "@nestjs/core": "^10.0.0",
        "express": "^4.18.0"
    }
}"""
        )

        resolver.resolve_from_directory(tmp_path)

        # Scoped packages should match exactly
        assert resolver.is_direct("@aws-sdk/client-dynamodb", "npm")
        assert resolver.is_direct("@nestjs/core", "npm")
        assert resolver.is_direct("express", "npm")

        # Other scoped packages from same scope should NOT be direct
        assert not resolver.is_direct("@aws-sdk/types", "npm")
        assert not resolver.is_direct("@nestjs/common", "npm")

    def test_get_direct_dependencies(
        self, resolver: DirectDependencyResolver, tmp_path: Path
    ) -> None:
        """Test getting all direct dependencies for an ecosystem."""
        pkg_json = tmp_path / "package.json"
        pkg_json.write_text(
            """{
    "dependencies": {
        "express": "^4.18.0",
        "lodash": "^4.17.0"
    }
}"""
        )

        resolver.resolve_from_directory(tmp_path)

        direct_npm = resolver.get_direct_dependencies("npm")

        assert "express" in direct_npm
        assert "lodash" in direct_npm
        assert len(direct_npm) == 2

    def test_multiple_ecosystems(
        self, resolver: DirectDependencyResolver, tmp_path: Path
    ) -> None:
        """Test resolving deps from multiple ecosystems."""
        # package.json
        pkg_json = tmp_path / "package.json"
        pkg_json.write_text('{"dependencies": {"express": "^4.0.0"}}')

        # requirements.txt
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("flask==2.3.0\n")

        resolver.resolve_from_directory(tmp_path)

        assert resolver.is_direct("express", "npm")
        assert resolver.is_direct("flask", "pypi")

        # Cross-ecosystem should not match
        assert not resolver.is_direct("express", "pypi")
        assert not resolver.is_direct("flask", "npm")

    def test_empty_directory(
        self, resolver: DirectDependencyResolver, tmp_path: Path
    ) -> None:
        """Test resolving from empty directory."""
        resolver.resolve_from_directory(tmp_path)

        assert resolver.get_direct_dependencies("npm") == set()
        assert resolver.get_direct_dependencies("pypi") == set()
        assert not resolver.is_direct("express", "npm")
