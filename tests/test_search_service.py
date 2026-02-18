"""Tests for the search service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from enrichment.services.chunking import Chunk
from enrichment.services.search import (
    BASELINE_INDEX_FIELDS,
    ENHANCED_INDEX_FIELDS,
    SearchService,
)


@pytest.fixture
def search_service():
    """Create a SearchService with a mock credential."""
    with patch("enrichment.services.search.SearchIndexClient") as mock_index_client_cls:
        mock_index_client = MagicMock()
        mock_index_client_cls.return_value = mock_index_client
        svc = SearchService(
            endpoint="https://test.search.windows.net",
            credential="test-api-key",
        )
        svc._mock_index_client = mock_index_client
        return svc


def test_init_creates_index_client(search_service):
    """SearchService initializes an index client."""
    assert search_service._index_client is not None


def test_create_baseline_index(search_service):
    """create_baseline_index calls create_or_update_index."""
    search_service.create_baseline_index("test-index")
    search_service._mock_index_client.create_or_update_index.assert_called_once()
    call_args = search_service._mock_index_client.create_or_update_index.call_args
    index = call_args[0][0]
    assert index.name == "test-index"


def test_baseline_index_fields():
    """Baseline index has the expected fields."""
    field_names = [f.name for f in BASELINE_INDEX_FIELDS]
    assert "id" in field_names
    assert "content" in field_names
    assert "document_id" in field_names
    assert "chunk_index" in field_names
    assert "content_vector" in field_names


def test_index_chunks(search_service):
    """index_chunks uploads documents to the search index."""
    with patch("enrichment.services.search.SearchClient") as mock_search_cls:
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.key = "doc-0000"
        mock_result.succeeded = True
        mock_client.upload_documents.return_value = [mock_result]
        mock_search_cls.return_value = mock_client

        chunks = [
            Chunk(
                id="doc-0000",
                content="test content",
                document_id="doc",
                chunk_index=0,
            )
        ]
        embeddings = [[0.1, 0.2, 0.3]]

        results = search_service.index_chunks("test-index", chunks, embeddings)
        assert len(results) == 1
        assert results[0]["key"] == "doc-0000"
        assert results[0]["succeeded"] is True


def test_search_keyword_only(search_service):
    """search works with keyword-only query."""
    with patch("enrichment.services.search.SearchClient") as mock_search_cls:
        mock_client = MagicMock()
        mock_result = {
            "id": "doc-0000",
            "content": "test",
            "document_id": "doc",
            "@search.score": 1.5,
        }
        mock_client.search.return_value = [mock_result]
        mock_search_cls.return_value = mock_client

        results = search_service.search("test-index", query="cybersecurity")
        assert len(results) == 1
        assert results[0]["content"] == "test"


def test_search_returns_metadata(search_service):
    """search includes metadata fields when present."""
    with patch("enrichment.services.search.SearchClient") as mock_search_cls:
        mock_client = MagicMock()
        mock_result = {
            "id": "doc-0000",
            "content": "test",
            "document_id": "doc",
            "@search.score": 1.5,
            "report_title": "Test Report",
            "report_number": "GAO-24-999",
            "topic_category": "Cybersecurity",
            "agencies": ["DHS"],
            "executive_summary": "A summary.",
            "section_title": "",
        }
        mock_client.search.return_value = [mock_result]
        mock_search_cls.return_value = mock_client

        results = search_service.search("test-index", query="test")
        assert results[0]["report_title"] == "Test Report"
        assert results[0]["agencies"] == ["DHS"]
        # Empty fields should not be included
        assert "section_title" not in results[0]


def test_list_indexes(search_service):
    """list_indexes returns index names."""
    mock_idx = MagicMock()
    mock_idx.name = "my-index"
    search_service._mock_index_client.list_indexes.return_value = [mock_idx]

    names = search_service.list_indexes()
    assert names == ["my-index"]


def test_delete_index(search_service):
    """delete_index calls the index client."""
    search_service.delete_index("old-index")
    search_service._mock_index_client.delete_index.assert_called_once_with("old-index")


def test_enhanced_index_fields():
    """Enhanced index has CU metadata fields."""
    field_names = [f.name for f in ENHANCED_INDEX_FIELDS]
    assert "report_title" in field_names
    assert "report_number" in field_names
    assert "topic_category" in field_names
    assert "executive_summary" in field_names
    assert "agencies" in field_names
    assert "content_vector" in field_names


def test_create_enhanced_index(search_service):
    """create_enhanced_index creates index with enhanced fields."""
    search_service.create_enhanced_index("enhanced-test")
    search_service._mock_index_client.create_or_update_index.assert_called_once()
    index = search_service._mock_index_client.create_or_update_index.call_args[0][0]
    assert index.name == "enhanced-test"


def test_index_enhanced_chunks(search_service):
    """index_enhanced_chunks includes metadata in uploaded documents."""
    with patch("enrichment.services.search.SearchClient") as mock_search_cls:
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.key = "doc-0000"
        mock_result.succeeded = True
        mock_client.upload_documents.return_value = [mock_result]
        mock_search_cls.return_value = mock_client

        chunks = [
            Chunk(id="doc-0000", content="test", document_id="doc", chunk_index=0)
        ]
        embeddings = [[0.1, 0.2]]
        metadata = {
            "reportTitle": "Test Report",
            "reportNumber": "GAO-24-999",
            "topicCategory": "Cybersecurity",
            "agencies": ["DOD"],
        }

        results = search_service.index_enhanced_chunks(
            "enhanced-idx", chunks, embeddings, metadata
        )

        assert results[0]["succeeded"] is True
        uploaded = mock_client.upload_documents.call_args[0][0]
        assert uploaded[0]["report_title"] == "Test Report"
        assert uploaded[0]["report_number"] == "GAO-24-999"
        assert uploaded[0]["agencies"] == ["DOD"]
