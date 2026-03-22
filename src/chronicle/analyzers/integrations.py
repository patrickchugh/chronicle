"""External integration detection for flow-based documentation.

Detects calls to external services:
- HTTP clients (requests, httpx, fetch, axios)
- Databases (SQLAlchemy, Django ORM, Prisma)
- Message queues (boto3 SQS, Kafka, RabbitMQ)
- Caches (Redis, Memcached)
- Cloud storage (S3, GCS)
"""

import logging
import re
from collections import defaultdict
from pathlib import Path

from chronicle.models.canonical.module import ExternalIntegration

logger = logging.getLogger(__name__)


class IntegrationDetector:
    """Detects external service integrations in a codebase.

    Scans for library imports and method calls that indicate connections
    to external services like databases, APIs, queues, and caches.
    """

    # Integration patterns by type and language
    # Format: (import_pattern, call_patterns, service_name)
    INTEGRATION_PATTERNS = {
        "http": {
            "python": [
                (
                    "requests",
                    [r"requests\.(get|post|put|delete|patch|head)"],
                    "requests",
                ),
                ("httpx", [r"httpx\.(get|post|put|delete|patch|AsyncClient)"], "httpx"),
                ("aiohttp", [r"aiohttp\.ClientSession"], "aiohttp"),
                ("urllib", [r"urllib\.request\.urlopen"], "urllib"),
            ],
            "javascript": [
                ("axios", [r"axios\.(get|post|put|delete|patch)"], "axios"),
                ("fetch", [r"fetch\s*\("], "fetch"),
                ("node-fetch", [r"fetch\s*\("], "node-fetch"),
                ("got", [r"got\.(get|post|put|delete|patch)"], "got"),
            ],
            "go": [
                ("net/http", [r"http\.(Get|Post|NewRequest)"], "net/http"),
            ],
        },
        "database": {
            "python": [
                (
                    "sqlalchemy",
                    [r"session\.(query|execute|add|delete)", r"create_engine"],
                    "sqlalchemy",
                ),
                (
                    "django",
                    [r"\.objects\.(filter|get|create|all)", r"models\."],
                    "django-orm",
                ),
                ("psycopg2", [r"psycopg2\.connect"], "postgresql"),
                (
                    "pymongo",
                    [r"pymongo\.MongoClient", r"\.find\(", r"\.insert"],
                    "mongodb",
                ),
                ("motor", [r"motor\.motor_asyncio"], "mongodb-async"),
                ("asyncpg", [r"asyncpg\.connect"], "postgresql-async"),
                ("sqlite3", [r"sqlite3\.connect"], "sqlite"),
            ],
            "javascript": [
                ("prisma", [r"prisma\.\w+\.(find|create|update|delete)"], "prisma"),
                ("mongoose", [r"mongoose\.(connect|model)", r"\.find\("], "mongoose"),
                ("sequelize", [r"sequelize\.define", r"\.findAll\("], "sequelize"),
                ("knex", [r"knex\(", r"\.select\("], "knex"),
                ("typeorm", [r"@Entity", r"getRepository"], "typeorm"),
            ],
            "go": [
                ("database/sql", [r"sql\.(Open|Query|Exec)"], "database/sql"),
                ("gorm", [r"gorm\.Open", r"db\.(Find|Create|Save)"], "gorm"),
            ],
        },
        "queue": {
            "python": [
                (
                    "boto3.*sqs",
                    [r"sqs\.send_message", r"sqs\.receive_message"],
                    "aws-sqs",
                ),
                (
                    "kafka",
                    [r"KafkaProducer", r"KafkaConsumer", r"\.produce\("],
                    "kafka",
                ),
                (
                    "pika",
                    [r"pika\.BlockingConnection", r"channel\.basic_publish"],
                    "rabbitmq",
                ),
                ("celery", [r"@celery\.task", r"\.delay\("], "celery"),
                ("rq", [r"rq\.Queue", r"\.enqueue\("], "redis-queue"),
            ],
            "javascript": [
                ("amqplib", [r"amqp\.connect", r"channel\.sendToQueue"], "rabbitmq"),
                ("kafkajs", [r"Kafka\(", r"producer\.send"], "kafka"),
                ("bull", [r"new Queue\(", r"\.add\("], "bull-queue"),
                (
                    "@aws-sdk/client-sqs",
                    [r"SQSClient", r"SendMessageCommand"],
                    "aws-sqs",
                ),
            ],
        },
        "cache": {
            "python": [
                (
                    "redis",
                    [r"redis\.Redis", r"\.get\(", r"\.set\(", r"\.hget\("],
                    "redis",
                ),
                (
                    "aiocache",
                    [r"@cached", r"Cache\.from_url"],
                    "aiocache",
                ),
                ("pymemcache", [r"pymemcache\.Client"], "memcached"),
                ("cachetools", [r"@cached", r"TTLCache"], "cachetools"),
            ],
            "javascript": [
                ("redis", [r"createClient\(", r"\.get\(", r"\.set\("], "redis"),
                ("ioredis", [r"new Redis\(", r"\.get\(", r"\.set\("], "redis"),
                ("memcached", [r"Memcached\("], "memcached"),
            ],
        },
        "storage": {
            "python": [
                (
                    "boto3.*s3",
                    [r"s3\.upload_file", r"s3\.download_file", r"s3\.put_object"],
                    "aws-s3",
                ),
                (
                    "google.cloud.storage",
                    [r"storage\.Client", r"bucket\.blob"],
                    "gcs",
                ),
                ("azure.storage", [r"BlobServiceClient"], "azure-blob"),
            ],
            "javascript": [
                (
                    "@aws-sdk/client-s3",
                    [r"S3Client", r"PutObjectCommand", r"GetObjectCommand"],
                    "aws-s3",
                ),
                ("@google-cloud/storage", [r"Storage\(", r"bucket\("], "gcs"),
            ],
        },
        "llm": {
            "python": [
                (
                    "litellm",
                    [r"litellm\.completion", r"litellm\.acompletion"],
                    "litellm",
                ),
                ("openai", [r"openai\.ChatCompletion", r"OpenAI\("], "openai"),
                (
                    "anthropic",
                    [r"anthropic\.Anthropic", r"\.messages\.create"],
                    "anthropic",
                ),
                (
                    "boto3.*bedrock",
                    [r"bedrock-runtime", r"invoke_model"],
                    "aws-bedrock",
                ),
                (
                    "langchain",
                    [r"ChatOpenAI", r"ChatAnthropic", r"LLMChain"],
                    "langchain",
                ),
                ("google.generativeai", [r"genai\.GenerativeModel"], "google-gemini"),
            ],
            "javascript": [
                ("openai", [r"OpenAI\(", r"chat\.completions"], "openai"),
                (
                    "@anthropic-ai/sdk",
                    [r"Anthropic\(", r"\.messages\.create"],
                    "anthropic",
                ),
                (
                    "@aws-sdk/client-bedrock-runtime",
                    [r"BedrockRuntimeClient", r"InvokeModelCommand"],
                    "aws-bedrock",
                ),
                ("langchain", [r"ChatOpenAI", r"ChatAnthropic"], "langchain"),
            ],
        },
    }

    def __init__(self, repo_path: Path) -> None:
        """Initialize the integration detector.

        Args:
            repo_path: Path to repository root
        """
        self.repo_path = repo_path

    def detect_external_integrations(
        self, file_paths: list[Path] | None = None
    ) -> list[ExternalIntegration]:
        """Detect external integrations in the repository.

        Args:
            file_paths: Optional specific files to scan

        Returns:
            List of detected external integrations
        """
        # Track integrations by (name, type, library)
        integrations: dict[tuple[str, str, str], set[str]] = defaultdict(set)

        if file_paths is None:
            file_paths = self._find_source_files()

        for file_path in file_paths:
            try:
                self._detect_in_file(file_path, integrations)
            except Exception as e:
                logger.warning(f"Failed to detect integrations in {file_path}: {e}")

        # Convert to ExternalIntegration objects
        result: list[ExternalIntegration] = []
        for (name, int_type, library), locations in integrations.items():
            result.append(
                ExternalIntegration(
                    name=name,
                    type=int_type,
                    library=library,
                    locations=sorted(locations),
                )
            )

        logger.info(f"Detected {len(result)} external integrations")
        return result

    def _find_source_files(self) -> list[Path]:
        """Find all source files in the repository."""
        extensions = [".py", ".js", ".ts", ".tsx", ".go", ".java"]
        skip_dirs = {
            ".git",
            ".venv",
            "venv",
            "node_modules",
            "__pycache__",
            "dist",
            "build",
            "tests",
            "test",
            "spec",
            "specs",
        }

        files: list[Path] = []
        for ext in extensions:
            for file_path in self.repo_path.rglob(f"*{ext}"):
                if any(skip_dir in file_path.parts for skip_dir in skip_dirs):
                    continue
                files.append(file_path)

        return files

    def _detect_in_file(
        self,
        file_path: Path,
        integrations: dict[tuple[str, str, str], set[str]],
    ) -> None:
        """Detect integrations in a single file.

        Args:
            file_path: Path to source file
            integrations: Dictionary to accumulate results
        """
        rel_path = str(file_path.relative_to(self.repo_path))

        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            return

        suffix = file_path.suffix.lower()
        language = self._get_language(suffix)

        if not language:
            return

        # Check each integration type
        for int_type, lang_patterns in self.INTEGRATION_PATTERNS.items():
            if language not in lang_patterns:
                continue

            for import_pattern, call_patterns, service_name in lang_patterns[language]:
                # Check if library is imported/used
                if not self._check_import(content, import_pattern, language):
                    continue

                # Check for actual usage
                for call_pattern in call_patterns:
                    if re.search(call_pattern, content):
                        key = (service_name, int_type, import_pattern.split(".")[0])
                        integrations[key].add(rel_path)
                        break

    def _get_language(self, suffix: str) -> str | None:
        """Get language from file suffix."""
        mapping = {
            ".py": "python",
            ".js": "javascript",
            ".mjs": "javascript",
            ".ts": "javascript",
            ".tsx": "javascript",
            ".go": "go",
            ".java": "java",
        }
        return mapping.get(suffix)

    def _check_import(self, content: str, import_pattern: str, language: str) -> bool:
        """Check if a library is imported in the file.

        Args:
            content: File content
            import_pattern: Pattern to match in imports
            language: Programming language

        Returns:
            True if the library is imported
        """
        # Normalize pattern for regex
        pattern_regex = import_pattern.replace(".", r"\.").replace("*", r".*")

        if language == "python":
            # Check for "import X" or "from X import"
            if re.search(rf"(?:import|from)\s+{pattern_regex}", content):
                return True
        elif language == "javascript":
            # Check for "require('X')" or "import ... from 'X'"
            if re.search(
                rf'(?:require\s*\(["\']|from\s+["\']){pattern_regex}', content
            ):
                return True
        elif language == "go":
            # Check for import "X"
            if re.search(rf'import\s+.*["\'].*{pattern_regex}', content):
                return True

        return False


def detect_external_integrations(
    repo_path: Path, file_paths: list[Path] | None = None
) -> list[ExternalIntegration]:
    """Detect external integrations in a repository.

    Convenience function for integration detection.

    Args:
        repo_path: Path to repository root
        file_paths: Optional specific files to scan

    Returns:
        List of detected external integrations
    """
    detector = IntegrationDetector(repo_path)
    return detector.detect_external_integrations(file_paths)
