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

    # STORM runs in an isolated environment (knowledge-storm's dependency pins conflict with the app's)
    STORM_PYTHON: str | None = None  # interpreter of the isolated STORM env; default: <repo>/venv-storm
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
from dataclasses import dataclass

DEFAULT_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_NVIDIA_MODEL = "deepseek-ai/deepseek-v4.1-flash"
DEFAULT_OPENAI_MODEL = "gpt-4o"


@dataclass(frozen=True)
class LLMProvider:
    """Resolved OpenAI-compatible LLM endpoint for the active provider."""
    name: str  # "openai" or "nvidia"
    api_key: str | None
    base_url: str | None
    model: str


def resolve_llm_provider(cfg: Settings | None = None, require_key: bool = False) -> LLMProvider:
    """
    The single place that decides which LLM provider, key, base URL and model Neosis uses.

    NVIDIA is used when LLM_PROVIDER is "nvidia", or when no OpenAI key is set but an NVIDIA key is.
    A trailing "/chat/completions" is stripped from the base URL. With require_key=True a missing
    key raises instead of returning an unusable provider.
    """
    cfg = cfg or settings
    use_nvidia = (cfg.LLM_PROVIDER or "").lower() == "nvidia" or (not cfg.OPENAI_API_KEY and cfg.NVIDIA_API_KEY)
    if use_nvidia:
        provider = LLMProvider(
            name="nvidia",
            api_key=cfg.NVIDIA_API_KEY or cfg.OPENAI_API_KEY,
            base_url=cfg.NVIDIA_BASE_URL or DEFAULT_NVIDIA_BASE_URL,
            model=cfg.NVIDIA_MODEL or DEFAULT_NVIDIA_MODEL,
        )
    else:
        provider = LLMProvider(
            name="openai",
            api_key=cfg.OPENAI_API_KEY,
            base_url=cfg.OPENAI_BASE_URL,
            model=cfg.OPENAI_MODEL or DEFAULT_OPENAI_MODEL,
        )

    if provider.base_url and provider.base_url.endswith("/chat/completions"):
        provider = LLMProvider(provider.name, provider.api_key, provider.base_url[: -len("/chat/completions")], provider.model)
    if require_key and not provider.api_key:
        raise RuntimeError("Neither OPENAI_API_KEY nor NVIDIA_API_KEY is configured.")
    return provider


# Export the resolved provider as OpenAI-compatible environment variables. Upstream engines (ODR's
# init_chat_model / the OpenAI client) read these, so this is the only place that writes them.
_provider = resolve_llm_provider()
if _provider.api_key:
    os.environ["OPENAI_API_KEY"] = _provider.api_key
if _provider.base_url:
    os.environ["OPENAI_BASE_URL"] = _provider.base_url
    os.environ["OPENAI_API_BASE"] = _provider.base_url
if _provider.model:
    os.environ["OPENAI_MODEL"] = _provider.model
if _provider.name == "nvidia":
    if _provider.api_key:
        os.environ["NVIDIA_API_KEY"] = _provider.api_key
    os.environ["NVIDIA_BASE_URL"] = _provider.base_url
    os.environ["NVIDIA_MODEL"] = _provider.model

if settings.TAVILY_API_KEY:
    os.environ["TAVILY_API_KEY"] = settings.TAVILY_API_KEY
