import asyncio
import logging
import os
import base64
import json
from google.cloud import storage
from google.api_core.exceptions import Conflict, NotFound
from fastmcp import FastMCP
from fastmcp.resources import BinaryResource, TextResource

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)

# --- Credential Normalization ---
key_env_var = 'GOOGLE_APPLICATION_CREDENTIALS'
if key_env_var in os.environ:
    key_path = os.environ[key_env_var]
    cleaned_path = key_path.strip().strip('\'"')
    if cleaned_path != key_path:
        logger.info(f"Normalized credentials path from '{key_path}' to '{cleaned_path}'.")
        os.environ[key_env_var] = cleaned_path
# --- End Credential Normalization ---

app = FastMCP("GCS")
storage_client = storage.Client()

# --- Tools ---

@app.tool()
async def create_bucket(bucket_name: str) -> str:
    """Creates a new Google Cloud Storage bucket."""
    try:
        bucket = storage_client.create_bucket(bucket_name)
        return f"Successfully created bucket '{bucket.name}'."
    except Conflict:
        return f"Bucket '{bucket_name}' already exists."
    except Exception as e:
        return f"Failed to create bucket '{bucket_name}': {e}"

@app.tool()
async def upload_file(bucket_name: str, path: str, content: bytes) -> str:
    """Uploads or overwrites a file in a GCS bucket."""
    try:
        bucket = storage_client.get_bucket(bucket_name)
        blob = bucket.blob(path)
        decoded_content = base64.b64decode(content)
        blob.upload_from_string(decoded_content)
        return f"File '{path}' successfully uploaded to bucket '{bucket_name}'."
    except NotFound:
        return f"Error: Bucket '{bucket_name}' not found."
    except Exception as e:
        return f"An error occurred: {e}"

@app.tool()
async def read_gcs_file(bucket_name: str, path: str) -> str:
    """
    Reads the content of a file from a GCS bucket.
    Returns the file content as a Base64-encoded string.
    """
    try:
        bucket = storage_client.get_bucket(bucket_name)
        blob = bucket.blob(path)
        if blob.exists():
            content = blob.download_as_bytes()
            return base64.b64encode(content).decode('utf-8')
        else:
            raise FileNotFoundError(f"File '{path}' not found in bucket '{bucket_name}'.")
    except Exception as e:
        raise e

@app.tool()
async def list_gcs_objects(bucket_name: str, path: str = "") -> str:
    """Lists the contents of a GCS bucket or a directory. Returns a JSON list."""
    try:
        bucket = storage_client.get_bucket(bucket_name)
    except Exception as e:
        return json.dumps({"error": str(e)})

    prefix = path
    if prefix and not prefix.endswith('/'):
        prefix += '/'

    blobs = bucket.list_blobs(prefix=prefix, delimiter="/")
    items = []
    for b in blobs:
        if b.name != prefix:
            items.append(b.name)
    if hasattr(blobs, "prefixes") and blobs.prefixes:
        for p in blobs.prefixes:
            items.append(p)
    return json.dumps(items)

@app.tool()
async def delete_gcs_object(bucket_name: str, path: str) -> str:
    """Deletes an object from a GCS bucket."""
    try:
        bucket = storage_client.get_bucket(bucket_name)
        if path.endswith('/'):
            blobs_to_delete = list(bucket.list_blobs(prefix=path))
            if not blobs_to_delete:
                return f"Directory '{path}' is already empty or does not exist."
            for blob in blobs_to_delete:
                blob.delete()
            return f"Successfully deleted directory '{path}' and its contents."
        else:
            blob = bucket.blob(path)
            if not blob.exists():
                return f"Error: File '{path}' not found in bucket '{bucket_name}'."
            blob.delete()
            return f"File '{path}' successfully deleted."
    except NotFound:
        return f"Error: Bucket '{bucket_name}' not found."
    except Exception as e:
        return f"An error occurred: {e}"

@app.tool()
async def move_gcs_object(source_bucket_name: str, source_path: str, dest_bucket_name: str, dest_path: str) -> str:
    """Moves or renames an object."""
    try:
        source_bucket = storage_client.get_bucket(source_bucket_name)
        source_blob = source_bucket.blob(source_path)
        if not source_blob.exists():
            return f"Error: Source file '{source_path}' not found."
        dest_bucket = storage_client.get_bucket(dest_bucket_name)
        final_dest_path = dest_path
        if dest_path.endswith('/'):
            final_dest_path += os.path.basename(source_path)
        source_bucket.copy_blob(source_blob, dest_bucket, final_dest_path)
        source_blob.delete()
        return f"Successfully moved '{source_path}' to '{final_dest_path}'."
    except NotFound:
        return f"Error: One of the buckets was not found."
    except Exception as e:
        return f"An error occurred: {e}"

@app.tool()
async def delete_bucket(bucket_name: str, force: bool = False) -> str:
    """Deletes an entire GCS bucket."""
    try:
        bucket = storage_client.get_bucket(bucket_name)
        bucket.delete(force=force)
        return f"Bucket '{bucket_name}' has been deleted."
    except NotFound:
        return f"Error: Bucket '{bucket_name}' not found."
    except Exception as e:
        return f"An error occurred: {e}"

@app.tool()
async def get_mcp_documentation() -> str:
    """
    Retrieves the official documentation for all available tools on this MCP server.
    """
    try:
        with open("MCP_DOCUMENTATION.md", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Error: The documentation file 'MCP_DOCUMENTATION.md' was not found."
    except Exception as e:
        return f"An unexpected error occurred while reading the documentation: {e}"

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    logger.info(f"GCS MCP server started on port {port}")
    asyncio.run(
        app.run_async(
            transport="streamable-http", 
            host="0.0.0.0", 
            port=port,
        )
    )
