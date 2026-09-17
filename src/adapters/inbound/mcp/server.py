import sys
import logging
from typing import Optional, List, Dict, Any
from mcp.server.mcpserver import MCPServer

from src.config.settings import settings
from src.adapters.outbound.embeddings.embedding_adapters import ResilientEmbeddingAdapter
from src.adapters.outbound.vector_store.chroma_vector_store import ChromaVectorStoreAdapter
from src.adapters.outbound.memory.chroma_episodic_memory import ChromaEpisodicMemoryAdapter
from src.adapters.outbound.llm.llm_adapters import LLMFactory

from src.application.use_cases.query_books_use_case import QueryBooksUseCase
from src.application.use_cases.analyze_project_use_case import AnalyzeProjectUseCase
from src.application.use_cases.manage_brain_use_case import ManageBrainUseCase
from src.application.services.hardware_budget_advisor_service import hardware_advisor_service

# Desativa logs verbosos no stdout para não corromper o canal stdio do MCP
logging.basicConfig(level=logging.ERROR)

mcp = MCPServer("ReductorPrompt-KnowledgeServer")


@mcp.tool()
def search_books(
    query: str, 
    book_filter: Optional[str] = None, 
    max_tokens: int = 2000,
    use_local_llm: bool = False,
    provider: Optional[str] = None,
    deep_reasoning: bool = False,
    use_brain: bool = True
) -> str:
    """
    Busca cirurgicamente nos livros técnicos indexados com suporte ao Cérebro Episódico.
    
    Por padrão (use_local_llm=False), retorna o contexto comprimido literal dos livros (>95% de economia)
    ou a memória prévia do cérebro para o agente consumir instantaneamente.
    Quando use_local_llm=True, aciona a LLM (Ollama local ou Gemini) para sintetizar e raciocinar
    sobre os trechos dos livros antes de responder.
    
    :param query: A pergunta técnica ou conceito a pesquisar.
    :param book_filter: (Opcional) Filtrar por título de livro específico ou palavra-chave no título.
    :param max_tokens: Limite máximo de tokens do contexto retornado (default: 2000).
    :param use_local_llm: Se True, aciona a LLM (Ollama/Gemini) para gerar raciocínio/resposta com base nos livros.
    :param provider: Provedor da LLM ('ollama' ou 'gemini'). Se omitido, usa a configuração padrão.
    :param deep_reasoning: Se True (quando use_local_llm=True), ativa Chain-of-Thought e auto-reflexão profunda.
    :param use_brain: Se True (default), consulta primeiro a memória episódica (<2ms de resposta se já resolvida).
    """
    try:
        embedding_port = ResilientEmbeddingAdapter()
        vector_store = ChromaVectorStoreAdapter()
        memory_port = ChromaEpisodicMemoryAdapter()
        selected_provider = provider or settings.LLM_PROVIDER
        llm_port = LLMFactory.create(selected_provider)
        
        use_case = QueryBooksUseCase(
            embedding_port=embedding_port,
            vector_store=vector_store,
            llm_port=llm_port,
            memory_port=memory_port
        )
        
        result = use_case.execute(
            query=query,
            book_filter=book_filter,
            max_tokens=max_tokens,
            only_context=not use_local_llm,
            deep_reasoning=deep_reasoning,
            use_brain=use_brain,
            auto_learn=True
        )
        
        sources_summary = "\n".join([
            f"• {s['book_title']} ({s.get('chapter', '')}) - Similaridade: {s['score']}"
            for s in result.get("sources", [])
        ])
        
        origin_label = "MEMÓRIA DO CÉREBRO EPISÓDICO" if result.get("from_brain") else (
            f"RESPOSTA SINTETIZADA PELA LLM ({selected_provider.upper()})" if use_local_llm else "CONTEXTO EXTRAÍDO DOS LIVROS"
        )
        
        header = f"=== {origin_label} (Tokens: {result['tokens_used']} | Economia: {result['reduction_percentage']}%) ===\n\n"
        
        sources_section = f"\n\n=== FONTES CONSULTADAS ===\n{sources_summary}" if sources_summary else ""
        
        return f"{header}{result['response']}{sources_section}"
    except Exception as e:
        return f"⚠️ Erro ao consultar base de livros: {str(e)}. Verifique se a base ChromaDB está acessível."


@mcp.tool()
def teach_brain(
    query: str,
    insight: str,
    topic: Optional[str] = None
) -> str:
    """
    Ensina e grava diretamente um aprendizado, solução ou insight no Cérebro Coletivo.
    
    Permite a qualquer agente ou desenvolvedor registrar uma solução canônica que ficará
    disponível instantaneamente para consultas futuras (<2ms de latência e 0 tokens de LLM).
    
    :param query: A pergunta, problema ou caso de uso que dispara este conhecimento.
    :param insight: A resposta lapidada, explicação técnica ou código correto.
    :param topic: (Opcional) Categoria ou tópico (ex: 'FastAPI', 'Rust Concurrency', 'PostgreSQL').
    """
    try:
        embedding_port = ResilientEmbeddingAdapter()
        memory_port = ChromaEpisodicMemoryAdapter()
        
        brain_use_case = ManageBrainUseCase(
            memory_port=memory_port,
            embedding_port=embedding_port
        )
        
        episode = brain_use_case.teach_brain(
            query=query,
            insight=insight,
            topic=topic
        )
        
        return f"✅ Conhecimento gravado no Cérebro Coletivo com sucesso! [ID: {episode.id} | Tópico: {episode.topic or 'Geral'}]"
    except Exception as e:
        return f"⚠️ Erro ao gravar conhecimento no cérebro: {str(e)}"


@mcp.tool()
def consult_brain(
    query: str,
    min_similarity: float = 0.85
) -> str:
    """
    Consulta exclusivamente a Memória Episódica do Cérebro Coletivo (conhecimentos e resoluções prévias).
    
    Retorna imediatamente se houver um caso resolvido com alta similaridade semântica.
    
    :param query: A dúvida técnica ou problema a consultar no cérebro.
    :param min_similarity: Limiar mínimo de similaridade de cosseno (default: 0.85).
    """
    try:
        embedding_port = ResilientEmbeddingAdapter()
        memory_port = ChromaEpisodicMemoryAdapter()
        
        brain_use_case = ManageBrainUseCase(
            memory_port=memory_port,
            embedding_port=embedding_port
        )
        
        episode = brain_use_case.consult_brain(query=query, min_similarity=min_similarity)
        if not episode:
            return "❌ Nenhuma memória encontrada no cérebro para essa consulta. Recomenda-se usar `search_books` para pesquisar na biblioteca."
            
        return (
            f"🧠 === MEMÓRIA EPISÓDICA ENCONTRADA (Confiança: {episode.confidence_score:.0%}) ===\n"
            f"📌 Pergunta Original: {episode.query}\n"
            f"🏷️ Tópico: {episode.topic or 'Geral'}\n"
            f"⏱️ Gravado em: {episode.created_at}\n\n"
            f"{episode.response}"
        )
    except Exception as e:
        return f"⚠️ Erro ao consultar o cérebro: {str(e)}"


@mcp.tool()
def validate_reasoning(
    hypothesis_or_plan: str,
    topic: Optional[str] = None,
    book_filter: Optional[str] = None,
    provider: Optional[str] = None,
    max_tokens: int = 2500
) -> str:
    """
    Validação Cruzada de Raciocínio (Peer Review Cognitivo).
    
    Permite ao agente submeter seu próprio raciocínio, plano técnico ou hipótese para ser
    confrontado contra a literatura técnica dos livros e avaliado pela LLM (Ollama/Gemini).
    
    A resposta analisa se o raciocínio do agente é:
    1. CONVERGENTE (Alinhado com a teoria)
    2. MELHOR/PIOR ou com Trade-offs ignorados
    3. ALTERNATIVAS SUPERIORES recomendadas pelos autores dos livros.
    
    :param hypothesis_or_plan: O raciocínio, hipótese, arquitetura ou plano formulado pelo agente.
    :param topic: (Opcional) Tópico de foco para guiar a validação (ex: 'concorrência', 'segurança', 'escalabilidade').
    :param book_filter: (Opcional) Filtrar por livro de referência específico.
    :param provider: Provedor da LLM ('ollama' ou 'gemini'). Default usa configuração ativa.
    :param max_tokens: Orçamento de tokens para o contexto dos livros.
    """
    try:
        embedding_port = ResilientEmbeddingAdapter()
        vector_store = ChromaVectorStoreAdapter()
        selected_provider = provider or settings.LLM_PROVIDER
        llm_port = LLMFactory.create(selected_provider)
        
        use_case = AnalyzeProjectUseCase(
            embedding_port=embedding_port,
            vector_store=vector_store,
            llm_port=llm_port
        )
        
        formatted_description = (
            f"[HIPÓTESE / RACIOCÍNIO DO AGENTE PARA VALIDAÇÃO]:\n{hypothesis_or_plan}\n\n"
            f"Por favor, compare criticamente este raciocínio com os livros técnicos. "
            f"Avalie se a proposta é sólida, se há falhas conceituais, se a abordagem é melhor, pior "
            f"ou equivalente ao padrão canônico da literatura, e aponte os trade-offs."
        )
        
        insight = use_case.execute(
            project_description=formatted_description,
            book_filter=book_filter,
            focus_topic=topic or "Validação Crítica de Hipótese e Alinhamento com a Literatura",
            max_tokens=max_tokens
        )
        
        return f"=== RESULTADO DA VALIDAÇÃO CRUZADA (PEER REVIEW VIA {selected_provider.upper()} + LIVROS) ===\n\n{insight.raw_response}"
    except Exception as e:
        return f"⚠️ Erro ao validar raciocínio: {str(e)}."


@mcp.tool()
def analyze_project_with_books(
    project_description: str,
    topic: Optional[str] = None,
    book_filter: Optional[str] = None,
    max_tokens: int = 2500
) -> str:
    """
    Realiza uma Análise Cruzada entre a arquitetura/código do seu projeto e os conceitos
    e melhores práticas extraídos dos livros técnicos de referência.
    """
    try:
        embedding_port = ResilientEmbeddingAdapter()
        vector_store = ChromaVectorStoreAdapter()
        llm_port = LLMFactory.create("ollama")
        
        use_case = AnalyzeProjectUseCase(
            embedding_port=embedding_port,
            vector_store=vector_store,
            llm_port=llm_port
        )
        
        insight = use_case.execute(
            project_description=project_description,
            book_filter=book_filter,
            focus_topic=topic,
            max_tokens=max_tokens
        )
        
        return insight.raw_response
    except Exception as e:
        return f"⚠️ Erro na análise cruzada: {str(e)}."


@mcp.tool()
def list_indexed_books(
    query_filter: Optional[str] = None,
    limit: int = 30
) -> Dict[str, Any]:
    """
    Lista os livros técnicos atualmente indexados e disponíveis no banco vetorial.
    """
    try:
        vector_store = ChromaVectorStoreAdapter()
        all_books = vector_store.list_indexed_books()
        
        if query_filter:
            q = query_filter.lower()
            filtered = [
                b for b in all_books 
                if q in b.get("title", "").lower() or q in b.get("filename", "").lower()
            ]
        else:
            filtered = all_books
            
        sliced = filtered[:limit]
        
        books_summary = [
            {
                "title": b.get("title"),
                "format": b.get("format"),
                "chunks": b.get("total_chunks", 0),
                "tokens": b.get("total_tokens", 0)
            }
            for b in sliced
        ]
        
        return {
            "total_indexed": len(all_books),
            "matched": len(filtered),
            "returned": len(books_summary),
            "books": books_summary
        }
    except Exception as e:
        return {"error": f"Erro ao listar livros: {str(e)}", "books": []}


@mcp.tool()
def get_runtime_budget_advice(
    provider: Optional[str] = None
) -> Dict[str, Any]:
    """
    Oráculo de Recursos & Telemetria Adaptativa (Hardware-Aware Budget Advisor).
    
    Inspeciona o hardware local (GPU/VRAM) e o provedor LLM configurado, retornando
    orientações dinâmicas sobre quais parâmetros o agente deve utilizar (ex: max_tokens,
    deep_reasoning, query expansion e estratégia de custo).
    
    :param provider: (Opcional) Provedor para simular ('ollama' ou 'gemini'). Se omitido, usa o ativo.
    """
    try:
        return hardware_advisor_service.get_runtime_advice(provider_override=provider)
    except Exception as e:
        return {"error": f"Erro ao gerar conselho de recursos: {str(e)}"}


if __name__ == "__main__":
    mcp.run(transport="stdio")

