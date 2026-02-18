"""Azure AI Search service for index management and document indexing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from azure.search.documents.models import VectorizedQuery

if TYPE_CHECKING:
    from azure.core.credentials import TokenCredential

    from ifwebuildit.services.chunking import Chunk

# Index schemas
BASELINE_INDEX_FIELDS = [
    SimpleField(name="id", type=SearchFieldDataType.String, key=True),
    SearchableField(name="content", type=SearchFieldDataType.String),
    SimpleField(name="document_id", type=SearchFieldDataType.String, filterable=True),
    SimpleField(name="chunk_index", type=SearchFieldDataType.Int32, sortable=True),
    SearchField(
        name="content_vector",
        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
        searchable=True,
        vector_search_dimensions=1536,
        vector_search_profile_name="default-profile",
    ),
]

# Enhanced index adds CU-extracted metadata for richer retrieval
ENHANCED_INDEX_FIELDS = [
    SimpleField(name="id", type=SearchFieldDataType.String, key=True),
    SearchableField(name="content", type=SearchFieldDataType.String),
    SimpleField(name="document_id", type=SearchFieldDataType.String, filterable=True),
    SimpleField(name="chunk_index", type=SearchFieldDataType.Int32, sortable=True),
    SearchableField(name="report_title", type=SearchFieldDataType.String),
    SimpleField(name="report_number", type=SearchFieldDataType.String, filterable=True),
    SimpleField(
        name="topic_category",
        type=SearchFieldDataType.String,
        filterable=True,
        facetable=True,
    ),
    SearchableField(name="executive_summary", type=SearchFieldDataType.String),
    SearchableField(name="section_title", type=SearchFieldDataType.String),
    SearchField(
        name="agencies",
        type=SearchFieldDataType.Collection(SearchFieldDataType.String),
        filterable=True,
    ),
    SearchField(
        name="content_vector",
        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
        searchable=True,
        vector_search_dimensions=1536,
        vector_search_profile_name="default-profile",
    ),
]


class SearchService:
    """Manages Azure AI Search indexes and document operations."""

    def __init__(
        self,
        endpoint: str,
        credential: TokenCredential | str,
    ) -> None:
        cred = (
            AzureKeyCredential(credential)
            if isinstance(credential, str)
            else credential
        )
        self._index_client = SearchIndexClient(endpoint=endpoint, credential=cred)
        self._endpoint = endpoint
        self._credential = cred

    def create_baseline_index(self, index_name: str) -> SearchIndex:
        """Create or update the baseline RAG index."""
        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="default-hnsw")],
            profiles=[
                VectorSearchProfile(
                    name="default-profile",
                    algorithm_configuration_name="default-hnsw",
                )
            ],
        )
        index = SearchIndex(
            name=index_name,
            fields=BASELINE_INDEX_FIELDS,
            vector_search=vector_search,
        )
        return self._index_client.create_or_update_index(index)

    def create_enhanced_index(self, index_name: str) -> SearchIndex:
        """Create or update the enhanced RAG index with CU metadata fields."""
        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="default-hnsw")],
            profiles=[
                VectorSearchProfile(
                    name="default-profile",
                    algorithm_configuration_name="default-hnsw",
                )
            ],
        )
        index = SearchIndex(
            name=index_name,
            fields=ENHANCED_INDEX_FIELDS,
            vector_search=vector_search,
        )
        return self._index_client.create_or_update_index(index)

    def get_search_client(self, index_name: str) -> SearchClient:
        """Get a SearchClient for a specific index."""
        return SearchClient(
            endpoint=self._endpoint,
            index_name=index_name,
            credential=self._credential,
        )

    def index_chunks(
        self,
        index_name: str,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> list[dict[str, Any]]:
        """Upload chunks with their embeddings to the search index."""
        client = self.get_search_client(index_name)
        documents = [
            {
                "id": chunk.id,
                "content": chunk.content,
                "document_id": chunk.document_id,
                "chunk_index": chunk.chunk_index,
                "content_vector": embedding,
            }
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]
        result = client.upload_documents(documents)
        return [{"key": r.key, "succeeded": r.succeeded} for r in result]

    def index_enhanced_chunks(
        self,
        index_name: str,
        chunks: list[Chunk],
        embeddings: list[list[float]],
        document_metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Upload chunks with embeddings and CU-extracted metadata."""
        client = self.get_search_client(index_name)
        documents = [
            {
                "id": chunk.id,
                "content": chunk.content,
                "document_id": chunk.document_id,
                "chunk_index": chunk.chunk_index,
                "content_vector": embedding,
                "report_title": document_metadata.get("reportTitle", ""),
                "report_number": document_metadata.get("reportNumber", ""),
                "topic_category": document_metadata.get("topicCategory", ""),
                "executive_summary": document_metadata.get("executiveSummary", ""),
                "section_title": chunk.section_title or "",
                "agencies": document_metadata.get("agencies", []),
            }
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]
        result = client.upload_documents(documents)
        return [{"key": r.key, "succeeded": r.succeeded} for r in result]

    def search(
        self,
        index_name: str,
        query: str,
        vector: list[float] | None = None,
        top: int = 5,
    ) -> list[dict[str, Any]]:
        """Hybrid search: keyword + vector if vector provided."""
        client = self.get_search_client(index_name)
        vector_queries = None
        if vector:
            vector_queries = [
                VectorizedQuery(
                    vector=vector,
                    k_nearest_neighbors=top,
                    fields="content_vector",
                )
            ]
        results = client.search(
            search_text=query,
            vector_queries=vector_queries,
            top=top,
        )
        hits = []
        for r in results:
            hit: dict[str, Any] = {
                "id": r["id"],
                "content": r["content"],
                "document_id": r["document_id"],
                "score": r["@search.score"],
            }
            # Include metadata fields when present (enhanced index)
            for field in (
                "report_title",
                "report_number",
                "topic_category",
                "executive_summary",
                "agencies",
                "section_title",
            ):
                if field in r and r[field]:
                    hit[field] = r[field]
            hits.append(hit)
        return hits

    def delete_index(self, index_name: str) -> None:
        """Delete an index."""
        self._index_client.delete_index(index_name)

    def list_indexes(self) -> list[str]:
        """List all index names."""
        return [idx.name for idx in self._index_client.list_indexes()]
