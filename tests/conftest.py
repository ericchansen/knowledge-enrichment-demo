"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture
def mock_azure_credential():
    """Mock Azure credential for testing without Azure access."""
    from unittest.mock import MagicMock

    from azure.identity import DefaultAzureCredential

    credential = MagicMock(spec=DefaultAzureCredential)
    credential.get_token.return_value = MagicMock(
        token="fake-token", expires_on=9999999999
    )
    return credential


@pytest.fixture
def azurite_connection_string():
    """Connection string for Azurite storage emulator."""
    return (
        "DefaultEndpointsProtocol=http;"
        "AccountName=devstoreaccount1;"
        "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
        "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
        "QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;"
        "TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"
    )
