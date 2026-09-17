---
name: book-consultant
description: Consulta a biblioteca técnica do ReductorPrompt de forma cirúrgica e com economia máxima de tokens (>95%). Use sempre que o usuário pedir opiniões arquiteturais, boas práticas, otimizações de código (Python, Rust, Polars, Concorrência, TDD, DevOps) ou análise cruzada entre projetos e livros.
---

# Skill: Consultor de Livros Técnicos (ReductorPrompt)

Esta skill permite ao Gemini e a qualquer agente de IA consultar a base de conhecimento de livros técnicos indexada no ReductorPrompt de forma instantânea e sem desperdiçar tokens.

---

## 🎯 Quando Ativar esta Skill
- Quando o usuário fizer perguntas conceituais ou práticas sobre:
  - **LLMs, RAG & Prompt Engineering**: *Hands-On Large Language Models* (O'Reilly 2024), *Designing Large Language Model Applications*, *Domain-Specific Small Language Models* (Manning), *Build a Large Language Model from Scratch*, *Prompt Engineering for LLMs*.
  - **Visão Computacional & Deep Learning**: *Modern Computer Vision with PyTorch (2E)*, *Learning OpenCV 4 with Python*, *Computer and Machine Vision* (Davies).
  - **Python Avançado & Performance**: *High Performance Python*, *Learning Python*, *Python in a Nutshell*, *Think Python*.
  - **Data Engineering & Analytics**: *Python for Data Analysis*, *Python Polars: The Definitive Guide*, *Data Wrangling & Quality*, *Causal Inference*.
  - **Rust, Concorrência & Baixo Nível**: *Programming Rust*, *Rust Atomics and Locks*, *Async Rust*, *Effective Rust*, *Command-Line Rust*.
  - **DevOps, Arquitetura & Testes**: *Clean Architecture*, *Designing Data-Intensive Applications*, *Python for DevOps*, *Test-Driven Development (TDD)*.
  - **Machine Learning**: *Machine Learning with Python Cookbook*, *Hands-On Machine Learning with Scikit-Learn and TensorFlow*.
- Quando o usuário pedir: *"O que os livros dizem sobre X?"* ou *"Tenho o projeto X, o que desse livro pode ser otimizado no meu projeto?"*.

---

## 🚀 Como o Gemini Acessa o Projeto (2 Métodos)

### Método 1: Via MCP Tools (Mais Rápido e Direto) 🌟
Se as ferramentas MCP estiverem ativas, chame diretamente:
- **`get_runtime_budget_advice(provider="ollama")`**:
  - **Oráculo de Recursos & Telemetria Adaptativa**: Inspeciona a GPU/VRAM local ou cota de API cloud e retorna os parâmetros ideais (`max_tokens`, `deep_reasoning`, expansão de busca) para o agente se auto-calibrar.
- **`search_books(query="...", book_filter="...", max_tokens=2000, use_local_llm=False)`**: 
  - Com `use_local_llm=False` (padrão): Retorna os trechos puros dos livros com scores e capítulos (>95% economia de tokens).
  - Com `use_local_llm=True`: Aciona a LLM local (Ollama) ou API (Gemini) para sintetizar a resposta com base nos livros.
- **`teach_brain(query="...", insight="...", topic="...")`**: Grava aprendizados e soluções canônicas diretamente no Cérebro Coletivo.
- **`consult_brain(query="...")`**: Consulta rápida exclusiva à memória episódica (<2ms se já resolvida).
- **`validate_reasoning(hypothesis_or_plan="...", topic="...", provider="ollama")`**:
  - Submete a hipótese, ideia ou plano de código do agente para **Peer Review Cognitivo**.
  - A LLM + livros confrontam a proposta do agente, avaliando se o raciocínio é convergente, se é melhor/pior ou se a literatura propõe alternativas superiores.
- **`analyze_project_with_books(project_description="...", topic="...")`**: Gera a análise cruzada comparando a arquitetura do usuário com a literatura.
- **`list_indexed_books(query_filter="...", limit=30)`**: Retorna a lista de todas as obras disponíveis no banco vetorial.


---

### Método 2: Via Terminal CLI (Ambiente Isolado Conda)
Caso precise executar via comando de terminal, use o Python do Conda (`reductor-prompt`):

#### A. Para Consulta de Dúvidas / Extração de Contexto:
```bash
python query.py "<PERGUNTA_DO_USUARIO>" --only-context
```

#### B. Para Consulta com Raciocínio Profundo (Chain-of-Thought):
```bash
python query.py "<PERGUNTA>" --deep
```

#### C. Para Análise Cruzada de Projeto:
```bash
python query.py analyze \
  --project "<DESCRICAO_DO_PROJETO>" \
  --topic "<TOPICO_FOCO>" \
  --provider ollama
```

#### D. Para Listar Livros Indexados:
```bash
python query.py list
```

---

## 📋 Padrão de Resposta do Agente

Ao responder com base nos livros técnicos:
1. **Direto ao Ponto**: Vá direto à resposta técnica, economizando tokens.
2. **Citação Rastreável**: Sempre informe o nome do livro e capítulo/seção citados.
3. **Exemplos Práticos**: Forneça exemplos de código limpos e idiomáticos.
4. **Trade-offs**: Destaque possíveis gargalos de memória, latência ou complexidade alertados pelos autores.
5. **Guia Completo**: Para detalhes e templates de prompts avançados (CoT, ToT, Few-Shot), consulte [PROMPT_OPTIMIZATION_AND_QUERY_GUIDE.md](docs/PROMPT_OPTIMIZATION_AND_QUERY_GUIDE.md).
