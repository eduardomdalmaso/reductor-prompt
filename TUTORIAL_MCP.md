# 🔌 Tutorial: Conexão e Comunicação MCP com o ReductorPrompt
*Guia completo para Desenvolvedores e Agentes Autônomos de IA*

---

## 🎯 1. O que é o Servidor MCP do ReductorPrompt?

O **ReductorPrompt MCP Server** implementa a especificação oficial do [Model Context Protocol (MCP)](https://modelcontextprotocol.io), permitindo que Agentes de IA (Claude Desktop, Cursor, Antigravity, Windsurf, LangChain, CrewAI, AutoGen) acessem a biblioteca técnica de **194+ livros e manuais técnicos** e o **Cérebro Coletivo (Memória Episódica)** de forma cirúrgica, reduzindo o consumo de tokens em **mais de 95%**.

---

## 🛠️ 2. Guia de Configuração para Pessoas (Desenvolvedores)

### 2.1 Requisitos Prévios
- O ambiente Conda `reductor-prompt` deve estar configurado.
- Os serviços do PM2 (`ollama`, `reductor-chromadb`, `reductor-api`) devem estar ativos.

---

### 2.2 Claude Desktop

Abra o arquivo de configuração do Claude Desktop:
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

Adicione a seção `reductor-books`:

```json
{
  "mcpServers": {
    "reductor-books": {
      "command": "C:\\Users\\eduar\\miniconda3\\envs\\reductor-prompt\\python.exe",
      "args": [
        "C:\\Users\\eduar\\Documents\\reductor-prompt\\mcp_server.py"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

---

### 2.3 Cursor IDE

Crie ou edite o arquivo `.cursor/mcp.json` na raiz do seu projeto:

```json
{
  "mcpServers": {
    "reductor-books": {
      "command": "C:\\Users\\eduar\\miniconda3\\envs\\reductor-prompt\\python.exe",
      "args": [
        "C:\\Users\\eduar\\Documents\\reductor-prompt\\mcp_server.py"
      ]
    }
  }
}
```

---

### 2.4 Antigravity IDE / Gemini Agent

No arquivo de configuração MCP (`mcp_config.json`):

```json
{
  "mcpServers": {
    "reductor-books": {
      "command": "C:\\Users\\eduar\\miniconda3\\envs\\reductor-prompt\\python.exe",
      "args": [
        "C:\\Users\\eduar\\Documents\\reductor-prompt\\mcp_server.py"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

---

### 2.5 VS Code (Extensões Roo-Code / Cline / Continue)

No painel de configurações MCP da extensão, configure:
- **Name**: `reductor-books`
- **Command**: `C:\Users\eduar\miniconda3\envs\reductor-prompt\python.exe`
- **Args**: `["C:\\Users\\eduar\\Documents\\reductor-prompt\\mcp_server.py"]`

---

## 🤖 3. Instruções e Diretrizes para Agentes de IA

### 3.1 Catálogo de Ferramentas Disponíveis

| Ferramenta | Propósito Principal | Quando Usar |
| :--- | :--- | :--- |
| **`search_books`** | Busca semântica e contextual nos 194+ livros técnicos | Sempre que precisar de referências, padrões, documentação ou soluções comprovadas. |
| **`consult_brain`** | Consulta a Memória Episódica do Cérebro Coletivo | Para dúvidas frequentes e soluções previamente registradas (<2ms de latência). |
| **`teach_brain`** | Grava uma nova solução canônica no Cérebro Coletivo | Após resolver com sucesso um bug complexo ou definir uma decisão de arquitetura. |
| **`validate_reasoning`** | Faz *Peer-Review* da hipótese do agente contra os livros e a LLM local | Antes de propor refatorações críticas ou mudanças arquiteturais arriscadas. |
| **`analyze_project_with_books`** | Diagnóstico cruzado de código/arquitetura vs teoria dos livros | Para auditorias de segurança, concorrência, gargalos ou alinhamento com DDD/Clean Arch. |
| **`list_indexed_books`** | Lista todos os livros, manuais e documentações indexadas | Para descobrir quais obras e tópicos estão disponíveis no acervo. |
| **`get_runtime_budget_advice`** | Oráculo de hardware e orçamento de tokens | Para dimensionar o teto de tokens ideal de acordo com a GPU instalada. |

---

### 3.2 Fluxo de Raciocínio Recomendado para o Agente

```
                      [Pergunta Técnica / Problema do Usuário]
                                         │
                                         ▼
                     [1. consult_brain(query="...")]
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   ▼ (Encontrou Memória)                       ▼ (Sem Memória Prévia)
      [Retorna resposta instantânea]             [2. search_books(query="...")]
                                                               │
                                                               ▼
                                                  [3. Raciocínio Técnico & Código]
                                                               │
                                                               ▼ (Opcional)
                                              [4. validate_reasoning(hypothesis="...")]
                                                               │
                                                               ▼
                                              [5. teach_brain(query="...", insight="...")]
                                                               │
                                                               ▼
                                                  [Resposta Final ao Usuário]
```

---

## 💻 4. Exemplos de Integração em Código

### 4.1 Cliente em Python (SDK MCP Oficial)

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command=r"C:\Users\eduar\miniconda3\envs\reductor-prompt\python.exe",
        args=[r"C:\Users\eduar\Documents\reductor-prompt\mcp_server.py"],
        env={"PYTHONUNBUFFERED": "1"}
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Listar ferramentas disponíveis
            tools = await session.list_tools()
            print("Ferramentas disponíveis:", [t.name for t in tools.tools])
            
            # Executar busca cirúrgica
            result = await session.call_tool(
                "search_books",
                arguments={
                    "query": "Como otimizar inferência do YOLO11 com TensorRT?",
                    "max_tokens": 1500
                }
            )
            print("\nResultado da Busca:\n", result.content[0].text)

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 4.2 Cliente em Node.js / TypeScript (`@modelcontextprotocol/sdk`)

```typescript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

async function run() {
  const transport = new StdioClientTransport({
    command: "C:\\Users\\eduar\\miniconda3\\envs\\reductor-prompt\\python.exe",
    args: ["C:\\Users\\eduar\\Documents\\reductor-prompt\\mcp_server.py"],
  });

  const client = new Client({ name: "meu-agente", version: "1.0.0" }, { capabilities: {} });
  await client.connect(transport);

  // Consulta ao MCP do Reductor
  const response = await client.callTool({
    name: "search_books",
    arguments: {
      query: "Quais os benefícios dos blocos C3k2 e C2PSA no YOLO11?",
      max_tokens: 1200,
    },
  });

  console.log(response.content[0].text);
}

run();
```

---

## ⚡ 5. Diagnóstico e Teste Rápido no Terminal

Para testar se o servidor MCP está respondendo normalmente sem precisar abrir uma interface:

```powershell
# Executar chamada direta via CLI de teste
& "C:\Users\eduar\miniconda3\envs\reductor-prompt\python.exe" -c "
import asyncio
from src.adapters.inbound.mcp.server import search_books
print(search_books('O que é C2PSA no YOLO11?'))
"
```
