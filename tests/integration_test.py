import asyncio
import uuid
import base64
import os
import json
from fastmcp import Client

# --- Configuration ---
# Determine the base URL from an environment variable, default to local
BASE_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8080").strip()
MCP_URL = f"{BASE_URL}/mcp"

async def test_gcs_integration():
    """
    Performs a full integration test against the GCS MCP server.
    Can target a local server or a deployed Cloud Run service via the proxy.
    """
    # Generate a unique bucket name for this test run.
    bucket_name = f"mcp-integration-test-{uuid.uuid4().hex[:12]}"
    file_path = "test-folder/test-file.txt"
    file_content = b"This is an integration test file."
    moved_file_path = "test-folder/test-file-renamed.txt"
    
    async with Client(MCP_URL) as client:
        print("\n--- Running GCS Integration Test ---")
        print(f">>> Targeting Server: {BASE_URL}")
        print(f">>> Using bucket: {bucket_name}")

        try:
            # 1. Create the bucket
            print(f"\n>>> 1. Creating bucket: {bucket_name}")
            result = await client.call_tool("create_bucket", {"bucket_name": bucket_name})
            print(f"<<< Result: {result.data}")
            assert "Successfully created bucket" in result.data
            await asyncio.sleep(5) # Delay for GCS consistency

            # 2. Upload a file
            print(f"\n>>> 2. Uploading file: {file_path}")
            encoded_content = base64.b64encode(file_content).decode('utf-8')
            result = await client.call_tool("upload_file", {"bucket_name": bucket_name, "path": file_path, "content": encoded_content})
            print(f"<<< Result: {result.data}")
            assert "successfully uploaded" in result.data

            # 3. List bucket contents
            print(f"\n>>> 3. Listing contents of bucket root")
            result = await client.call_tool("list_gcs_objects", {"bucket_name": bucket_name})
            bucket_paths = json.loads(result.data)
            print(f"<<< Found paths: {bucket_paths}")
            assert "test-folder/" in bucket_paths

            # 4. Read the file
            print(f"\n>>> 4. Reading file: {file_path}")
            result = await client.call_tool("read_gcs_file", {"bucket_name": bucket_name, "path": file_path})
            decoded_content = base64.b64decode(result.data)
            print(f"<<< Retrieved content matches original: {decoded_content == file_content}")
            assert decoded_content == file_content

            # 5. Move the file
            print(f"\n>>> 5. Moving file to: {moved_file_path}")
            result = await client.call_tool("move_gcs_object", {
                "source_bucket_name": bucket_name, "source_path": file_path,
                "dest_bucket_name": bucket_name, "dest_path": moved_file_path
            })
            print(f"<<< Result: {result.data}")
            assert "Successfully moved" in result.data

            # 6. List contents to verify move
            print(f"\n>>> 6. Listing contents of sub-directory")
            result = await client.call_tool("list_gcs_objects", {"bucket_name": bucket_name, "path": "test-folder/"})
            bucket_paths = json.loads(result.data)
            print(f"<<< Found paths: {bucket_paths}")
            assert moved_file_path in bucket_paths

            # 7. Delete the moved file
            print(f"\n>>> 7. Deleting file: {moved_file_path}")
            result = await client.call_tool("delete_gcs_object", {"bucket_name": bucket_name, "path": moved_file_path})
            print(f"<<< Result: {result.data}")
            assert "successfully deleted" in result.data

            # --- Binary File Test ---
            print("\n--- Testing Binary File (PNG) ---")
            png_path = "test-folder/red-pixel.png"
            png_content = base64.b64decode(b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/wcAAwAB/epv2AAAAABJRU5ErkJggg==')
            
            print(f"\n>>> 8. Uploading binary file: {png_path}")
            encoded_png_content = base64.b64encode(png_content).decode('utf-8')
            result = await client.call_tool("upload_file", {"bucket_name": bucket_name, "path": png_path, "content": encoded_png_content})
            print(f"<<< Result: {result.data}")
            assert "successfully uploaded" in result.data

            print(f"\n>>> 9. Reading binary file: {png_path}")
            result = await client.call_tool("read_gcs_file", {"bucket_name": bucket_name, "path": png_path})
            decoded_png_content = base64.b64decode(result.data)
            print(f"<<< Retrieved binary content matches original: {decoded_png_content == png_content}")
            assert decoded_png_content == png_content

            print(f"\n>>> 10. Deleting binary file: {png_path}")
            result = await client.call_tool("delete_gcs_object", {"bucket_name": bucket_name, "path": png_path})
            print(f"<<< Result: {result.data}")
            assert "successfully deleted" in result.data
            print("\n--- Binary File Test Completed ---")

        finally:
            # Final cleanup: Delete the bucket
            print(f"\n>>> Final Cleanup. Deleting bucket: {bucket_name}")
            result = await client.call_tool("delete_bucket", {"bucket_name": bucket_name, "force": True})
            print(f"<<< Result: {result.data}")
            assert "has been deleted" in result.data
            
        print("\n--- GCS Integration Test Completed Successfully ---")

async def test_documentation_tool():
    """Tests the get_mcp_documentation tool."""
    async with Client(MCP_URL) as client:
        print("\n--- Testing Documentation Tool ---")
        print(f">>> Targeting Server: {BASE_URL}")
        result = await client.call_tool("get_mcp_documentation", {})
        print("<<< Successfully retrieved documentation.")
        assert "GCS MCP Server Documentation" in result.data
        assert "list_gcs_objects" in result.data
        print("--- Documentation Tool Test Completed ---")

if __name__ == "__main__":
    async def main():
        await test_gcs_integration()
        await test_documentation_tool()

    # To run this test:
    # 1. For local:
    #    - Start the server: `uv run main.py`
    #    - Run this test: `uv run tests/integration_test.py`
    # 2. For deployed service via Cloud Run Proxy:
    #    - Terminal 1: `gcloud run services proxy gcs-mcp-server --region us-central1 --port 8080`
    #    - Terminal 2: `set MCP_SERVER_URL=http://localhost:8080`
    #    - Terminal 2: `uv run tests/integration_test.py`
    asyncio.run(main())
