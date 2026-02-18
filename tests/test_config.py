"""Tests for application configuration."""

from enrichment.config import Settings, get_settings


def test_settings_defaults():
    """Settings should have sensible defaults."""
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
    )
    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.search_index_baseline == "baseline-index"
    assert settings.search_index_enhanced == "enhanced-index"
    assert settings.storage_container_corpus == "corpus"
    assert settings.storage_container_results == "cu-results"
    assert settings.foundry_model_deployment_name == "gpt-4o"


def test_settings_from_env(monkeypatch):
    """Settings should load from environment variables."""
    monkeypatch.setenv(
        "CONTENTUNDERSTANDING_ENDPOINT", "https://test.services.ai.azure.com/"
    )
    monkeypatch.setenv("SEARCH_ENDPOINT", "https://test.search.windows.net")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")

    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert (
        settings.contentunderstanding_endpoint == "https://test.services.ai.azure.com/"
    )
    assert settings.search_endpoint == "https://test.search.windows.net"
    assert settings.environment == "production"
    assert settings.log_level == "WARNING"


def test_get_settings_returns_settings():
    """get_settings should return a Settings instance."""
    settings = get_settings()
    assert isinstance(settings, Settings)
