#!/usr/bin/env python3
"""
Ponto de entrada para o Servidor MCP (Model Context Protocol).
Uso:
  python mcp_server.py
"""
import os
import sys
from pathlib import Path

# Fixa o diretório de trabalho e PYTHONPATH na raiz do projeto ReductorPrompt
PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.adapters.inbound.mcp.server import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")

