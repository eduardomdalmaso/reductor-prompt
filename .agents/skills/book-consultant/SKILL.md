---
name: book-consultant
description: Consulta a biblioteca técnica do ReductorPrompt de forma cirúrgica e com economia máxima de tokens (>95%). Use sempre que o usuário pedir opiniões arquiteturais, boas práticas, otimizações de código (Python, Rust, Polars, Concorrência, TDD, DevOps) ou análise cruzada entre projetos e livros.
---

# Skill: Consultor de Livros Técnicos (ReductorPrompt)

Esta skill permite ao Gemini e a qualquer agente de IA consultar a base de conhecimento de livros técnicos localizada em `/home/hades/Documents/ReductorPrompt` de forma instantânea e sem desperdiçar tokens.

---

## 🎯 Quando Ativar esta Skill
- Quando o usuário fizer perguntas conceituais ou práticas sobre:
  - **Python Avançado & Performance**: *High Performance Python*, *Learning Python*, *Python in a Nutshell*, *Think Python*.
  - **Data Engineering & Analytics**: *Python for Data Analysis*, *Python Polars: The Definitive Guide*, *Data Wrangling & Quality*, *Causal Inference*.
  - **Rust, Concorrência & Baixo Nível**: *Programming Rust*, *Rust Atomics and Locks*, *Async Rust*, *Effective Rust*, *Command-Line Rust*.
  - **DevOps, Arquitetura & Testes**: *Clean Architecture*, *Designing Data-Intensive Applications*, *Python for DevOps*, *Test-Driven Development (TDD)*.
  - **Machine Learning**: *Machine Learning with Python Cookbook*.
- Quando o usuário pedir: *"O que os livros dizem sobre X?"* ou *"Tenho o projeto X, o que desse livro pode ser otimizado no meu projeto?"*.

---

## 🚀 Como o Gemini Acessa o Projeto (2 Métodos)

### Método 1: Via MCP Tools (Mais Rápido e Direto - Milissegundos) 🌟
Se as ferramentas MCP estiverem ativas, chame diretamente:
- **`search_books(query="...", book_filter="...", max_tokens=2000)`**: Retorna o extrato enxuto dos livros com scores de similaridade e capítulos.
- **`analyze_project_with_books(project_description="...", topic="...")`**: Gera a análise cruzada comparando a arquitetura do usuário com a literatura.
- **`list_indexed_books()`**: Retorna a lista de todas as obras disponíveis no banco vetorial.

---

### Método 2: Via Terminal CLI (Ambiente Isolado Conda)
Caso precise executar via comando de terminal, use SEMPRE o Python do Conda:

**Python**: `/home/hades/miniconda3/envs/reductor-prompt/bin/python`  
**Query Script**: `/home/hades/Documents/ReductorPrompt/query.py`

#### A. Para Consulta de Dúvidas / Extração de Contexto:
```bash
/home/hades/miniconda3/envs/reductor-prompt/bin/python /home/hades/Documents/ReductorPrompt/query.py ask "<PERGUNTA_DO_USUARIO>" --only-context
```

#### B. Para Análise Cruzada de Projeto:
```bash
/home/hades/miniconda3/envs/reductor-prompt/bin/python /home/hades/Documents/ReductorPrompt/query.py analyze \
  --project "<DESCRICAO_DO_PROJETO>" \
  --topic "<TOPICO_FOCO>" \
  --provider ollama
```

#### C. Para Listar Livros Indexados:
```bash
/home/hades/miniconda3/envs/reductor-prompt/bin/python /home/hades/Documents/ReductorPrompt/query.py list
```

---

## 📋 Padrão de Resposta do Agente

Ao responder com base nos livros técnicos:
1. **Direto ao Ponto**: Vá direto à resposta técnica, economizando tokens.
2. **Citação Rastreável**: Sempre informe o nome do livro e capítulo/seção citados.
3. **Exemplos Práticos**: Forneça exemplos de código limpos e idiomáticos.
4. **Trade-offs**: Destaque possíveis gargalos de memória, latência ou complexidade alertados pelos autores.
