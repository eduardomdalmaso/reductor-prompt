# Rodada 13 — Estabilidade Prolongada (60 Minutos Contínuos) e Arquitetura Modular

**Data:** 2026-11-18  
**Versão:** `hybrid-bm25-v4` / `qa-v4-strict-urls` (`economy` padrão, módulos `<= 180–200` linhas, `76 passed` no `pytest`)  
**Processo PM2:** `reductor-api` (`PID 36612`, uptime `61m`, **`0` reinícios** durante o teste)  
**Dados brutos:** [round_13_soak_60m.json](file:///c:/Users/hades/Documents/reductor-prompt/docs/benchmarks/round_13_soak_60m.json)

---

## 1. Resumo da Execução Contínua (`3.603,8s` / 60 minutos)

| Indicador | Resultado Observado |
| :--- | :---: |
| **Duração real** | **`3.603,8 s`** (`859` ciclos, `388` amostras de `/health`) |
| **Respostas completas (`HTTP 200`)** | **`2.653`** (`qwen2.5:14b`, `only_context=false`) |
| **Rejeições por saturação (`HTTP 429`)** | **`170`** (rajadas periódicas de 15 > 13 slots) |
| **Timeouts (`503`) / Outros erros** | **`0` / `0`** |
| **Duração média da geração LLM** | **`1,3065 s`** (máx `5,606 s`) |
| **Espera média na fila** | **`3,6116 s`** (máx `18,3858 s`) |
| **Fila drenada ao final** | **`true`** (`active = 0`, `pending = 0`) |
| **Consistência ChromaDB ↔ FTS5 ao final** | `72.360 == 72.360` (**`in_sync: true`**, `delta: 0`) |

---

## 2. Curva de Memória (`388` Amostras ao Longo de 60 Minutos)

| Marco Temporal | RSS (`psutil`, PM2 `PID 36612`) | Heap Python (`tracemalloc`) |
| :--- | :---: | :---: |
| **Início (`0 min`)** | `412,46 MB` | `~0,5 MB` |
| **25% (`~15 min`)** | `559,94 MB` | `11,85 MB` |
| **50% (`~30 min`)** | `530,30 MB` | `12,07 MB` |
| **75% (`~45 min`)** | `550,31 MB` | `11,42 MB` |
| **Fim (`60 min`)** | **`558,45 MB`** (pico `571,56 MB`) | **`6,11 MB`** |

**Diagnóstico de memória:** após o aquecimento inicial dos primeiros ~15 minutos (cache LRU `_QUERY_CACHE` + páginas SQLite/ChromaDB), o **RSS estabilizou em platô de `530–560 MB`** durante os 45 minutos finais e o **heap Python fechou em `6,11 MB`** — sem tendência progressiva de crescimento ou *memory leak*.

---

## 3. Critérios de Aprovação — Rodada 13

- Nenhum slot preso (`active = 0`, `pending = 0`): **Aprovado**
- Zero divergência ChromaDB ↔ FTS5 (`72.360 == 72.360`): **Aprovado**
- Zero erros inesperados ou timeouts em 2.653 gerações: **Aprovado**
- Memória estabilizada em platô durante 60 minutos: **Aprovado**
- **Decisão:** **🟢 APROVADO PARA PRODUÇÃO** (dentro da capacidade medida da GPU de ~`0,74`–`0,85 req/s` e fila configurada `1 ativa + 12 pendentes`).
