# GCS MCP Server Roadmap

This document outlines planned features to enhance the capabilities of the GCS MCP server, making it more powerful and intuitive for AI agents.

## 1. Enhanced Discovery and Search

To allow agents to find resources without knowing their exact paths.

- **`search_files(bucket_name, glob_pattern)`**: A tool to find files across an entire bucket using glob patterns (e.g., `**/sales_report_*.csv`). This is the highest priority feature.
- **Pagination for `list_gcs_objects`**: Enhance the listing tool to accept `page_size` and `page_token` arguments to handle directories with thousands of objects gracefully.

## 2. Metadata Operations

To enable agents to get information *about* a file, not just its content.

- **`get_object_metadata(bucket_name, path)`**: A tool to retrieve key metadata for a file or directory, such as:
    - `size` (in bytes)
    - `updated_at` (timestamp)
    - `created_at` (timestamp)
    - `content_type` (MIME type)
- **`object_exists(bucket_name, path)`**: A lightweight, low-cost tool to quickly check for the existence of an object without the overhead of a read operation.

## 3. Advanced File Operations

For more complex file manipulations.

- **`read_partial_file(bucket_name, path, offset, length)`**: A tool to read a specific chunk of a large file (e.g., the first 100 lines of a 10GB log file).
- **`copy_object(source_bucket, source_path, dest_bucket, dest_path)`**: A tool for a pure copy operation, which is a missing counterpart to the current `move` tool.
- **`get_signed_url(bucket_name, path, expiration_minutes)`**: A tool to generate a temporary, secure, shareable URL for a private GCS object.

## 4. Permissions Management (IAM)

For more autonomous agents that might manage infrastructure access.

- **`get_bucket_permissions(bucket_name)`**: Lists all users and roles associated with a bucket.
- **`grant_user_access(bucket_name, user_email, role)`**: Grants a specific role (e.g., `objectViewer`) to a user for a bucket.
- **`revoke_user_access(bucket_name, user_email, role)`**: Removes a role from a user for a bucket.
