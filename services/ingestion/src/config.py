from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "ingestion-service"
    debug: bool = False

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "documents"

    redis_url: str = "redis://localhost:6389"

    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "qwen2.5:14b"
    embedding_model: str = "nomic-embed-text"
    chunk_size: int = 512
    chunk_overlap: int = 64

    database_url: str = "postgresql+asyncpg://rag:rag_dev_password@localhost:5632/rag"
    index_version: str = "v1.0.0-nomic-768"

    kafka_brokers: str = "localhost:9092"


settings = Settings()
