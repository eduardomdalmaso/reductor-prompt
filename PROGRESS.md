# ReductorPrompt - Estado & Progresso do Projeto (Harness State Artifact)

> **Padrão de Harness Engineering**: Este arquivo mantém a continuidade de contexto entre sessões de agentes de IA e desenvolvedores, evitando amnésia e redundância de análise.

---

## 📌 Status Atual do Sistema

| Componente | Status | Detalhes |
| :--- | :--- | :--- |
| **Runtime & Ambiente** | 🟢 Operacional | Python 3.11 (`reductor-prompt` Conda env) |
| **Vector Store (ChromaDB)** | 🟢 Operacional | 194 livros técnicos indexados (Fallback persistente local ativo) |
| **Segurança & Anti-SSRF** | 🟢 100% Coberto | Validação de IP público, chaves em headers, CORS restrito, Auth Bearer/X-API-Key |
| **Suíte de Testes** | 🟢 15/15 Passando | Testes unitários, de arquitetura, segurança e adaptive budgeting |
| **Harness Health Check** | 🟢 Operacional | Executável via `python scripts/harness_check.py` (1.2s) |

---

## 🚀 Marcos Recentes Concluídos

1. **Auditoria e Blindagem de Segurança**:
   - Proteção contra SSRF em downloads dinâmicos (`is_safe_public_url` com bloqueio de RFC 1918, loopback e metadados de nuvem).
   - Eliminação de `GEMINI_API_KEY` na URL, migrando para cabeçalho `x-goog-api-key`.
   - Binding seguro da porta do ChromaDB para `127.0.0.1:8001:8000`.
   - Middleware `verify_auth` com comparação em tempo constante (`secrets.compare_digest`).
   - Geração de relatório visual de auditoria em `docs/security-audit/relatorio-auditoria-seguranca.pdf`.

2. **Ingestão de Referências Técnicas de Ponta**:
   - Ingestão do guia *Learn Harness Engineering* (VitePress/WalkingLabs) no ChromaDB.
   - Ingestão de *Hands-On Large Language Models* e *Modern Computer Vision*.

3. **Implementação de Práticas de Harness Engineering**:
   - Criação do script de diagnóstico instantâneo `scripts/harness_check.py`.
   - Padronização de artefatos de estado (`PROGRESS.md`).
   - Refatoração dos fluxos de ingestão para compatibilidade total com loaders compostos.

4. **Otimização Avançada do Servidor MCP (`reductor-books`)**:
   - Refinamento de schemas e docstrings com *Few-Shot invocation examples* para LLMs menores.
   - Implementação de busca semântica/substring (`query_filter`) e paginação em `list_indexed_books` evitando context blowouts.
   - Tratamento de exceções resiliente sem crash de processo no protocolo `stdio`.
   - Alinhamento de endpoints REST e MCP Hub (`/api/v1/mcp/call`).

5. **Compressor Adaptativo & Orçamento Dinâmico de Tokens (Adaptive RAG)**:
   - Classificação automática de complexidade da query (`factual` 400-800 tokens, `conceptual` 1200-1800 tokens, `architectural` 3500-4500 tokens).
   - Implementação do algoritmo *Elbow Cutoff* para eliminar cauda de ruído quando a similaridade relativa despenca (>35% ou degrau >0.22), eliminando o efeito *Lost in the Middle*.

---

## 🛠️ Comandos Rápidos do Harness

```bash
# 1. Diagnóstico completo do ambiente e testes (1 segundo)
python scripts/harness_check.py

# 2. Ingestão e sincronização de novos livros
python query.py ingest

# 3. Consulta semântica com redução extrema (>95% economia)
python query.py "sua pergunta"

# 4. Execução da suíte de testes
pytest -v
```
