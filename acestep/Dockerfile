FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
RUN pip install --no-cache-dir uv

# Copy startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Create directories
RUN mkdir -p /app/checkpoints /app/lora

EXPOSE 8001

HEALTHCHECK --interval=10s --timeout=5s --retries=10 --start-period=30s \
  CMD curl -f http://localhost:8001/health || exit 1

CMD ["/app/start.sh"]
