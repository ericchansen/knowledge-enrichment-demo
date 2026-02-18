"""Tests for Content Understanding service."""

from unittest.mock import MagicMock, patch

from ifwebuildit.services.content_understanding import (
    GAO_ANALYZER_SCHEMA,
    ContentUnderstandingService,
)


@patch("ifwebuildit.services.content_understanding.ContentUnderstandingClient")
@patch("ifwebuildit.services.content_understanding.DefaultAzureCredential")
def test_init_with_default_credential(mock_cred_class, mock_client_class):
    """Should use DefaultAzureCredential when no API key is provided."""
    ContentUnderstandingService(endpoint="https://test.services.ai.azure.com/")
    mock_cred_class.assert_called_once()
    mock_client_class.assert_called_once()


@patch("ifwebuildit.services.content_understanding.ContentUnderstandingClient")
@patch("ifwebuildit.services.content_understanding.AzureKeyCredential")
def test_init_with_api_key(mock_key_class, mock_client_class):
    """Should use AzureKeyCredential when API key is provided."""
    ContentUnderstandingService(
        endpoint="https://test.services.ai.azure.com/",
        api_key="test-key",
    )
    mock_key_class.assert_called_once_with("test-key")
    mock_client_class.assert_called_once()


@patch("ifwebuildit.services.content_understanding.ContentUnderstandingClient")
@patch("ifwebuildit.services.content_understanding.DefaultAzureCredential")
def test_create_analyzer_uses_gao_schema_by_default(mock_cred, mock_client_class):
    """create_analyzer should use the GAO schema when none is provided."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_poller = MagicMock()
    mock_poller.result.return_value = {"analyzerId": "test-analyzer"}
    mock_client.begin_create_analyzer.return_value = mock_poller

    svc = ContentUnderstandingService(endpoint="https://test.services.ai.azure.com/")
    result = svc.create_analyzer("test-analyzer")

    mock_client.begin_create_analyzer.assert_called_once_with(
        "test-analyzer", body=GAO_ANALYZER_SCHEMA
    )
    assert result == {"analyzerId": "test-analyzer"}


@patch("ifwebuildit.services.content_understanding.ContentUnderstandingClient")
@patch("ifwebuildit.services.content_understanding.DefaultAzureCredential")
def test_analyze_document(mock_cred, mock_client_class):
    """analyze_document should call begin_analyze with the correct inputs."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_poller = MagicMock()
    mock_result = MagicMock()
    mock_poller.result.return_value = mock_result
    mock_client.begin_analyze.return_value = mock_poller

    svc = ContentUnderstandingService(endpoint="https://test.services.ai.azure.com/")
    result = svc.analyze_document("prebuilt-documentSearch", "https://storage/test.pdf")

    assert result == mock_result
    call_args = mock_client.begin_analyze.call_args
    assert call_args.kwargs["analyzer_id"] == "prebuilt-documentSearch"
    inputs = call_args.kwargs["inputs"]
    assert len(inputs) == 1
    assert inputs[0].url == "https://storage/test.pdf"


@patch("ifwebuildit.services.content_understanding.ContentUnderstandingClient")
@patch("ifwebuildit.services.content_understanding.DefaultAzureCredential")
def test_analyze_document_baseline(mock_cred, mock_client_class):
    """analyze_document_baseline should use prebuilt-documentSearch."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_poller = MagicMock()
    mock_client.begin_analyze.return_value = mock_poller

    svc = ContentUnderstandingService(endpoint="https://test.services.ai.azure.com/")
    svc.analyze_document_baseline("https://storage/test.pdf")

    call_args = mock_client.begin_analyze.call_args
    assert call_args.kwargs["analyzer_id"] == "prebuilt-documentSearch"


@patch("ifwebuildit.services.content_understanding.ContentUnderstandingClient")
@patch("ifwebuildit.services.content_understanding.DefaultAzureCredential")
def test_analyze_document_enhanced(mock_cred, mock_client_class):
    """analyze_document_enhanced should use the custom GAO analyzer."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_poller = MagicMock()
    mock_client.begin_analyze.return_value = mock_poller

    svc = ContentUnderstandingService(endpoint="https://test.services.ai.azure.com/")
    svc.analyze_document_enhanced("https://storage/test.pdf")

    call_args = mock_client.begin_analyze.call_args
    assert call_args.kwargs["analyzer_id"] == "gao-report-analyzer"


@patch("ifwebuildit.services.content_understanding.ContentUnderstandingClient")
@patch("ifwebuildit.services.content_understanding.DefaultAzureCredential")
def test_list_analyzers(mock_cred, mock_client_class):
    """list_analyzers should return a list of dicts."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.list_analyzers.return_value = [
        {"analyzerId": "a1"},
        {"analyzerId": "a2"},
    ]

    svc = ContentUnderstandingService(endpoint="https://test.services.ai.azure.com/")
    result = svc.list_analyzers()

    assert len(result) == 2


def test_gao_schema_has_expected_fields():
    """GAO analyzer schema should define the expected fields."""
    fields = GAO_ANALYZER_SCHEMA["fieldSchema"]["fields"]
    expected = {
        "reportTitle",
        "reportNumber",
        "publicationDate",
        "agencies",
        "keyFindings",
        "recommendations",
        "topicCategory",
        "executiveSummary",
    }
    assert set(fields.keys()) == expected


def test_gao_schema_topic_categories():
    """Topic category field should have the expected enum values."""
    fields = GAO_ANALYZER_SCHEMA["fieldSchema"]["fields"]
    categories = fields["topicCategory"]["enum"]
    assert "Cybersecurity" in categories
    assert "Defense" in categories
    assert len(categories) == 8
