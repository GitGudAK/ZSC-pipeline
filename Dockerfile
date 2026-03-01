FROM python:3.11-slim

# Install system dependencies including ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \\
    ffmpeg \\
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY pyproject.toml .
# Normally, we'd copy the whole project and `pip install -e .` but for deployment
# we want a standard install
COPY src/ ./src/
COPY templates/ ./templates/
RUN pip install --no-cache-dir google-genai pydantic click ffmpeg-python aiohttp pyyaml google-cloud-storage

# Set execution entrypoint
ENTRYPOINT ["python", "-m", "src.main"]
