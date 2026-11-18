# Relatório de Benchmark Real — ReductorPrompt vs. RAG Convencional

**Data:** 2026-11-18  
**Corpus:** `./storage/chroma` (biblioteca local completa indexada com `nomic-embed-text`)  
**Modelo LLM:** `qwen2.5:14b` via Ollama (`http://127.0.0.1:11434/api/chat`)  
**Parâmetros de Geração:** `temperature = 0.0`, `seed = 42`, aquecimento prévio executado (`40.289 ms` cold load), cache limpo entre todas as rodadas.  
**Amostra:** 5 perguntas obrigatórias × 3 cenários × 3 execuções = **45 chamadas reais** (`0` erros, `0` timeouts).  
**Dados brutos:** [benchmark_results.json](file:///c:/Users/hades/Documents/reductor-prompt/benchmark_results.json) | **Perguntas:** [test_questions.json](file:///c:/Users/hades/Documents/reductor-prompt/test_questions.json)

---

## 1. Diferença de Prompt entre os Cenários

- **Cenário A (`A_conventional_topk12`)**: Busca vetorial simples (`top_k=12` sem *query rewriting*, sem *Elbow Cutoff* e sem truncamento de orçamento). System prompt direto pedindo resposta baseada no contexto e recusa explícita se não houver resposta.
- **Cenário B (`B_reductor_standard`)**: `QueryBooksUseCase` com `enable_rewriting=True`, fusão RRF, *Elbow Cutoff*, orçamento dinâmico e `deep_reasoning=False` (`use_brain=False`).
- **Cenário C (`C_reductor_deep`)**: Idêntico ao Cenário B na recuperação, mas com `deep_reasoning=True`, alterando o `system_instruction` para exigir resposta estruturada em 4 seções (Fundamentos, Aplicação Prática, Auto-Validação e Citações).

---

## 2. Resultados Agregados (Média de 15 execuções por cenário)

| Métrica (Média) | Cenário A (Convencional Top-12) | Cenário B (Reductor Padrão) | Cenário C (Reductor Deep) | Delta B vs A | Delta C vs A |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Tokens de Entrada (`prompt_eval_count`)** | `3.901,0` | `2.432,8` | `2.496,8` | **-37,6%** | **-36,0%** |
| **Tokens de Saída (`eval_count`)** | `328,7` | `399,4` | `770,8` | **+21,5%** | **+134,5%** |
| **Tokens Totais (Entrada + Saída)** | `4.229,7` | `2.832,2` | `3.267,6` | **-33,0%** | **-22,7%** |
| **Latência LLM (`llm_latency_ms`)** | `2.921,6 ms` | `3.312,1 ms` | `6.275,1 ms` | **+13,4%** | **+114,8%** |
| **Latência Total (`total_latency_ms`)** | `2.944,1 ms` | `3.366,0 ms` | `6.329,0 ms` | **+14,3%** | **+115,0%** |
| **Erros / Timeouts** | `0` | `0` | `0` | `0` | `0` |

> **Conclusão numérica honesta:** A redução real de tokens de entrada do ReductorPrompt frente ao RAG Convencional Top-12 foi de **37,6%** (Padrão) e **36,0%** (Deep) — e não 98%. Em contrapartida, o modo `--deep` aumentou os tokens de saída em **+134,5%** e mais que dobrou a latência (**+115,0%**).

---

## 3. Resultados por Pergunta Obrigatória (Média de 3 execuções)

| Pergunta | Cenário A (`in` / `out` / `ms`) | Cenário B (`in` / `out` / `ms`) | Cenário C (`in` / `out` / `ms`) | Fidelidade & Comportamento Observado |
| :--- | :---: | :---: | :---: | :--- |
| **Q1 (Respondível)** — Repository pattern em *Architecture Patterns with Python* | `3.620` / `304,0` / `2.645,6 ms` | `1.964` / `372,3` / `3.068,6 ms` | `2.028` / `644,0` / `5.219,2 ms` | Todos os 3 citaram `Architecturepatternswithpython` (p. 49, p. 1, p. 14) e explicaram o desacoplamento corretamente. B economizou **45,7%** de entrada. |
| **Q2 (Parcial)** — Latência p99 do ReductorPrompt na RTX 5090 | `2.404` / `77,0` / `767,6 ms` | `955` / `131,0` / `1.141,2 ms` | `1.019` / `674,0` / `5.276,8 ms` | Todos recusaram/indicaram ausência dos dados do ReductorPrompt (fontes recuperadas eram de Redis/Polars). C gerou `674` tokens de saída mesmo sem evidência. |
| **Q3 (Inexistente)** — Senha de API e canal Slack do Komtek K-Monitor | `3.108` / `111,3` / `1.077,0 ms` | `2.743` / `116,0` / `1.092,9 ms` | `2.807` / `923,7` / `7.582,8 ms` | Todos recusaram sem inventar credenciais. Porém, o RRF normalizou o score dos chunks irrelevantes de Redis para `1.0`; C gastou `923,7` tokens de saída (`7,58s`) para recusar. |
| **Q4 (Contraditória)** — Microservices vs. Modular Monolith | `6.704` / `581,3` / `5.358,9 ms` | `4.167` / `682,7` / `5.892,6 ms` | `4.231` / `908,7` / `7.837,6 ms` | Todos apresentaram prós/contras de ambos os lados citando `Buildingmicroservices2Ndedition` (p. 97, p. 58, p. 36). B economizou **37,8%** de entrada. |
| **Q5 (Código Técnico)** — `Batch`, `OrderLine` e `allocate` | `3.669` / `570,0` / `4.871,2 ms` | `2.335` / `695,0` / `5.634,8 ms` | `2.399` / `703,7` / `5.728,8 ms` | Todos recuperaram `Architecturepatternswithpython` (p. 45–46) e preservaram estrutura Python válida das classes e função. |

---

## 4. Achados Críticos e Veredito da Validação

1. **Economia de entrada é real, mas moderada (36%–38%)**: o *Elbow Cutoff* + orçamento dinâmico cortaram ~37,6% dos tokens de entrada em relação ao Top-12 sem corte, mantendo a qualidade factual nas 5 perguntas.
2. **Trade-off de saída e latência no modo `--deep`**: o `--deep` não executa segunda passada de verificação; apenas força 4 seções no prompt. Em perguntas inexistentes (`Q3`) ou parciais (`Q2`), isso multiplicou os tokens de saída em **6× a 8×** (`923,7` vs `111,3` tokens em `Q3`), piorando custo e latência sem ganho factual.
3. **Normalização do RRF mascara irrelevância absoluta**: em `Q3_nonexistent`, chunks de `Redis Operations Clustering And Kubernetes` apareceram com `score = 1.0` após normalização RRF, embora a similaridade cosseno original fosse `~0.688`. A recusa funcionou porque o `qwen2.5:14b` respeitou o prompt, não porque o recuperador bloqueou a busca.
4. **Custo financeiro**: todos os testes rodaram localmente em `qwen2.5:14b` + `nomic-embed-text` (custo direto de API = \$0,00; em APIs pagas por token, Cenário B reduziria custo de entrada em ~37,6% e aumentaria saída em ~21,5%).
