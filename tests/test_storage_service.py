"""Tests for the Storage service."""

from unittest.mock import MagicMock, patch

from ifwebuildit.services.storage import StorageService


@patch("ifwebuildit.services.storage.BlobServiceClient")
def test_storage_service_init(mock_blob_class):
    """StorageService should initialize from a connection string."""
    mock_blob_class.from_connection_string.return_value = MagicMock()
    svc = StorageService("fake-connection-string")
    mock_blob_class.from_connection_string.assert_called_once_with(
        "fake-connection-string"
    )
    assert svc._corpus_container_name == "corpus"
    assert svc._results_container_name == "cu-results"


@patch("ifwebuildit.services.storage.BlobServiceClient")
def test_upload_document(mock_blob_class):
    """upload_document should upload data and return the blob URL."""
    mock_blob_service = MagicMock()
    mock_blob_class.from_connection_string.return_value = mock_blob_service
    mock_container = MagicMock()
    mock_container.exists.return_value = True
    mock_blob_service.get_container_client.return_value = mock_container
    mock_blob = MagicMock()
    mock_blob.url = "https://storage/corpus/test.pdf"
    mock_container.get_blob_client.return_value = mock_blob

    svc = StorageService("fake")
    url = svc.upload_document("test.pdf", b"pdf-bytes")

    assert url == "https://storage/corpus/test.pdf"
    mock_blob.upload_blob.assert_called_once_with(b"pdf-bytes", overwrite=True)


@patch("ifwebuildit.services.storage.BlobServiceClient")
def test_list_documents(mock_blob_class):
    """list_documents should return blob names."""
    mock_blob_service = MagicMock()
    mock_blob_class.from_connection_string.return_value = mock_blob_service
    mock_container = MagicMock()
    mock_container.exists.return_value = True
    mock_blob_service.get_container_client.return_value = mock_container

    blob1 = MagicMock()
    blob1.name = "report1.pdf"
    blob2 = MagicMock()
    blob2.name = "report2.pdf"
    mock_container.list_blobs.return_value = [blob1, blob2]

    svc = StorageService("fake")
    docs = svc.list_documents()

    assert docs == ["report1.pdf", "report2.pdf"]


@patch("ifwebuildit.services.storage.BlobServiceClient")
def test_save_result_str(mock_blob_class):
    """save_result should encode strings to bytes before uploading."""
    mock_blob_service = MagicMock()
    mock_blob_class.from_connection_string.return_value = mock_blob_service
    mock_container = MagicMock()
    mock_container.exists.return_value = True
    mock_blob_service.get_container_client.return_value = mock_container
    mock_blob = MagicMock()
    mock_blob.url = "https://storage/cu-results/result.json"
    mock_container.get_blob_client.return_value = mock_blob

    svc = StorageService("fake")
    url = svc.save_result("result.json", '{"key": "value"}')

    assert url == "https://storage/cu-results/result.json"
    mock_blob.upload_blob.assert_called_once_with(b'{"key": "value"}', overwrite=True)


@patch("ifwebuildit.services.storage.BlobServiceClient")
def test_delete_document(mock_blob_class):
    """delete_document should call delete_blob on the blob client."""
    mock_blob_service = MagicMock()
    mock_blob_class.from_connection_string.return_value = mock_blob_service
    mock_container = MagicMock()
    mock_container.exists.return_value = True
    mock_blob_service.get_container_client.return_value = mock_container
    mock_blob = MagicMock()
    mock_container.get_blob_client.return_value = mock_blob

    svc = StorageService("fake")
    svc.delete_document("test.pdf")

    mock_blob.delete_blob.assert_called_once()


@patch("ifwebuildit.services.storage.BlobServiceClient")
def test_download_document(mock_blob_class):
    """download_document should return blob content as bytes."""
    mock_blob_service = MagicMock()
    mock_blob_class.from_connection_string.return_value = mock_blob_service
    mock_container = MagicMock()
    mock_container.exists.return_value = True
    mock_blob_service.get_container_client.return_value = mock_container
    mock_blob = MagicMock()
    mock_blob.download_blob.return_value.readall.return_value = b"pdf-content"
    mock_container.get_blob_client.return_value = mock_blob

    svc = StorageService("fake")
    data = svc.download_document("test.pdf")

    assert data == b"pdf-content"


@patch("ifwebuildit.services.storage.BlobServiceClient")
def test_container_created_if_not_exists(mock_blob_class):
    """Container should be created if it doesn't exist."""
    mock_blob_service = MagicMock()
    mock_blob_class.from_connection_string.return_value = mock_blob_service
    mock_container = MagicMock()
    mock_container.exists.return_value = False
    mock_blob_service.get_container_client.return_value = mock_container

    svc = StorageService("fake")
    container = svc.corpus_container

    mock_container.create_container.assert_called_once()
    assert container == mock_container
