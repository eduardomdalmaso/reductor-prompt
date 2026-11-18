# Rodada 9 — Auditoria Final de Qualidade (`hybrid-bm25-v4`)

**Data:** 2026-11-18  
**Avaliador Independente:** Gemini 4 Hydrogen (auditoria item a item das `15` respostas completas contra os trechos gabarito)  
**Testes Automatizados:** `73 passed` (`pytest -q`) | **Pipeline:** sem alterações durante a auditoria  
**Dados brutos:** [human_quality_review.json](file:///c:/Users/hades/Documents/reductor-prompt/docs/benchmarks/human_quality_review.json) | [recovery_consistency_tests.json](file:///c:/Users/hades/Documents/reductor-prompt/docs/benchmarks/recovery_consistency_tests.json)

---

## 1. Comparação dos 3 Perfis (`25` Perguntas E2E: `15` Held-out + `10` `no_evidence`)

| Perfil | Entrada Média | Saída Média | Total Médio | Latência Média | Citações Auto (`15`) | Recusa (`10`) | Correção Factual (Gemini 4 Hydrogen, `15`) | Fidelidade Estrita (Gemini 4 Hydrogen, `15`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`fidelity` (E1)** | `3.608,6` | `109,3` | `3.717,9` | `1.754,7 ms` | `14/15` (`93,3%`) | **`10/10` (`100%`)** | `13/15` (`86,7%`) | `11/15` (`73,3%`) |
| **`economy` (E4)** | **`1.472,6`** | `96,5` | **`1.569,1`** | **`1.286,3 ms`** | `14/15` (`93,3%`) | **`10/10` (`100%`)** | **`14/15` (`93,3%`)** | **`14/15` (`93,3%`)** |
| **`legacy` (rollback)** | `2.566,6` | **`94,4`** | `2.661,0` | `1.309,3 ms` | **`15/15` (`100%`)** | **`10/10` (`100%`)** | — | — |

---

## 2. Divergências Identificadas pela Auditoria Independente (`15` Respostas)

1. **`Q009_factual` (Erro factual no `fidelity`)**: `fidelity` afirmou *"with higher scores preceding lower scores"* (invertendo a ordem crescente de Sorted Sets do Redis); `economy` respondeu corretamente (*"from the lowest to the highest"*).
2. **URLs fabricadas (`Q003`, `Q017`, `Q023` no `fidelity`)**: `qwen2.5:14b` gerou links fictícios `https://example.com/redis-core-...` e citou `p. 134` não recuperada em `Q023`. **`economy` teve `0` URLs `example.com`**.
3. **`Q002_factual` (Ambos)**: recuperaram `p. 73` (tutorial anterior de JSON) em vez de `p. 92` (`bikes:inventory`).
4. **`Q005_factual` (Ambos)**: resposta correta (`dictionary`), mas vinda de `Redis Ai Vector Search` (`p. 738`/`742`) em vez de `Redis Core` (`p. 9`).

---

## 3. Resiliência, Reconciliação e Concorrência da API

- **Interrupção na ingestão** (ChromaDB atualizado sem FTS5): `verify_consistency()` detectou o desvio (`delta = +1`) e `rebuild_from_chroma()` reconciliou para `in_sync: true`.
- **Interrupção na exclusão** (ChromaDB deletado sem FTS5): `verify_consistency()` detectou o desvio (`delta = -1`), `rebuild_from_chroma()` + `invalidate_query_cache()` restauraram `72.360 == 72.360` (`in_sync: true`, `0` chunks órfãos).
- **Concorrência na API (`http://127.0.0.1:8002/api/v1/query`)**: **`6/6` requisições simultâneas** (`fidelity`, `economy`, `legacy`) responderam HTTP `200` em `2.784,1 ms` totais (`0` erros).
