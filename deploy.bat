@echo off
rem
rem This script automates the deployment of the GCS MCP Server to Google Cloud Run on Windows.
rem
rem Prerequisites:
rem 1. Google Cloud SDK (`gcloud`) is installed and in your PATH.
rem 2. You are authenticated (`gcloud auth login`).
rem 3. The user running the script has the necessary permissions (e.g., Project Owner,
rem    or roles like Artifact Registry Administrator, Cloud Build Editor, Cloud Run Admin).

setlocal

rem --- Configuration ---
echo ">>> Detecting active Google Cloud project..."
for /f "tokens=*" %%i in ('gcloud config get-value project') do set PROJECT_ID=%%i
if not defined PROJECT_ID (
    echo "ERROR: No active Google Cloud project found."
    echo "Please set a project using 'gcloud config set project YOUR_PROJECT_ID'"
    exit /b 1
)

set "REGION=us-central1"
set "REPO_NAME=remote-mcp-servers"
set "SERVICE_NAME=gcs-mcp-server"
set "IMAGE_NAME=%SERVICE_NAME%"

rem Construct the full image tag for Artifact Registry.
set "IMAGE_TAG=%REGION%-docker.pkg.dev/%PROJECT_ID%/%REPO_NAME%/%IMAGE_NAME%:latest"

rem --- Deployment Steps ---

echo --- Starting Deployment to Google Cloud Run ---
echo Project ID: %PROJECT_ID%
echo Region: %REGION%
echo Service Name: %SERVICE_NAME%
echo Image Tag: %IMAGE_TAG%
echo.

rem 1. Enable required Google Cloud services
echo ">>> Step 1: Enabling required Google Cloud APIs..."
gcloud services enable ^
    artifactregistry.googleapis.com ^
    cloudbuild.googleapis.com ^
    run.googleapis.com ^
    --project="%PROJECT_ID%" || exit /b
echo "APIs enabled successfully."
echo.

rem 2. Create Artifact Registry repository if it doesn't exist
echo ">>> Step 2: Checking for Artifact Registry repository '%REPO_NAME%'..."
gcloud artifacts repositories describe "%REPO_NAME%" --location="%REGION%" --project="%PROJECT_ID%" >nul 2>&1
if %errorlevel% neq 0 (
    echo "Repository not found. Creating it now..."
    gcloud artifacts repositories create "%REPO_NAME%" ^
        --repository-format=docker ^
        --location="%REGION%" ^
        --description="Repository for remote MCP servers" ^
        --project="%PROJECT_ID%" || exit /b
    echo "Repository created successfully."
) else (
    echo "Repository already exists."
)
echo.

rem 3. Build the container image using Cloud Build and push to Artifact Registry
echo ">>> Step 3: Building container image with Cloud Build..."
gcloud builds submit . --tag="%IMAGE_TAG%" --region="%REGION%" --project="%PROJECT_ID%" || exit /b
echo "Image built and pushed successfully."
echo.

rem 4. Deploy the container image to Cloud Run
echo ">>> Step 4: Deploying service '%SERVICE_NAME%' to Cloud Run..."
gcloud run deploy "%SERVICE_NAME%" ^
    --image="%IMAGE_TAG%" ^
    --region="%REGION%" ^
    --no-allow-unauthenticated ^
    --project="%PROJECT_ID%" || exit /b
echo "Service deployed successfully."
echo.

echo --- Deployment Complete ---
for /f "tokens=*" %%i in ('gcloud run services describe %SERVICE_NAME% --region=%REGION% --project=%PROJECT_ID% --format="value(status.url)"') do set SERVICE_URL=%%i
echo Your GCS MCP Server is now running at: %SERVICE_URL%
echo To connect your local MCP client, run the Cloud Run proxy:
echo gcloud run services proxy %SERVICE_NAME% --region=%REGION% --project=%PROJECT_ID%

endlocal
