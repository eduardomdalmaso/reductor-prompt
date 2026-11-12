from typing import Optional, Dict, Any
from mcp.server.mcpserver import MCPServer

from src.adapters.outbound.embeddings.embedding_adapters import ResilientEmbeddingAdapter
from src.adapters.outbound.memory.chroma_episodic_memory import ChromaEpisodicMemoryAdapter
from src.application.use_cases.manage_brain_use_case import ManageBrainUseCase
from src.application.services.hardware_budget_advisor_service import hardware_advisor_service


def register_brain_tools(mcp: MCPServer):
    @mcp.tool()
    def teach_brain(query: str, insight: str, topic: Optional[str] = None) -> str:
        """
        Ensina e grava diretamente um aprendizado, solução ou insight no Cérebro Coletivo.
        Disponível instantaneamente para consultas futuras (<2ms de latência e 0 tokens de LLM).
        """
        try:
            embedding_port = ResilientEmbeddingAdapter()
            memory_port = ChromaEpisodicMemoryAdapter()
            use_case = ManageBrainUseCase(memory_port=memory_port, embedding_port=embedding_port)
            episode = use_case.teach_brain(query=query, insight=insight, topic=topic)
            return f"✅ Conhecimento gravado no Cérebro Coletivo com sucesso! [ID: {episode.id} | Tópico: {episode.topic or 'Geral'}]"
        except Exception as e:
            return f"⚠️ Erro ao gravar conhecimento no cérebro: {str(e)}"

    @mcp.tool()
    def consult_brain(query: str, min_similarity: float = 0.85) -> str:
        """
        Consulta exclusivamente a Memória Episódica do Cérebro Coletivo (conhecimentos e resoluções prévias).
        """
        try:
            embedding_port = ResilientEmbeddingAdapter()
            memory_port = ChromaEpisodicMemoryAdapter()
            use_case = ManageBrainUseCase(memory_port=memory_port, embedding_port=embedding_port)
            episode = use_case.consult_brain(query=query, min_similarity=min_similarity)
            if not episode:
                return "❌ Nenhuma memória encontrada no cérebro para essa consulta. Recomenda-se usar `search_books`."
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
    def get_runtime_budget_advice(provider: Optional[str] = None) -> Dict[str, Any]:
        """
        Oráculo de Recursos & Telemetria Adaptativa (Hardware-Aware Budget Advisor).
        Inspeciona o hardware local (GPU/VRAM) e o provedor LLM configurado.
        """
        try:
            return hardware_advisor_service.get_runtime_advice(provider_override=provider)
        except Exception as e:
            return {"error": f"Erro ao gerar conselho de recursos: {str(e)}"}
