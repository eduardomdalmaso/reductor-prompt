#!/usr/bin/env bash
# Para o container ChromaDB do Podman
echo "🛑 Parando container ChromaDB (reductor_chromadb)..."
podman stop reductor_chromadb || true
echo "✔ Container parado com sucesso."
