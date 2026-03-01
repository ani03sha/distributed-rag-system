from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "query-service"
    debug: bool = False

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    redis_url: str = "redis://localhost:6389"

    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "qwen2.5:14b"
    embedding_model: str = "nomic-embed-text"


settings = Settings()
