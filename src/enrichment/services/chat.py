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
Keep your answer to 2-3 short paragraphs. Cite the document ID in brackets like [GAO-24-107231] when referencing information."""

SYSTEM_PROMPT_ENHANCED = """You are a helpful assistant that answers questions about GAO cybersecurity reports.
You have access to enriched metadata: report titles, agencies, topic categories, findings, and recommendations.

Rules:
- Use ONLY the provided context. Be concise — 3-5 bullet points max.
- Start each bullet with the specific finding or fact, not filler.
- Cite using the full report title and number, e.g. [GAO-24-107231, "High-Risk Series..."].
- When agencies are mentioned, name them specifically.
- End with a one-sentence takeaway.
- Do NOT repeat the question or use filler phrases like "According to the reports..."."""


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
                    "agencies": r.get("agencies", []),
                    "topic_category": r.get("topic_category", ""),
                    "executive_summary": r.get("executive_summary", ""),
                    "key_findings": r.get("key_findings", []),
                    "recommendations": r.get("recommendations", []),
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

        # Aggregate metadata across citations
        all_agencies: list[str] = []
        all_topics: list[str] = []
        reports: list[dict[str, str]] = []
        seen_reports: set[str] = set()
        has_summary = False

        for c in citations:
            for a in c.get("agencies", []):
                if a and a not in all_agencies:
                    all_agencies.append(a)
            topic = c.get("topic_category", "")
            if topic and topic not in all_topics:
                all_topics.append(topic)
            if c.get("executive_summary"):
                has_summary = True
            rn = c.get("report_number", "")
            if rn and rn not in seen_reports:
                seen_reports.add(rn)
                reports.append({"title": c.get("report_title", ""), "number": rn})

        metadata = {
            "reports": reports,
            "agencies": all_agencies,
            "topics": all_topics,
            "has_executive_summary": has_summary,
        }

        return {"message": answer, "citations": citations, "metadata": metadata}

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
