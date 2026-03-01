#!/bin/bash
set -e

echo "Setting up Google Cloud Project for Anime Pipeline..."

if [ -z "$GCP_PROJECT_ID" ]; then
    echo "GCP_PROJECT_ID environment variable is not set."
    echo "Please set it before running this script."
    exit 1
fi

gcloud config set project "$GCP_PROJECT_ID"

echo "Enabling Vertex AI API..."
gcloud services enable aiplatform.googleapis.com

echo "Setup complete!"
