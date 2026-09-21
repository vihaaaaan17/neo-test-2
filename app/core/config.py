from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

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
    MAX_WORKSPACES_PER_USER: int = 5
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

    # Advanced Research Engine (Phase 1)
    ENABLE_ADVANCED_RESEARCH: bool = False
    ACTIVE_RESEARCH_ENGINE: str | None = "open_deep_research"

settings = Settings()
