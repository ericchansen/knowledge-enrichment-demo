"""Chat service — RAG-based question answering over indexed documents."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from openai import AzureOpenAI

if TYPE_CHECKING:
    from azure.core.credentials import TokenCredential

    from enrichment.services.embedding import EmbeddingService
    from enrichment.services.search import SearchService

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_BASELINE = """You are a helpful assistant that answers questions about GAO (Government Accountability Office) cybersecurity reports.
Use ONLY the provided context to answer. If the context doesn't contain relevant information, say so.
Cite the document ID when referencing specific information."""

SYSTEM_PROMPT_ENHANCED = """You are a helpful assistant that answers questions about GAO cybersecurity reports.
You have access to enriched document metadata including report titles, agencies, topic categories, and executive summaries.
Use ONLY the provided context to answer. When available, include:
- The specific report number and title
- Relevant agencies mentioned
- Key findings or recommendations
Cite the document ID when referencing specific information."""


class ChatService:
    """RAG chat service — retrieves context from search, generates answers via LLM."""

    def __init__(
        self,
        search: SearchService,
        embedding: EmbeddingService,
        endpoint: str,
        credential: TokenCredential | str,
        chat_deployment: str = "gpt-4o",
    ) -> None:
        self.search = search
        self.embedding = embedding
        self._chat_deployment = chat_deployment

        kwargs: dict = {"azure_endpoint": endpoint, "api_version": "2024-10-21"}
        if isinstance(credential, str):
            kwargs["api_key"] = credential
        else:
            from azure.identity import get_bearer_token_provider

            kwargs["azure_ad_token_provider"] = get_bearer_token_provider(
                credential, "https://cognitiveservices.azure.com/.default"
            )
        self._client = AzureOpenAI(**kwargs)

    def chat(
        self,
        message: str,
        index_name: str,
        system_prompt: str = SYSTEM_PROMPT_BASELINE,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """Answer a question using RAG over the specified index.

        Returns:
            Dict with 'message', 'citations' list, and 'context_used'
        """
        # Step 1: Embed the query
        query_vector = self.embedding.embed_single(message)

        # Step 2: Retrieve relevant chunks
        results = self.search.search(
            index_name=index_name,
            query=message,
            vector=query_vector,
            top=top_k,
        )

        if not results:
            return {
                "message": "I couldn't find relevant information in the knowledge base.",
                "citations": [],
            }

        # Step 3: Build context from search results
        context_parts = []
        citations = []
        for r in results:
            doc_id = r.get("document_id", "unknown")
            content = r.get("content", "")

            # Build context entry — include metadata when available
            header_parts = [f"[{doc_id}]"]
            if r.get("report_title"):
                header_parts.append(f"Report: {r['report_title']}")
            if r.get("report_number"):
                header_parts.append(f"({r['report_number']})")
            if r.get("topic_category"):
                header_parts.append(f"Category: {r['topic_category']}")
            if r.get("agencies"):
                header_parts.append(f"Agencies: {', '.join(r['agencies'])}")

            header = " | ".join(header_parts)
            entry = f"{header}\n{content}"
            if r.get("executive_summary"):
                entry += f"\nExecutive Summary: {r['executive_summary']}"

            context_parts.append(entry)
            citations.append(
                {
                    "document_id": doc_id,
                    "chunk_id": r.get("id", ""),
                    "score": r.get("score", 0),
                    "snippet": content[:200],
                    "report_title": r.get("report_title", ""),
                    "report_number": r.get("report_number", ""),
                }
            )

        context = "\n\n---\n\n".join(context_parts)

        # Step 4: Generate answer via LLM
        response = self._client.chat.completions.create(
            model=self._chat_deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Context:\n{context}\n\nQuestion: {message}",
                },
            ],
            temperature=0.3,
            max_tokens=1024,
        )

        answer = response.choices[0].message.content or ""
        return {"message": answer, "citations": citations}

    def chat_baseline(self, message: str, index_name: str) -> dict[str, Any]:
        """Chat using the baseline index."""
        return self.chat(
            message=message,
            index_name=index_name,
            system_prompt=SYSTEM_PROMPT_BASELINE,
        )

    def chat_enhanced(self, message: str, index_name: str) -> dict[str, Any]:
        """Chat using the enhanced index with richer system prompt."""
        return self.chat(
            message=message,
            index_name=index_name,
            system_prompt=SYSTEM_PROMPT_ENHANCED,
        )
