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
    # Set DEBUG_SQL=true in .env to log all SQL statements (development only).
    # NEVER enable this in production — it degrades throughput 10-20% and floods stdout.
    DEBUG_SQL: bool = False


settings = Settings()
