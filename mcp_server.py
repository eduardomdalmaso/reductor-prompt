#!/usr/bin/env python3
"""
Ponto de entrada para o Servidor MCP (Model Context Protocol).
Uso:
  python mcp_server.py
"""
from src.adapters.inbound.mcp.server import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")
