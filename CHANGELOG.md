# Changelog

Todas as mudanças notáveis do **ReductorPrompt** são documentadas neste arquivo.

## [1.0.0] - 2026-11-18

### Adicionado
- **Arquitetura Modular & Contratos:** decomposição de API (`src/adapters/inbound/api/routes/`, `observability.py`, `dependencies.py`), serviços (`elbow_budget_service.py`, `citation_guard.py`, `hybrid_retrieval_helpers.py`, `hardware_detector.py`, `telemetry_sqlite_store.py`), loaders (`ipynb_loader.py`) e memória (`memory_serializer.py`); introdução da porta abstrata `ILexicalIndexPort` implementada por `BM25SqliteIndex`.
- **Controle de Saturação e Cancelamento Cooperativo:** `GenerationQueue` com `max_concurrent=1`, `max_pending=12`, timeout de espera, proteção `HTTP 429` e cancelamento cooperativo sem liberação prematura de slot durante geração GPU.
- **Observabilidade Prometheus:** endpoint `GET /metrics` (`text/plain; version=0.0.4`) baseado em snapshot em memória (`~0.1 ms/scrape`), expondo métricas de fila, RSS do processo, sincronização de índice e duração/erros de scrape.
- **Cache LRU+TTL de Embeddings:** `EmbeddingLRUCache` (`maxsize=512`, `ttl_s=1800.0`) isolado por `(provider, model, version, texto_normalizado)` em `ResilientEmbeddingAdapter`.
- **Relatório de Validação v1.0.0:** consolidação das Rodadas 12–18 em `docs/releases/v1.0.0-validation-report.md`.

### Otimizado
- **ChromaDB `search()`:** eliminação de `collection.count()` no caminho crítico de busca vetorial (`-85.8%` no p95 de `10.60 ms` para `1.51 ms`).
- **SQLite FTS5 (`BM25SqliteIndex`):** conexão `threading.local()` com PRAGMAs (`WAL`, `cache_size=-64000`, `mmap_size=268435456`, `temp_store=MEMORY`) e filtro de stopwords com fallback (`-56.9%` no p95 de `77.81 ms` para `33.57 ms`).

### Validado
- **78 testes automatizados** passando (`pytest -q`).
- **Qualidade semântica preservada (25 perguntas rotuladas):** `Recall@5 = 1.0000`, `Precision@5 = 0.2240`, `MRR@5 = 0.9000`, `NDCG@5 = 0.9051` com `-64.2%` na latência `p95` de retrieval.
- **Consistência de índices:** `72.360 == 72.360` chunks sincronizados entre ChromaDB e SQLite FTS5.
