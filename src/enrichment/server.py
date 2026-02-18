"""FastAPI server — API endpoints for the Knowledge Base Enrichment demo."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from enrichment.config import get_settings
from enrichment.models import (
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
from enrichment.services.chat import ChatService
from enrichment.services.content_understanding import ContentUnderstandingService
from enrichment.services.embedding import EmbeddingService
from enrichment.services.search import SearchService
from enrichment.services.storage import StorageService

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Knowledge Enrichment Demo",
        description="Knowledge Base Overnight Enrichment — Content Understanding demo",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize services
    storage = StorageService(
        connection_string=settings.azure_storage_connection_string,
        corpus_container=settings.storage_container_corpus,
        results_container=settings.storage_container_results,
    )

    # Chat service (lazy — only initialised when Azure OpenAI is configured)
    _chat_service: ChatService | None = None

    def get_chat_service() -> ChatService | None:
        nonlocal _chat_service
        if _chat_service is not None:
            return _chat_service
        if not settings.azure_openai_endpoint or not settings.search_endpoint:
            return None
        search = SearchService(
            endpoint=settings.search_endpoint,
            credential=settings.search_api_key or "",
        )
        embedding = EmbeddingService(
            endpoint=settings.azure_openai_endpoint,
            credential=settings.azure_openai_key or "",
            deployment=settings.embedding_deployment,
        )
        _chat_service = ChatService(
            search=search,
            embedding=embedding,
            endpoint=settings.azure_openai_endpoint,
            credential=settings.azure_openai_key or "",
            chat_deployment=settings.chat_deployment,
        )
        return _chat_service

    # ── API routes ────────────────────────────────────────────

    @app.get("/api/health", response_model=HealthResponse)
    async def health_check() -> HealthResponse:
        return HealthResponse(environment=settings.environment)

    @app.get("/api/corpus", response_model=CorpusInfo)
    async def get_corpus() -> CorpusInfo:
        """List all documents in the corpus."""
        filenames = storage.list_documents()
        documents = [
            Document(filename=f, status=DocumentStatus.UPLOADED) for f in filenames
        ]
        return CorpusInfo(
            total_documents=len(documents),
            documents=documents,
        )

    @app.post("/api/corpus/upload", response_model=Document)
    async def upload_document(file: UploadFile) -> Document:
        """Upload a document to the corpus."""
        filename = file.filename or "unnamed"
        data = await file.read()
        blob_url = storage.upload_document(filename, data)
        logger.info("Uploaded %s (%d bytes)", filename, len(data))
        return Document(filename=filename, blob_url=blob_url)

    @app.delete("/api/corpus/{filename}")
    async def delete_document(filename: str) -> dict[str, str]:
        """Delete a document from the corpus."""
        storage.delete_document(filename)
        return {"status": "deleted", "filename": filename}

    @app.post("/api/chat/baseline", response_model=ChatResponse)
    async def chat_baseline(request: ChatRequest) -> ChatResponse:
        """Chat with the baseline RAG agent."""
        svc = get_chat_service()
        if svc is None:
            return ChatResponse(
                message="Baseline agent is not yet configured. "
                "Please set AZURE_OPENAI_ENDPOINT and SEARCH_ENDPOINT.",
                pipeline_type=PipelineType.BASELINE,
            )
        try:
            result = svc.chat_baseline(request.message, settings.search_index_baseline)
        except Exception:
            logger.exception("Baseline chat error")
            return ChatResponse(
                message="Sorry, an error occurred while processing your question. "
                "Please check that the baseline pipeline has been run.",
                pipeline_type=PipelineType.BASELINE,
            )
        return ChatResponse(
            message=result["message"],
            pipeline_type=PipelineType.BASELINE,
            citations=result.get("citations", []),
        )

    @app.post("/api/chat/enhanced", response_model=ChatResponse)
    async def chat_enhanced(request: ChatRequest) -> ChatResponse:
        """Chat with the CU-enhanced RAG agent."""
        svc = get_chat_service()
        if svc is None:
            return ChatResponse(
                message="Enhanced agent is not yet configured. "
                "Please set AZURE_OPENAI_ENDPOINT and SEARCH_ENDPOINT.",
                pipeline_type=PipelineType.ENHANCED,
            )
        try:
            result = svc.chat_enhanced(request.message, settings.search_index_enhanced)
        except Exception:
            logger.exception("Enhanced chat error")
            return ChatResponse(
                message="Sorry, an error occurred while processing your question. "
                "Please check that the enhanced pipeline has been run.",
                pipeline_type=PipelineType.ENHANCED,
            )
        return ChatResponse(
            message=result["message"],
            pipeline_type=PipelineType.ENHANCED,
            citations=result.get("citations", []),
        )

    @app.post("/api/pipeline/run", response_model=PipelineStatus)
    async def run_pipeline(request: PipelineRequest) -> PipelineStatus:
        """Run a pipeline on all documents in the corpus."""
        if not settings.contentunderstanding_endpoint or not settings.search_endpoint:
            return PipelineStatus(
                pipeline_type=request.pipeline_type,
                status="error",
                message="Pipeline services not configured. "
                "Set CONTENTUNDERSTANDING_ENDPOINT and SEARCH_ENDPOINT.",
            )
        if not settings.azure_openai_endpoint:
            return PipelineStatus(
                pipeline_type=request.pipeline_type,
                status="error",
                message="Azure OpenAI not configured. Set AZURE_OPENAI_ENDPOINT.",
            )

        try:
            cu = ContentUnderstandingService(
                endpoint=settings.contentunderstanding_endpoint,
                api_key=settings.contentunderstanding_key,
            )
            embedding = EmbeddingService(
                endpoint=settings.azure_openai_endpoint,
                credential=settings.azure_openai_key or "",
                deployment=settings.embedding_deployment,
            )
            search = SearchService(
                endpoint=settings.search_endpoint,
                credential=settings.search_api_key or "",
            )

            filenames = storage.list_documents()
            if not filenames:
                return PipelineStatus(
                    pipeline_type=request.pipeline_type,
                    status="error",
                    message="No documents in corpus. Upload documents first.",
                )

            total = len(filenames)
            processed = 0

            if request.pipeline_type == PipelineType.BASELINE:
                from enrichment.pipeline.baseline import BaselinePipeline

                pipeline = BaselinePipeline(
                    storage=storage,
                    cu=cu,
                    embedding=embedding,
                    search=search,
                    index_name=settings.search_index_baseline,
                )
                pipeline.ensure_index()
                for fname in filenames:
                    blob_url = storage.get_document_url(fname)
                    doc_id = Path(fname).stem
                    pipeline.process_document(document_url=blob_url, document_id=doc_id)
                    processed += 1
            else:
                from enrichment.pipeline.enhanced import EnhancedPipeline

                pipeline = EnhancedPipeline(
                    storage=storage,
                    cu=cu,
                    embedding=embedding,
                    search=search,
                    index_name=settings.search_index_enhanced,
                )
                pipeline.ensure_index()
                pipeline.ensure_analyzer()
                for fname in filenames:
                    blob_url = storage.get_document_url(fname)
                    doc_id = Path(fname).stem
                    pipeline.process_document(document_url=blob_url, document_id=doc_id)
                    processed += 1

            return PipelineStatus(
                pipeline_type=request.pipeline_type,
                status="complete",
                documents_processed=processed,
                documents_total=total,
                message=f"Processed {processed}/{total} documents.",
            )
        except Exception:
            logger.exception("Pipeline run error")
            return PipelineStatus(
                pipeline_type=request.pipeline_type,
                status="error",
                message="An error occurred while running the pipeline.",
            )

    # ── Static files & SPA fallback ──────────────────────────

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    async def serve_index() -> FileResponse:
        """Serve the comparison UI."""
        return FileResponse(str(STATIC_DIR / "index.html"))

    return app


app = create_app()
