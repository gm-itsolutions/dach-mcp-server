# ─────────────────────────────────────────────────
# Gefährdungsbeurteilungs-MCP Server
# Multi-stage build: lean production image mit ffmpeg
# ─────────────────────────────────────────────────
FROM python:3.12-slim AS base

# System-Abhängigkeiten: ffmpeg für Video-Frames
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python-Dependencies installieren (Cache-Layer)
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[cli]" 2>/dev/null || pip install --no-cache-dir .

# Applikation kopieren
COPY src/ src/
COPY templates/ templates/

# Temporäres Verzeichnis für Video-Verarbeitung
RUN mkdir -p /tmp/processing

# Umgebungsvariablen
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=32400
ENV TEMPLATES_DIR=/app/templates
ENV TEMP_DIR=/tmp/processing
ENV PYTHONUNBUFFERED=1

EXPOSE 32400

# Healthcheck: prüft ob der HTTP-Server antwortet
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:32400/mcp')" || exit 1

CMD ["python", "-m", "src.server"]
