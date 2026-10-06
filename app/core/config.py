from dotenv import load_dotenv
load_dotenv(".env")

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENVIRONMENT: str = "development"  # "development", "test", "production"
    NEOSIS_ENV: str | None = None

    # Default to local docker-compose postgres
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/neosislm"
    SUPABASE_JWT_SECRET: str = "super-secret-jwt-token-for-supabase-local-dev-only"
    S3_BUCKET: str = "neosislm-dev"
    S3_ENDPOINT_URL: str | None = None
    AWS_ACCESS_KEY_ID: str = "mock-key"
    AWS_SECRET_ACCESS_KEY: str = "mock-secret"
    AWS_REGION: str = "us-east-1"
    # Redis — used as the background job queue broker and L2 cache.
    # Never store canonical data here; it is a pure acceleration layer.
    REDIS_URL: str = "redis://localhost:6379"
    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # CORS
    ALLOWED_ORIGINS: list[str] = ["*"]
    
    # Quotas
    MAX_WORKSPACES_PER_USER: int = 50
    MAX_SOURCES_PER_WORKSPACE: int = 50
    MAX_STORAGE_BYTES_PER_WORKSPACE: int = 500_000_000  # 500MB
    MAX_KNOWLEDGE_PER_WORKSPACE: int = 1000
    MAX_CONCURRENT_LLM_CALLS: int = 5

    # Set DEBUG_SQL=true in .env to log all SQL statements (development only).
    # NEVER enable this in production — it degrades throughput 10-20% and floods stdout.
    DEBUG_SQL: bool = False

    # Open Notebook Ground Engine Integration
    OPEN_NOTEBOOK_ENABLED: bool = True
    OPEN_NOTEBOOK_BASE_URL: str = "http://localhost:5055"
    OPEN_NOTEBOOK_TIMEOUT: int = 30
    OPEN_NOTEBOOK_ENCRYPTION_KEY: str | None = None
    GOOGLE_API_KEY: str | None = None

    # Advanced Research Engine (Phase 1)
    ENABLE_ADVANCED_RESEARCH: bool = False
    ACTIVE_RESEARCH_ENGINE: str | None = "open_deep_research"

    # STORM Configuration
    STORM_ENABLED: bool = False
    # Checkpointer Settings
    ASYNC_POSTGRES_SAVER_ENABLED: bool = False
    POSTGRES_DSN: str = "postgresql+asyncpg://user:password@localhost:5432/dbname"

    # Research Admission Settings
    USER_CONCURRENCY_LIMIT: int = 1
    WORKSPACE_CONCURRENCY_LIMIT: int = 2
    GLOBAL_CONCURRENCY_LIMIT: int = 10

    # LLM Provider Configuration ("openai" or "nvidia")
    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str | None = None
    OPENAI_MODEL: str = "gpt-4o"

    # NVIDIA NIM / OpenAI-compatible configuration
    NVIDIA_API_KEY: str | None = None
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL: str = "deepseek-ai/deepseek-v4.1-flash"
    TAVILY_API_KEY: str | None = None

    # Budget Policy Settings
    MAX_MODEL_CALLS: int = 100
    MAX_INPUT_TOKENS: int = 10000
    MAX_OUTPUT_TOKENS: int = 10000
    MAX_COST: float = 10.0


settings = Settings()

import os
# Auto-configure OpenAI compatibility variables when provider is NVIDIA or OpenAI
if (settings.LLM_PROVIDER or "").lower() == "nvidia":
    base_url = settings.NVIDIA_BASE_URL or "https://integrate.api.nvidia.com/v1"
    key = settings.NVIDIA_API_KEY or ""
    model = settings.NVIDIA_MODEL or "deepseek-ai/deepseek-v4.1-flash"

    os.environ["OPENAI_API_KEY"] = key
    os.environ["OPENAI_BASE_URL"] = base_url
    os.environ["OPENAI_API_BASE"] = base_url
    os.environ["OPENAI_MODEL"] = model
    os.environ["NVIDIA_API_KEY"] = key
    os.environ["NVIDIA_BASE_URL"] = base_url
    os.environ["NVIDIA_MODEL"] = model
elif (settings.LLM_PROVIDER or "").lower() == "openai":
    if settings.OPENAI_API_KEY:
        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
    if settings.OPENAI_BASE_URL:
        os.environ["OPENAI_BASE_URL"] = settings.OPENAI_BASE_URL
        os.environ["OPENAI_API_BASE"] = settings.OPENAI_BASE_URL
    if settings.OPENAI_MODEL:
        os.environ["OPENAI_MODEL"] = settings.OPENAI_MODEL

if settings.TAVILY_API_KEY:
    os.environ["TAVILY_API_KEY"] = settings.TAVILY_API_KEY
