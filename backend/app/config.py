import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://tlac:tlac@db:5432/tlac")
SESSION_TTL_MINUTES = int(os.getenv("SESSION_TTL_MINUTES", "480"))
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "tlac_session")
CSRF_HEADER_NAME = "X-CSRF-Token"
LINK_OVERRIDES_PATH = os.getenv("LINK_OVERRIDES_PATH", "/data/link-overrides.json")
RUNNER_ENABLED = os.getenv("RUNNER_ENABLED", "1").lower() in {"1", "true", "yes"}
RUNNER_AUTO_PULL = os.getenv("RUNNER_AUTO_PULL", "0").lower() in {"1", "true", "yes"}
RUNNER_IMAGE = os.getenv("RUNNER_IMAGE", "python:3.12-slim")
RUNNER_DOCKER_HOST = os.getenv("RUNNER_DOCKER_HOST", "unix:///var/run/docker.sock")
RUNNER_DOCKER_API_VERSION = os.getenv("RUNNER_DOCKER_API_VERSION", "1.41")
RUNNER_TIMEOUT_SEC = int(os.getenv("RUNNER_TIMEOUT_SEC", "3"))
RUNNER_MEMORY_MB = int(os.getenv("RUNNER_MEMORY_MB", "128"))
RUNNER_CPUS = float(os.getenv("RUNNER_CPUS", "0.5"))
RUNNER_PIDS_LIMIT = int(os.getenv("RUNNER_PIDS_LIMIT", "64"))
RUNNER_TMPFS_MB = int(os.getenv("RUNNER_TMPFS_MB", "32"))
RUNNER_MAX_OUTPUT = int(os.getenv("RUNNER_MAX_OUTPUT", "20000"))
RUNNER_MAX_CODE_SIZE = int(os.getenv("RUNNER_MAX_CODE_SIZE", "20000"))
RUNNER_MAX_FILES = int(os.getenv("RUNNER_MAX_FILES", "8"))
RUNNER_MAX_FILE_BYTES = int(os.getenv("RUNNER_MAX_FILE_BYTES", "50000"))
RUNNER_MAX_ARCHIVE_BYTES = int(os.getenv("RUNNER_MAX_ARCHIVE_BYTES", "250000"))
RUNNER_CONCURRENCY = int(os.getenv("RUNNER_CONCURRENCY", "2"))
ATTENTION_STUCK_DAYS = int(os.getenv("ATTENTION_STUCK_DAYS", "7"))
ATTENTION_REVISION_THRESHOLD = int(os.getenv("ATTENTION_REVISION_THRESHOLD", "5"))
ATTENTION_LIMIT = int(os.getenv("ATTENTION_LIMIT", "200"))
RETENTION_YEARS = int(os.getenv("RETENTION_YEARS", "2"))
