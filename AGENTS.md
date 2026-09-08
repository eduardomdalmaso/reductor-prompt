# Diretrizes do Agente - ReductorPrompt

## 🧠 Instruções de Comportamento para o Agente

1. **Economia Estrita de Tokens**:
   - Nunca tente ler ou concatenar livros brutos (.pdf, .epub, etc.) diretamente no prompt ou na janela de contexto.
   - Sempre utilize o CLI de consulta (`query.py`) para obter o contexto reduzido e cirúrgico com relevância semântica.

2. **Isolamento de Ambiente**:
   - Sempre execute os scripts do projeto utilizando o Python do Conda:
     `/home/hades/miniconda3/envs/reductor-prompt/bin/python`
   - O banco vetorial ChromaDB deve ser acessado via Podman na porta `8001` (`http://127.0.0.1:8001`) ou modo local como fallback.

3. **Análise Cruzada de Projetos**:
   - Quando o usuário solicitar comparações entre seu código/arquitetura e a teoria dos livros, utilize o caso de uso `analyze` via `query.py analyze --project "..." --topic "..."`.
   - Estruture a resposta em: Diagnóstico, Oportunidades de Otimização, Riscos/Trade-offs, Plano de Ação e Citações de Fontes.
