# Relatório da Rodada 3 — Dataset de 100 Perguntas, Métricas de IR e Reteste `CODE2` (`rrf-elbow-v2-lexical`)

**Data:** 2026-11-18  
**Versão do Algoritmo:** `rrf-elbow-v2-lexical` (auto `book_filter` + Multi-Query RRF + `$contains` para identificadores + lexical boost)  
**Modelo:** `qwen2.5:14b` (`temperature = 0.0`, `seed = 42`) | **Embeddings:** `nomic-embed-text`  
**Dataset:** [eval_dataset_100.json](file:///c:/Users/hades/Documents/reductor-prompt/eval_dataset_100.json) (25 factual, 20 code, 20 architecture, 15 contradiction, 10 structure, 10 `no_evidence`)  
**Dados brutos:** [eval_results_100.json](file:///c:/Users/hades/Documents/reductor-prompt/eval_results_100.json)

---

## 1. Reteste de `CODE2_sqlalchemy_repo` (com `$contains` + `book_filter` automático)

- **Resultado:** **`has_sqlalchemy_class = True`** (sucesso).
- **Fontes recuperadas:** `Architecturepatternswithpython` — páginas `82`, `60`, `61`, `62`.
- O fallback lexical `$contains` no ChromaDB trouxe a definição real da classe `SqlAlchemyRepository` que antes ficava fora do `top_k=12` vetorial.

---

## 2. Métricas de Recuperação (IR) — 90 Perguntas Respondíveis com Gabarito

Critério de acerto: `chunk_id` idêntico ao gabarito **ou** `(book_title, page_number)` idênticos.

| Métrica (90 perguntas) | Baseline (RAG Convencional Top-10) | ReductorPrompt `v2` | Delta |
| :--- | :---: | :---: | :---: |
| **Precision@5** | `0,2333` | **`0,2400`** | **+2,9%** |
| **Recall@5** | `0,6111` | **`0,6444`** | **+5,4%** (`+3,33 p.p.`) |
| **Recall@10** | `0,6889` | **`0,7333`** | **+6,4%** (`+4,44 p.p.`) |
| **MRR** | `0,5249` | **`0,5396`** | **+2,8%** |

---

## 3. Comparativo Ponta a Ponta (E2E LLM — 30 Perguntas Estratificadas)

Amostra: `20` respondíveis (`5 factual`, `5 code`, `5 architecture`, `3 contradiction`, `2 structure`) + `10` `no_evidence`.

| Métrica | Cenário A (Convencional Top-10) | Cenário B (Reductor `v2` Padrão) | Delta |
| :--- | :---: | :---: | :---: |
| **Tokens de Entrada Médios (`prompt_eval_count`)** | `3.119,6` | **`2.157,0`** | **-30,9%** |
| **Tokens de Saída Médios (`eval_count`)** | `156,1` | `217,6` | **+39,4%** |
| **Latência Média** | `1.703,3 ms` | `2.034,6 ms` | **+19,4%** |
| **Recusa em `no_evidence` (10 perguntas)** | — | **`10 / 10` (100%)** | `0` alucinações |
| **Acerto de Livro no Top-4 (20 respondíveis)** | — | **`15 / 20` (75%)** | — |
| **Acerto de Página Exata no Top-4 (20 respondíveis)** | — | **`9 / 20` (45%)** | — |

---

## 4. Leitura Técnica Honesta

1. **IR superior ao Baseline**: o `rrf-elbow-v2-lexical` superou o RAG Convencional Top-10 em todas as 4 métricas (`Precision@5`, `Recall@5`, `Recall@10` e `MRR`) nas 90 perguntas ancoradas em páginas reais.
2. **Economia de entrada vs. latência**: redução real de **30,9%** nos tokens de entrada (`3.119,6` → `2.157,0`), com aumento de **+19,4%** na latência (`1,70s` → `2,03s`) devido às múltiplas queries do RRF e à resposta um pouco mais longa (`217,6` vs `156,1` tokens).
3. **Limitação aberta**: o acerto de página exata no top-4 (`9/20 = 45%`) ocorre principalmente porque perguntas geradas sem o nome do livro no enunciado frequentemente casam com páginas de *outros* livros sobre o mesmo tema na biblioteca de 194+ obras (ainda que a resposta seja tecnicamente válida).
