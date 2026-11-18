# Validação de Invalidação e Isolamento de Cache

**Arquivo auditado:** [query_books_use_case.py](file:///c:/Users/hades/Documents/reductor-prompt/src/application/use_cases/query_books_use_case.py)  
**Pontos de invalidação:** [ingest_books_use_case.py](file:///c:/Users/hades/Documents/reductor-prompt/src/application/use_cases/ingest_books_use_case.py#L114-L116) e [fastapi_app.py](file:///c:/Users/hades/Documents/reductor-prompt/src/adapters/inbound/api/fastapi_app.py#L194-L200)  
**Testes automatizados:** [test_services.py](file:///c:/Users/hades/Documents/reductor-prompt/tests/test_services.py#L83-L102)

---

## 1. Campos incluídos na chave de cache (`_get_cache_key`)

A chave SHA-256 agora combina todos os parâmetros que alteram recuperação, geração ou estado do corpus:

- `query.strip().lower()` e `book_filter`
- `max_tokens`, `only_ctx`, `deep_reasoning`, `enable_rewriting`, `use_brain`
- `LLM_PROVIDER` e modelo ativo (`OLLAMA_LLM_MODEL` ou `GEMINI_MODEL`)
- `EMBEDDING_PROVIDER` e `OLLAMA_EMBED_MODEL`
- `DEFAULT_TOP_K` e `SIMILARITY_THRESHOLD`
- `_CACHE_EPOCH` (incrementado a cada `invalidate_query_cache()`)
- `RETRIEVAL_ALGO_VERSION` (`"rrf-elbow-v1"`) e `PROMPT_TEMPLATE_VERSION` (`"qa-v1"`)

---

## 2. Resultados Executáveis (registrados em `benchmark_results.json`)

Teste executado contra o `ChromaVectorStoreAdapter` real (`./storage/chroma`):

| Passo | Chamada | `cache_hit` observado | Resultado |
| :--- | :--- | :---: | :--- |
| 1 | Primeira consulta (`enable_rewriting=True`) | `false` | Executou busca vetorial completa |
| 2 | Repetição idêntica (`enable_rewriting=True`) | `true` | Retornou do cache em memória |
| 3 | Mesma pergunta com `enable_rewriting=False` | `false` | Chave isolada — não reutilizou o cache anterior |
| 4 | Chamada a `invalidate_query_cache()` | — | `_QUERY_CACHE` limpo; `_CACHE_EPOCH` incrementado (`3`) |
| 5 | Repetição da consulta original após invalidação | `false` | Cache invalidado — reexecutou contra o corpus atualizado |

---

## 3. Suíte Unitária

`pytest -q` executado após todas as alterações: **66 passed** (incluindo `test_query_cache_key_isolates_flags`, que valida chaves distintas para flags diferentes e mudança de chave após `invalidate_query_cache()`).
