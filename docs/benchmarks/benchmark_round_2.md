# Relatório da Rodada 2 — Experimentos Separados e Testes de Estresse

**Data:** 2026-11-18  
**Modelo:** `qwen2.5:14b` (`temperature = 0.0`, `seed = 42`, aquecimento prévio) | **Embeddings:** `nomic-embed-text`  
**Parâmetros do Elbow Cutoff:** mantidos inalterados (`DYNAMIC_ELBOW_MAX_RELATIVE_DROP=0.35`, `DYNAMIC_ELBOW_MAX_STEP_DROP=0.22`).  
**Referência da Rodada 1:** [benchmark_report.md](file:///c:/Users/hades/Documents/reductor-prompt/benchmark_report.md)

---

## 1. Teste 1 — Sensibilidade ao Corte (Experimento A: Recuperação Isolada)

Mesmo prompt padrão, mesmo modelo e mesmas 5 perguntas (`S1_repo`, `S2_uow`, `S3_ddd`, `S4_wal`, `S5_micro`) variando apenas o orçamento de corte sobre os 12 chunks recuperados.  
**Dados brutos:** [cutoff_sensitivity.json](file:///c:/Users/hades/Documents/reductor-prompt/cutoff_sensitivity.json)

| Corte Solicitado | Faixa de Corte Efetivo | Tokens de Entrada Médios (`prompt_eval_count`) | Cobertura Factual Média (`facts_hit / expected`) |
| :---: | :---: | :---: | :---: |
| **0%** (baseline) | `0.0%` | `4.192,6` | **0,80** (`4/4, 3/4, 3/3, 2/4, 3/4`) |
| **10%** | `10.5% – 22.1%` | `3.508,2` | **0,65** (`3/4, 2/4, 3/3, 1/4, 3/4`) |
| **20%** | `20.8% – 32.9%` | `3.229,6` | **0,65** (`2/4, 3/4, 3/3, 1/4, 3/4`) |
| **30%** | `32.9% – 35.9%` | `2.781,6` | **0,58** (`4/4, 2/4, 2/3, 1/4, 3/4`) |
| **40%** | `42.4% – 57.4%` | `2.352,6` | **0,57** (`2/4, 4/4, 1/3, 1/4, 3/4`) |
| **50%** | `50.6% – 59.8%` | `1.979,0` | **0,47** (`0/4, 3/4, 1/3, 1/4, 3/4`) |
| **60%** | `61.8% – 77.2%` | `1.482,0` | **0,42** (`1/4, 3/4, 1/3, 1/4, 2/4`) |

**Leitura técnica:** cortes efetivos acima de **~35%–40%** causam queda acentuada de cobertura factual (ex.: `S1_repo` cai para `0/4` em `50%`; `S3_ddd` cai de `3/3` em `20%` para `1/3` em `40%+`). Isso confirma empiricamente que cortes moderados (**20%–35%**) preservam a maior parte dos fatos, enquanto cortes agressivos degradam a precisão.

---

## 2. Teste 2 — Evidência no Final do Ranking

Avaliação se o `apply_elbow_cutoff` descarta chunks relevantes localizados entre as posições 6 e 12 (`top_k=12`).  
**Dados brutos:** [ranking_position_tests.json](file:///c:/Users/hades/Documents/reductor-prompt/ranking_position_tests.json)

| Pergunta | Chunks Mantidos pelo Elbow | Chunks na Cauda (rank 6–12) com Palavras-Chave | Evidências da Cauda Descartadas |
| :--- | :---: | :---: | :---: |
| `R1_aggregate_invariant` | `12 / 12` | `5` | `0` |
| `R2_strangler_fig` | `12 / 12` | `6` | `0` |
| `R3_backpressure_queue` | `12 / 12` | `6` | `0` |

**Leitura técnica:** nas 3 consultas, a curva de similaridade cosseno caiu suavemente dentro da tolerância do Elbow (`35%` relativo / `0.22` degrau), mantendo `12/12` chunks e **0** evidências da cauda perdidas.

---

## 3. Teste 3 — Contradições entre Livros (Experimento B e C)

Perguntas sobre **Monólito Modular vs. Microsserviços (`C1`)** e **Banco Compartilhado vs. Isolado (`C2`)**.  
**Dados brutos:** [contradiction_tests.json](file:///c:/Users/hades/Documents/reductor-prompt/contradiction_tests.json)

- **Experimento B (Geração Isolada — mesmos 10 chunks para A, B e C)**: os três modos apresentaram os dois lados e explicaram condições de aplicabilidade (sem escolher arbitrariamente um vencedor).
- **Experimento C (Pipeline Completo — `B_std_full` e `C_deep_full`)**: ambos citaram explicitamente recomendações e exceções de *Software Architecture: The Hard Parts* (p. 268) e *Building Microservices* (ex.: `B_std_full` gastou `3.951` entrada / `948` saída em `C2`; `C_deep_full` gastou `4.150` entrada / `744` saída).

---

## 4. Teste 4 — Recusa Econômica após Correção do `--deep` (Experimento B e C)

Comparação em 3 perguntas inexistentes (`N1_komtek`, `N2_protocol`, `N3_salary`) após adicionar a `REGRA DE RECUSA ECONÔMICA` em [prompt_compressor_service.py](file:///c:/Users/hades/Documents/reductor-prompt/src/application/services/prompt_compressor_service.py#L245-L255).  
**Dados brutos:** [refusal_efficiency.json](file:///c:/Users/hades/Documents/reductor-prompt/refusal_efficiency.json)

| Experimento / Cenário | Tokens Entrada (Média) | Tokens Saída (Média) | Latência Média | Recusa Correta / Alucinações |
| :--- | :---: | :---: | :---: | :---: |
| **Rodada 1 (Antes da correção — `Q3` Deep)** | `2.807,0` | **`923,7`** | `7.582,8 ms` | `3/3` recusas / `0` alucinações |
| **Exp B — `A_conv`** | `2.103,0` | `51,0` | `738,7 ms` | `3/3` recusas / `0` alucinações |
| **Exp B — `B_std`** | `2.214,0` | `99,0` | `1.065,2 ms` | `3/3` recusas / `0` alucinações |
| **Exp B — `C_deep_fixed`** | `2.413,0` | **`67,7`** | `876,8 ms` | `3/3` recusas / `0` alucinações |
| **Exp C — `B_std_full`** | `1.772,7` | `96,7` | `986,7 ms` | `3/3` recusas / `0` alucinações |
| **Exp C — `C_deep_fixed_full`** | `1.971,7` | **`70,7`** | `796,3 ms` | `3/3` recusas / `0` alucinações |

**Leitura técnica:** a correção reduziu os tokens de saída do `--deep` em recusa de **`923,7` para `67,7`–`70,7` tokens (-92,3%)** e a latência de **`7,58s` para `0,80s`–`0,88s`**, mantendo `100%` de recusa sem alucinações.

---

## 5. Teste 5 — Fidelidade de Código

**Dados brutos:** [code_fidelity_tests.json](file:///c:/Users/hades/Documents/reductor-prompt/code_fidelity_tests.json)

- **`CODE1_batch_allocate`**: recuperou `Architecturepatternswithpython` (p. 46 e p. 266), **preservou indentação Python (`\n    `)** no contexto recuperado (`retrieved_context_preserves_indentation = True`) e gerou `Batch` / `allocate` fiéis ao livro.
- **`CODE2_sqlalchemy_repo`**: sem `book_filter`, a busca vetorial pura por `"SqlAlchemyRepository"` recuperou trechos de *Introducing Python 3rd Edition* (p. 465, 469) em vez de *Architecture Patterns with Python*. O modelo **recusou corretamente** afirmando que a classe não estava no contexto recuperado (sem alucinar o código).

**Achado importante:** a preservação estrutural do PDF resolveu o achatamento de código quando o chunk certo é recuperado (`CODE1`), mas busca puramente densa sem filtro de livro ou busca lexical/BM25 pode errar identificadores exatos de classe em bibliotecas grandes (`CODE2`).
