# Rodada 12 — Confiabilidade Operacional, Cancelamento HTTP e Observabilidade

**Data:** 2026-11-18  
**Testes Automatizados:** `76 passed` (`pytest -q`) | **PM2:** `reductor-api` `online` (`PID 25032`)  
**Dados brutos:** [cancellation_tests.json](file:///c:/Users/hades/Documents/reductor-prompt/docs/benchmarks/cancellation_tests.json) | [memory_profile.json](file:///c:/Users/hades/Documents/reductor-prompt/docs/benchmarks/memory_profile.json) | [soak_test_results.json](file:///c:/Users/hades/Documents/reductor-prompt/docs/benchmarks/soak_test_results.json) | [generation_observability.json](file:///c:/Users/hades/Documents/reductor-prompt/docs/benchmarks/generation_observability.json)

---

## 1. Cancelamento Cooperativo HTTP (`cancellation_tests.json`)

| Cenário Testado | Resultado |
| :--- | :---: |
| Requisição ativa na GPU durante desconexão de outros clientes | **`HTTP 200`** (slot mantido até concluir) |
| 3 clientes desconectados após `0,25s` aguardando na fila | **`3 / 3` cancelados** (`cancelled_delta = 3`, `HTTP 499`) |
| Slots presos após cancelamento | **`0`** (`active = 0`, `pending = 0`) |
| Requisição normal imediatamente após cancelamentos | **`HTTP 200`** |

---

## 2. Observabilidade de Fila Exposta em `GET /health` (`generation_observability.json`)

Métricas em tempo real implementadas em [generation_queue.py](file:///c:/Users/hades/Documents/reductor-prompt/src/adapters/outbound/llm/generation_queue.py) e [fastapi_app.py](file:///c:/Users/hades/Documents/reductor-prompt/src/adapters/inbound/api/fastapi_app.py):
- `generation_active`, `generation_pending`
- `generation_rejected_total`, `generation_timeout_total`, `generation_cancelled_total`
- `generation_queue_wait_seconds` (`avg`, `max`, `last`)
- `generation_duration_seconds` (`avg`, `max`, `last`)
- `process_memory` (`pid`, `heap_current_mb`, `heap_peak_mb`)

---

## 3. Soak Test Escalado (`126,7s`) e Perfil de Memória PM2 (`PID 25032`)

> **Nota de transparência:** este experimento executou um **soak test escalado de `126,7s` (`15` ciclos)** alternando carga contínua e rajadas de saturação (`15` requisições simultâneas), e **não** uma execução contínua de 60 minutos.

| Indicador | Resultado Observado |
| :--- | :---: |
| **Requisições atendidas (`HTTP 200`)** | **`85`** |
| **Rejeições por saturação (`HTTP 429`)** | **`10`** (`2` por rajada de 15 > 13 slots) |
| **Outros erros / Timeouts (`503`)** | **`0`** |
| **Consistência ChromaDB ↔ FTS5 ao final** | `72.360 == 72.360` (`in_sync: true`, `delta: 0`) |
| **Drenagem da fila ao final** | **`true`** (`active = 0`, `pending = 0`) |
| **RSS inicial → pico → pós-drenagem (PM2)** | `434,16 MB` → `505,37 MB` → `505,37 MB` (`+71,21 MB` de cache LRU/páginas) |
| **Heap Python (`tracemalloc`) final / pico** | **`7,16 MB`** / **`7,45 MB`** |
