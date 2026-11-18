# Rodada 5 — Índice BM25 (SQLite FTS5) e Ablação A–G (`dev` / `eval`)

**Data:** 2026-11-18  
**Índice BM25:** `storage/bm25_fts5.db` (`72.360` chunks canônicos indexados do ChromaDB em `7,77s`)  
**Modelo / Embedding:** `qwen2.5:14b` (`temperature=0.0`, `seed=42`) | `nomic-embed-text`  
**Split de Validação:** `dev` (`30` perguntas para calibração de pesos) e `eval` held-out (`60` perguntas respondíveis + `10` `no_evidence`)  
**Pesos calibrados no `dev`:** `dense = 0,40`, `bm25 = 0,60` (`MRR dev = 0,7067`)  
**Dados brutos:** [ablation_a_g_results.json](file:///c:/Users/hades/Documents/reductor-prompt/docs/benchmarks/ablation_a_g_results.json)

---

## 1. Ablação A–G no Split Held-out (`60` Perguntas Respondíveis)

| Configuração | `Precision@5` | `Recall@5` | `Recall@10` | `MRR` | `Book@4` | `Page@4` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **A. `Dense` (sem corte)** | `0,2300` | `0,6000` | `0,7167` | `0,5195` | `88,33%` | `55,00%` |
| **B. `Dense + Lexical` (sem corte)** | `0,2333` | `0,6333` | `0,7500` | `0,5206` | `88,33%` | `55,00%` |
| **C. `Dense + BM25` (sem corte)** | **`0,2900`** | `0,7667` | `0,7667` | **`0,6328`** | **`91,67%`** | **`70,00%`** |
| **D. `Dense + BM25 + Lexical` (sem corte)** | `0,2700` | **`0,7833`** | **`0,8000`** | `0,6172` | `85,00%` | `68,33%` |
| **E. `D + Conservative (5%)`** | `0,2700` | **`0,7833`** | **`0,8000`** | `0,6172` | `85,00%` | `68,33%` |
| **F. `D + Balanced`** | `0,1733` | `0,6833` | `0,6833` | `0,5922` | `83,33%` | `66,67%` |
| **G. `D + Aggressive`** | `0,1533` | `0,6333` | `0,6333` | `0,5714` | `80,00%` | `61,67%` |

*(No conjunto completo de `90` perguntas: **C (`Dense + BM25`)** atingiu `Recall@10 = 0,7667`, `MRR = 0,6574`, `Book@4 = 92,22%`, `Page@4 = 71,11%` — batendo todas as metas de recuperação e localização).*

---

## 2. Validação E2E no Held-out (`25` Perguntas: `15` Respondíveis + `10` `no_evidence`)

| Cenário | Tokens Entrada (`prompt_eval_count`) | Tokens Saída (`eval_count`) | Latência Média | Recusa `no_evidence` |
| :--- | :---: | :---: | :---: | :---: |
| **A (`Dense` Top-12, sem corte)** | `2.962,1` | `91,4` | `1.402,7 ms` | — |
| **E (`D + Conservative 5%`)** | `10.642,2` | `203,6` | `3.875,2 ms` | **`10 / 10` (100%)** |

### Diagnóstico Crítico do E2E
1. **Por que `E` consumiu `10.642` tokens de entrada?** A fusão `Dense(16) + BM25(16)` gerou uma união de até **32 chunks** sem truncar o pool para `top_k=12` antes do compressor `Conservative (5%)`, que preservou `97,7%` da união completa (`avg_cut_pct = 2,28%`).
2. **Lição arquitetural clara:**
   - **Recuperação vencedora:** `Dense + BM25` (`0,4 / 0,6`) resolve o gargalo de localização (`Book@4 = 91,7%–92,2%`, `Page@4 = 70,0%–71,1%`, `MRR = 0,63–0,66`).
   - **Próximo passo necessário:** limitar o pool pós-fusão (ex.: Top-10 ou Top-12 de `Dense + BM25`) antes da compressão `Conservative`/`Balanced`, para unir a alta precisão do `BM25 + Dense` com economia real de tokens frente ao Top-12 convencional.
