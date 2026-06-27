"""Application configuration from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "documents"
    db_user: str = "postgres"
    db_password: str = "postgres"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_ttl_seconds: int = 3600
    redis_session_ttl_seconds: int = 86400
    redis_rate_limit_window_seconds: int = 60

    s3_bucket: str = "document-uploads"
    aws_region: str = "us-east-1"
    s3_prefix_raw: str = "upload/"
    s3_prefix_processing: str = "processing/"
    s3_prefix_processed: str = "processed/"
    s3_prefix_failed: str = "failed/"
    s3_prefix_archived: str = "archived/"

    sqs_queue_url: str = ""
    sqs_poll_wait_seconds: int = 20
    sqs_max_messages: int = 10

    openai_api_key: str | None = None
    chunk_size: int = 1000
    chunk_overlap: int = 200

    upload_rate_limit: int = 30
    search_rate_limit: int = 60

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
