#!/usr/bin/env python3
"""
Ponto de entrada flexível para consultas e análises.
Exemplos de uso:
  # Consulta direta:
  python query.py "Qual a melhor prática para particionamento de tabelas?"
  
  # Consulta com filtro de livro:
  python query.py "O que diz sobre concorrência?" --book "Designing Data-Intensive"
  
  # Apenas extrair o contexto enxuto (sem gastar tokens de resposta):
  python query.py "Resumo dos princípios de Clean Architecture" --only-context
  
  # Análise Cruzada de Projeto:
  python query.py analyze --project "Pipeline analítico com FastAPI, Kafka e Postgres" --topic "gargalos de escrita"
  
  # Listar livros indexados:
  python query.py list
"""
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.adapters.inbound.cli.cli_controller import app

if __name__ == "__main__":
    if len(sys.argv) > 1:
        first_arg = sys.argv[1]
        # Se o primeiro argumento não for um subcomando conhecido, assume que é o comando 'ask'
        if first_arg not in ["ask", "chat", "serve", "analyze", "ingest", "list", "fetch", "brain", "advisor", "--help", "-h"]:
            sys.argv.insert(1, "ask")
    else:
        # Mostra ajuda se nenhum argumento for passado
        sys.argv.append("--help")
        
    app()
