"""Tests for the baseline pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ifwebuildit.pipeline.baseline import BaselinePipeline


@pytest.fixture
def pipeline():
    """Create a BaselinePipeline with all mocked services."""
    storage = MagicMock()
    cu = MagicMock()
    embedding = MagicMock()
    search = MagicMock()

    p = BaselinePipeline(
        storage=storage,
        cu=cu,
        embedding=embedding,
        search=search,
        index_name="test-baseline",
    )
    return p


def test_ensure_index(pipeline):
    """ensure_index creates the search index."""
    pipeline.ensure_index()
    pipeline.search.create_baseline_index.assert_called_once_with("test-baseline")


def test_process_document(pipeline):
    """process_document runs the full pipeline."""
    # Mock CU extraction
    mock_result = MagicMock()
    pipeline.cu.analyze_document.return_value = mock_result
    pipeline.cu.result_to_dict.return_value = {
        "contents": [{"markdown": "This is extracted text from the document. " * 20}],
    }

    # Mock embeddings
    pipeline.embedding.embed.return_value = [[0.1] * 1536]

    # Mock indexing
    pipeline.search.index_chunks.return_value = [{"key": "doc-0000", "succeeded": True}]

    result = pipeline.process_document(
        document_url="https://example.com/doc.pdf",
        document_id="doc1",
        chunk_size=100,
        chunk_overlap=20,
    )

    assert result["document_id"] == "doc1"
    assert result["chunks"] >= 1
    assert result["indexed"] == 1
    pipeline.cu.analyze_document.assert_called_once()
    pipeline.embedding.embed.assert_called_once()
    pipeline.search.index_chunks.assert_called_once()


def test_process_document_empty_text(pipeline):
    """process_document handles empty extraction gracefully."""
    mock_result = MagicMock()
    pipeline.cu.analyze_document.return_value = mock_result
    pipeline.cu.result_to_dict.return_value = {"contents": [{"markdown": ""}]}

    result = pipeline.process_document(
        document_url="https://example.com/empty.pdf",
        document_id="empty",
    )

    assert result["chunks"] == 0
    assert result["indexed"] == 0
    pipeline.embedding.embed.assert_not_called()
    pipeline.search.index_chunks.assert_not_called()


def test_process_document_default_analyzer(pipeline):
    """process_document uses prebuilt-documentSearch as baseline analyzer."""
    mock_result = MagicMock()
    pipeline.cu.analyze_document.return_value = mock_result
    pipeline.cu.result_to_dict.return_value = {"contents": [{"markdown": "Some text."}]}
    pipeline.embedding.embed.return_value = [[0.1]]
    pipeline.search.index_chunks.return_value = [{"key": "doc-0000", "succeeded": True}]

    pipeline.process_document(
        document_url="https://example.com/doc.pdf",
        document_id="doc",
    )

    call_kwargs = pipeline.cu.analyze_document.call_args[1]
    assert call_kwargs["analyzer_id"] == "prebuilt-documentSearch"
