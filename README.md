# 📚 ReductorPrompt

**Otimizador Extremo de Prompts e RAG Hierárquico para Livros Técnicos e Documentos Volumosos**  
Construído sob os princípios de **Arquitetura Hexagonal (Ports & Adapters)** e **Domain-Driven Design (DDD)** em Python.

---

## 🛡️ Isolamento do Ambiente (Sistema 100% Limpo)

1. **Python via Miniconda**: O projeto roda em um ambiente virtual Conda isolado (`reductor-prompt`), garantindo que o Python do seu sistema operacional permaneça intacto.
2. **ChromaDB via Podman**: O banco vetorial roda como um container Podman isolado (`docker.io/chromadb/chroma:latest`) na porta `8001`, persistindo os dados em `./storage/chroma`.

---

## 🚀 Como Inicializar e Usar

### 1. Iniciar o ChromaDB no Podman
Basta executar o script pronto:
```bash
./start_chroma.sh
```
*(Para parar o container quando terminar: `./stop_chroma.sh`)*

---

### 2. Ativar o Ambiente Conda
```bash
conda activate reductor-prompt
```

---

### 3. Coloque seus livros na pasta `database/`
Copie seus arquivos `.pdf`, `.epub`, `.txt` ou `.md` para a pasta:
```bash
cp /caminho/do/seu/livro.pdf ./database/
```

---

### 4. Indexar os livros (Apenas 1x por livro novo)
```bash
python ingest.py
```
*(O sistema calcula o hash SHA-256 e só reprocessa livros novos ou modificados).*

---

### 5. Análise Cruzada de Projeto (*Seu Caso de Uso Principal*)

Ideal para o cenário: *"Tenho o projeto X, o que desse livro pode ser otimizado no meu projeto?"*

```bash
python query.py analyze \
  --project "Tenho um pipeline analítico em Python que ingere 50k eventos por segundo via Kafka e grava no PostgreSQL" \
  --topic "gargalos de escrita e latência de ingestão" \
  --provider ollama
```

O agente retornará um relatório estratégico completo com:
- 🎯 **Diagnóstico e Alinhamento Teórico**
- 🚀 **Oportunidades Concretas de Otimização**
- ⚠️ **Riscos Arquiteturais, Gargalos e Trade-offs**
- 📋 **Plano de Ação Recomendado**
- 📖 **Referências Citadas (Capítulos e Páginas)**
- 📊 **Taxa de Economia de Tokens (>98%)**

---

### 6. Consultas e Perguntas Rápidas
```bash
# Pergunta direta
python query.py "Qual a diferença entre SSTables e B-Trees?"

# Filtrar por um livro específico
python query.py "Como funciona a inversão de dependência?" --book "Clean Architecture"

# Apenas extrair o contexto enxuto sem chamar o LLM
python query.py "Princípios de particionamento" --only-context

# Listar livros ativos no banco vetorial
python query.py list
```

---

### 7. Usar o Gemini como LLM de Resposta
Para usar o **Gemini** (com busca local grátis e prompt mínimo):
1. Copie o arquivo `.env`:
   ```bash
   cp .env.example .env
   ```
2. Adicione sua chave: `GEMINI_API_KEY=sua_chave_aqui` e `LLM_PROVIDER=gemini`.

---

### 8. Servidor MCP (Model Context Protocol) para Agentes
O **MCP** permite que o Gemini ou qualquer agente no IDE chame as ferramentas de busca dos livros diretamente em milissegundos.

O arquivo `mcp_config.json` já está pronto:
```json
{
  "mcpServers": {
    "reductor-books": {
      "command": "/home/hades/miniconda3/envs/reductor-prompt/bin/python",
      "args": ["/home/hades/Documents/ReductorPrompt/mcp_server.py"]
    }
  }
}
```

Ferramentas MCP disponíveis nativamente para o Agente:
- `search_books(query, book_filter, max_tokens)`: busca trechos comprimidos (>95% de economia).
- `analyze_project_with_books(project_description, topic, book_filter)`: análise cruzada de projeto.
- `list_indexed_books()`: lista livros disponíveis no banco.

