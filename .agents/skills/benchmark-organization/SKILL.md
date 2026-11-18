---
name: benchmark-organization
description: Padrão de organização de benchmarks, relatórios .md e testes no ReductorPrompt para evitar arquivos soltos na raiz, economizar tokens de contexto e manter rastreabilidade entre rodadas. Use sempre que executar avaliações de RAG, gerar relatórios técnicos ou criar novos testes.
---

# Organização de Benchmarks, Relatórios `.md` e Testes

## 1. Onde cada arquivo deve ficar (Zero arquivos soltos na raiz)
- **Relatórios e datasets de avaliação**: salvar exclusivamente em `docs/benchmarks/` (ex.: `docs/benchmarks/round_4.md`, `docs/benchmarks/eval_dataset_100.json`). Nunca criar `.md` ou `.json` de experimento na raiz do repositório.
- **Scripts de experimento pontuais**: salvar no diretório `scratch/` da sessão; promover para `scripts/` apenas se for utilitário permanente (`<= 200` linhas).
- **Testes automatizados de regressão**: ficam exclusivamente em `tests/` e devem rodar rápido via `pytest` sem depender de LLM externa ou GPU.

## 2. Economia de Tokens em `.md` e `.json`
- **Um `.md` por rodada**: consolide achados (IR, E2E, cache, PDF) em um único arquivo (`docs/benchmarks/round_N.md`) em vez de gerar múltiplos `.md` fragmentados.
- **Tabelas e deltas, nunca dumps**: em `.md`, registre apenas métricas agregadas, deltas vs. baseline e no máximo exemplos curtos (`<= 200` caracteres) para falhas/alucinações.
- **Não ler JSONs brutos inteiros no contexto**: para analisar resultados, execute um script Python curto que imprima apenas médias, contagens e falhas.
- **Retenção enxuta**: preserve os datasets de gabarito (`eval_dataset_*.json`) e os relatórios `.md`; remova ou arquive JSONs intermediários redundantes quando não forem mais necessários.

## 3. Rastreabilidade Obrigatória
Todo relatório em `docs/benchmarks/round_N.md` deve conter no cabeçalho:
1. **Versão do algoritmo** (ex.: `rrf-elbow-v3-grounded`).
2. **Modelo LLM, Embedding e parâmetros** (`temperature`, `seed`, `top_k`).
3. **Tamanho real da amostra** (ex.: `90` IR + `30` E2E) e fonte do gabarito.
4. **Comparabilidade**: nunca sobrescrever ou editar resultados de rodadas anteriores; cada mudança no pipeline gera uma nova versão identificável.
