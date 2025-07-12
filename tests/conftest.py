import pytest
import sys
import os
from unittest.mock import MagicMock
from httpx import AsyncClient

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from gcs_mcp_server.__main__ import app


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration", action="store_true", default=False, help="run integration tests"
    )

def pytest_configure(config):
    config.addinivalue_line("markers", "integration: mark test as integration to run")

def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-integration"):
        skip_integration = pytest.mark.skip(reason="need --run-integration option to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)

@pytest.fixture
def mock_storage_client():
    """
    Provides a MagicMock for the google.cloud.storage.Client.
    This prevents real calls to GCS during tests.
    """
    mock_client = MagicMock()
    
    # Mock the bucket and blob interactions
    mock_blob = MagicMock()
    mock_blob.exists.return_value = True
    mock_blob.download_as_bytes.return_value = b"mock file content"
    
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_bucket.list_blobs.return_value = []

    mock_client.get_bucket.return_value = mock_bucket
    mock_client.create_bucket.return_value = MagicMock(name="new_bucket")
    
    return mock_client

@pytest.fixture
async def client():
    """
    Provides a test client for the application within the lifespan context.
    """
    async with AsyncClient(app=app.http_app(), base_url="http://test") as client:
        yield client
