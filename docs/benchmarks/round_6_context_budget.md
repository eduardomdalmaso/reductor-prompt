# Rodada 6 — Experimento de Orçamento de Contexto (`E1–E5`)

**Data:** 2026-11-18  
**Versão Experimental:** `round_6_context_budget_v4_exp` (`Dense 0,4 + BM25 0,6`, deduplicação por `chunk_id`, sem alterar `QueryBooksUseCase` nem `reductor-api`)  
**Modelo / Embedding:** `qwen2.5:14b` (`temperature=0.0`, `seed=42`) | `nomic-embed-text`  
**Amostra:** `60` perguntas held-out respondíveis (IR) + `25` E2E (`15` held-out respondíveis + `10` `no_evidence`)  
**Dados brutos:** [context_budget_results.json](file:///c:/Users/hades/Documents/reductor-prompt/docs/benchmarks/context_budget_results.json)

---

## 1. Métricas de Recuperação no Held-out (`60` Perguntas Respondíveis)

| Configuração | Pool | Compressor | `Recall@5` | `Recall@10` | `MRR` | `Book@4` | `Page@4` | Evidências Perdidas vs. União Completa |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **E1** | `Top-10` | `Conservative 5%` | **`0,7667`** | **`0,7667`** | **`0,6328`** | **`91,67%`** | **`70,00%`** | `9` |
| **E2** | `Top-12` | `Conservative 5%` | **`0,7667`** | **`0,7667`** | **`0,6328`** | **`91,67%`** | **`70,00%`** | `7` |
| **E3** | `Top-16` | `Conservative 5%` | **`0,7667`** | **`0,7667`** | **`0,6328`** | **`91,67%`** | **`70,00%`** | **`5`** |
| **E4** | `Top-12` | `Balanced` | `0,6833` | `0,6833` | `0,6139` | `90,00%` | `68,33%` | `14` |
| **E5** | `Top-12` | Sem compressor | **`0,7667`** | **`0,7667`** | **`0,6328`** | **`91,67%`** | **`70,00%`** | `7` |

---

## 2. Consumo Real de Tokens, Latência e Recusa no E2E (`25` Perguntas)

| Configuração | Entrada Média (`in`) | Saída Média (`out`) | Total Médio | Latência Média | Recusa `no_evidence` |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Baseline `A` (`Dense Top-12`, sem corte)** | `2.962,1` | `88,6` | `3.050,7` | `1.182,0 ms` | `10 / 10` (100%) |
| **E1 (`Top-10` + `Conservative 5%`)** | **`2.896,8`** (`-2,2%`) | `181,0` | `3.077,8` | `1.850,4 ms` | **`10 / 10` (100%)** |
| **E2 (`Top-12` + `Conservative 5%`)** | `3.320,6` (`+12,1%`) | `197,1` | `3.517,7` | `2.056,8 ms` | **`10 / 10` (100%)** |
| **E3 (`Top-16` + `Conservative 5%`)** | `4.245,7` (`+43,3%`) | `181,1` | `4.426,8` | `2.126,0 ms` | **`10 / 10` (100%)** |
| **E4 (`Top-12` + `Balanced`)** | **`827,5`** (**`-72,1%`**) | `161,8` | **`989,3`** (**`-67,6%`**) | **`1.299,1 ms`** (`+9,9%`) | **`10 / 10` (100%)** |
| **E5 (`Top-12`, sem compressor)** | `3.410,2` (`+15,1%`) | `196,4` | `3.606,6` | `2.065,1 ms` | **`10 / 10` (100%)** |

---

## 3. Conclusão e Recomendação de Integração

1. **Explosão de contexto resolvida:** limitar o pool pós-fusão reduziu a entrada de `10.642,2` tokens (Rodada 5) para `2.896,8` (`E1`), `3.320,6` (`E2`) e `827,5` (`E4`).
2. **Dois perfis claros para produção:**
   - **Perfil Máxima Precisão (`E1` — `Top-10` + `Conservative 5%`)**: entrega `Recall@10 = 0,7667`, `MRR = 0,6328`, `Book@4 = 91,67%`, `Page@4 = 70,00%` com entrada menor que o baseline (`2.896,8` vs `2.962,1`), mas não atinge `-25%` de redução total porque mantém quase os 10 chunks inteiros.
   - **Perfil Eficiência + Qualidade (`E4` — `Top-12` + `Balanced`)**: entrega **-72,1% de entrada** (`-67,6%` no total de tokens), apenas **`+9,9%` de latência**, `10/10` de recusa e ainda supera o `Dense` puro em `MRR` (`0,6139` vs `0,5195`), `Book@4` (`90,00%` vs `88,33%`) e `Page@4` (`68,33%` vs `55,00%`).
