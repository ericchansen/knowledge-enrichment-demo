"""Azure Blob Storage service for managing the document corpus."""

from __future__ import annotations

import logging
from typing import BinaryIO

from azure.storage.blob import BlobServiceClient, ContainerClient

logger = logging.getLogger(__name__)


class StorageService:
    """Manages document corpus in Azure Blob Storage."""

    def __init__(
        self,
        connection_string: str,
        corpus_container: str = "corpus",
        results_container: str = "cu-results",
    ) -> None:
        self._blob_service = BlobServiceClient.from_connection_string(connection_string)
        self._corpus_container_name = corpus_container
        self._results_container_name = results_container

    def _get_container(self, name: str) -> ContainerClient:
        """Get or create a container."""
        container = self._blob_service.get_container_client(name)
        if not container.exists():
            container.create_container()
            logger.info("Created container: %s", name)
        return container

    @property
    def corpus_container(self) -> ContainerClient:
        """Get the corpus container client."""
        return self._get_container(self._corpus_container_name)

    @property
    def results_container(self) -> ContainerClient:
        """Get the CU results container client."""
        return self._get_container(self._results_container_name)

    def upload_document(self, filename: str, data: BinaryIO | bytes) -> str:
        """Upload a document to the corpus container.

        Returns the blob URL.
        """
        container = self.corpus_container
        blob = container.get_blob_client(filename)
        blob.upload_blob(data, overwrite=True)
        logger.info("Uploaded document: %s", filename)
        return blob.url

    def list_documents(self) -> list[str]:
        """List all document names in the corpus container."""
        container = self.corpus_container
        return [blob.name for blob in container.list_blobs()]

    def get_document_url(self, filename: str) -> str:
        """Get the URL for a document in the corpus."""
        blob = self.corpus_container.get_blob_client(filename)
        return blob.url

    def download_document(self, filename: str) -> bytes:
        """Download a document from the corpus container."""
        blob = self.corpus_container.get_blob_client(filename)
        return blob.download_blob().readall()

    def save_result(self, filename: str, data: bytes | str) -> str:
        """Save a CU result to the results container.

        Returns the blob URL.
        """
        container = self.results_container
        blob = container.get_blob_client(filename)
        content = data.encode("utf-8") if isinstance(data, str) else data
        blob.upload_blob(content, overwrite=True)
        logger.info("Saved CU result: %s", filename)
        return blob.url

    def delete_document(self, filename: str) -> None:
        """Delete a document from the corpus container."""
        blob = self.corpus_container.get_blob_client(filename)
        blob.delete_blob()
        logger.info("Deleted document: %s", filename)
