"""Tests for data models."""

from enrichment.models import (
    AnalysisComparison,
    ChatRequest,
    ChatResponse,
    CorpusInfo,
    Document,
    DocumentStatus,
    HealthResponse,
    PipelineRequest,
    PipelineStatus,
    PipelineType,
)


def test_pipeline_type_values():
    """PipelineType should have baseline and enhanced."""
    assert PipelineType.BASELINE == "baseline"
    assert PipelineType.ENHANCED == "enhanced"


def test_document_status_values():
    """DocumentStatus should have all expected statuses."""
    assert DocumentStatus.UPLOADED == "uploaded"
    assert DocumentStatus.BASELINE_COMPLETE == "baseline_complete"
    assert DocumentStatus.ENHANCED_COMPLETE == "enhanced_complete"
    assert DocumentStatus.FAILED == "failed"


def test_document_defaults():
    """Document should have sensible defaults."""
    doc = Document(filename="test.pdf")
    assert doc.filename == "test.pdf"
    assert doc.status == DocumentStatus.UPLOADED
    assert doc.blob_url == ""
    assert doc.baseline_result is None
    assert doc.enhanced_result is None


def test_corpus_info_defaults():
    """CorpusInfo should default to empty."""
    info = CorpusInfo()
    assert info.total_documents == 0
    assert info.baseline_indexed == 0
    assert info.enhanced_indexed == 0
    assert info.documents == []


def test_corpus_info_with_documents():
    """CorpusInfo should hold documents."""
    docs = [Document(filename="a.pdf"), Document(filename="b.pdf")]
    info = CorpusInfo(total_documents=2, documents=docs)
    assert info.total_documents == 2
    assert len(info.documents) == 2


def test_analysis_comparison():
    """AnalysisComparison should hold both pipelines' results."""
    comp = AnalysisComparison(
        filename="test.pdf",
        baseline_markdown="# Basic",
        enhanced_markdown="# Enriched",
        enhanced_fields={"reportTitle": "Test Report"},
    )
    assert comp.filename == "test.pdf"
    assert comp.enhanced_fields["reportTitle"] == "Test Report"


def test_chat_request_defaults():
    """ChatRequest should default to baseline pipeline."""
    req = ChatRequest(message="What is cybersecurity?")
    assert req.pipeline_type == PipelineType.BASELINE


def test_chat_response():
    """ChatResponse should serialize properly."""
    resp = ChatResponse(
        message="Here are the findings...",
        pipeline_type=PipelineType.ENHANCED,
        citations=[{"page": 14, "source": "GAO-24-106583"}],
    )
    assert resp.pipeline_type == PipelineType.ENHANCED
    assert len(resp.citations) == 1


def test_health_response():
    """HealthResponse should have expected defaults."""
    health = HealthResponse()
    assert health.status == "ok"
    assert health.version == "0.1.0"


def test_pipeline_request_defaults():
    """PipelineRequest should default to baseline."""
    req = PipelineRequest()
    assert req.pipeline_type == PipelineType.BASELINE


def test_pipeline_status():
    """PipelineStatus should hold run results."""
    status = PipelineStatus(
        pipeline_type=PipelineType.ENHANCED,
        status="complete",
        documents_processed=5,
        documents_total=5,
        message="Done",
    )
    assert status.status == "complete"
    assert status.documents_processed == 5
