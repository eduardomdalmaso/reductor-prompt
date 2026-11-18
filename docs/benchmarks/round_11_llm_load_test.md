# Rodada 11 — Validação E2E (`Economy` Padrão) e Carga Real com Geração LLM

**Data:** 2026-11-18  
**Modelo:** `qwen2.5:14b` via `GenerationQueue` (`max_concurrent=1`, `max_pending=12`, `acquire_timeout_s=45.0`)  
**Testes Automatizados:** `75 passed` (`pytest -q`) | **PM2:** `reductor-api` `online` (`PID 27736`)  
**Dados brutos:** [e2e_economy_regression.json](file:///c:/Users/hades/Documents/reductor-prompt/docs/benchmarks/e2e_economy_regression.json) | [llm_concurrency_results.json](file:///c:/Users/hades/Documents/reductor-prompt/docs/benchmarks/llm_concurrency_results.json) | [generation_queue_metrics.json](file:///c:/Users/hades/Documents/reductor-prompt/docs/benchmarks/generation_queue_metrics.json)

---

## 1. Regressão Funcional E2E (`25` Perguntas, `economy` padrão, `only_context=false`)

| Indicador | Resultado |
| :--- | :---: |
| **HTTP `200`** | **`25 / 25` (100%)** |
| **Latência Média** | **`1.232,9 ms`** |
| **Tokens de Contexto Médios (`tokens_used`)** | **`706,8`** |
| **Livro Esperado no Top-4 (`15` respondíveis)** | `13 / 15` (`86,7%`) |
| **Recusa em `no_evidence` (`10`)** | **`10 / 10` (`100,0%`)** |
| **URLs `example.com` Fabricadas** | **`0`** |

---

## 2. Carga Real com Geração LLM (`only_context=false`, `qwen2.5:14b`)

| Concorrência | HTTP `200` | HTTP `429` (Saturação) | Timeouts (`503`) | Throughput (`req/s`) | `p50` | `p95` | VRAM GPU (`RTX 5090`) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | `1` | `0` | `0` | `0,60` | `1.656,7 ms` | `1.656,7 ms` | `12.208 MB` |
| **2** | `2` | `0` | `0` | `0,65` | `1.409,8 ms` | `3.061,2 ms` | `12.203 MB` |
| **5** | `5` | `0` | `0` | `0,83` | `3.974,5 ms` | `5.998,1 ms` | `12.191 MB` |
| **10** | `10` | `0` | `0` | **`0,86`** | `5.761,5 ms` | `11.574,1 ms` | `12.194 MB` |
| **15** *(sobrecarga > 13 slots)* | `13` | **`2`** | `0` | `0,78` | `7.853,5 ms` | `15.332,3 ms` | **`12.190 MB`** |

---

## 3. Métricas da Fila de Geração (`/health` após os testes)

- `total_acquired`: **`57`** | `total_rejected_saturation`: **`2`** | `total_timeouts`: **`0`**
- `avg_queue_wait_ms`: **`2.779,05 ms`** | `max_queue_wait_ms`: **`14.807,21 ms`**
- `active_generations`: `0` | `pending_in_queue`: `0` (fila drenada integralmente)
- **VRAM estável**: `~12,2 GB` de `32 GB` em todos os níveis (zero crescimento de memória ou OOM sob concorrência).
- **Capacidade real medida**: ~**0,85 respostas LLM completas/s** com fila segura para até **13 requisições simultâneas** (`1` ativa + `12` na fila) e rejeição rápida (`HTTP 429`) acima disso.
