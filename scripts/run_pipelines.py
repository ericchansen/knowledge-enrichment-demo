"""Run both baseline and enhanced pipelines on the corpus.

Usage:
    uv run python scripts/run_pipelines.py [--corpus-dir data/corpus]

Processes all PDFs through:
  1. Baseline pipeline (plain text extraction → chunk → embed → index)
  2. Enhanced pipeline (CU custom analyzer → chunk → embed → index with metadata)

Requires .env with Azure credentials configured.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from enrichment.config import get_settings  # noqa: E402
from enrichment.pipeline.baseline import BaselinePipeline  # noqa: E402
from enrichment.pipeline.enhanced import EnhancedPipeline  # noqa: E402
from enrichment.services.content_understanding import (  # noqa: E402
    ContentUnderstandingService,
)
from enrichment.services.embedding import EmbeddingService  # noqa: E402
from enrichment.services.search import SearchService  # noqa: E402
from enrichment.services.storage import StorageService  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logging.getLogger("azure").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run enrichment pipelines")
    parser.add_argument(
        "--corpus-dir",
        default="data/corpus",
        help="Directory containing PDF files",
    )
    parser.add_argument(
        "--pipeline",
        choices=["baseline", "enhanced", "both"],
        default="both",
        help="Which pipeline(s) to run",
    )
    args = parser.parse_args()

    settings = get_settings()
    corpus_dir = Path(args.corpus_dir)

    if not corpus_dir.exists():
        logger.error("Corpus directory not found: %s", corpus_dir)
        sys.exit(1)

    pdfs = sorted(corpus_dir.glob("*.pdf"))
    if not pdfs:
        logger.error("No PDFs found in %s", corpus_dir)
        sys.exit(1)

    logger.info("Found %d PDFs in %s", len(pdfs), corpus_dir)

    # Initialise shared services
    cu = ContentUnderstandingService(
        endpoint=settings.contentunderstanding_endpoint,
        api_key=settings.contentunderstanding_key,
    )
    embedding = EmbeddingService(
        endpoint=settings.azure_openai_endpoint,
        credential=settings.azure_openai_key,
        deployment=settings.embedding_deployment,
    )
    search = SearchService(
        endpoint=settings.search_endpoint,
        credential=settings.search_api_key,
    )
    storage_kwargs: dict[str, str] = {
        "corpus_container": settings.storage_container_corpus,
        "results_container": settings.storage_container_results,
    }
    if settings.storage_account_url:
        storage_kwargs["account_url"] = settings.storage_account_url
    else:
        storage_kwargs["connection_string"] = settings.azure_storage_connection_string
    storage = StorageService(**storage_kwargs)

    # Upload PDFs to blob storage and collect SAS URLs (for CU access)
    doc_urls: list[tuple[str, str]] = []
    for pdf in pdfs:
        logger.info("Uploading %s …", pdf.name)
        storage.upload_document(pdf.name, pdf.read_bytes())
        doc_id = pdf.stem
        sas_url = storage.get_document_sas_url(pdf.name)
        doc_urls.append((doc_id, sas_url))

    # Run baseline pipeline
    if args.pipeline in ("baseline", "both"):
        logger.info("=" * 60)
        logger.info("BASELINE PIPELINE")
        logger.info("=" * 60)
        baseline = BaselinePipeline(
            storage=storage,
            cu=cu,
            embedding=embedding,
            search=search,
            index_name=settings.search_index_baseline,
        )
        baseline.ensure_index()
        for doc_id, url in doc_urls:
            logger.info("Processing %s (baseline) …", doc_id)
            result = baseline.process_document(document_url=url, document_id=doc_id)
            logger.info(
                "  → %d chunks, %d indexed", result["chunks"], result["indexed"]
            )

    # Run enhanced pipeline
    if args.pipeline in ("enhanced", "both"):
        logger.info("=" * 60)
        logger.info("ENHANCED PIPELINE (CU enrichment)")
        logger.info("=" * 60)
        enhanced = EnhancedPipeline(
            storage=storage,
            cu=cu,
            embedding=embedding,
            search=search,
            index_name=settings.search_index_enhanced,
        )
        enhanced.ensure_index()
        enhanced.ensure_analyzer()
        for doc_id, url in doc_urls:
            logger.info("Processing %s (enhanced) …", doc_id)
            result = enhanced.process_document(document_url=url, document_id=doc_id)
            logger.info(
                "  → %d chunks, %d indexed, metadata: %s",
                result["chunks"],
                result["indexed"],
                list(result.get("metadata", {}).keys()),
            )

    logger.info("=" * 60)
    logger.info("DONE — pipelines complete")
    logger.info("Start the server: uv run uvicorn enrichment.server:app --reload")


if __name__ == "__main__":
    main()
