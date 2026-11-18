# Relatório de Prontidão para Produção — ReductorPrompt (`hybrid-bm25-v4`)

**Data:** 2026-11-18  
**Decisão Objetiva:** **🟡 APROVADO COM RESSALVAS PARA PRODUÇÃO**  
**Referências:** [round_9_final_quality_audit.md](file:///c:/Users/hades/Documents/reductor-prompt/docs/benchmarks/round_9_final_quality_audit.md) | [human_quality_review.json](file:///c:/Users/hades/Documents/reductor-prompt/docs/benchmarks/human_quality_review.json) | [recovery_consistency_tests.json](file:///c:/Users/hades/Documents/reductor-prompt/docs/benchmarks/recovery_consistency_tests.json)

---

## 1. Critérios Validados (Prontos)

| Critério | Evidência Observada | Status |
| :--- | :--- | :---: |
| **Testes de Regressão** | `73 passed` (`pytest -q`) sem falhas | 🟢 |
| **Recuperação Híbrida (`Dense + BM25`)** | `Recall@10 = 0,7667`, `MRR = 0,6328`, `Book@4 = 91,67%`, `Page@4 = 70,00%` (held-out `60Q`) | 🟢 |
| **Consistência e Reconciliação de Índices** | `72.360 == 72.360` (`in_sync: true`), reconciliação automática via `rebuild_from_chroma()`, `0` órfãos | 🟢 |
| **Concorrência da API REST (`PM2`)** | `6/6` HTTP `200` simultâneos em `2,78s`; fallback controlado caso FTS5 falhe | 🟢 |
| **Recusa em `no_evidence`** | `10/10` (`100%`) nos 3 perfis (`fidelity`, `economy`, `legacy`) | 🟢 |
| **Rollback Operacional** | `profile="legacy"` retorna ao pipeline anterior sem reiniciar o servidor | 🟢 |

---

## 2. Ressalvas Objetivas (Ações Recomendadas Pós-Auditoria)

1. **Promover `economy` como padrão ou corrigir `example.com` no `fidelity`**:
   - Na auditoria independente (Gemini 4 Hydrogen, `15Q`), **`economy` superou `fidelity`** em correção factual (`93,3%` vs `86,7%`), fidelidade estrita (`93,3%` vs `73,3%`), tokens totais (`1.569,1` vs `3.717,9`, **-57,8%**) e latência (`1.286,3 ms` vs `1.754,7 ms`).
   - Adicionar uma linha no prompt conciso proibindo explicitamente a criação de URLs externas (`"Nunca invente URLs ou links que não estejam literalmente no contexto"`).
2. **Alinhar `scripts/harness_check.py` / `rebuild_from_chroma` no startup**:
   - Incluir checagem `verify_consistency()` automática na inicialização ou no `harness_check.py` para detectar desvios ChromaDB ↔ FTS5 após quedas abruptas.
