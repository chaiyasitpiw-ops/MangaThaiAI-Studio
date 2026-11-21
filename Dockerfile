# MangaThaiAI-Studio: 24/7 Free Cloud Deployment (Hugging Face Spaces / Docker)
FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    HOME=/home/user

# Install system dependencies: OpenCV, Raqm/HarfBuzz for Thai complex text shaping, Thai fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libraqm0 \
    libharfbuzz0b \
    libfribidi0 \
    fonts-thai-tlwg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set up non-root user (UID 1000 required by Hugging Face Spaces)
RUN useradd -m -u 1000 user
WORKDIR /home/user/app

# Pre-install Python dependencies for maximum caching speed
COPY --chown=user:user requirements-control-center.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-control-center.txt \
    rapidocr_onnxruntime \
    opencv-python-headless \
    wordsegment \
    qrcode[pil] \
    beautifulsoup4 \
    lxml \
    curl_cffi

# Copy application files
COPY --chown=user:user . .

# Ensure cache and runtime directories exist with proper write permissions
RUN mkdir -p data/inputs data/outputs/cache control_center/static && \
    chown -R user:user /home/user

USER user

EXPOSE 7860

# Run FastAPI app dynamically on whatever PORT is assigned by the cloud platform
CMD ["sh", "-c", "uvicorn control_center.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
