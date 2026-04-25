from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    database_url: str

    class Config:
        env_file = ".env"


settings = Settings()
