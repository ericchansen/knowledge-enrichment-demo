"""Tests for Content Understanding service."""

from unittest.mock import MagicMock, patch

from enrichment.services.content_understanding import (
    GAO_ANALYZER_SCHEMA,
    ContentUnderstandingService,
)


@patch("enrichment.services.content_understanding.ContentUnderstandingClient")
@patch("enrichment.services.content_understanding.DefaultAzureCredential")
def test_init_with_default_credential(mock_cred_class, mock_client_class):
    """Should use DefaultAzureCredential when no API key is provided."""
    ContentUnderstandingService(endpoint="https://test.services.ai.azure.com/")
    mock_cred_class.assert_called_once()
    mock_client_class.assert_called_once()


@patch("enrichment.services.content_understanding.ContentUnderstandingClient")
@patch("enrichment.services.content_understanding.AzureKeyCredential")
def test_init_with_api_key(mock_key_class, mock_client_class):
    """Should use AzureKeyCredential when API key is provided."""
    ContentUnderstandingService(
        endpoint="https://test.services.ai.azure.com/",
        api_key="test-key",
    )
    mock_key_class.assert_called_once_with("test-key")
    mock_client_class.assert_called_once()


@patch("enrichment.services.content_understanding.ContentUnderstandingClient")
@patch("enrichment.services.content_understanding.DefaultAzureCredential")
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
        "test-analyzer", resource=GAO_ANALYZER_SCHEMA
    )
    assert result == {"analyzerId": "test-analyzer"}


@patch("enrichment.services.content_understanding.ContentUnderstandingClient")
@patch("enrichment.services.content_understanding.DefaultAzureCredential")
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


@patch("enrichment.services.content_understanding.ContentUnderstandingClient")
@patch("enrichment.services.content_understanding.DefaultAzureCredential")
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


@patch("enrichment.services.content_understanding.ContentUnderstandingClient")
@patch("enrichment.services.content_understanding.DefaultAzureCredential")
def test_analyze_document_enhanced(mock_cred, mock_client_class):
    """analyze_document_enhanced should use the custom GAO analyzer."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_poller = MagicMock()
    mock_client.begin_analyze.return_value = mock_poller

    svc = ContentUnderstandingService(endpoint="https://test.services.ai.azure.com/")
    svc.analyze_document_enhanced("https://storage/test.pdf")

    call_args = mock_client.begin_analyze.call_args
    assert call_args.kwargs["analyzer_id"] == "gaoReportAnalyzer"


@patch("enrichment.services.content_understanding.ContentUnderstandingClient")
@patch("enrichment.services.content_understanding.DefaultAzureCredential")
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


@patch("enrichment.services.content_understanding.ContentUnderstandingClient")
@patch("enrichment.services.content_understanding.DefaultAzureCredential")
def test_get_analyzer(mock_cred, mock_client_class):
    """get_analyzer should return an analyzer as a dict."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.get_analyzer.return_value = {
        "analyzerId": "test-analyzer",
        "description": "Test",
    }

    svc = ContentUnderstandingService(endpoint="https://test.services.ai.azure.com/")
    result = svc.get_analyzer("test-analyzer")

    mock_client.get_analyzer.assert_called_once_with("test-analyzer")
    assert result["analyzerId"] == "test-analyzer"


@patch("enrichment.services.content_understanding.ContentUnderstandingClient")
@patch("enrichment.services.content_understanding.DefaultAzureCredential")
def test_delete_analyzer(mock_cred, mock_client_class):
    """delete_analyzer should call delete on the client."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    svc = ContentUnderstandingService(endpoint="https://test.services.ai.azure.com/")
    svc.delete_analyzer("test-analyzer")

    mock_client.delete_analyzer.assert_called_once_with("test-analyzer")


@patch("enrichment.services.content_understanding.ContentUnderstandingClient")
@patch("enrichment.services.content_understanding.DefaultAzureCredential")
def test_create_analyzer_with_custom_schema(mock_cred, mock_client_class):
    """create_analyzer should use custom schema when provided."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_poller = MagicMock()
    mock_poller.result.return_value = {"analyzerId": "custom"}
    mock_client.begin_create_analyzer.return_value = mock_poller

    custom = {"description": "Custom", "fieldSchema": {"fields": {}}}
    svc = ContentUnderstandingService(endpoint="https://test.services.ai.azure.com/")
    result = svc.create_analyzer("custom", schema=custom)

    mock_client.begin_create_analyzer.assert_called_once_with("custom", resource=custom)
    assert result == {"analyzerId": "custom"}


@patch("enrichment.services.content_understanding.ContentUnderstandingClient")
@patch("enrichment.services.content_understanding.DefaultAzureCredential")
def test_create_analyzer_returns_fallback_on_none(mock_cred, mock_client_class):
    """create_analyzer should return fallback dict when poller returns None."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_poller = MagicMock()
    mock_poller.result.return_value = None
    mock_client.begin_create_analyzer.return_value = mock_poller

    svc = ContentUnderstandingService(endpoint="https://test.services.ai.azure.com/")
    result = svc.create_analyzer("fallback-test")

    assert result == {"analyzerId": "fallback-test"}


@patch("enrichment.services.content_understanding.ContentUnderstandingClient")
@patch("enrichment.services.content_understanding.DefaultAzureCredential")
def test_result_to_dict_with_fields(mock_cred, mock_client_class):
    """result_to_dict should extract fields correctly from AnalyzeResult."""
    mock_client_class.return_value = MagicMock()

    # Build a mock AnalyzeResult with fields
    mock_field = MagicMock()
    mock_field.value = "GAO Cybersecurity Report"
    mock_field.confidence = 0.95

    mock_array_item = MagicMock()
    mock_array_item.value = "DHS"
    mock_array_field = MagicMock()
    mock_array_field.value = [mock_array_item]
    mock_array_field.confidence = 0.88

    mock_null_field = None

    mock_content = MagicMock()
    mock_content.markdown = "# Report Content"
    mock_content.kind = "document"
    mock_content.fields = {
        "reportTitle": mock_field,
        "agencies": mock_array_field,
        "nullField": mock_null_field,
    }

    mock_result = MagicMock()
    mock_result.analyzer_id = "gaoReportAnalyzer"
    mock_result.contents = [mock_content]

    svc = ContentUnderstandingService(endpoint="https://test.services.ai.azure.com/")
    result_dict = svc.result_to_dict(mock_result)

    assert result_dict["analyzerId"] == "gaoReportAnalyzer"
    assert len(result_dict["contents"]) == 1
    content = result_dict["contents"][0]
    assert content["markdown"] == "# Report Content"
    assert content["fields"]["reportTitle"]["value"] == "GAO Cybersecurity Report"
    assert content["fields"]["reportTitle"]["confidence"] == 0.95
    assert content["fields"]["agencies"]["value"] == ["DHS"]
    assert "nullField" not in content["fields"]


@patch("enrichment.services.content_understanding.ContentUnderstandingClient")
@patch("enrichment.services.content_understanding.DefaultAzureCredential")
def test_result_to_dict_no_fields(mock_cred, mock_client_class):
    """result_to_dict should handle content without fields."""
    mock_client_class.return_value = MagicMock()

    mock_content = MagicMock()
    mock_content.markdown = "Plain text content"
    mock_content.kind = None
    mock_content.fields = None
    # Ensure hasattr check works properly
    del mock_content.fields

    mock_result = MagicMock()
    mock_result.analyzer_id = "prebuilt-documentSearch"
    mock_result.contents = [mock_content]

    result_dict = ContentUnderstandingService.result_to_dict(mock_result)

    assert result_dict["analyzerId"] == "prebuilt-documentSearch"
    content = result_dict["contents"][0]
    assert content["markdown"] == "Plain text content"
    assert "fields" not in content


@patch("enrichment.services.content_understanding.ContentUnderstandingClient")
@patch("enrichment.services.content_understanding.DefaultAzureCredential")
def test_result_to_dict_nested_value(mock_cred, mock_client_class):
    """result_to_dict should handle nested SDK objects with .value attribute."""
    mock_client_class.return_value = MagicMock()

    # Field whose .value itself has a .value (nested SDK type)
    inner = MagicMock()
    inner.value = "nested-value"
    mock_field = MagicMock()
    mock_field.value = inner
    mock_field.confidence = 0.7

    mock_content = MagicMock()
    mock_content.markdown = "Nested"
    mock_content.kind = "document"
    mock_content.fields = {"nestedField": mock_field}

    mock_result = MagicMock()
    mock_result.analyzer_id = "test"
    mock_result.contents = [mock_content]

    result_dict = ContentUnderstandingService.result_to_dict(mock_result)
    assert (
        result_dict["contents"][0]["fields"]["nestedField"]["value"] == "nested-value"
    )


@patch("enrichment.services.content_understanding.ContentUnderstandingClient")
@patch("enrichment.services.content_understanding.DefaultAzureCredential")
def test_result_to_json(mock_cred, mock_client_class):
    """result_to_json should return a valid JSON string."""
    mock_client_class.return_value = MagicMock()

    mock_content = MagicMock()
    mock_content.markdown = "JSON test"
    mock_content.kind = "document"
    mock_content.fields = None
    del mock_content.fields

    mock_result = MagicMock()
    mock_result.analyzer_id = "test"
    mock_result.contents = [mock_content]

    import json

    json_str = ContentUnderstandingService.result_to_json(mock_result)
    parsed = json.loads(json_str)

    assert parsed["analyzerId"] == "test"
    assert len(parsed["contents"]) == 1
