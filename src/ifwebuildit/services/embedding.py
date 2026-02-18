"""Embedding service using Azure OpenAI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from openai import AzureOpenAI

if TYPE_CHECKING:
    from azure.core.credentials import TokenCredential


class EmbeddingService:
    """Generate text embeddings via Azure OpenAI."""

    def __init__(
        self,
        endpoint: str,
        credential: TokenCredential | str,
        deployment: str = "text-embedding-3-small",
    ) -> None:
        kwargs: dict = {"azure_endpoint": endpoint, "api_version": "2024-10-21"}
        if isinstance(credential, str):
            kwargs["api_key"] = credential
        else:
            from azure.identity import get_bearer_token_provider

            kwargs["azure_ad_token_provider"] = get_bearer_token_provider(
                credential, "https://cognitiveservices.azure.com/.default"
            )
        self._client = AzureOpenAI(**kwargs)
        self._deployment = deployment

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        Azure OpenAI supports up to 2048 texts per batch, but we
        process in smaller batches to stay within token limits.
        """
        if not texts:
            return []

        all_embeddings: list[list[float]] = []
        batch_size = 16

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = self._client.embeddings.create(
                input=batch,
                model=self._deployment,
            )
            all_embeddings.extend([item.embedding for item in response.data])

        return all_embeddings

    def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        return self.embed([text])[0]
