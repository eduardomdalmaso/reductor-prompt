# Rodada 10 — Hardening, Correções Fatuais e Teste de Carga (`hybrid-bm25-v4`)

**Data:** 2026-11-18  
**Perfil Padrão:** `economy` (E4) | **Experimental:** `fidelity` (E1) | **Rollback:** `legacy`  
**Testes Automatizados:** `74 passed` (`pytest -q`) | **PM2:** `reductor-api` `online` (`423,5 MB` após carga)  
**Dados brutos:** [hallucination_url_tests.json](file:///c:/Users/hades/Documents/reductor-prompt/docs/benchmarks/hallucination_url_tests.json) | [redis_semantics_tests.json](file:///c:/Users/hades/Documents/reductor-prompt/docs/benchmarks/redis_semantics_tests.json) | [load_test_results.json](file:///c:/Users/hades/Documents/reductor-prompt/docs/benchmarks/load_test_results.json) | [production_health_report.json](file:///c:/Users/hades/Documents/reductor-prompt/docs/benchmarks/production_health_report.json)

---

## 1. Correção de URLs Fabricadas (`Q003`, `Q017`, `Q023`)

- **Prompt (`qa-v4-strict-urls`) + Sanitizador (`validate_and_sanitize_urls`)**:
  - `6 / 6` execuções (`economy` e `fidelity`): **`0` ocorrências de `example.com`** e `0` URLs fabricadas.

## 2. Regressão Semântica Redis Sorted Sets (`Q009` + `ZRANGE`/`ZREVRANGE`)

- `4 / 4` execuções (`economy` e `fidelity`): **`ascending_ok = True`** (`0` inversões de ordenação).

## 3. Integridade de Índices e `/health`

- `GET http://127.0.0.1:8002/health`: `status = "ok"`, `index_sync = {"chroma_chunks": 72360, "bm25_chunks": 72360, "in_sync": true, "delta": 0}`.
- Se `bm25_cnt != chroma_cnt`, `_get_bm25_index()` bloqueia a busca híbrida e faz fallback seguro para `Dense-only`, enquanto o startup executa reconciliação assíncrona via `rebuild_from_chroma()`.

## 4. Teste de Carga HTTP na API (`POST /api/v1/query`, `only_context=true`, perfil `economy`)

| Concorrência | HTTP `200` | Erros | Throughput (`req/s`) | `p50` | `p95` | `p99` |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **10** (cold warm) | `10 / 10` | `0` | `3,42` | `2.756,8 ms` | `2.920,0 ms` | `2.920,0 ms` |
| **25** | `25 / 25` | `0` | `22,37` | `668,8 ms` | `1.105,2 ms` | `1.105,8 ms` |
| **50** | `50 / 50` | `0` | **`24,44`** | `1.103,1 ms` | `1.367,2 ms` | `1.416,4 ms` |
| **100** | `100 / 100` | `0` | `24,32` | `1.293,4 ms` | `1.374,9 ms` | `1.412,5 ms` |

- **Consultas simultâneas à mutação (`upsert` + `delete` + `invalidate_query_cache`)**: `0` erros HTTP e `in_sync: true` (`72.360 == 72.360`) ao final.
- **Nota metodológica:** o teste de carga mediu o throughput de API + ChromaDB + SQLite FTS5 (`only_context=true`); em chamadas com geração LLM (`only_context=false`), o gargalo continua sendo a fila da GPU do Ollama (~`1,2s` por geração).
