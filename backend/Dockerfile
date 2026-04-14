FROM python:3.11-slim

# Ensure Python stdout/stderr stream to the container log without buffering.
# This is critical for diagnosing Railway startup hangs — without it, Python
# tracebacks can be stuck in the stderr buffer when the process dies, leaving
# the log showing only a pymongo UserWarning and nothing else.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies needed by some Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libffi-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY . .

EXPOSE 8001

# Health check via Python stdlib — no curl/wget needed in slim image
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8001}/health')" || exit 1

# --workers 1: Railway handles horizontal scaling via replica count. Running
# 2 uvicorn workers in one replica doubles memory use and makes startup hangs
# twice as hard to diagnose (each worker runs lifespan independently).
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-8001} --workers 1
