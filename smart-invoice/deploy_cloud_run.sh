#!/bin/bash
# ==============================================================================
# GCP Cloud Run Deployment Script for Smart Freelance Invoice & Risk Platform
# ==============================================================================

set -e

SERVICE_NAME="smart-invoice"
REGION="us-central1"

echo "🚀 Deploying ${SERVICE_NAME} to Google Cloud Run from source..."
echo "📍 Region: ${REGION}"

# Deploy directly from source directory using Cloud Buildpacks / Dockerfile
gcloud run deploy ${SERVICE_NAME} \
    --source . \
    --region ${REGION} \
    --allow-unauthenticated \
    --set-env-vars="GCS_BUCKET_NAME=smart-invoice-pdfs-extreme-gecko-472506-s9" \
    --set-secrets="SECRET_KEY=SECRET_KEY:latest"

echo "✅ Cloud Run deployment complete! Access your live service URL above."
