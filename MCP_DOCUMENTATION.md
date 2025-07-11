# GCS MCP Server Documentation

This document outlines the available tools for the GCS MCP Server.

---

### Tool: `create_bucket`

- **Description**: Creates a new Google Cloud Storage bucket. Bucket names must be globally unique.
- **Parameters**:
    - `bucket_name` (str): The unique name for the new bucket.
- **Returns**: (str) A confirmation message.

---

### Tool: `upload_file`

- **Description**: Uploads or overwrites a file in a GCS bucket.
- **Parameters**:
    - `bucket_name` (str): The name of the target bucket.
    - `path` (str): The full path for the object within the bucket (e.g., `folder/file.txt`).
    - `content` (bytes): The file content, which must be Base64-encoded by the client before sending.
- **Returns**: (str) A confirmation message.

---

### Tool: `read_gcs_file`

- **Description**: Reads the raw content of a file from a GCS bucket.
- **Parameters**:
    - `bucket_name` (str): The name of the bucket.
    - `path` (str): The full path of the object to read.
- **Returns**: (str) The file content, Base64-encoded.

---

### Tool: `list_gcs_objects`

- **Description**: Lists the contents of a GCS bucket or a specific directory within it.
- **Parameters**:
    - `bucket_name` (str): The name of the bucket.
    - `path` (str, optional): The directory path to list. If omitted, lists the root of the bucket.
- **Returns**: (str) A JSON-formatted string containing a list of object and directory names.

---

### Tool: `delete_gcs_object`

- **Description**: Deletes a file or a directory (including all its contents) from a GCS bucket.
- **Parameters**:
    - `bucket_name` (str): The name of the bucket.
    - `path` (str): The path of the object or directory to delete. To delete a directory, ensure the path ends with a `/`.
- **Returns**: (str) A confirmation message.

---

### Tool: `move_gcs_object`

- **Description**: Moves or renames an object within or between GCS buckets.
- **Parameters**:
    - `source_bucket_name` (str): The name of the source bucket.
    - `source_path` (str): The path of the object to move.
    - `dest_bucket_name` (str): The name of the destination bucket.
    - `dest_path` (str): The new path for the object.
- **Returns**: (str) A confirmation message.

---

### Tool: `delete_bucket`

- **Description**: Deletes an entire GCS bucket. This is irreversible.
- **Parameters**:
    - `bucket_name` (str): The name of the bucket to delete.
    - `force` (bool, optional): If set to `True`, it will delete a non-empty bucket and all its contents. Defaults to `False`.
- **Returns**: (str) A confirmation message.
