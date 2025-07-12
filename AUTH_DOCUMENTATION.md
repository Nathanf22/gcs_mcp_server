# GCS MCP Server Authentication Architecture

## Overview

The GCS MCP Server uses a flexible, token-based authentication system that delegates identity verification to a trusted, external **Authentication Gateway**. This design allows for two distinct modes of operation:

1.  **Authenticated Access (Recommended & Secure)**: For agents handling private, user-specific data.
2.  **Anonymous Access (Discouraged & Unsecured)**: For agents working with public, non-sensitive data.

The server's primary security principle is **data isolation**, which is strictly enforced in Authenticated mode.

---

## 1. Authenticated Access (Recommended)

This is the standard and secure mode for all operations involving user-specific data.

### How it Works

-   The agent must include an `Authorization` header with a `Bearer` token in its request to the MCP server.
-   The MCP server does not interpret this token directly. Instead, it forwards the token to the configured Authentication Gateway for validation.
-   The Gateway is the **single source of truth** for user identity. It validates the token and, if successful, returns the user's canonical, persistent `user_id` and their assigned `role` (e.g., `agent`, `agent-admin`).

### Data Isolation

If authentication is successful, the MCP server **automatically sandboxes all file operations**. Every file path is prefixed with the `user_id` provided by the Gateway.

-   An agent requesting to write to `reports/quarterly.pdf` for a user with `user_id` of `user-a-123` will actually write to `user-a-123/reports/quarterly.pdf`.
-   This ensures that an agent for one user can **never** see or access the files of another user.

---

## 2. Anonymous Access (Unsecured)

The server allows requests that do not contain an `Authorization` header. This mode is available but **strongly discouraged** for anything other than explicitly public data.

### How it Works

If no token is provided, the server operates in a public, shared space.

-   **No Data Isolation**: All file operations are performed in the root of the GCS bucket.
-   **Public by Default**: Any file created in this mode can be read, overwritten, or deleted by any other anonymous agent.
-   **No Access to Secure Data**: An anonymous agent has no ability to access any user-specific, sandboxed directories (e.g., `/user-a-123/`).

**WARNING**: This mode offers no data protection between different agents or systems using it. Use with extreme caution.

---

## Authenticated Request Workflow

1.  **Token Acquisition**: An agent first authenticates with the **Authentication Gateway** to obtain a short-lived access token.
2.  **MCP Request**: The agent makes a request to a tool on the MCP server, including the token in the `Authorization: Bearer <token>` header.
3.  **Token Validation**: The MCP server sends the token to the Gateway's validation endpoint (configured via an environment variable).
4.  **Gateway Response**:
    -   **On Success**: The Gateway responds with a `200 OK` and a JSON payload containing `{"user_id": "...", "role": "..."}`.
    -   **On Failure**: The Gateway responds with a `401 Unauthorized` error.
5.  **Execution**:
    -   If validation succeeds, the MCP server proceeds with the operation, enforcing the `user_id` sandbox.
    -   If validation fails, the MCP server rejects the request with a `401 Unauthorized` error.

## Server Configuration

The only security-related configuration required for the MCP server is the URL of the Gateway's validation endpoint, which should be set in an environment variable (e.g., `AUTH_GATEWAY_URL`).
