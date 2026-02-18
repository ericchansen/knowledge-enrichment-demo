"""Tests for the chat service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ifwebuildit.services.chat import (
    SYSTEM_PROMPT_BASELINE,
    SYSTEM_PROMPT_ENHANCED,
    ChatService,
)


@pytest.fixture
def chat_service():
    """Create a ChatService with mocked dependencies."""
    search = MagicMock()
    embedding = MagicMock()

    with patch("ifwebuildit.services.chat.AzureOpenAI") as mock_openai_cls:
        mock_openai = MagicMock()
        mock_openai_cls.return_value = mock_openai

        svc = ChatService(
            search=search,
            embedding=embedding,
            endpoint="https://test.openai.azure.com",
            credential="test-key",
            chat_deployment="gpt-4o",
        )
        svc._mock_openai = mock_openai
        return svc


def test_chat_with_results(chat_service):
    """chat returns an answer with citations when results found."""
    chat_service.embedding.embed_single.return_value = [0.1] * 1536
    chat_service.search.search.return_value = [
        {
            "id": "doc1-0000",
            "content": "Federal cybersecurity challenges...",
            "document_id": "doc1",
            "score": 1.5,
        }
    ]

    mock_choice = MagicMock()
    mock_choice.message.content = "The report discusses cybersecurity challenges."
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    chat_service._mock_openai.chat.completions.create.return_value = mock_response

    result = chat_service.chat("What are the main challenges?", "test-index")

    assert "cybersecurity challenges" in result["message"]
    assert len(result["citations"]) == 1
    assert result["citations"][0]["document_id"] == "doc1"


def test_chat_no_results(chat_service):
    """chat returns a fallback when no search results."""
    chat_service.embedding.embed_single.return_value = [0.1] * 1536
    chat_service.search.search.return_value = []

    result = chat_service.chat("Something irrelevant?", "test-index")

    assert "couldn't find" in result["message"]
    assert result["citations"] == []
    chat_service._mock_openai.chat.completions.create.assert_not_called()


def test_chat_baseline_uses_baseline_prompt(chat_service):
    """chat_baseline uses the baseline system prompt."""
    chat_service.embedding.embed_single.return_value = [0.1] * 1536
    chat_service.search.search.return_value = [
        {"id": "c1", "content": "text", "document_id": "d1", "score": 1.0}
    ]
    mock_choice = MagicMock()
    mock_choice.message.content = "Answer"
    chat_service._mock_openai.chat.completions.create.return_value = MagicMock(
        choices=[mock_choice]
    )

    chat_service.chat_baseline("question", "baseline-index")

    call_args = chat_service._mock_openai.chat.completions.create.call_args
    messages = call_args[1]["messages"]
    assert messages[0]["content"] == SYSTEM_PROMPT_BASELINE


def test_chat_enhanced_uses_enhanced_prompt(chat_service):
    """chat_enhanced uses the enhanced system prompt."""
    chat_service.embedding.embed_single.return_value = [0.1] * 1536
    chat_service.search.search.return_value = [
        {"id": "c1", "content": "text", "document_id": "d1", "score": 1.0}
    ]
    mock_choice = MagicMock()
    mock_choice.message.content = "Answer"
    chat_service._mock_openai.chat.completions.create.return_value = MagicMock(
        choices=[mock_choice]
    )

    chat_service.chat_enhanced("question", "enhanced-index")

    call_args = chat_service._mock_openai.chat.completions.create.call_args
    messages = call_args[1]["messages"]
    assert messages[0]["content"] == SYSTEM_PROMPT_ENHANCED


def test_chat_embeds_query(chat_service):
    """chat embeds the user's query for vector search."""
    chat_service.embedding.embed_single.return_value = [0.1] * 1536
    chat_service.search.search.return_value = []

    chat_service.chat("test query", "index")

    chat_service.embedding.embed_single.assert_called_once_with("test query")


def test_chat_passes_vector_to_search(chat_service):
    """chat passes the query vector to search."""
    vector = [0.5] * 1536
    chat_service.embedding.embed_single.return_value = vector
    chat_service.search.search.return_value = []

    chat_service.chat("test", "index")

    call_kwargs = chat_service.search.search.call_args[1]
    assert call_kwargs["vector"] == vector


def test_chat_enhanced_includes_metadata_in_context(chat_service):
    """Enhanced chat includes report metadata in LLM context."""
    chat_service.embedding.embed_single.return_value = [0.1] * 1536
    chat_service.search.search.return_value = [
        {
            "id": "c1",
            "content": "text about cyber threats",
            "document_id": "d1",
            "score": 1.0,
            "report_title": "Federal Cybersecurity Report",
            "report_number": "GAO-24-106583",
            "topic_category": "Cybersecurity",
            "agencies": ["DHS", "DOD"],
            "executive_summary": "A review of federal cyber posture.",
        }
    ]
    mock_choice = MagicMock()
    mock_choice.message.content = "Answer"
    chat_service._mock_openai.chat.completions.create.return_value = MagicMock(
        choices=[mock_choice]
    )

    result = chat_service.chat_enhanced("question", "enhanced-index")

    # Verify metadata appears in LLM context
    call_args = chat_service._mock_openai.chat.completions.create.call_args
    user_msg = call_args[1]["messages"][1]["content"]
    assert "Federal Cybersecurity Report" in user_msg
    assert "GAO-24-106583" in user_msg
    assert "DHS" in user_msg
    assert "A review of federal cyber posture" in user_msg

    # Verify citations include metadata
    assert result["citations"][0]["report_title"] == "Federal Cybersecurity Report"
    assert result["citations"][0]["report_number"] == "GAO-24-106583"
