# Self-contained Dockerfile with Ollama + escape-room game
# Everything needed to run locally, no external services

FROM ollama/ollama:latest as base

# Install Python and build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir --break-system-packages -r requirements.txt

# Copy application code
COPY . .

# Create startup script that runs Ollama and the game
RUN echo '#!/bin/bash' > /app/entrypoint.sh && \
    echo 'set -e' >> /app/entrypoint.sh && \
    echo '' >> /app/entrypoint.sh && \
    echo 'echo "Starting Ollama service..."' >> /app/entrypoint.sh && \
    echo 'ollama serve &' >> /app/entrypoint.sh && \
    echo 'OLLAMA_PID=$!' >> /app/entrypoint.sh && \
    echo '' >> /app/entrypoint.sh && \
    echo 'echo "Waiting for Ollama to start..."' >> /app/entrypoint.sh && \
    echo 'for i in {1..60}; do' >> /app/entrypoint.sh && \
    echo '    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then' >> /app/entrypoint.sh && \
    echo '        echo "Ollama is ready!"' >> /app/entrypoint.sh && \
    echo '        break' >> /app/entrypoint.sh && \
    echo '    fi' >> /app/entrypoint.sh && \
    echo '    if [ $i -eq 60 ]; then' >> /app/entrypoint.sh && \
    echo '        echo "Ollama failed to start"' >> /app/entrypoint.sh && \
    echo '        kill $OLLAMA_PID 2>/dev/null || true' >> /app/entrypoint.sh && \
    echo '        exit 1' >> /app/entrypoint.sh && \
    echo '    fi' >> /app/entrypoint.sh && \
    echo '    sleep 1' >> /app/entrypoint.sh && \
    echo 'done' >> /app/entrypoint.sh && \
    echo '' >> /app/entrypoint.sh && \
    echo 'echo "Checking for llama3.1:8b model..."' >> /app/entrypoint.sh && \
    echo 'if ! ollama list | grep -q "llama3.1:8b"; then' >> /app/entrypoint.sh && \
    echo '    echo "Pulling llama3.1:8b model (this may take several minutes on first run)..."' >> /app/entrypoint.sh && \
    echo '    ollama pull llama3.1:8b' >> /app/entrypoint.sh && \
    echo 'else' >> /app/entrypoint.sh && \
    echo '    echo "llama3.1:8b model already available"' >> /app/entrypoint.sh && \
    echo 'fi' >> /app/entrypoint.sh && \
    echo '' >> /app/entrypoint.sh && \
    echo 'echo "Model ready! Starting game..."' >> /app/entrypoint.sh && \
    echo 'cd /app' >> /app/entrypoint.sh && \
    echo 'PYTHONPATH=/app OLLAMA_BASE_URL=http://localhost:11434 python3 game/loop.py --evaluator-type llm --narrator-type llm --level between-floors.yaml' >> /app/entrypoint.sh && \
    echo '' >> /app/entrypoint.sh && \
    echo 'kill $OLLAMA_PID 2>/dev/null || true' >> /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    OLLAMA_BASE_URL=http://localhost:11434

# Expose Ollama API port (optional, for external access)
EXPOSE 11434

# Default command
ENTRYPOINT ["/app/entrypoint.sh"]
