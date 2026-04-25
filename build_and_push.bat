@echo off
REM ==============================================================================
REM Build Docker image (with model files) and push to ECR
REM Chay tren may local - noi co model_trash/best.pt va model_liquid/best.pt
REM ==============================================================================

set AWS_ACCOUNT_ID=536322508586
set AWS_REGION=ap-southeast-1
set REPO_NAME=trash-classification
set ECR_URL=%AWS_ACCOUNT_ID%.dkr.ecr.%AWS_REGION%.amazonaws.com

REM Get git commit hash for tag
for /f "tokens=*" %%i in ('git rev-parse --short HEAD 2^>nul') do set IMAGE_TAG=%%i
if "%IMAGE_TAG%"=="" set IMAGE_TAG=latest

echo ============================================
echo   Build ^& Push Docker Image to ECR
echo ============================================

REM Check model files - at least one must exist
set HAS_MODEL=0
if exist "model_trash\best.pt" set HAS_MODEL=1
if exist "model_liquid\best.pt" set HAS_MODEL=1
if "%HAS_MODEL%"=="0" (
    echo ERROR: No model files found!
    echo Place at least one: model_trash\best.pt or model_liquid\best.pt
    exit /b 1
)

echo [1/4] Logging in to ECR...
aws ecr get-login-password --region %AWS_REGION% | docker login --username AWS --password-stdin %ECR_URL%

echo [2/4] Building Docker image...
docker build -t %REPO_NAME%:%IMAGE_TAG% -t %REPO_NAME%:latest .

echo [3/4] Tagging image...
docker tag %REPO_NAME%:%IMAGE_TAG% %ECR_URL%/%REPO_NAME%:%IMAGE_TAG%
docker tag %REPO_NAME%:latest %ECR_URL%/%REPO_NAME%:latest

echo [4/4] Pushing to ECR...
docker push %ECR_URL%/%REPO_NAME%:%IMAGE_TAG%
docker push %ECR_URL%/%REPO_NAME%:latest

echo.
echo Done! Image pushed:
echo   %ECR_URL%/%REPO_NAME%:%IMAGE_TAG%
echo   %ECR_URL%/%REPO_NAME%:latest
pause
