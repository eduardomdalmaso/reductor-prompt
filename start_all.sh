#!/usr/bin/env bash
# ==============================================================================
# Script de Inicialização Completa do ReductorPrompt
# Orquestra: Podman (ChromaDB), Ollama, PM2 (API, Web, Relatórios)
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================================"
echo "🚀 INICIANDO ECOSSISTEMA COMPLETO REDUCTOR-PROMPT"
echo "======================================================================"

# 1. Iniciar ChromaDB via Podman
echo "📦 [1/4] Verificando e iniciando ChromaDB (Podman)..."
mkdir -p "$SCRIPT_DIR/storage/chroma"

if ! podman ps --format "{{.Names}}" | grep -q "reductor_chromadb"; then
    echo "  -> Subindo container reductor_chromadb na porta 8001..."
    podman run -d \
      --name reductor_chromadb \
      -p 8001:8000 \
      -v "$SCRIPT_DIR/storage/chroma:/chroma/chroma:Z" \
      --replace \
      docker.io/chromadb/chroma:latest run --host 0.0.0.0 --port 8000 --path /chroma/chroma
fi

echo "  -> Aguardando ChromaDB responder em http://127.0.0.1:8001..."
until curl -s http://127.0.0.1:8001/api/v2/heartbeat > /dev/null 2>&1; do
    sleep 1
done
echo "  ✅ ChromaDB ONLINE em http://127.0.0.1:8001"

# 2. Iniciar serviços via PM2 (Ollama, API, Web, Gerar Relatório)
echo "⚡ [2/4] Iniciando processos via PM2..."
pm2 start ecosystem.config.cjs

# 3. Aguardar Ollama inicializar e verificar modelos
echo "🧠 [3/4] Verificando Ollama Server..."
until curl -s http://127.0.0.1:11434/api/tags > /dev/null 2>&1; do
    sleep 1
done
echo "  ✅ Ollama Server ONLINE em http://127.0.0.1:11434"

# Garantir modelos nomic-embed-text e qwen2.5:14b
echo "  -> Verificando modelos necessários no Ollama..."
if ! /home/hades/.local/bin/ollama list | grep -q "nomic-embed-text"; then
    echo "  -> Baixando modelo de embeddings nomic-embed-text..."
    /home/hades/.local/bin/ollama pull nomic-embed-text
fi

# 4. Aguardar API FastAPI
echo "🌐 [4/4] Verificando ReductorPrompt API..."
until curl -s http://127.0.0.1:8002/health > /dev/null 2>&1; do
    sleep 1
done
echo "  ✅ API REST ONLINE em http://127.0.0.1:8002"

echo "======================================================================"
echo "🎉 TODOS OS SERVIÇOS ESTÃO OPERACIONAIS!"
echo "======================================================================"
pm2 status
