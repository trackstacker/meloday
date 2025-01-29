# Use a lightweight Python image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed for any of your Python packages)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy application files
COPY meloday.py requirements.txt /app/
COPY covers/ /app/covers/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set Python to run in unbuffered mode (better for logging)
ENV PYTHONUNBUFFERED=1

# Declare the required environment variables
ENV PLEX_SERVER_URL=""
ENV PLEX_AUTH_TOKEN=""
ENV OPENAI_API_KEY=""

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import sys, os; sys.exit(0 if all([os.getenv('PLEX_SERVER_URL'), os.getenv('PLEX_AUTH_TOKEN'), os.getenv('OPENAI_API_KEY')]) else 1)"

# Run the script
CMD ["python", "meloday.py"]