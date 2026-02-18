"""Tests for the enhanced pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ifwebuildit.pipeline.enhanced import EnhancedPipeline, _extract_fields


@pytest.fixture
def pipeline():
    """Create an EnhancedPipeline with mocked services."""
    return EnhancedPipeline(
        storage=MagicMock(),
        cu=MagicMock(),
        embedding=MagicMock(),
        search=MagicMock(),
        index_name="test-enhanced",
        analyzer_id="test-analyzer",
    )


def test_ensure_index(pipeline):
    """ensure_index creates the enhanced search index."""
    pipeline.ensure_index()
    pipeline.search.create_enhanced_index.assert_called_once_with("test-enhanced")


def test_ensure_analyzer_exists(pipeline):
    """ensure_analyzer skips creation if analyzer exists."""
    pipeline.cu.get_analyzer.return_value = {"analyzerId": "test-analyzer"}
    pipeline.ensure_analyzer()
    pipeline.cu.get_analyzer.assert_called_once_with("test-analyzer")
    pipeline.cu.create_analyzer.assert_not_called()


def test_ensure_analyzer_creates(pipeline):
    """ensure_analyzer creates the analyzer if it doesn't exist."""
    pipeline.cu.get_analyzer.side_effect = Exception("Not found")
    pipeline.ensure_analyzer()
    pipeline.cu.create_analyzer.assert_called_once_with("test-analyzer")


def test_process_document(pipeline):
    """process_document runs the full enhanced pipeline."""
    mock_result = MagicMock()
    pipeline.cu.analyze_document.return_value = mock_result
    pipeline.cu.result_to_dict.return_value = {
        "contents": [
            {
                "markdown": ("This is the extracted document content. " * 50),
                "fields": {
                    "reportTitle": {"value": "Test Report"},
                    "reportNumber": {"value": "GAO-24-999999"},
                    "topicCategory": {"value": "Cybersecurity"},
                    "executiveSummary": {"value": "A summary."},
                    "agencies": {"value": ["DOD", "DHS"]},
                },
            }
        ]
    }

    pipeline.embedding.embed.return_value = [[0.1] * 1536]
    pipeline.search.index_enhanced_chunks.return_value = [
        {"key": "doc-0000", "succeeded": True}
    ]

    result = pipeline.process_document(
        document_url="https://example.com/doc.pdf",
        document_id="doc1",
        chunk_size=100,
    )

    assert result["document_id"] == "doc1"
    assert result["chunks"] >= 1
    assert result["indexed"] == 1
    assert result["metadata"]["reportTitle"] == "Test Report"
    assert result["metadata"]["topicCategory"] == "Cybersecurity"
    pipeline.cu.analyze_document.assert_called_once()
    pipeline.search.index_enhanced_chunks.assert_called_once()


def test_process_document_empty_text(pipeline):
    """process_document handles empty extraction."""
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


def test_extract_fields():
    """_extract_fields extracts CU field values correctly."""
    result_dict = {
        "contents": [
            {
                "fields": {
                    "reportTitle": {"value": "My Report", "confidence": 0.95},
                    "agencies": {"value": ["DOD", "DHS"]},
                }
            }
        ]
    }
    fields = _extract_fields(result_dict)
    assert fields["reportTitle"] == "My Report"
    assert fields["agencies"] == ["DOD", "DHS"]


def test_extract_fields_empty():
    """_extract_fields handles empty contents."""
    assert _extract_fields({"contents": []}) == {}
    assert _extract_fields({}) == {}


def test_process_document_uses_custom_analyzer(pipeline):
    """process_document uses the custom analyzer ID."""
    mock_result = MagicMock()
    pipeline.cu.analyze_document.return_value = mock_result
    pipeline.cu.result_to_dict.return_value = {
        "contents": [{"markdown": "Some text.", "fields": {}}]
    }
    pipeline.embedding.embed.return_value = [[0.1]]
    pipeline.search.index_enhanced_chunks.return_value = [
        {"key": "doc-0000", "succeeded": True}
    ]

    pipeline.process_document("https://example.com/doc.pdf", "doc")

    call_kwargs = pipeline.cu.analyze_document.call_args[1]
    assert call_kwargs["analyzer_id"] == "test-analyzer"
