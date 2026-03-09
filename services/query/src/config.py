from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).parent.parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    service_name: str = "query-service"
    debug: bool = False

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "documents"

    redis_url: str = "redis://localhost:6389"

    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "llama3.2:3b"
    embedding_model: str = "nomic-embed-text"
    retrieval_top_k: int = 5
    reranker_enabled: bool = False
    
    api_keys: str = "dev-key-1,dev-key-2" # Comma separated, replace with DB in prod
    jwt_secret_key: str = "change-me-inp-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 15
    jwt_refresh_expiry_days: int = 7
    
    otlp_endpoint: str = "http://localhost:4317"
    tracing_enabled: bool = True


settings = Settings()
