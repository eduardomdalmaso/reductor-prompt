# Diretrizes do Agente - ReductorPrompt

## 🧠 Instruções de Comportamento para Agentes de IA

1. **Economia Estrita de Tokens (>95%)**:
   - **Nunca** tente ler ou concatenar livros brutos (`.pdf`, `.epub`, etc.) diretamente no prompt ou na janela de contexto.
   - Sempre utilize o CLI de consulta (`query.py`) ou o MCP Server (`reductor-books`) para obter o contexto reduzido e cirúrgico com relevância semântica calculada.

2. **Isolamento de Ambiente e Execução**:
   - Sempre execute os scripts do projeto utilizando o ambiente Conda (`reductor-prompt`):
     `conda run -n reductor-prompt python <script>` ou `python <script>` (com o ambiente ativo).
   - O banco vetorial ChromaDB deve ser acessado prioritariamente via Podman na porta `8001` (`http://127.0.0.1:8001`) ou modo persistente local (`./storage/chroma`) como fallback automático.

3. **Modos de Consulta e Raciocínio**:
   - **Consulta Padrão com Expansão**: `python query.py "sua pergunta"` (utiliza Multi-Query e fusão RRF).
   - **Raciocínio Profundo (`--deep`)**: `python query.py "sua pergunta" --deep` (ativa Chain-of-Thought e Auto-Reflexão com validação de fontes).
   - **Download Dinâmico (`fetch`)**: `python query.py fetch "<urls>" [--ingest]` para baixar repositórios, pastas ou links diretos com deduplicação criptográfica SHA-256.

4. **Análise Cruzada de Projetos**:
   - Quando o usuário solicitar comparações entre seu código/arquitetura e a teoria dos livros, utilize:
     `python query.py analyze --project "..." --topic "..."`
   - Estruture a resposta rigorosamente em:
     1. 🎯 **Diagnóstico e Alinhamento Teórico**
     2. 🚀 **Oportunidades de Otimização**
     3. ⚠️ **Riscos Arquiteturais e Trade-offs**
     4. 📋 **Plano de Ação Recomendado**
     5. 📖 **Citações de Fontes (Livro, Capítulo e Página)**

5. **Diretrizes de Hardware e Provedores LLM**:
   - **Ollama Local (RTX 5090 / 4090 / 3090)**: Use modelos `qwen2.5:14b` ou `qwen2.5:32b` para raciocínio técnico sem custo de API.
   - **Ollama Local (GPUs 8GB - 16GB)**: Use `qwen2.5:7b` ou `llama3.1:8b`.
   - **Gemini API**: Use `LLM_PROVIDER=gemini` como fallback para máquinas sem GPU dedicada.

6. **Harness Engineering & Continuidade de Estado**:
   - Consulte `PROGRESS.md` para verificar o estado atual e evitar amnésia de contexto.
   - Valide a integridade do ambiente e testes executando: `python scripts/harness_check.py`.

7. **🗺️ Mapa de Especialidades da Biblioteca Técnica (194 Livros Indexados)**:
   - **Visão Computacional & Imagens**: *Learning OpenCV 4*, *Modern Computer Vision with PyTorch 2E*, *Computer Vision Algorithms*.
   - **LLMs, RAG & Transformers**: *Hands-On Large Language Models (O'Reilly)*, *Generative AI Design Patterns*, *Prompt Engineering*.
   - **Engenharia de Alta Performance & Streaming**: *Pion WebRTC Media Guide*, *Go Rust Video Pipeline*, *Concurrency in Go*, *Zero-Copy Memory*.
   - **Arquitetura, Harness & Agentes Autônomos**: *Learn Harness Engineering*, *AI Agents In Depth*, *Domain-Driven Design (DDD)*.
   - **Bancos de Dados, Storage & Sistemas Distribuídos**: *Database Internals (LSM-Trees, B-Trees, Raft)*, *Polars & Data Engineering*.

8. **🔄 Cruzamento Multi-Livros & Síntese Interdisciplinar**:
   - Para problemas complexos ou de ponta a ponta, **não restrinja a busca a um único livro** (`book_filter=None`).
   - O pipeline vetorial realiza busca global com fusão RRF, permitindo que a LLM sintetize soluções cruzando múltiplos autores (ex: rede em Go + decodificação em Rust + inferência PyTorch).
   - Sempre cite as fontes de cada camada da solução final.

9. **🧠 Triangulação Cognitiva & Validação de Raciocínio (Peer Review com Livros e LLM)**:
   - O Agente de IA pode e deve **validar seu próprio pensamento** consultando a biblioteca técnica E acionando a LLM local (Ollama) ou API (Gemini).
   - **Fluxo de Validação**: Submeta sua hipótese/plano técnico para a ferramenta MCP `validate_reasoning` ou `search_books(query="...", use_local_llm=True)` ou execute `python query.py analyze --project "..." --topic "..."`.
   - **Julgamento Crítico**: Compare ativamente o raciocínio gerado com o seu próprio para avaliar se sua proposta é:
     - 🎯 **Convergente** (alinhada aos padrões dos livros).
     - 🚀 **Superior** (otimizada para o contexto específico do usuário).
     - ⚠️ **Inferior ou com Riscos** (quando os livros alertam sobre trade-offs, gargalos ou anti-patterns que você não havia considerado).
   - Sintetize essa comparação com transparência para o usuário.

10. **Modularidade Estrita e Limites de Linhas por Arquivo (Zero Monólitos)**:
    - **Princípio da Responsabilidade Única (SRP)**: Nenhum arquivo deve acumular múltiplas responsabilidades.
    - **Arquitetura Puramente Terminal (CLI) + REST API + MCP**: O projeto não possui acoplamento de desktop ou UI legada. Todas as interfaces de entrada residem em `src/adapters/inbound/` (CLI, API FastAPI e MCP Server).
    - **Controladores e Handlers CLI/API**: Máximo de **180 linhas** por módulo. Módulos que excederem esse limite devem ser decompostos em submódulos (`formatters.py`, `chat_handler.py`, `routes/`, `dtos/`).
    - **Scripts e Módulos Python (`.py`)**: Máximo de **200 linhas** por arquivo.


