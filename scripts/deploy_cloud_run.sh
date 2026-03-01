#!/bin/bash
set -e

JOB_NAME="anime-pipeline-job"
REGION="us-central1"

if [ -z "$GCP_PROJECT_ID" ]; then
    echo "GCP_PROJECT_ID environment variable is not set."
    exit 1
fi

echo "Enabling Cloud Run and Cloud Build APIs..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com

echo "Building Docker image and pushing to Artifact Registry..."
# Note: For production, you should create an Artifact Registry repository. 
# Here we use the default gcr.io container registry for simplicity.
IMAGE_URL="gcr.io/${GCP_PROJECT_ID}/${JOB_NAME}:latest"

gcloud builds submit --tag "${IMAGE_URL}" .

echo "Creating/Updating Cloud Run Job..."
gcloud run jobs create "${JOB_NAME}" \\
    --image "${IMAGE_URL}" \\
    --region "${REGION}" \\
    --tasks 1 \\
    --max-retries 0 \\
    --task-timeout 60m \\
    --memory 4Gi \\
    --cpu 2 \\
    --set-env-vars "GCP_PROJECT_ID=${GCP_PROJECT_ID}"

echo "=========================================================="
echo "Deployment successful!"
echo "To execute a run, use the following command:"
echo "gcloud run jobs execute ${JOB_NAME} --region ${REGION}"
echo "=========================================================="
