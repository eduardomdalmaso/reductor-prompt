# Relatório da Rodada 4 — Rastreabilidade por Trecho, Citation Grounding e Otimização (`rrf-elbow-v3-grounded`)

**Data:** 2026-11-18  
**Versão do Algoritmo:** `rrf-elbow-v3-grounded` (`embed_batch`, `top_k=16`, boost de termos compostos, spans por chunk e `verify_citation_grounding`)  
**Dataset:** [eval_dataset_100.json](file:///c:/Users/hades/Documents/reductor-prompt/eval_dataset_100.json) | **Dados brutos:** [eval_results_round4.json](file:///c:/Users/hades/Documents/reductor-prompt/eval_results_round4.json)  
**Referência anterior (Rodada 3):** [benchmark_round_3_100q.md](file:///c:/Users/hades/Documents/reductor-prompt/benchmark_round_3_100q.md)

---

## 1. Comparativo IR (90 Perguntas Respondíveis) — Rodada 3 vs. Rodada 4

| Métrica | Rodada 3 (`v2`) | Rodada 4 (`v3`) | Delta |
| :--- | :---: | :---: | :---: |
| **Precision@5** | `0,2400` | `0,2400` | `0,0%` |
| **Recall@5** | `0,6444` | `0,6444` | `0,0%` |
| **Recall@10** | `0,7333` | `0,7222` | `-1,5%` |
| **MRR** | `0,5396` | **`0,5456`** | **+1,1%** |

---

## 2. Comparativo E2E LLM (30 Perguntas Estratificadas, `qwen2.5:14b`)

| Indicador | Rodada 3 (`v2`) | Rodada 4 (`v3`) | Observação |
| :--- | :---: | :---: | :--- |
| **Tokens de Entrada Médios** | `2.157,0` | `2.195,5` | Estável (~30% abaixo do baseline `3.119,6`) |
| **Tokens de Saída Médios** | `217,6` | `213,6` | Estável |
| **Latência Média** | `2.034,6 ms` | `2.075,8 ms` | >95% do tempo está na geração LLM, não no embedding |
| **Recusa em `no_evidence` (10)** | `10 / 10` (100%) | **`10 / 10` (100%)** | `0` alucinações |
| **Acerto de Livro no Top-4 (20)** | `15 / 20` (75%) | `15 / 20` (75%) | Inalterado sem `book_filter` |
| **Acerto de Página Exata no Top-4 (20)** | `9 / 20` (45%) | `9 / 20` (45%) | Inalterado sem `book_filter` |
| **Citation Grounding Médio (`30`)** | — | **`0,9722` (97,2%)** | Detectou `1` caso (`Q068_contradiction`) com 5 páginas não recuperadas (`[84, 94, 111, 120, 126]`) |

---

## 3. Conclusões Técnicas da Rodada 4

1. **Rastreabilidade e Grounding funcionam**: todos os `sources` agora retornam `chunk_id`, `book_id`, `page_start`/`page_end`, `char_start`/`char_end` e `excerpt_preview`. O `verify_citation_grounding` detectou automaticamente a única resposta com páginas inventadas (`Q068_contradiction`, `grounding_ratio = 0,1667`).
2. **Por que `Book Hit` (75%) e `Page Hit` (45%) não subiram**: aumentar `top_k` de `12` para `16` e fazer boost de termos compostos melhorou o `MRR` (`0,5396` → `0,5456`), mas perguntas abertas que não citam o título do livro continuam sendo atraídas por livros concorrentes do mesmo tema no índice denso.
3. **Por que a latência não caiu com `embed_batch`**: o tempo de embedding é mínimo (<50 ms) frente aos ~2.000 ms de geração de ~214 tokens de saída no `qwen2.5:14b`. Reduzir a latência abaixo de `+15%` exige limitar tokens de saída (`num_predict` / concisão no prompt), não apenas otimizar embeddings.

---

## 4. Auditoria das 11 Falhas de Página e Estudo de Ablação (5 Configurações)

**Dados brutos:** [retrieval_failure_analysis.json](file:///c:/Users/hades/Documents/reductor-prompt/docs/benchmarks/retrieval_failure_analysis.json)

### 4.1 Onde a evidência desapareceu nas 11 perguntas que falharam a página esperada

| Causa Raiz | Quantidade | % |
| :--- | :---: | :---: |
| `NEVER_RETRIEVED` (não entrou no Dense Top-20 nem no RRF) | **`7`** | **63,6%** |
| `DROPPED_BY_COMPRESSOR` (estava no RRF, mas cortada pelo Elbow/orçamento) | **`3`** | **27,3%** |
| `PRESENT_IN_FINAL_CONTEXT` (chegou no contexto final, fora do top-6) | **`1`** | **9,1%** |

### 4.2 Estudo de Ablação (90 Perguntas Respondíveis, mesmos documentos e parâmetros)

| Configuração | `Recall@5` | `Recall@10` | `MRR` | `Book@4` | `Page@4` |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **1. `Dense only`** | `0,6111` | `0,6889` | `0,5249` | **`0,8889`** | `0,5556` |
| **2. `Dense + lexical` (`$contains` + boost)** | **`0,6444`** | **`0,7333`** | **`0,5385`** | `0,8778` | **`0,5778`** |
| **3. `Dense + Multi-Query RRF`** | `0,6111` | `0,6778` | `0,5236` | `0,8889` | `0,5556` |
| **4. `Dense + RRF + Elbow`** | `0,5889` | `0,6111` | `0,5128` | `0,8778` | `0,5556` |
| **5. `Pipeline completo + roteamento`** | `0,5889` | `0,6111` | `0,5269` | `0,8667` | **`0,5778`** |

**Conclusão causal definitiva:**
1. O maior ganho real de recuperação vem do **reforço lexical** (`2_dense_lexical` vence em `Recall@5 = 0,6444`, `Recall@10 = 0,7333`, `MRR = 0,5385` e `Page@4 = 0,5778`).
2. O **Elbow Cutoff atual** derruba `Recall@10` de `0,6778` para `0,6111` (`-6,67 p.p.`), explicando os **27,3% (`3/11`)** de evidências descartadas após a recuperação.
3. Os outros **63,6% (`7/11`)** nunca chegam nem ao Top-20 denso — exigindo busca híbrida lexical ampla (ex.: BM25) além de `$contains` apenas para identificadores CamelCase/snake_case.
