# deploy.py
import subprocess
import sys
import json
import shutil

# --- Configuration ---
# Please configure these variables before running the script.
GCP_PROJECT_ID = ""  # LEAVE BLANK TO DETECT FROM GCLOUD CLI
REGION = "us-central1"
REPO_NAME = "remote-mcp-servers"
SERVICE_NAME = "gcs-mcp-server"
IMAGE_NAME = SERVICE_NAME

# --- Script ---

GCLOUD_PATH = None

def find_gcloud():
    """Finds the full path to the gcloud executable."""
    global GCLOUD_PATH
    GCLOUD_PATH = shutil.which('gcloud')
    if GCLOUD_PATH is None:
        print("ERROR: 'gcloud' executable not found in your system's PATH.")
        print("Please ensure the Google Cloud SDK is installed and that its 'bin' directory is in your PATH.")
        sys.exit(1)
    print(f"Found gcloud at: {GCLOUD_PATH}")

def run_command(command, capture_output=False):
    """Executes a shell command and exits if it fails."""
    # Prepend the full path to the gcloud executable
    command[0] = GCLOUD_PATH
    
    print(f"--- Running command: {' '.join(command)}")
    try:
        process = subprocess.run(
            command,
            check=True,
            text=True,
            capture_output=capture_output,
            encoding='utf-8',
            shell=True # Use shell=True on Windows to properly handle .cmd files
        )
        if capture_output:
            return process.stdout.strip()
        return None
    except FileNotFoundError as e:
        print(f"ERROR: Command not found: {e.filename}. Is gcloud installed and in your PATH?")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Command failed with exit code {e.returncode}.")
        if e.stdout:
            print(f"--- STDOUT ---\n{e.stdout}")
        if e.stderr:
            print(f"--- STDERR ---\n{e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

def get_project_id():
    """Detects and returns the active Google Cloud project ID."""
    print(">>> Detecting active Google Cloud project...")
    project_id = run_command(["gcloud", "config", "get-value", "project"], capture_output=True)
    if not project_id:
        print("ERROR: No active Google Cloud project found.")
        print("Please set one using 'gcloud config set project YOUR_PROJECT_ID'")
        sys.exit(1)
    return project_id

def main():
    """Main function to run the deployment process."""
    find_gcloud() # Find the gcloud path at the beginning

    global GCP_PROJECT_ID
    if not GCP_PROJECT_ID:
        GCP_PROJECT_ID = get_project_id()

    image_tag = f"{REGION}-docker.pkg.dev/{GCP_PROJECT_ID}/{REPO_NAME}/{IMAGE_NAME}:latest"

    print("\n--- Starting Deployment to Google Cloud Run ---")
    print(f"Project ID:   {GCP_PROJECT_ID}")
    print(f"Region:       {REGION}")
    print(f"Service Name: {SERVICE_NAME}")
    print(f"Image Tag:    {image_tag}")
    print("-------------------------------------------------")

    # 1. Enable required Google Cloud services
    print("\n>>> Step 1: Enabling required Google Cloud APIs...")
    run_command([
        "gcloud", "services", "enable",
        "artifactregistry.googleapis.com",
        "cloudbuild.googleapis.com",
        "run.googleapis.com",
        f"--project={GCP_PROJECT_ID}"
    ])
    print("APIs enabled successfully.")

    # 2. Create Artifact Registry repository if it doesn't exist
    print(f"\n>>> Step 2: Checking for Artifact Registry repository '{REPO_NAME}'...")
    repo_check_command = [
        GCLOUD_PATH, "artifacts", "repositories", "describe", REPO_NAME,
        f"--location={REGION}",
        f"--project={GCP_PROJECT_ID}"
    ]
    try:
        # We call subprocess.run directly here to handle the error case locally
        # without exiting the entire script, as run_command() would.
        subprocess.run(
            repo_check_command,
            check=True,
            text=True,
            capture_output=True, # Suppress stdout/stderr on success
            encoding='utf-8',
            shell=True
        )
        print("Repository already exists.")
    except subprocess.CalledProcessError as e:
        # A non-zero exit code means the repository does not exist.
        if "NOT_FOUND" in e.stderr:
            print("Repository not found. Creating it now...")
            run_command([
                "gcloud", "artifacts", "repositories", "create", REPO_NAME,
                "--repository-format=docker",
                f"--location={REGION}",
                "--description=Repository for remote MCP servers",
                f"--project={GCP_PROJECT_ID}"
            ])
            print("Repository created successfully.")
        else:
            # Another error occurred. Print it and exit.
            print(f"ERROR: Failed to check for repository with exit code {e.returncode}.")
            if e.stdout:
                print(f"--- STDOUT ---\n{e.stdout}")
            if e.stderr:
                print(f"--- STDERR ---\n{e.stderr}")
            sys.exit(1)


    # 3. Build the container image using Cloud Build
    print("\n>>> Step 3: Building container image with Cloud Build...")
    run_command([
        "gcloud", "builds", "submit", ".",
        f"--tag={image_tag}",
        f"--project={GCP_PROJECT_ID}"
    ])
    print("Image built and pushed successfully.")

    # 4. Deploy the container image to Cloud Run
    print(f"\n>>> Step 4: Deploying service '{SERVICE_NAME}' to Cloud Run...")
    run_command([
        "gcloud", "run", "deploy", SERVICE_NAME,
        f"--image={image_tag}",
        f"--region={REGION}",
        "--no-allow-unauthenticated",
        f"--project={GCP_PROJECT_ID}",
        "--quiet"
    ])
    print("Service deployed successfully.")

    # 5. Get the service URL
    print("\n--- Deployment Complete ---")
    service_url = run_command([
        "gcloud", "run", "services", "describe", SERVICE_NAME,
        f"--region={REGION}",
        f"--project={GCP_PROJECT_ID}",
        "--format=value(status.url)"
    ], capture_output=True)

    print(f"Your GCS MCP Server is now running at: {service_url}")
    print("To connect your local MCP client, run the Cloud Run proxy:")
    print(f"gcloud run services proxy {SERVICE_NAME} --region={REGION} --project={GCP_PROJECT_ID}")

if __name__ == "__main__":
    main()
