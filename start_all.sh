#!/usr/bin/env bash
# ==============================================================================
# Script de Inicialização Completa do ReductorPrompt
# Orquestra: Podman (ChromaDB + Ollama GPU), PM2 (API, Web, Relatórios)
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================================"
echo "🚀 INICIANDO ECOSSISTEMA COMPLETO REDUCTOR-PROMPT"
echo "======================================================================"

# 1. Iniciar ChromaDB via Podman
echo "📦 [1/4] Verificando e iniciando ChromaDB (Podman)..."
bash "$SCRIPT_DIR/start_chroma.sh"

# 2. Iniciar Ollama via Podman com GPU
echo "🧠 [2/4] Verificando e iniciando Ollama (Podman + GPU)..."
if ! podman ps --format "{{.Names}}" | grep -q "reductor_ollama"; then
    bash "$SCRIPT_DIR/start_ollama.sh"
else
    echo "  ✅ Ollama já está em execução no Podman."
fi

echo "  -> Aguardando Ollama responder em http://127.0.0.1:11434..."
until curl -s http://127.0.0.1:11434/api/tags > /dev/null 2>&1; do
    sleep 1
done
echo "  ✅ Ollama Server ONLINE em http://127.0.0.1:11434"

# Garantir modelos nomic-embed-text e qwen2.5:7b
echo "  -> Verificando modelos necessários no Ollama..."
if ! podman exec reductor_ollama ollama list | grep -q "nomic-embed-text"; then
    echo "  -> Baixando modelo de embeddings nomic-embed-text..."
    podman exec reductor_ollama ollama pull nomic-embed-text
fi

if ! podman exec reductor_ollama ollama list | grep -q "qwen2.5:7b"; then
    echo "  -> Baixando modelo LLM qwen2.5:7b..."
    podman exec reductor_ollama ollama pull qwen2.5:7b
fi

# 3. Iniciar serviços via PM2 (API, Web, Gerar Relatório)
echo "⚡ [3/4] Iniciando processos via PM2..."
PM2_TARGET=reductor pm2 start ecosystem.config.cjs

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
