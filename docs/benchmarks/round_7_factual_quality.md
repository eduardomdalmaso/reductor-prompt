# Rodada 7 — Avaliação Factual Comparativa, Evidências Descartadas e Padronização de Prompt

**Data:** 2026-11-18  
**Modelo / Juiz:** `qwen2.5:14b` (`temperature=0.0`, `seed=42`) | **Embeddings:** `nomic-embed-text`  
**Amostra:** `25` perguntas held-out (`15` respondíveis + `10` `no_evidence`) | **Ablação de descarte:** `60` perguntas held-out  
**Dados brutos:** [factual_quality_results.json](file:///c:/Users/hades/Documents/reductor-prompt/docs/benchmarks/factual_quality_results.json) | [discarded_evidence_analysis.json](file:///c:/Users/hades/Documents/reductor-prompt/docs/benchmarks/discarded_evidence_analysis.json)

---

## 1. Avaliação Factual Comparativa (`25` Perguntas E2E)

| Configuração | Entrada Média | Saída Média | Total Médio | Latência Média | Correção Factual (`15`) | Fidelidade (`15`) | Citação OK (`15`) | Completude (`15`) | Alucinações (`25`) | Recusa (`10`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline `A` (`Dense Top-12`, prompt unificado)** | `2.979,1` | `76,5` | `3.055,6` | `1.029,9 ms` | `12/15` (`80,0%`) | `12/15` (`80,0%`) | **`15/15`** (`100%`) | `12/15` (`80,0%`) | `4` | `9/10` (`90,0%`) |
| **`E1` Fidelity (prompt unificado)** | `2.804,8` | `77,8` | `2.882,6` (`-5,7%`) | **`1.016,5 ms`** (`-1,3%`) | **`15/15` (`100%`)** | **`15/15` (`100%`)** | `14/15` (`93,3%`) | **`15/15` (`100%`)** | **`0`** | **`10/10` (`100%`)** |
| **`E4` Economy (prompt unificado)** | **`735,5`** (`-75,3%`) | **`76,6`** | **`812,1`** (**`-73,4%`**) | **`670,0 ms`** (`-34,9%`) | `13/15` (`86,7%`) | `13/15` (`86,7%`) | `14/15` (`93,3%`) | `13/15` (`86,7%`) | `2` | **`10/10` (`100%`)** |
| **`E1` com `build_qa_prompt` (controle)** | `2.896,8` | **`180,3`** | `3.077,1` | `1.821,1 ms` | `13/15` (`86,7%`) | `13/15` (`86,7%`) | `14/15` (`93,3%`) | `13/15` (`86,7%`) | `2` | **`10/10` (`100%`)** |

---

## 2. Causa do Aumento de Tokens de Saída no `E1`

- Com `build_qa_prompt`, `E1` gerou **`180,3` tokens de saída** (`1.821,1 ms`).
- Com o **mesmo prompt conciso** do Baseline `A`, `E1` gerou **`77,8` tokens de saída** (praticamente idêntico aos `76,5` do Baseline `A`) e foi **mais rápido que o Baseline** (`1.016,5 ms` vs `1.029,9 ms`), subindo a correção factual para **`100%` (`15/15`)** e zerando alucinações (`0/25`).
- **Conclusão:** o excesso de saída na Rodada 6 era efeito exclusivo do `build_qa_prompt`.

---

## 3. Análise das Evidências Descartadas (`60` Perguntas Held-out)

| Perfil | Total Descartadas vs. União Completa | Redundantes (mesmo livro mantido) | Indispensáveis (livro perdido) |
| :--- | :---: | :---: | :---: |
| **`E1` (`Top-10` + `Conservative 5%`)** | `9` | `7` (`77,8%`) | **`2`** (`22,2%`) |
| **`E4` (`Top-12` + `Balanced`)** | `14` | `10` (`71,4%`) | **`4`** (`28,6%`) |

Os `4` descartes indispensáveis no `E4` explicam a diferença factual entre `E1` (`100%`) e `E4` (`86,7%`). Mesmo assim, `E4` superou o Baseline `Dense Top-12` em precisão factual (`86,7%` vs `80,0%`) consumindo **73,4% menos tokens totais** e **34,9% menos latência**.
