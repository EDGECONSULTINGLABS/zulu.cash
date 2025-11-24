FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libsqlcipher-dev \
    libsndfile1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install package
RUN pip install -e .

# Create necessary directories
RUN mkdir -p /app/data/models/whisper \
    /app/data/backups \
    /app/data/temp \
    /app/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV ZULU_CONFIG=/app/config/default.yaml

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python cli.py health || exit 1

# Entry point
ENTRYPOINT ["python", "cli.py"]
CMD ["health"]
