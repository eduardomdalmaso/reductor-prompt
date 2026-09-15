# 🧠 Guia Definitivo de Prompt Engineering & Consultas Cirúrgicas (ReductorPrompt)

> **Base Teórica e Prática:** *Hands-On Large Language Models* (O'Reilly, 2024), *Designing Large Language Model Applications*, *Domain-Specific Small Language Models* (Manning), OpenAI Best Practices, Chain-of-Thought (CoT) e Tree-of-Thoughts (ToT).

---

## 🎯 Objetivo: Máxima Precisão com Orçamento Estrito de Tokens (< 2.500 Tokens)

Quando a biblioteca vetorial cresce para dezenas de livros e centenas de milhares de tokens, o segredo para obter respostas técnicas de elite sem estourar a janela de contexto ou gastar tokens desnecessários é formular perguntas estruturadas e direcionadas.

---

## 🏗️ 1. Princípios de Prompt Engineering para Consultas RAG

### Regra 1: Seja Específico e Evite Ambiguidade Semântica
* ❌ **Prompt Fraco:** *"Como detectar objetos?"*  
  *(Causa dispersão: retorna trechos de OpenCV clássico, Deep Learning, Visão Robótica e OCR de vários livros ao mesmo tempo).*
* ✅ **Prompt Otimizado:** *"Como implementar detecção de pedestres usando HOG + Linear SVM com OpenCV em Python? Mostre o código e parâmetros."*  
  *(Ativa casamento denso e esparso cirúrgico no Capítulo 7 de Learning OpenCV).*

### Regra 2: Estrutura de Papel e Instrução Clara (Chat Completion Pattern)
Sempre declare:
1. **Contexto/Papel:** *"Atue como um Arquiteto de Visão Computacional / Engenheiro de Machine Learning."*
2. **Tarefa Específica:** *"Explique o cálculo do IoU e mostre a função em PyTorch."*
3. **Formato Desejado:** *"Forneça: (1) Fórmula matemática LaTeX, (2) Implementação idiomática em Python, (3) Exemplo numérico de entrada e saída."*
4. **Restrições:** *"Direto ao ponto, sem introduções genéricas."*

---

## 🧩 2. Técnicas Avançadas de Raciocínio (Quando usar cada uma)

### A. Zero-Shot & Few-Shot Prompting
* **Zero-Shot:** Pergunta direta para conceitos e códigos padronizados da literatura.
* **Few-Shot:** Quando você deseja que a resposta siga uma estrutura de código ou formato JSON específico, forneça um exemplo mínimo no prompt.

### B. Chain-of-Thought (CoT) — `--deep`
* **Conceito:** Força o modelo a detalhar as etapas lógicas de raciocínio intermediárias antes de emitir a conclusão final, reduzindo drasticamente alucinações em problemas matemáticos e arquiteturais.
* **Como ativar no ReductorPrompt:**
  ```bash
  python query.py "Qual o trade-off de usar Selective Search vs Region Proposal Networks (RPN) em detecção de objetos?" --deep
  ```

### C. Tree-of-Thoughts (ToT) / Análise de Alternativas
* **Conceito:** Explora múltiplos caminhos de raciocínio concorrentes e avalia os prós e contras de cada ramificação arquitetural.
* **Como estruturar sua pergunta:**
  ```bash
  python query.py "Compare 3 abordagens para detecção de objetos em hardware restrito (Raspberry Pi/Edge): (A) Haar Cascades, (B) HOG+SVM, (C) MobileNet-SSD. Avalie latência (FPS), consumo de RAM e acurácia mAP segundo os livros."
  ```

---

## 🛠️ 3. Como Consultar Localmente (CLI) e via MCP

### Método 1: Linha de Comando (CLI)

```bash
# 1. Consulta Rápida com Extração Cirúrgica de Contexto (Zero custo de API)
python query.py "Como funciona a loss function do YOLOv8?" --only-context

# 2. Consulta Filtrada por Livro Específico (Elimina 100% do ruído cruzado)
python query.py "Explique o cálculo de embeddings e tokenização" --book "Hands On Llms"

# 3. Análise Cruzada de Código/Projeto vs Literatura Técnica
python query.py analyze \
  --project "Pipeline de vídeo RTSP em Go decodificando H.264 e inferência em Python PyTorch" \
  --topic "Gargalos de latência de IPC e cópia de memória"
```

### Método 2: Via MCP Server (`reductor-books`) no Antigravity / Cursor / Claude Desktop

Se você estiver interagindo com um agente de IA via MCP, utilize as ferramentas disponíveis:

1. **`search_books(query, book_filter, max_tokens)`**:
   * *Query recomendada:* *"Código PyTorch para calcular Intersection over Union (IoU) com tensores"*
   * *Filtro (opcional):* *"Pytorch Cv 2E"* ou *"Hands On Llms"*
2. **`analyze_project_with_books(project_description, topic)`**:
   * Forneça a stack tecnológica completa para obter um diagnóstico com 5 seções estruturadas e citações bibliográficas rastreáveis.

---

## 📊 4. Tabela Rápida de Boas Práticas

| O que você precisa | Estratégia de Pergunta | Flag CLI Recomendada |
| :--- | :--- | :--- |
| **Apenas o código limpo** | *"Mostre apenas a implementação Python da classe X com type hints e docstring."* | `--only-context` |
| **Dedução matemática/fórmula** | *"Explique a formulação matemática de X passo a passo com equações LaTeX."* | `--deep` |
| **Comparação arquitetural** | *"Faça uma análise de trade-offs entre técnica A e B baseada nos livros."* | `analyze --topic "..."` |
| **Conceito de um livro específico** | Indique termos exatos ou o nome do autor/livro na busca. | `--book "<nome>"` |
