# ReductorPrompt - Estado & Progresso do Projeto (Harness State Artifact)

> **Padrão de Harness Engineering**: Este arquivo mantém a continuidade de contexto entre sessões de agentes de IA e desenvolvedores, evitando amnésia e redundância de análise.

---

## 📌 Status Atual do Sistema

| Componente | Status | Detalhes |
| :--- | :--- | :--- |
| **Runtime & Ambiente** | 🟢 Operacional | Python 3.11 (`reductor-prompt` Conda env) |
| **Vector Store (ChromaDB)** | 🟢 Operacional | 194 livros indexados + Coleção `agent_episodic_brain` ativa |
| **Segurança & Anti-SSRF** | 🟢 100% Coberto | Validação de IP público, chaves em headers, CORS restrito, Auth Bearer/X-API-Key |
| **Suíte de Testes** | 🟢 20/20 Passando | Testes unitários, de arquitetura, segurança, adaptive budgeting, memória episódica e hardware advisor |
| **Harness Health Check** | 🟢 Operacional | Executável via `python scripts/harness_check.py` (0.8s) |

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

6. **🧠 Memória Episódica & Cérebro Coletivo (Continuous Knowledge Distillation)**:
   - Implementação da coleção persistente `agent_episodic_brain` no ChromaDB.
   - *Semantic Memory Hit*: Resposta instantânea (<2ms) e zero consumo de tokens para perguntas recorrentes com similaridade cosseno >= 88%.
   - Auto-destilação: Toda consulta inédita sintetizada pela LLM é salva como novo aprendizado no cérebro.
   - Novas ferramentas MCP: `teach_brain`, `consult_brain` e `validate_reasoning`.
   - Subcomando CLI: `python query.py brain list` e `python query.py brain teach`.

7. **🔮 Oráculo de Recursos & Telemetria Adaptativa (Hardware & Budget Advisor)**:
   - Detecção em tempo real de hardware (NVIDIA RTX 5090 32GB VRAM detectada) e provedores ativos (Ollama local vs Gemini Cloud).
   - Perfilamento inteligente de parâmetros ideais (`max_tokens`, `deep_reasoning`, expansão de queries e estratégia de custo).
   - Ferramenta MCP: `get_runtime_budget_advice()` para auto-calibração autônoma de agentes (Gemini/Claude).
   - Endpoint REST `GET /api/v1/hardware/budget-advice` e subcomando CLI `python query.py advisor`.

8. **📚 Ingestão de Documentações Técnicas Oficiais (Elasticsearch, Redis, Triton, PHP 8.4, Laravel 12.x)**:
   - Download concorrente e compilação de repositórios oficiais GitHub (`elastic/elasticsearch`, `redis/docs`, `triton-inference-server/server`, `laravel/docs`, `php/php-src`).
   - 14 manuais técnicos estruturados em `database/` somando **15.817 chunks** e mais de **3.360.000 tokens** indexados no ChromaDB.

9. **🌐 Extrator & Compilador Dinâmico Universal (Zero Scripts Avulsos)**:
   - Implementação de [`DocFetcherService`](file:///c:/Users/eduar/Documents/reductor-prompt/src/application/services/doc_fetcher_service.py) e [`DocCompilerService`](file:///c:/Users/eduar/Documents/reductor-prompt/src/application/services/doc_compiler_service.py) baseados em *Clean Architecture*, *Strategy Pattern* e I/O concorrente.
   - Resolução polimórfica de links (árvores GitHub, arquivos únicos, links diretos e web) com compilação semântica em manuais canônicos.
   - Eliminação de todos os scripts avulsos da pasta `scripts/`, integrando todo o pipeline diretamente ao CLI (`python query.py fetch "<urls>" [--compile] [--ingest]`).

---

## 🛠️ Comandos Rápidos do Harness

```bash
# 1. Diagnóstico completo do ambiente e testes (1 segundo)
python scripts/harness_check.py

# 2. Oráculo de Recursos e Telemetria de Hardware
python query.py advisor

# 3. Consultar o Cérebro Coletivo e Livros
python query.py "sua pergunta"

# 4. Gerenciar o Cérebro Episódico
python query.py brain list
python query.py brain teach "pergunta" "resposta"

# 5. Execução da suíte de testes
pytest -v
```
