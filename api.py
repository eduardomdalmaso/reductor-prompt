#!/usr/bin/env python3
"""
Ponto de entrada para iniciar o servidor API REST / Tool Server.
Uso:
  python api.py
"""
import sys
import uvicorn

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import os

if __name__ == "__main__":
    port = int(os.environ.get("API_PORT", "8002"))
    print(f"🚀 Iniciando ReductorPrompt API em http://0.0.0.0:{port} ...")
    uvicorn.run("src.adapters.inbound.api.fastapi_app:app", host="0.0.0.0", port=port, reload=True)
