#!/usr/bin/env bash
# Inicia o ChromaDB via Podman em background na porta 8001
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$SCRIPT_DIR/storage/chroma"

echo "📦 Iniciando container ChromaDB via Podman na porta 8001..."
podman run -d \
  --name reductor_chromadb \
  -p 8001:8000 \
  -v "$SCRIPT_DIR/storage/chroma:/chroma/chroma:Z" \
  --replace \
  docker.io/chromadb/chroma:latest run --host 0.0.0.0 --port 8000 --path /chroma/chroma

echo "⏳ Aguardando ChromaDB inicializar..."
until curl -s http://127.0.0.1:8001/api/v2/heartbeat > /dev/null 2>&1; do
  sleep 1
done

echo "✅ ChromaDB rodando perfeitamente via Podman em http://127.0.0.1:8001"
