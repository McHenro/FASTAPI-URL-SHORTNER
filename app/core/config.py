from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0          # DB 0 → URL cache (existing)
    redis_password: Optional[str] = None

    database_url: str          # postgresql+asyncpg://...

    # Celery uses separate Redis DBs to avoid key collisions with the URL cache
    celery_broker_db: int = 1  # DB 1 → task queue
    celery_backend_db: int = 2 # DB 2 → task results

    class Config:
        env_file = ".env"

    @property
    def redis_url(self) -> str:
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}"

    @property
    def celery_broker_url(self) -> str:
        return f"{self.redis_url}/{self.celery_broker_db}"

    @property
    def celery_backend_url(self) -> str:
        return f"{self.redis_url}/{self.celery_backend_db}"

    @property
    def sync_database_url(self) -> str:
        """Celery workers need a sync driver — swap asyncpg for psycopg2."""
        return self.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")


settings = Settings()
