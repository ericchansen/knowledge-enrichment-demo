"""Tests for the embedding service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ifwebuildit.services.embedding import EmbeddingService


@pytest.fixture
def embedding_service():
    """Create an EmbeddingService with a mocked OpenAI client."""
    with patch("ifwebuildit.services.embedding.AzureOpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        svc = EmbeddingService(
            endpoint="https://test.openai.azure.com",
            credential="test-key",
            deployment="text-embedding-3-small",
        )
        svc._mock_client = mock_client
        return svc


def test_embed_empty_list(embedding_service):
    """embed([]) returns empty list without API call."""
    result = embedding_service.embed([])
    assert result == []
    embedding_service._mock_client.embeddings.create.assert_not_called()


def test_embed_single_text(embedding_service):
    """embed_single returns a single embedding vector."""
    mock_item = MagicMock()
    mock_item.embedding = [0.1, 0.2, 0.3]
    mock_response = MagicMock()
    mock_response.data = [mock_item]
    embedding_service._mock_client.embeddings.create.return_value = mock_response

    result = embedding_service.embed_single("test text")
    assert result == [0.1, 0.2, 0.3]


def test_embed_batch(embedding_service):
    """embed processes multiple texts."""
    mock_items = [MagicMock(embedding=[float(i)]) for i in range(3)]
    mock_response = MagicMock()
    mock_response.data = mock_items
    embedding_service._mock_client.embeddings.create.return_value = mock_response

    result = embedding_service.embed(["a", "b", "c"])
    assert len(result) == 3
    assert result[0] == [0.0]


def test_embed_batching(embedding_service):
    """embed splits large lists into batches of 16."""
    texts = [f"text {i}" for i in range(20)]

    mock_items_16 = [MagicMock(embedding=[float(i)]) for i in range(16)]
    mock_items_4 = [MagicMock(embedding=[float(i)]) for i in range(4)]
    mock_resp_16 = MagicMock(data=mock_items_16)
    mock_resp_4 = MagicMock(data=mock_items_4)
    embedding_service._mock_client.embeddings.create.side_effect = [
        mock_resp_16,
        mock_resp_4,
    ]

    result = embedding_service.embed(texts)
    assert len(result) == 20
    assert embedding_service._mock_client.embeddings.create.call_count == 2


def test_init_with_api_key():
    """EmbeddingService initializes with API key."""
    with patch("ifwebuildit.services.embedding.AzureOpenAI") as mock_cls:
        EmbeddingService(
            endpoint="https://test.openai.azure.com",
            credential="test-key",
        )
        mock_cls.assert_called_once()
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["api_key"] == "test-key"
        assert "azure_endpoint" in call_kwargs
