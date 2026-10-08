#!/usr/bin/env bash
# Inicia o Ollama com aceleracao GPU NVIDIA via Podman na porta 11434
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$SCRIPT_DIR/storage/ollama"

echo "🧠 Iniciando container Ollama com GPU via Podman na porta 11434..."
podman run -d \
  --name reductor_ollama \
  -p 127.0.0.1:11434:11434 \
  --security-opt label=disable \
  --device /dev/nvidia0 --device /dev/nvidiactl --device /dev/nvidia-uvm --device /dev/nvidia-uvm-tools --device /dev/nvidia-modeset \
  -v /usr/lib64/libcuda.so.1:/usr/lib/x86_64-linux-gnu/libcuda.so.1:ro \
  -v /usr/lib64/libnvidia-ml.so.1:/usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1:ro \
  -v /usr/lib64/libnvidia-ptxjitcompiler.so.1:/usr/lib/x86_64-linux-gnu/libnvidia-ptxjitcompiler.so.1:ro \
  -v /usr/lib64/libnvidia-ptxjitcompiler.so.1:/usr/lib/ollama/cuda_v13/libnvidia-ptxjitcompiler.so.1:ro \
  -v /usr/lib64/libnvidia-ptxjitcompiler.so.1:/usr/lib/ollama/cuda_v12/libnvidia-ptxjitcompiler.so.1:ro \
  -v "$SCRIPT_DIR/storage/ollama:/root/.ollama:Z" \
  -e OLLAMA_HOST=0.0.0.0:11434 \
  -e OLLAMA_ORIGINS=* \
  -e OLLAMA_KEEP_ALIVE=24h \
  -e OLLAMA_NUM_PARALLEL=2 \
  --replace \
  docker.io/ollama/ollama:latest serve

echo "⏳ Aguardando Ollama inicializar..."
until curl -s http://127.0.0.1:11434/api/tags > /dev/null 2>&1; do
  sleep 1
done

echo "✅ Ollama rodando perfeitamente via Podman em http://127.0.0.1:11434"
