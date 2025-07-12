import asyncio
import logging
import os
import base64
import json
import httpx
from functools import wraps
from dataclasses import dataclass

from google.cloud import storage
from google.api_core.exceptions import Conflict, NotFound
from fastmcp import FastMCP
from fastmcp.resources import BinaryResource, TextResource

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)

# --- Authentication Configuration ---
AUTH_GATEWAY_URL = os.environ.get("AUTH_GATEWAY_URL") # e.g., "http://localhost:8000/validate-token"
if not AUTH_GATEWAY_URL:
    logger.warning("AUTH_GATEWAY_URL is not set. Authentication is disabled.")

@dataclass
class AuthInfo:
    """Holds authentication information for a request."""
    user_id: str
    role: str

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

# --- Storage Client Initialization ---
# Check for a local service account key first, otherwise use default credentials.
SERVICE_ACCOUNT_KEY_PATH = "service_account_key.json"
if os.path.exists(SERVICE_ACCOUNT_KEY_PATH):
    logger.info(f"Using local service account key: {SERVICE_ACCOUNT_KEY_PATH}")
    storage_client = storage.Client.from_service_account_json(SERVICE_ACCOUNT_KEY_PATH)
else:
    logger.info("No local service account key found. Using default credentials.")
    storage_client = storage.Client()

# --- Authentication Decorator ---

def authenticated_tool(func):
    """
    Decorator that handles authentication and injects user info.
    It replaces the original tool function with a wrapper that performs
    authentication before calling the original function.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        auth_info = kwargs.get("auth_info")

        # If auth_info is not passed directly, try to get it from the request.
        if not auth_info:
            # The first positional argument is expected to be the request object.
            if not args:
                return "Error: Request object not provided."
            
            req = args[0]
            auth_header = req.headers.get("Authorization")

            if AUTH_GATEWAY_URL and auth_header:
                if auth_header.startswith("Bearer "):
                    token = auth_header.split(" ")[1]
                    try:
                        async with httpx.AsyncClient() as client:
                            # Mocked response for demonstration:
                            if token == "TEST_TOKEN_ADMIN":
                                response = httpx.Response(200, json={"user_id": "user-123-admin", "role": "agent-admin"})
                            elif token == "TEST_TOKEN_USER":
                                response = httpx.Response(200, json={"user_id": "user-456-basic", "role": "agent"})
                            else:
                                response = httpx.Response(401, json={"error": "Invalid token"})

                            if response.status_code == 200:
                                data = response.json()
                                auth_info = AuthInfo(user_id=data["user_id"], role=data["role"])
                                logger.info(f"Authenticated user {auth_info.user_id} with role {auth_info.role}")
                            else:
                                return f"Authentication failed: {response.json().get('error', 'Unknown error')}"
                    except httpx.RequestError as e:
                        return f"Error contacting authentication gateway: {e}"
                else:
                    return "Invalid Authorization header format. Must be 'Bearer <token>'."
        
        # Remove auth_info from kwargs if it was passed, to avoid conflicts.
        kwargs.pop("auth_info", None)
        
        # Call the original tool function with the auth_info
        return await func(auth_info=auth_info, **kwargs)

    # Replace the original tool's endpoint with our wrapper
    return app.tool()(wrapper)

# --- Tools ---

@authenticated_tool
async def upload_file(auth_info: AuthInfo, bucket_name: str, path: str, content: bytes) -> str:
    """Uploads or overwrites a file in a GCS bucket. Supports user sandboxing."""
    final_path = path
    if auth_info:
        # Sandbox the path within the user's directory
        final_path = f"{auth_info.user_id}/{path}"
        logger.info(f"Sandboxing path for user {auth_info.user_id}: '{path}' -> '{final_path}'")
    else:
        logger.warning(f"Operating in anonymous mode. Path: '{path}'")

    try:
        bucket = storage_client.get_bucket(bucket_name)
        blob = bucket.blob(final_path)
        decoded_content = base64.b64decode(content)
        blob.upload_from_string(decoded_content)
        return f"File '{path}' successfully uploaded to bucket '{bucket_name}'."
    except NotFound:
        return f"Error: Bucket '{bucket_name}' not found."
    except Exception as e:
        return f"An error occurred: {e}"

@authenticated_tool
async def create_bucket(auth_info: AuthInfo, bucket_name: str) -> str:
    """Creates a new Google Cloud Storage bucket. Requires 'agent-admin' role."""
    if not auth_info or auth_info.role != "agent-admin":
        return "Error: This operation requires 'agent-admin' role."
    try:
        bucket = storage_client.create_bucket(bucket_name)
        return f"Successfully created bucket '{bucket.name}'."
    except Conflict:
        return f"Bucket '{bucket_name}' already exists."
    except Exception as e:
        return f"Failed to create bucket '{bucket_name}': {e}"

@authenticated_tool
async def read_gcs_file(auth_info: AuthInfo, bucket_name: str, path: str) -> str:
    """
    Reads the content of a file from a GCS bucket.
    Returns the file content as a Base64-encoded string.
    """
    final_path = path
    if auth_info:
        final_path = f"{auth_info.user_id}/{path}"
    
    try:
        bucket = storage_client.get_bucket(bucket_name)
        blob = bucket.blob(final_path)
        if blob.exists():
            content = blob.download_as_bytes()
            return base64.b64encode(content).decode('utf-8')
        else:
            raise FileNotFoundError(f"File '{path}' not found in bucket '{bucket_name}'.")
    except Exception as e:
        raise e

@authenticated_tool
async def list_gcs_objects(auth_info: AuthInfo, bucket_name: str, path: str = "") -> str:
    """Lists the contents of a GCS bucket or a directory. Returns a JSON list."""
    final_path = path
    if auth_info:
        final_path = f"{auth_info.user_id}/{path}"

    try:
        bucket = storage_client.get_bucket(bucket_name)
    except Exception as e:
        return json.dumps({"error": str(e)})

    prefix = final_path
    if prefix and not prefix.endswith('/'):
        prefix += '/'

    blobs = bucket.list_blobs(prefix=prefix, delimiter="/")
    items = []
    
    # Strip the user_id prefix for user-facing output
    strip_prefix = f"{auth_info.user_id}/" if auth_info else ""
    
    for b in blobs:
        if b.name != prefix:
            items.append(b.name.removeprefix(strip_prefix))
            
    if hasattr(blobs, "prefixes") and blobs.prefixes:
        for p in blobs.prefixes:
            items.append(p.removeprefix(strip_prefix))
            
    return json.dumps(items)

@authenticated_tool
async def delete_gcs_object(auth_info: AuthInfo, bucket_name: str, path: str) -> str:
    """Deletes an object from a GCS bucket."""
    final_path = path
    if auth_info:
        final_path = f"{auth_info.user_id}/{path}"

    try:
        bucket = storage_client.get_bucket(bucket_name)
        if final_path.endswith('/'):
            blobs_to_delete = list(bucket.list_blobs(prefix=final_path))
            if not blobs_to_delete:
                return f"Directory '{path}' is already empty or does not exist."
            for blob in blobs_to_delete:
                blob.delete()
            return f"Successfully deleted directory '{path}' and its contents."
        else:
            blob = bucket.blob(final_path)
            if not blob.exists():
                return f"Error: File '{path}' not found in bucket '{bucket_name}'."
            blob.delete()
            return f"File '{path}' successfully deleted."
    except NotFound:
        return f"Error: Bucket '{bucket_name}' not found."
    except Exception as e:
        return f"An error occurred: {e}"

@authenticated_tool
async def move_gcs_object(auth_info: AuthInfo, source_bucket_name: str, source_path: str, dest_bucket_name: str, dest_path: str) -> str:
    """Moves or renames an object."""
    final_source_path = source_path
    final_dest_path = dest_path

    if auth_info:
        final_source_path = f"{auth_info.user_id}/{source_path}"
        final_dest_path = f"{auth_info.user_id}/{dest_path}"

    try:
        source_bucket = storage_client.get_bucket(source_bucket_name)
        source_blob = source_bucket.blob(final_source_path)
        if not source_blob.exists():
            return f"Error: Source file '{source_path}' not found."
        
        dest_bucket = storage_client.get_bucket(dest_bucket_name)
        
        # Handle case where dest_path is a directory
        if dest_path.endswith('/'):
            final_dest_path += os.path.basename(source_path)

        source_bucket.copy_blob(source_blob, dest_bucket, final_dest_path)
        source_blob.delete()
        return f"Successfully moved '{source_path}' to '{dest_path}'."
    except NotFound:
        return f"Error: One of the buckets was not found."
    except Exception as e:
        return f"An error occurred: {e}"

@authenticated_tool
async def delete_bucket(auth_info: AuthInfo, bucket_name: str, force: bool = False) -> str:
    """Deletes an entire GCS bucket. Requires 'agent-admin' role."""
    if not auth_info or auth_info.role != "agent-admin":
        return "Error: This operation requires 'agent-admin' role."
    try:
        bucket = storage_client.get_bucket(bucket_name)
        bucket.delete(force=force)
        return f"Bucket '{bucket_name}' has been deleted."
    except NotFound:
        return f"Error: Bucket '{bucket_name}' not found."
    except Exception as e:
        return f"An error occurred: {e}"

@authenticated_tool
async def get_bucket_permissions(auth_info: AuthInfo, bucket_name: str) -> str:
    """
    Lists all IAM roles and members for a given bucket.
    Requires 'agent-admin' role. Returns a JSON string.
    """
    if not auth_info or auth_info.role != "agent-admin":
        return "Error: This operation requires 'agent-admin' role."

    try:
        bucket = storage_client.get_bucket(bucket_name)
        policy = bucket.get_iam_policy(requested_policy_version=3)
        
        permissions = []
        if policy.bindings:
            for binding in policy.bindings:
                role = binding.get("role")
                members = binding.get("members")
                if role and members:
                    for member in members:
                        permissions.append({"role": role, "member": member})
        
        return json.dumps(permissions)

    except NotFound:
        return f"Error: Bucket '{bucket_name}' not found."
    except Exception as e:
        return f"An error occurred while fetching permissions: {e}"

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

def main():
    """Main entry point for the server."""
    port = int(os.getenv("PORT", 8080))
    logger.info(f"GCS MCP server started on port {port}")
    asyncio.run(
        app.run_async(
            transport="streamable-http",
            host="0.0.0.0",
            port=port,
        )
    )

if __name__ == "__main__":
    main()
