"""Unit tests for canonical data formats (Principle V)."""

from datetime import UTC, datetime

from chronicle.models.canonical import (
    CanonicalArchitecture,
    CanonicalAST,
    CanonicalClass,
    CanonicalFunction,
    CanonicalGraph,
    CanonicalModule,
    CanonicalPackage,
    CanonicalSBOM,
    NodeMetadata,
    SBOMSource,
)


class TestCanonicalSBOM:
    """Tests for CanonicalSBOM format."""

    def test_empty_sbom(self) -> None:
        """Test creating an empty SBOM."""
        sbom = CanonicalSBOM()

        assert sbom.packages == []
        assert sbom.package_count == 0
        assert sbom.get_unique_ecosystems() == []

    def test_add_package(self) -> None:
        """Test adding packages to SBOM."""
        sbom = CanonicalSBOM()

        sbom.add_package(
            CanonicalPackage(
                name="express",
                ecosystem="npm",
                version="4.18.0",
            )
        )

        assert sbom.package_count == 1
        assert sbom.get_unique_ecosystems() == ["npm"]

    def test_get_packages_by_ecosystem(self) -> None:
        """Test filtering packages by ecosystem."""
        sbom = CanonicalSBOM(
            packages=[
                CanonicalPackage(name="express", ecosystem="npm"),
                CanonicalPackage(name="lodash", ecosystem="npm"),
                CanonicalPackage(name="flask", ecosystem="pypi"),
            ]
        )

        npm_packages = sbom.get_packages_by_ecosystem("npm")

        assert len(npm_packages) == 2
        assert all(p.ecosystem == "npm" for p in npm_packages)

    def test_to_dict(self) -> None:
        """Test converting SBOM to dictionary."""
        sbom = CanonicalSBOM(
            packages=[
                CanonicalPackage(
                    name="express",
                    ecosystem="npm",
                    version="4.18.0",
                    license="MIT",
                )
            ],
            source=SBOMSource(
                tool="syft",
                tool_version="0.90.0",
                scanned_at=datetime.now(UTC),
                target="/repo",
            ),
        )

        data = sbom.to_dict()

        assert data["package_count"] == 1
        assert "npm" in data["ecosystems"]
        assert data["source"]["tool"] == "syft"

    def test_get_direct_packages(self) -> None:
        """Test filtering direct dependencies (T064k)."""
        sbom = CanonicalSBOM(
            packages=[
                CanonicalPackage(name="express", ecosystem="npm", is_direct=True),
                CanonicalPackage(name="lodash", ecosystem="npm", is_direct=True),
                CanonicalPackage(name="accepts", ecosystem="npm", is_direct=False),
                CanonicalPackage(
                    name="array-flatten", ecosystem="npm", is_direct=False
                ),
            ]
        )

        direct = sbom.get_direct_packages()

        assert len(direct) == 2
        assert all(p.is_direct for p in direct)
        assert {p.name for p in direct} == {"express", "lodash"}

    def test_get_transitive_packages(self) -> None:
        """Test filtering transitive dependencies (T064k)."""
        sbom = CanonicalSBOM(
            packages=[
                CanonicalPackage(name="express", ecosystem="npm", is_direct=True),
                CanonicalPackage(name="lodash", ecosystem="npm", is_direct=True),
                CanonicalPackage(name="accepts", ecosystem="npm", is_direct=False),
                CanonicalPackage(
                    name="array-flatten", ecosystem="npm", is_direct=False
                ),
            ]
        )

        transitive = sbom.get_transitive_packages()

        assert len(transitive) == 2
        assert all(not p.is_direct for p in transitive)
        assert {p.name for p in transitive} == {"accepts", "array-flatten"}

    def test_direct_package_count(self) -> None:
        """Test direct_package_count property (T064k)."""
        sbom = CanonicalSBOM(
            packages=[
                CanonicalPackage(name="express", ecosystem="npm", is_direct=True),
                CanonicalPackage(name="lodash", ecosystem="npm", is_direct=True),
                CanonicalPackage(name="accepts", ecosystem="npm", is_direct=False),
                CanonicalPackage(
                    name="array-flatten", ecosystem="npm", is_direct=False
                ),
                CanonicalPackage(name="body-parser", ecosystem="npm", is_direct=False),
            ]
        )

        assert sbom.package_count == 5
        assert sbom.direct_package_count == 2

    def test_to_dict_includes_direct_package_count(self) -> None:
        """Test that to_dict includes direct_package_count (T064k)."""
        sbom = CanonicalSBOM(
            packages=[
                CanonicalPackage(name="express", ecosystem="npm", is_direct=True),
                CanonicalPackage(name="accepts", ecosystem="npm", is_direct=False),
            ]
        )

        data = sbom.to_dict()

        assert data["package_count"] == 2
        assert data["direct_package_count"] == 1


class TestCanonicalPackage:
    """Tests for CanonicalPackage format."""

    def test_minimal_package(self) -> None:
        """Test creating a minimal package."""
        pkg = CanonicalPackage(name="test", ecosystem="npm")

        assert pkg.name == "test"
        assert pkg.ecosystem == "npm"
        assert pkg.version is None
        assert pkg.license is None
        assert pkg.is_direct is False  # Default is False

    def test_full_package(self) -> None:
        """Test creating a fully specified package."""
        pkg = CanonicalPackage(
            name="express",
            ecosystem="npm",
            version="4.18.0",
            license="MIT",
            source_file="package.json",
            purl="pkg:npm/express@4.18.0",
        )

        data = pkg.to_dict()

        assert data["name"] == "express"
        assert data["version"] == "4.18.0"
        assert data["purl"] == "pkg:npm/express@4.18.0"

    def test_is_direct_field(self) -> None:
        """Test is_direct field for distinguishing direct vs transitive deps (T064k)."""
        direct_pkg = CanonicalPackage(
            name="express",
            ecosystem="npm",
            version="4.18.0",
            is_direct=True,
        )
        transitive_pkg = CanonicalPackage(
            name="@types/express",
            ecosystem="npm",
            version="4.17.0",
            is_direct=False,
        )

        assert direct_pkg.is_direct is True
        assert transitive_pkg.is_direct is False

        # Verify is_direct is included in to_dict when True
        direct_data = direct_pkg.to_dict()
        transitive_data = transitive_pkg.to_dict()

        assert direct_data.get("is_direct") is True
        assert "is_direct" not in transitive_data  # Not included when False


class TestCanonicalArchitecture:
    """Tests for CanonicalArchitecture format."""

    def test_empty_architecture(self) -> None:
        """Test creating an empty architecture."""
        arch = CanonicalArchitecture()

        assert arch.graph.node_count == 0
        assert arch.graph.connection_count == 0
        assert arch.cloud_providers == []
        assert arch.has_image is False

    def test_add_nodes_and_connections(self) -> None:
        """Test adding nodes and connections."""
        graph = CanonicalGraph()

        graph.add_node(
            "aws_s3_bucket.data",
            NodeMetadata(type="aws_s3_bucket", provider="aws", name="data-bucket"),
        )
        graph.add_node(
            "aws_lambda_function.processor",
            NodeMetadata(type="aws_lambda_function", provider="aws"),
        )
        graph.add_connection("aws_s3_bucket.data", "aws_lambda_function.processor")

        assert graph.node_count == 2
        assert graph.connection_count == 1
        assert "aws" in graph.cloud_providers

    def test_multi_cloud(self) -> None:
        """Test multi-cloud architecture."""
        graph = CanonicalGraph()

        graph.add_node(
            "aws_s3_bucket.data",
            NodeMetadata(type="aws_s3_bucket", provider="aws"),
        )
        graph.add_node(
            "google_compute_instance.vm",
            NodeMetadata(type="google_compute_instance", provider="gcp"),
        )

        assert set(graph.cloud_providers) == {"aws", "gcp"}

    def test_to_dict(self) -> None:
        """Test converting architecture to dictionary."""
        graph = CanonicalGraph()
        graph.add_node(
            "aws_s3_bucket.data",
            NodeMetadata(type="aws_s3_bucket", provider="aws"),
        )

        arch = CanonicalArchitecture(graph=graph)
        data = arch.to_dict()

        assert data["node_count"] == 1
        assert data["connection_count"] == 0
        assert "aws" in data["cloud_providers"]


class TestCanonicalAST:
    """Tests for CanonicalAST format."""

    def test_empty_ast(self) -> None:
        """Test creating an empty AST."""
        ast = CanonicalAST()

        assert ast.module_count == 0
        assert ast.class_count == 0
        assert ast.function_count == 0
        assert ast.get_languages() == []

    def test_add_elements(self) -> None:
        """Test adding AST elements."""
        ast = CanonicalAST()

        ast.add_module(
            CanonicalModule(
                name="user_service",
                path="src/services/user.py",
                language="python",
                imports=["typing", "dataclasses"],
            )
        )

        ast.add_class(
            CanonicalClass(
                name="UserService",
                file="src/services/user.py",
                line=10,
                methods=["create", "get", "delete"],
                bases=["BaseService"],
            )
        )

        ast.add_function(
            CanonicalFunction(
                name="main",
                file="src/main.py",
                line=1,
                parameters=[],
                is_async=False,
            )
        )

        assert ast.module_count == 1
        assert ast.class_count == 1
        assert ast.function_count == 1
        assert "python" in ast.get_languages()

    def test_get_by_file(self) -> None:
        """Test getting elements by file path."""
        ast = CanonicalAST()

        ast.add_class(CanonicalClass(name="A", file="file1.py", line=1))
        ast.add_class(CanonicalClass(name="B", file="file1.py", line=10))
        ast.add_class(CanonicalClass(name="C", file="file2.py", line=1))

        classes_in_file1 = ast.get_classes_in_file("file1.py")

        assert len(classes_in_file1) == 2
        assert all(c.file == "file1.py" for c in classes_in_file1)

    def test_to_dict(self) -> None:
        """Test converting AST to dictionary."""
        ast = CanonicalAST()
        ast.add_module(
            CanonicalModule(
                name="test",
                path="test.py",
                language="python",
            )
        )

        data = ast.to_dict()

        assert data["module_count"] == 1
        assert data["class_count"] == 0
        assert data["function_count"] == 0
        assert "python" in data["languages"]


# =============================================================================
# Phase 4d: Code Explanation Data Model Tests (T076a, T076b)
# =============================================================================


class TestCanonicalFunctionNewFields:
    """Tests for CanonicalFunction new fields (T076a)."""

    def test_function_with_docstring(self) -> None:
        """Test CanonicalFunction with docstring field."""
        func = CanonicalFunction(
            name="calculate_total",
            file="src/utils.py",
            line=10,
            parameters=["items", "tax_rate"],
            docstring="Calculate the total price including tax.",
        )

        assert func.docstring == "Calculate the total price including tax."
        data = func.to_dict()
        assert data["docstring"] == "Calculate the total price including tax."

    def test_function_with_return_type(self) -> None:
        """Test CanonicalFunction with return_type field."""
        func = CanonicalFunction(
            name="get_user",
            file="src/services.py",
            line=25,
            parameters=["user_id"],
            return_type="User",
        )

        assert func.return_type == "User"
        data = func.to_dict()
        assert data["return_type"] == "User"

    def test_function_with_source_snippet(self) -> None:
        """Test CanonicalFunction with source_snippet field."""
        snippet = """result = x + y
if result > max_value:
    result = max_value
return result"""
        func = CanonicalFunction(
            name="add_with_cap",
            file="src/math.py",
            line=5,
            parameters=["x", "y", "max_value"],
            source_snippet=snippet,
        )

        assert func.source_snippet == snippet
        data = func.to_dict()
        assert data["source_snippet"] == snippet

    def test_function_with_description(self) -> None:
        """Test CanonicalFunction with LLM-generated description field."""
        func = CanonicalFunction(
            name="process_data",
            file="src/processor.py",
            line=42,
            parameters=["data"],
            description="Transforms raw data into the expected output format.",
        )

        assert (
            func.description == "Transforms raw data into the expected output format."
        )
        data = func.to_dict()
        assert (
            data["description"]
            == "Transforms raw data into the expected output format."
        )

    def test_function_with_all_new_fields(self) -> None:
        """Test CanonicalFunction with all new fields set."""
        func = CanonicalFunction(
            name="full_function",
            file="src/complete.py",
            line=100,
            parameters=["a", "b", "c"],
            is_async=True,
            docstring="A fully documented function.",
            return_type="dict[str, int]",
            source_snippet="return {'sum': a + b + c}",
            description="Calculates the sum of three numbers and returns it in a dict.",
        )

        assert func.docstring == "A fully documented function."
        assert func.return_type == "dict[str, int]"
        assert func.source_snippet == "return {'sum': a + b + c}"
        assert (
            func.description
            == "Calculates the sum of three numbers and returns it in a dict."
        )

        data = func.to_dict()
        assert all(
            key in data
            for key in ["docstring", "return_type", "source_snippet", "description"]
        )

    def test_function_optional_fields_are_none_by_default(self) -> None:
        """Test that new fields are None by default."""
        func = CanonicalFunction(
            name="simple_func",
            file="test.py",
            line=1,
        )

        assert func.docstring is None
        assert func.return_type is None
        assert func.source_snippet is None
        assert func.description is None


class TestCanonicalClassNewFields:
    """Tests for CanonicalClass new fields (T076b)."""

    def test_class_with_docstring(self) -> None:
        """Test CanonicalClass with docstring field."""
        cls = CanonicalClass(
            name="UserService",
            file="src/services/user.py",
            line=15,
            methods=["create", "get", "update", "delete"],
            bases=["BaseService"],
            docstring="Service for managing user accounts.",
        )

        assert cls.docstring == "Service for managing user accounts."
        data = cls.to_dict()
        assert data["docstring"] == "Service for managing user accounts."

    def test_class_with_description(self) -> None:
        """Test CanonicalClass with LLM-generated description field."""
        cls = CanonicalClass(
            name="DataProcessor",
            file="src/processor.py",
            line=10,
            methods=["process", "validate"],
            bases=[],
            description="Handles data transformation and validation pipeline.",
        )

        assert cls.description == "Handles data transformation and validation pipeline."
        data = cls.to_dict()
        assert (
            data["description"]
            == "Handles data transformation and validation pipeline."
        )

    def test_class_with_both_docstring_and_description(self) -> None:
        """Test CanonicalClass with both docstring and description."""
        cls = CanonicalClass(
            name="APIClient",
            file="src/api.py",
            line=20,
            methods=["get", "post", "put", "delete"],
            bases=["HTTPClient"],
            docstring="HTTP client for REST API interactions.",
            description="Provides methods for making HTTP requests to external APIs.",
        )

        assert cls.docstring is not None
        assert cls.description is not None
        assert cls.docstring != cls.description

    def test_class_optional_fields_are_none_by_default(self) -> None:
        """Test that new fields are None by default."""
        cls = CanonicalClass(
            name="SimpleClass",
            file="test.py",
            line=1,
        )

        assert cls.docstring is None
        assert cls.description is None
