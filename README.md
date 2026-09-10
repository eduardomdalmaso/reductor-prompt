# 📚 ReductorPrompt

**Otimizador Extremo de Prompts e RAG Cognitivo para Livros Técnicos e Documentos Volumosos**  
Construído sob os princípios de **Arquitetura Hexagonal (Ports & Adapters)** e **Domain-Driven Design (DDD)** em Python.

Economize **>98% de tokens** em consultas a livros técnicos com busca vetorial cirúrgica, deduplicação criptográfica SHA-256 e raciocínio cognitivo (*Chain-of-Thought* e *Self-Reflection*).

---

## 🖥️ Guia de Hardware: Qual LLM e Embedding Usar na sua GPU?

O ReductorPrompt funciona de forma modular: você pode rodar **100% offline e local** via [Ollama](https://ollama.com) (custo zero de API) ou na **nuvem** via Google Gemini API.

### 📊 Tabela de Recomendações por Hardware e VRAM

| Hardware / VRAM | Modelo LLM Recomendado | Modelo de Embedding | Desempenho / Velocidade |
| :--- | :--- | :--- | :--- |
| **Top-Tier (24GB a 32GB VRAM)**<br>`RTX 5090`, `RTX 4090`, `RTX 3090` | `qwen2.5:32b`<br>`qwen2.5:14b`<br>`deepseek-r1:14b` | `nomic-embed-text`<br>`bge-m3` | 🚀 **Extremo (>100 tokens/s)**<br>Raciocínio profundo, zero alucinação |
| **Gamer / Pro (12GB a 16GB VRAM)**<br>`RTX 4070 Ti / 4080`, `RTX 3060 12GB` | `qwen2.5:14b-q4`<br>`qwen2.5:7b`<br>`llama3.1:8b` | `nomic-embed-text` | ⚡ **Muito Rápido (60-90 tokens/s)**<br>Excelente para 99% das tarefas de engenharia |
| **Entrada / Notebook (6GB a 8GB VRAM)**<br>`RTX 3060 6GB`, `RTX 4050 / 4060 8GB` | `qwen2.5:7b-q4`<br>`deepseek-r1:8b-q4`<br>`mistral:7b` | `nomic-embed-text` | 🏎️ **Rápido (30-50 tokens/s)**<br>Bom equilíbrio entre memória e precisão |
| **Sem GPU / Apenas CPU ou Laptop Leve** | **Google Gemini API** (`gemini-2.0-flash`) | `nomic-embed-text` (CPU) ou `all-MiniLM-L6-v2` | ☁️ **Nuvem (Custo Centavos/Grátis)**<br>Busca vetorial local + inferência na nuvem |

> [!TIP]
> **Modelo Recomendado Padrão**: O modelo `qwen2.5` (7B, 14B ou 32B) oferece os melhores resultados em raciocínio de código, síntese em português e seguimento estrito de instruções RAG.

---

## 🛡️ Isolamento do Ambiente (Sistema 100% Limpo)

1. **Python via Miniconda**: O projeto roda em um ambiente virtual Conda isolado (`reductor-prompt`), mantendo as bibliotecas do sistema intactas.
2. **ChromaDB via Podman**: O banco vetorial roda isolado em container (`docker.io/chromadb/chroma:latest`) na porta `8001`, persistindo em `./storage/chroma` (com fallback automático para modo local persistente se o container não estiver ativo).

---

## 🚀 Como Inicializar e Usar

### 1. Iniciar o ChromaDB no Podman
```bash
./start_chroma.sh
```
*(Para parar quando terminar: `./stop_chroma.sh`)*

---

### 2. Ativar o Ambiente Conda
```bash
conda activate reductor-prompt
```

---

### 3. Baixar Livros Automaticamente com o Fetcher Dinâmico
Você pode baixar pastas do GitHub, arquivos ou links diretos com verificação de deduplicação SHA-256:

```bash
# Baixar pastas inteiras do GitHub (ex: repositório de livros de IA):
python query.py fetch "https://github.com/MinhNguyenDS/AI-pdf-books/tree/Master/Paper,https://github.com/MinhNguyenDS/AI-pdf-books/tree/Master/AI%20books"

# Baixar um artigo/livro direto da web e já indexar no ChromaDB (--ingest):
python query.py fetch "https://arxiv.org/pdf/2401.05566.pdf" --ingest
```

*(Você também pode simplesmente copiar arquivos `.pdf`, `.epub`, `.md` diretamente para a pasta [`database/`](file:///home/hades/Documents/ReductorPrompt/database)).*

---

### 4. Indexar os Livros (Deduplicação Inteligente)
```bash
python ingest.py
```
- Utiliza **PyMuPDF** para extração ultra-rápida de texto;
- Calcula hash SHA-256 e **só processa livros novos ou modificados**;
- Gera embeddings locais e armazena chunks no ChromaDB.

---

### 5. Consultas e Modos de Raciocínio

#### 🔹 Modo Padrão (Expansão Multi-Query & Fusão RRF)
```bash
python query.py "Qual o padrão de concorrência em Rust e Go?"
```

#### 🧠 Modo Profundo com Chain-of-Thought e Auto-Reflexão (`--deep`)
```bash
python query.py "Como mitigar gargalos de escrita no PostgreSQL?" --deep
```

#### ⚡ Modo Direto Ultrarrápido (`--fast`)
```bash
python query.py "O que é WAL?" --fast
```

#### 📄 Apenas Extrair o Contexto Enxuto (Sem chamar LLM)
```bash
python query.py "Princípios de Clean Architecture" --only-context
```

#### 📚 Listar Livros Indexados no Banco Vetorial
```bash
python query.py list
```

---

### 6. Análise Cruzada de Projeto (*Diagnóstico Arquitetural*)
Cruze o código ou arquitetura do seu projeto com as melhores práticas dos livros:

```bash
python query.py analyze \
  --project "Tenho um pipeline analítico em Python que ingere 50k eventos por segundo via Kafka e grava no PostgreSQL" \
  --topic "gargalos de escrita e particionamento"
```

O agente retorna:
- 🎯 **Diagnóstico e Alinhamento Teórico**
- 🚀 **Oportunidades Concretas de Otimização**
- ⚠️ **Riscos Arquiteturais, Gargalos e Trade-offs**
- 📋 **Plano de Ação Recomendado**
- 📖 **Referências Citadas (Livro, Capítulo e Página)**
- 📊 **Taxa de Economia de Tokens (>98%)**

---

### 7. Benchmark de Performance e Precisão
Execute a bateria de testes científicos para medir similaridade, latência e economia de tokens:

```bash
python scripts/benchmark_rag.py
```

---

### 8. Servidor MCP (Model Context Protocol) para IDEs e Agentes
O ReductorPrompt possui suporte nativo ao protocolo MCP. O arquivo [`mcp_config.json`](file:///home/hades/Documents/ReductorPrompt/mcp_config.json) já está configurado:

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

Ferramentas MCP expostas:
- `search_books(query, book_filter, max_tokens)`: busca trechos comprimidos (>95% de economia).
- `analyze_project_with_books(project_description, topic, book_filter)`: análise cruzada de projetos.
- `list_indexed_books()`: catálogo de livros disponíveis.

---

### 9. API REST FastAPI
Inicie a API HTTP para integração com backends ou frontends externos:
```bash
python api.py
# Documentação Swagger disponível em: http://127.0.0.1:8000/docs
```
