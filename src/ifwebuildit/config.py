"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Azure AI Content Understanding
    contentunderstanding_endpoint: str = ""
    contentunderstanding_key: str = ""

    # Azure AI Search
    search_endpoint: str = ""
    search_api_key: str = ""
    search_index_baseline: str = "baseline-index"
    search_index_enhanced: str = "enhanced-index"

    # Azure Storage
    azure_storage_connection_string: str = "UseDevelopmentStorage=true"
    storage_container_corpus: str = "corpus"
    storage_container_results: str = "cu-results"

    # Azure AI Foundry
    foundry_project_endpoint: str = ""
    foundry_model_deployment_name: str = "gpt-4o"

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_key: str = ""
    embedding_deployment: str = "text-embedding-3-small"
    chat_deployment: str = "gpt-4o"

    # General
    environment: str = "development"
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


def get_settings() -> Settings:
    """Create and return application settings."""
    return Settings()
