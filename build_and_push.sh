#!/bin/bash
#==============================================================================
# Build Docker image (with model files) and push to ECR
# Chạy trên máy local - nơi có model_trash/best.pt và model_liquid/best.pt
#==============================================================================

set -e

AWS_ACCOUNT_ID="536322508586"
AWS_REGION="ap-southeast-1"
REPO_NAME="trash-classification"
ECR_URL="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_TAG=$(git rev-parse --short HEAD 2>/dev/null || echo "latest")

echo "============================================"
echo "  Build & Push Docker Image to ECR"
echo "============================================"

# Check model files exist
if [ ! -f "model_trash/best.pt" ] && [ ! -f "model_liquid/best.pt" ]; then
    echo "ERROR: No model files found!"
    echo "Place at least one: model_trash/best.pt or model_liquid/best.pt"
    exit 1
fi

echo "[1/4] Logging in to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_URL}

echo "[2/4] Building Docker image..."
docker build -t ${REPO_NAME}:${IMAGE_TAG} -t ${REPO_NAME}:latest .

echo "[3/4] Tagging image..."
docker tag ${REPO_NAME}:${IMAGE_TAG} ${ECR_URL}/${REPO_NAME}:${IMAGE_TAG}
docker tag ${REPO_NAME}:latest ${ECR_URL}/${REPO_NAME}:latest

echo "[4/4] Pushing to ECR..."
docker push ${ECR_URL}/${REPO_NAME}:${IMAGE_TAG}
docker push ${ECR_URL}/${REPO_NAME}:latest

echo ""
echo "Done! Image pushed:"
echo "  ${ECR_URL}/${REPO_NAME}:${IMAGE_TAG}"
echo "  ${ECR_URL}/${REPO_NAME}:latest"
