FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create model directories
RUN mkdir -p model_trash model_liquid

# Copy model files if they exist (use wildcard - won't fail if missing)
COPY model_trash* model_liquid* /tmp/models/
RUN if [ -f /tmp/models/model_trash/best.pt ]; then cp /tmp/models/model_trash/best.pt model_trash/; echo "Copied model_trash/best.pt"; fi && \
    if [ -f /tmp/models/model_liquid/best.pt ]; then cp /tmp/models/model_liquid/best.pt model_liquid/; echo "Copied model_liquid/best.pt"; fi && \
    rm -rf /tmp/models

# Copy application code
COPY config.py main.py models.py run.py ./
COPY services/ services/
COPY repositories/ repositories/
COPY templates/ templates/
COPY static/ static/

# Create runtime directories
RUN mkdir -p uploads database logs

EXPOSE 8000

CMD ["python", "run.py"]
