# 📚 ReductorPrompt

**Motor de Recuperação RAG Especializado, Otimização Adaptativa de Contexto e Plataforma de Conhecimento Técnico**  
Construído sob os princípios de **Arquitetura Hexagonal (Ports & Adapters)** e **Domain-Driven Design (DDD)** em Python, com CLI nativo de alta velocidade em Go.

O ReductorPrompt reduz o volume de contexto documental enviado a LLMs de nuvem ou locais através de busca vetorial híbrida, fusão RRF, corte dinâmico por curva de relevância (*Elbow Method*) e **preservação integral de evidências canônicas** (Livro, Capítulo, Página e Score).

---

## 🖥️ Dimensionamento de Recursos e GPUs Genéricas

O ReductorPrompt é agnóstico a hardware: opera desde instâncias de entrada (8 GB VRAM) até servidores de alta densidade (32 GB VRAM), ou 100% via API em nuvem (Google Gemini).

### 📊 Guia de Alocação de Memória e Modelos

| Perfil de Hardware | VRAM Típica | Modelo Local (Ollama) | Embeddings | Latência / Throughput Estimado* |
| :--- | :--- | :--- | :--- | :--- |
| **Top-Tier / Workstation**<br>`RTX 5090`, `RTX 4090`, `A5000` | **24 GB a 32 GB** | `qwen2.5:32b`<br>`qwen2.5:14b` | `nomic-embed-text`<br>`bge-m3` | Inferência local de alto paralelismo e múltiplos batches |
| **Intermediário / Cloud GPU**<br>`RTX 4070 Ti / 4080`, `L4`, `A10` | **12 GB a 16 GB** | `qwen2.5:14b-q4`<br>`qwen2.5:7b` | `nomic-embed-text` | Equilíbrio ideal entre precisão técnica e consumo de VRAM |
| **Entrada / Instâncias Spot**<br>`RTX 3060`, `RTX 4060`, `T4` | **8 GB a 12 GB** | `qwen2.5:7b-q4`<br>`qwen2.5:3b` | `nomic-embed-text` | Operação econômica com modelos quantizados em Q4_K_M |
| **Ambientes Sem GPU Dedicada** | **Apenas CPU** | **Google Gemini API** (`gemini-2.5-flash`) | `all-MiniLM-L6-v2` | Busca vetorial local com síntese delegada à API remota |

*\* Medições reais variam conforme o tamanho da janela de contexto (Prompt Tokens), quantidade de tokens gerados e taxa de quantização utilizada.*

---

## 🛡️ Isolamento e Arquitetura do Sistema

1. **Camada de Aplicação (Python)**: Isolada via ambiente virtual (`conda` ou `venv`), com verificação de tipagem estática e sem caminhos acoplados ao sistema operacional.
2. **Vector Store (ChromaDB)**: Opera prioritariamente em container Podman/Docker (`127.0.0.1:8001`), com persistência em `./storage/chroma` e fallback automático para modo embutido local.
3. **CLI Nativo em Go (`reductor`)**: Binário compilado em `bin/reductor` para inicialização instantânea (`< 3ms`) no terminal diário, comunicando-se com o daemon via HTTP/REST.

---

## 🚀 Como Inicializar e Usar

### 1. Iniciar o ChromaDB
```bash
./start_chroma.sh
# Para encerrar o serviço: ./stop_chroma.sh
```

### 2. Ativar o Ambiente
```bash
conda activate reductor-prompt
# ou ative o seu ambiente virtual Python correspondente
```

### 3. Ingestão e Deduplicação Criptográfica
```bash
# Ingestão de arquivos na pasta database/ (com deduplicação SHA-256):
python ingest.py

# Download concorrente e ingestão de repositórios ou papers:
python query.py fetch "https://arxiv.org/pdf/2401.05566.pdf" --ingest
```

---

## 🔍 Modos de Consulta e CLI

Você pode consultar via CLI em Python (`query.py`) ou pelo binário nativo em Go (`./bin/reductor`):

#### 🔹 Consulta Padrão (Expansão Multi-Query & Fusão RRF)
```bash
python query.py "Qual o padrão de concorrência recomendado em Go e Rust?"
```

#### 🧠 Raciocínio Profundo (`--deep`)
```bash
python query.py "Como mitigar gargalos de escrita no PostgreSQL?" --deep
```

#### 📄 Extração de Contexto Canônico (Bypass de LLM)
Retorna exclusivamente as evidências selecionadas e formatadas, com zero consumo de tokens de resposta:
```bash
python query.py "Princípios de Clean Architecture" --only-context
```

#### 💬 Chat Interativo no Terminal (REPL)
```bash
python query.py chat
```

#### 🚀 Análise Cruzada de Projeto vs. Literatura Técnica
```bash
python query.py analyze \
  --project "Pipeline analítico que consome 50k eventos/s do Kafka e persiste em Postgres" \
  --topic "particionamento e gargalos de escrita"
```

Retorno estruturado:
- 🎯 **Diagnóstico e Alinhamento Teórico**
- 🚀 **Oportunidades Concretas de Otimização**
- ⚠️ **Riscos Arquiteturais e Trade-offs**
- 📋 **Plano de Ação Recomendado**
- 📖 **Fontes Canônicas Citadas (Livro, Capítulo e Página)**

---

## 🧪 Suíte de Benchmarks e Metrologia

O projeto conta com ferramentas dedicadas para auditar tempos e taxas de redução sem suposições teóricas:

```bash
# Executa a aferição detalhada do ciclo de vida da consulta (TTFT, I/O e corte):
python scripts/benchmark_baseline.py
```

O script afere isoladamente:
- Tempo de expansão de consulta (`t_expand`);
- Latência de geração de embeddings na GPU (`t_embed`);
- Varredura e similaridade no ChromaDB (`t_search`);
- Fusão RRF e corte de ruído por *Elbow Cutoff* (`t_compress`);
- Proporção real de tokens antes e depois da seleção contextual.

---

## 🔌 Servidor MCP (Model Context Protocol)

O ReductorPrompt expõe suas capacidades para Claude Desktop, Cursor e outros agentes de IA via MCP (`mcp_config.json`):

```json
{
  "mcpServers": {
    "reductor-books": {
      "command": "python",
      "args": ["mcp_server.py"],
      "env": {
        "PYTHONPATH": "."
      }
    }
  }
}
```

**Principais ferramentas expostas**:
- `search_books(query, book_filter, max_tokens)`: Recuperação cirúrgica com orçamento adaptativo.
- `analyze_project_with_books(project_description, topic)`: Diagnóstico arquitetural cruzado.
- `consult_brain(query)`: Consulta à memória episódica persistente (<1ms).
- `validate_reasoning(hypothesis, context)`: Peer-review de decisões técnicas contra os livros.

---

## 🌐 API REST FastAPI

Inicie o servidor HTTP para integração com serviços externos ou frontends:

```bash
python api.py
# Documentação interativa Swagger: http://127.0.0.1:8000/docs
```
