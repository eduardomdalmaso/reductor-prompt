# Rodada 8 — Relatório de Integração Controlada (`hybrid-bm25-v4`)

**Data:** 2026-11-18  
**Versão:** `hybrid-bm25-v4` / `qa-v3-concise` (`profile="fidelity"` padrão, `"economy"` alternativo, `"legacy"` rollback)  
**Testes Unitários / Regressão:** `73 passed` (`pytest -q`)  
**Dados brutos:** [integration_test_results.json](file:///c:/Users/hades/Documents/reductor-prompt/docs/benchmarks/integration_test_results.json) | [index_consistency_report.json](file:///c:/Users/hades/Documents/reductor-prompt/docs/benchmarks/index_consistency_report.json) | [independent_quality_review.json](file:///c:/Users/hades/Documents/reductor-prompt/docs/benchmarks/independent_quality_review.json)

---

## 1. Consistência dos Índices (ChromaDB ↔ SQLite FTS5)

| Etapa | `chroma_chunks` | `bm25_chunks` | `in_sync` |
| :--- | :---: | :---: | :---: |
| Inicial | `72.360` | `72.360` | `True` (`delta=0`) |
| Após `upsert` de livro teste | `72.361` | `72.361` | `True` (`BM25` encontrou o chunk) |
| Após `delete` + `invalidate_query_cache()` | `72.360` | `72.360` | `True` (`delta=0`) |

---

## 2. Resultados E2E Integrados via `QueryBooksUseCase` (`25` Perguntas Held-out)

| Perfil Integrado | Entrada Média | Saída Média | Total Médio | Latência Média | Citações OK (`15`) | Recusa `no_evidence` (`10`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`fidelity` (`Top-10` + `Conservative 5%` + proteção de livro único)** | `3.608,6` | `109,3` | `3.717,9` | `1.754,7 ms` | **`14/15` (`93,3%`)** | **`10/10` (`100%`)** |
| **`economy` (`Top-12` + `Balanced` + proteção de livro único)** | **`1.472,6`** | **`96,5`** | **`1.569,1`** (`-57,8%` vs `fidelity`) | **`1.286,3 ms`** | **`14/15` (`93,3%`)** | **`10/10` (`100%`)** |

**Observação honesta:** a proteção de livro único adicionada em `compress_and_format` preservou mais livros distintos no contexto, elevando a entrada média do `economy` de `735,5` (Rodada 7) para `1.472,6` tokens (ainda ~50% abaixo do baseline `Dense Top-12` de `2.979,1` tokens) e mantendo `14/15` citações corretas e `10/10` recusas.

---

## 3. Revisão Independente e Rollback

- **Revisão independente**: as `15` respostas respondíveis de `fidelity` e `economy` foram registradas integralmente com overlap lexical e verificação de citações em [independent_quality_review.json](file:///c:/Users/hades/Documents/reductor-prompt/docs/benchmarks/independent_quality_review.json) (com status `PENDING_HUMAN_SIGN_OFF` para revisão humana, pois não há chave de outro provedor LLM configurada neste ambiente).
- **Rollback operacional**: passar `profile="legacy"` no `POST /api/v1/query` ou em `QueryBooksUseCase.execute()` desativa imediatamente o `BM25SqliteIndex` e retorna ao pipeline `Dense + RRF` anterior sem reiniciar o servidor.
