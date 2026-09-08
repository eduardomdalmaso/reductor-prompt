#!/usr/bin/env python3
"""
Ponto de entrada para iniciar o servidor API REST / Tool Server.
Uso:
  python api.py
"""
import uvicorn

if __name__ == "__main__":
    print("🚀 Iniciando ReductorPrompt API em http://0.0.0.0:8000 ...")
    uvicorn.run("src.adapters.inbound.api.fastapi_app:app", host="0.0.0.0", port=8000, reload=True)
