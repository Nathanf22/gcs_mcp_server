import asyncio
import uuid
import base64
import time
from fastmcp import Client
from fastmcp.resources import Resource, BinaryResource

async def test_gcs_integration():
    """
    Performs a full integration test against the real GCS MCP server.
    It creates a bucket, uploads, lists, reads, moves, and deletes a file,
    then deletes the bucket.
    """
    # Generate a unique bucket name for this test run to avoid conflicts.
    # GCS bucket names must be globally unique, lowercase, and start/end with a number or letter.
    bucket_name = f"mcp-integration-test-{uuid.uuid4().hex[:12]}"
    
    file_path = "test-folder/test-file.txt"
    file_content = b"This is a real integration test file."
    
    moved_file_path = "test-folder/test-file-renamed.txt"
    
    # The base bucket URI is not used for listing anymore.
    bucket_uri = f"gcs://{bucket_name}"
    file_uri = f"{bucket_uri}/{file_path}"
    moved_file_uri = f"{bucket_uri}/{moved_file_path}"
    
    async with Client("http://localhost:8080/mcp") as client:
        print("\n--- Running GCS Integration Test ---")
        print(f">>> Using bucket: {bucket_name}")

        try:
            # 1. Create the bucket
            print(f"\n>>> 1. Creating bucket: {bucket_name}")
            result = await client.call_tool("create_bucket", {"bucket_name": bucket_name})
            print(f"<<< Result: {result.data}")
            assert "Successfully created bucket" in result.data
            # GCS can have a slight delay for bucket availability
            await asyncio.sleep(5)

            # 2. Upload a file
            print(f"\n>>> 2. Uploading file: {file_path}")
            encoded_content = base64.b64encode(file_content)
            result = await client.call_tool("upload_file", {"bucket_name": bucket_name, "path": file_path, "content": encoded_content})
            print(f"<<< Result: {result.data}")
            assert "successfully uploaded" in result.data

            # 3. List bucket contents to verify upload
            print(f"\n>>> 3. Listing contents of bucket root")
            result = await client.call_tool("list_gcs_objects", {"bucket_name": bucket_name})
            import json
            bucket_paths = json.loads(result.data)
            print(f"<<< Found paths: {bucket_paths}")
            assert "test-folder/" in bucket_paths

            # 4. Read the file to verify content
            print(f"\n>>> 4. Reading file: {file_path}")
            result = await client.call_tool("read_gcs_file", {"bucket_name": bucket_name, "path": file_path})
            decoded_content = base64.b64decode(result.data)
            print(f"<<< Retrieved content matches original: {decoded_content == file_content}")
            assert decoded_content == file_content

            # 5. Move the file
            print(f"\n>>> 5. Moving file to: {moved_file_path}")
            result = await client.call_tool("move_gcs_object", {
                "source_bucket_name": bucket_name,
                "source_path": file_path,
                "dest_bucket_name": bucket_name,
                "dest_path": moved_file_path
            })
            print(f"<<< Result: {result.data}")
            assert "Successfully moved" in result.data

            # 6. List contents again to verify move
            print(f"\n>>> 6. Listing contents of sub-directory")
            result = await client.call_tool("list_gcs_objects", {"bucket_name": bucket_name, "path": "test-folder/"})
            bucket_paths = json.loads(result.data)
            print(f"<<< Found paths: {bucket_paths}")
            assert file_path not in bucket_paths
            assert moved_file_path in bucket_paths

            # 7. Delete the moved file
            print(f"\n>>> 7. Deleting file: {moved_file_path}")
            result = await client.call_tool("delete_gcs_object", {"bucket_name": bucket_name, "path": moved_file_path})
            print(f"<<< Result: {result.data}")
            assert "successfully deleted" in result.data

            # --- Binary File Test ---
            print("\n--- Testing Binary File (PNG) ---")
            
            # 8. Upload a binary file (1x1 red PNG)
            png_path = "test-folder/red-pixel.png"
            # A minimal 1x1 red PNG.
            png_content = base64.b64decode(b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/wcAAwAB/epv2AAAAABJRU5ErkJggg==')
            print(f"\n>>> 8. Uploading binary file: {png_path}")
            encoded_png_content = base64.b64encode(png_content)
            result = await client.call_tool("upload_file", {"bucket_name": bucket_name, "path": png_path, "content": encoded_png_content})
            print(f"<<< Result: {result.data}")
            assert "successfully uploaded" in result.data

            # 9. Read the binary file back to verify content
            print(f"\n>>> 9. Reading binary file: {png_path}")
            result = await client.call_tool("read_gcs_file", {"bucket_name": bucket_name, "path": png_path})
            decoded_png_content = base64.b64decode(result.data)
            print(f"<<< Retrieved binary content matches original: {decoded_png_content == png_content}")
            assert decoded_png_content == png_content

            # 10. Delete the binary file
            print(f"\n>>> 10. Deleting binary file: {png_path}")
            result = await client.call_tool("delete_gcs_object", {"bucket_name": bucket_name, "path": png_path})
            print(f"<<< Result: {result.data}")
            assert "successfully deleted" in result.data
            print("\n--- Binary File Test Completed ---")

        finally:
            # Final cleanup: Delete the bucket
            print(f"\n>>> Final Cleanup. Deleting bucket: {bucket_name}")
            # The 'force=True' parameter deletes the bucket even if it's not empty
            result = await client.call_tool("delete_bucket", {"bucket_name": bucket_name, "force": True})
            print(f"<<< Result: {result.data}")
            assert "has been deleted" in result.data
            
        print("\n--- GCS Integration Test Completed Successfully ---")

async def test_documentation_tool():
    """Tests that the get_mcp_documentation tool returns the documentation content."""
    async with Client("http://localhost:8080/mcp") as client:
        print("\n--- Testing Documentation Tool ---")
        result = await client.call_tool("get_mcp_documentation", {})
        print("<<< Successfully retrieved documentation.")
        # Check for a known substring to validate the content.
        assert "GCS MCP Server Documentation" in result.data
        assert "list_gcs_objects" in result.data
        print("--- Documentation Tool Test Completed ---")

if __name__ == "__main__":
    # Make sure you are authenticated with Google Cloud before running:
    # gcloud auth application-default login
    #
    # To run this test:
    # 1. Start the server in one terminal: `uv run main.py`
    # 2. Run this test script in another terminal: `uv run tests/integration_test.py`
    async def main():
        await test_gcs_integration()
        await test_documentation_tool()

    asyncio.run(main())