"""Baseline RAG pipeline — ingest, chunk, embed, index."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ifwebuildit.services.chunking import chunk_text

if TYPE_CHECKING:
    from ifwebuildit.services.content_understanding import (
        ContentUnderstandingService,
    )
    from ifwebuildit.services.embedding import EmbeddingService
    from ifwebuildit.services.search import SearchService
    from ifwebuildit.services.storage import StorageService

logger = logging.getLogger(__name__)


class BaselinePipeline:
    """Orchestrates the baseline RAG pipeline.

    Steps:
    1. Download document from Blob Storage
    2. Extract text via CU (prebuilt document analyzer)
    3. Chunk the extracted text
    4. Generate embeddings for each chunk
    5. Index chunks + embeddings in AI Search
    """

    def __init__(
        self,
        storage: StorageService,
        cu: ContentUnderstandingService,
        embedding: EmbeddingService,
        search: SearchService,
        index_name: str = "baseline",
    ) -> None:
        self.storage = storage
        self.cu = cu
        self.embedding = embedding
        self.search = search
        self.index_name = index_name

    def ensure_index(self) -> None:
        """Create the baseline search index if it doesn't exist."""
        self.search.create_baseline_index(self.index_name)
        logger.info("Ensured baseline index '%s' exists", self.index_name)

    def process_document(
        self,
        document_url: str,
        document_id: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> dict:
        """Run the full baseline pipeline for a single document.

        Args:
            document_url: SAS URL or public URL to the document in Blob Storage
            document_id: Unique identifier for the document
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between consecutive chunks

        Returns:
            Summary dict with chunk count and index results
        """
        # Step 1: Extract text using CU baseline analyzer (prebuilt)
        logger.info("Extracting text from %s", document_id)
        result = self.cu.analyze_document(
            document_url=document_url,
            analyzer_id="prebuilt-documentSearch",
        )
        extracted = self.cu.result_to_dict(result)
        text_parts = [c.get("markdown", "") for c in extracted.get("contents", [])]
        text = "\n\n".join(p for p in text_parts if p)

        if not text.strip():
            logger.warning("No text extracted from %s", document_id)
            return {"document_id": document_id, "chunks": 0, "indexed": 0}

        # Step 2: Chunk the text
        logger.info("Chunking %d characters from %s", len(text), document_id)
        chunks = chunk_text(
            text=text,
            document_id=document_id,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        logger.info("Created %d chunks from %s", len(chunks), document_id)

        # Step 3: Generate embeddings
        logger.info("Generating embeddings for %d chunks", len(chunks))
        texts = [c.content for c in chunks]
        embeddings = self.embedding.embed(texts)

        # Step 4: Index chunks with embeddings
        logger.info("Indexing %d chunks into '%s'", len(chunks), self.index_name)
        results = self.search.index_chunks(self.index_name, chunks, embeddings)
        indexed = sum(1 for r in results if r["succeeded"])

        logger.info(
            "Indexed %d/%d chunks for %s",
            indexed,
            len(chunks),
            document_id,
        )
        return {
            "document_id": document_id,
            "chunks": len(chunks),
            "indexed": indexed,
            "text_length": len(text),
        }
