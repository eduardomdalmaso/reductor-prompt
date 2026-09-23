#!/usr/bin/env python3
"""
Ponto de entrada rápido para ingestão de livros.
Uso:
  python ingest.py
  python ingest.py --force
"""
import sys

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            getattr(sys.stdout, "reconfigure")(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            getattr(sys.stderr, "reconfigure")(encoding="utf-8")
    except Exception:
        pass

from src.adapters.inbound.cli.cli_controller import app

if __name__ == "__main__":
    # Redireciona para o comando ingest
    if len(sys.argv) == 1:
        sys.argv.append("ingest")
    elif sys.argv[1] not in ["ingest", "ask", "analyze", "list", "fetch", "--help", "-h"]:
        sys.argv.insert(1, "ingest")
    app()
