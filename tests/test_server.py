"""Tests for the FastAPI server."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from enrichment.server import create_app


@pytest.fixture
def client():
    """Create a test client with mocked storage and empty settings."""
    with (
        patch("enrichment.server.StorageService") as mock_storage_class,
        patch("enrichment.server.get_settings") as mock_settings,
    ):
        settings = MagicMock()
        settings.azure_openai_endpoint = ""
        settings.azure_openai_key = ""
        settings.search_endpoint = ""
        settings.search_api_key = ""
        settings.contentunderstanding_endpoint = ""
        settings.contentunderstanding_key = ""
        settings.embedding_deployment = "text-embedding-3-small"
        settings.chat_deployment = "gpt-4o"
        settings.search_index_baseline = "baseline-index"
        settings.search_index_enhanced = "enhanced-index"
        settings.azure_storage_connection_string = "UseDevelopmentStorage=true"
        settings.storage_account_url = ""
        settings.storage_container_corpus = "corpus"
        settings.storage_container_results = "cu-results"
        settings.environment = "test"
        settings.log_level = "INFO"
        mock_settings.return_value = settings
        mock_storage = mock_storage_class.return_value
        mock_storage.list_documents.return_value = []
        app = create_app()
        yield TestClient(app), mock_storage


def test_health_check(client):
    """GET /api/health should return ok."""
    test_client, _ = client
    response = test_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


def test_get_corpus_empty(client):
    """GET /api/corpus should return empty corpus info."""
    test_client, mock_storage = client
    mock_storage.list_documents.return_value = []

    response = test_client.get("/api/corpus")
    assert response.status_code == 200
    data = response.json()
    assert data["total_documents"] == 0
    assert data["documents"] == []


def test_get_corpus_with_documents(client):
    """GET /api/corpus should list documents."""
    test_client, mock_storage = client
    mock_storage.list_documents.return_value = ["report1.pdf", "report2.pdf"]

    response = test_client.get("/api/corpus")
    assert response.status_code == 200
    data = response.json()
    assert data["total_documents"] == 2
    assert len(data["documents"]) == 2
    assert data["documents"][0]["filename"] == "report1.pdf"


def test_upload_document(client):
    """POST /api/corpus/upload should upload and return document info."""
    test_client, mock_storage = client
    mock_storage.upload_document.return_value = "https://storage/corpus/test.pdf"

    response = test_client.post(
        "/api/corpus/upload",
        files={"file": ("test.pdf", b"fake-pdf-content", "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.pdf"
    assert data["blob_url"] == "https://storage/corpus/test.pdf"
    mock_storage.upload_document.assert_called_once()


def test_delete_document(client):
    """DELETE /api/corpus/{filename} should delete the document."""
    test_client, mock_storage = client

    response = test_client.delete("/api/corpus/test.pdf")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "deleted"
    mock_storage.delete_document.assert_called_once_with("test.pdf")


def test_chat_baseline_unconfigured(client):
    """POST /api/chat/baseline returns fallback when services not configured."""
    test_client, _ = client
    response = test_client.post("/api/chat/baseline", json={"message": "test question"})
    assert response.status_code == 200
    data = response.json()
    assert data["pipeline_type"] == "baseline"
    assert "not yet configured" in data["message"]


def test_chat_enhanced_unconfigured(client):
    """POST /api/chat/enhanced returns fallback when services not configured."""
    test_client, _ = client
    response = test_client.post("/api/chat/enhanced", json={"message": "test question"})
    assert response.status_code == 200
    data = response.json()
    assert data["pipeline_type"] == "enhanced"
    assert "not yet configured" in data["message"]


def test_serve_index(client):
    """GET / serves the comparison UI HTML."""
    test_client, _ = client
    response = test_client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Knowledge Base Enrichment" in response.text


def test_static_css(client):
    """GET /static/style.css serves the stylesheet."""
    test_client, _ = client
    response = test_client.get("/static/style.css")
    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]


def test_static_js(client):
    """GET /static/app.js serves the JavaScript."""
    test_client, _ = client
    response = test_client.get("/static/app.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]


def test_chat_baseline_with_service():
    """POST /api/chat/baseline uses ChatService when configured."""
    with (
        patch("enrichment.server.StorageService"),
        patch("enrichment.server.SearchService"),
        patch("enrichment.server.EmbeddingService"),
        patch("enrichment.server.ChatService") as mock_chat_cls,
        patch("enrichment.server.get_settings") as mock_settings,
    ):
        settings = MagicMock()
        settings.azure_openai_endpoint = "https://test.openai.azure.com"
        settings.azure_openai_key = "test-key"
        settings.search_endpoint = "https://test.search.windows.net"
        settings.search_api_key = "test-key"
        settings.embedding_deployment = "text-embedding-3-small"
        settings.chat_deployment = "gpt-4o"
        settings.search_index_baseline = "baseline-index"
        settings.search_index_enhanced = "enhanced-index"
        settings.azure_storage_connection_string = "UseDevelopmentStorage=true"
        settings.storage_account_url = ""
        settings.storage_container_corpus = "corpus"
        settings.storage_container_results = "cu-results"
        settings.environment = "test"
        mock_settings.return_value = settings

        mock_chat = mock_chat_cls.return_value
        mock_chat.chat_baseline.return_value = {
            "message": "Test answer",
            "citations": [
                {"document_id": "d1", "chunk_id": "c1", "score": 1.0, "snippet": "..."}
            ],
        }

        app = create_app()
        test_client = TestClient(app)

        response = test_client.post(
            "/api/chat/baseline", json={"message": "What about cybersecurity?"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Test answer"
        assert len(data["citations"]) == 1


def test_chat_baseline_error_handling():
    """POST /api/chat/baseline returns error message when service throws."""
    with (
        patch("enrichment.server.StorageService"),
        patch("enrichment.server.SearchService"),
        patch("enrichment.server.EmbeddingService"),
        patch("enrichment.server.ChatService") as mock_chat_cls,
        patch("enrichment.server.get_settings") as mock_settings,
    ):
        settings = MagicMock()
        settings.azure_openai_endpoint = "https://test.openai.azure.com"
        settings.azure_openai_key = "test-key"
        settings.search_endpoint = "https://test.search.windows.net"
        settings.search_api_key = "test-key"
        settings.embedding_deployment = "text-embedding-3-small"
        settings.chat_deployment = "gpt-4o"
        settings.search_index_baseline = "baseline-index"
        settings.search_index_enhanced = "enhanced-index"
        settings.azure_storage_connection_string = "UseDevelopmentStorage=true"
        settings.storage_account_url = ""
        settings.storage_container_corpus = "corpus"
        settings.storage_container_results = "cu-results"
        settings.environment = "test"
        mock_settings.return_value = settings

        mock_chat = mock_chat_cls.return_value
        mock_chat.chat_baseline.side_effect = RuntimeError("Search index not found")

        app = create_app()
        test_client = TestClient(app)

        response = test_client.post("/api/chat/baseline", json={"message": "test"})
        assert response.status_code == 200
        data = response.json()
        assert "error occurred" in data["message"]
        assert data["pipeline_type"] == "baseline"


def test_pipeline_run_unconfigured(client):
    """POST /api/pipeline/run returns error when services not configured."""
    test_client, _ = client
    response = test_client.post("/api/pipeline/run", json={"pipeline_type": "baseline"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "not configured" in data["message"]
