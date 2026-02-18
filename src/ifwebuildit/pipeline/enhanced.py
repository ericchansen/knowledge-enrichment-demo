"""CU-enhanced RAG pipeline — ingest, CU-analyze, chunk, embed, index with metadata."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ifwebuildit.services.chunking import chunk_text

if TYPE_CHECKING:
    from ifwebuildit.services.content_understanding import (
        ContentUnderstandingService,
    )
    from ifwebuildit.services.embedding import EmbeddingService
    from ifwebuildit.services.search import SearchService
    from ifwebuildit.services.storage import StorageService

logger = logging.getLogger(__name__)


def _extract_fields(cu_result_dict: dict[str, Any]) -> dict[str, Any]:
    """Extract CU field values from the analysis result dict."""
    fields: dict[str, Any] = {}
    for content in cu_result_dict.get("contents", []):
        for name, field_data in content.get("fields", {}).items():
            if isinstance(field_data, dict):
                fields[name] = field_data.get("value", "")
            else:
                fields[name] = field_data
    return fields


class EnhancedPipeline:
    """Orchestrates the CU-enhanced RAG pipeline.

    Steps:
    1. Extract text AND structured metadata via CU custom analyzer
    2. Chunk the extracted text
    3. Generate embeddings
    4. Index chunks + embeddings + CU metadata in the enhanced AI Search index
    """

    def __init__(
        self,
        storage: StorageService,
        cu: ContentUnderstandingService,
        embedding: EmbeddingService,
        search: SearchService,
        index_name: str = "enhanced",
        analyzer_id: str = "gao-report-analyzer",
    ) -> None:
        self.storage = storage
        self.cu = cu
        self.embedding = embedding
        self.search = search
        self.index_name = index_name
        self.analyzer_id = analyzer_id

    def ensure_index(self) -> None:
        """Create the enhanced search index if it doesn't exist."""
        self.search.create_enhanced_index(self.index_name)
        logger.info("Ensured enhanced index '%s' exists", self.index_name)

    def ensure_analyzer(self) -> None:
        """Create the custom CU analyzer if it doesn't exist."""
        try:
            self.cu.get_analyzer(self.analyzer_id)
            logger.info("Analyzer '%s' already exists", self.analyzer_id)
        except Exception:
            logger.info("Creating analyzer '%s'", self.analyzer_id)
            self.cu.create_analyzer(self.analyzer_id)

    def process_document(
        self,
        document_url: str,
        document_id: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> dict[str, Any]:
        """Run the full enhanced pipeline for a single document.

        Returns:
            Summary dict with chunk count, index results, and extracted metadata
        """
        # Step 1: Extract text + structured fields via custom CU analyzer
        logger.info("CU-analyzing %s with %s", document_id, self.analyzer_id)
        result = self.cu.analyze_document(
            analyzer_id=self.analyzer_id,
            document_url=document_url,
        )
        result_dict = self.cu.result_to_dict(result)

        # Get the raw text content
        text_parts = [c.get("markdown", "") for c in result_dict.get("contents", [])]
        text = "\n\n".join(p for p in text_parts if p)

        # Extract CU-generated metadata fields
        metadata = _extract_fields(result_dict)
        logger.info(
            "Extracted metadata for %s: %s",
            document_id,
            {k: type(v).__name__ for k, v in metadata.items()},
        )

        if not text.strip():
            logger.warning("No text extracted from %s", document_id)
            return {
                "document_id": document_id,
                "chunks": 0,
                "indexed": 0,
                "metadata": metadata,
            }

        # Step 2: Chunk the text
        chunks = chunk_text(
            text=text,
            document_id=document_id,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        logger.info("Created %d chunks from %s", len(chunks), document_id)

        # Step 3: Generate embeddings
        texts = [c.content for c in chunks]
        embeddings = self.embedding.embed(texts)

        # Step 4: Index with CU metadata
        results = self.search.index_enhanced_chunks(
            self.index_name, chunks, embeddings, metadata
        )
        indexed = sum(1 for r in results if r["succeeded"])

        logger.info(
            "Indexed %d/%d enhanced chunks for %s", indexed, len(chunks), document_id
        )
        return {
            "document_id": document_id,
            "chunks": len(chunks),
            "indexed": indexed,
            "text_length": len(text),
            "metadata": metadata,
        }
