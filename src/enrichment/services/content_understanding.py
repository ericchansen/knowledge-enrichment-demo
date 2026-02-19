"""Azure AI Content Understanding service for document analysis."""

from __future__ import annotations

import json
import logging
from typing import Any

from azure.ai.contentunderstanding import ContentUnderstandingClient
from azure.ai.contentunderstanding.models import AnalyzeInput, AnalyzeResult
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

# Custom analyzer schema for GAO reports
GAO_ANALYZER_SCHEMA: dict[str, Any] = {
    "description": "GAO Report Analyzer — extracts structured fields for RAG enrichment",
    "baseAnalyzerId": "prebuilt-document",
    "models": {
        "completion": "gpt-4.1",
        "embedding": "text-embedding-3-large",
    },
    "fieldSchema": {
        "fields": {
            "reportTitle": {"type": "string", "method": "extract"},
            "reportNumber": {
                "type": "string",
                "method": "extract",
                "description": "GAO report number, e.g. GAO-24-106583",
            },
            "publicationDate": {"type": "date", "method": "extract"},
            "agencies": {
                "type": "array",
                "items": {"type": "string"},
                "method": "extract",
                "description": "Federal agencies mentioned or audited",
            },
            "keyFindings": {
                "type": "array",
                "items": {"type": "string"},
                "method": "generate",
                "description": "Top 3-5 key findings from the report",
            },
            "recommendations": {
                "type": "array",
                "items": {"type": "string"},
                "method": "generate",
                "description": "Actionable recommendations made by GAO",
            },
            "topicCategory": {
                "type": "string",
                "method": "classify",
                "enum": [
                    "Cybersecurity",
                    "Defense",
                    "Healthcare",
                    "Finance",
                    "Technology",
                    "Environment",
                    "Government Operations",
                    "Other",
                ],
            },
            "executiveSummary": {
                "type": "string",
                "method": "generate",
                "description": "2-3 sentence summary of the entire report",
            },
        },
    },
}


class ContentUnderstandingService:
    """Manages Content Understanding analyzers and document analysis."""

    def __init__(
        self,
        endpoint: str,
        api_key: str | None = None,
    ) -> None:
        if api_key:
            credential = AzureKeyCredential(api_key)
        else:
            credential = DefaultAzureCredential()  # type: ignore[assignment]
        self._client = ContentUnderstandingClient(
            endpoint=endpoint,
            credential=credential,
        )

    def create_analyzer(
        self,
        analyzer_id: str,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a custom analyzer with the given schema.

        If no schema is provided, uses the GAO report analyzer schema.
        Returns the analyzer definition.
        """
        body = schema or GAO_ANALYZER_SCHEMA
        poller = self._client.begin_create_analyzer(analyzer_id, resource=body)
        result = poller.result()
        logger.info("Created analyzer: %s", analyzer_id)
        return dict(result) if result else {"analyzerId": analyzer_id}

    def get_analyzer(self, analyzer_id: str) -> dict[str, Any]:
        """Get an analyzer definition."""
        result = self._client.get_analyzer(analyzer_id)
        return dict(result)

    def list_analyzers(self) -> list[dict[str, Any]]:
        """List all analyzers."""
        return [dict(a) for a in self._client.list_analyzers()]

    def delete_analyzer(self, analyzer_id: str) -> None:
        """Delete an analyzer."""
        self._client.delete_analyzer(analyzer_id)
        logger.info("Deleted analyzer: %s", analyzer_id)

    def analyze_document(
        self,
        analyzer_id: str,
        document_url: str,
    ) -> AnalyzeResult:
        """Analyze a document using the specified analyzer.

        Args:
            analyzer_id: The analyzer to use (e.g. 'prebuilt-documentSearch' or a custom one).
            document_url: Public URL of the document to analyze.

        Returns:
            The analysis result containing extracted content and fields.
        """
        poller = self._client.begin_analyze(
            analyzer_id=analyzer_id,
            inputs=[AnalyzeInput(url=document_url)],
        )
        result = poller.result()
        logger.info("Analyzed document with %s: %s", analyzer_id, document_url)
        return result

    def analyze_document_baseline(self, document_url: str) -> AnalyzeResult:
        """Analyze a document using the prebuilt RAG analyzer (baseline pipeline)."""
        return self.analyze_document("prebuilt-documentSearch", document_url)

    def analyze_document_enhanced(
        self,
        document_url: str,
        analyzer_id: str = "gaoReportAnalyzer",
    ) -> AnalyzeResult:
        """Analyze a document using the custom GAO analyzer (enhanced pipeline)."""
        return self.analyze_document(analyzer_id, document_url)

    @staticmethod
    def result_to_dict(result: AnalyzeResult) -> dict[str, Any]:
        """Convert an AnalyzeResult to a serializable dictionary."""
        contents = []
        for content in result.contents:
            entry: dict[str, Any] = {
                "markdown": content.markdown,
                "kind": str(content.kind) if content.kind else None,
            }
            if hasattr(content, "fields") and content.fields:
                entry["fields"] = {}
                for k, v in content.fields.items():
                    if v is None:
                        continue
                    val = v.value
                    # Recursively convert SDK types to plain Python
                    if isinstance(val, list):
                        val = [
                            item.value if hasattr(item, "value") else item
                            for item in val
                        ]
                    elif hasattr(val, "value"):
                        val = val.value
                    entry["fields"][k] = {
                        "value": val,
                        "confidence": v.confidence,
                    }
            contents.append(entry)
        return {
            "analyzerId": result.analyzer_id,
            "contents": contents,
        }

    @staticmethod
    def result_to_json(result: AnalyzeResult) -> str:
        """Convert an AnalyzeResult to a JSON string."""
        return json.dumps(ContentUnderstandingService.result_to_dict(result), indent=2)
