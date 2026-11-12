from typing import Optional
from mcp.server.mcpserver import MCPServer

from src.config.settings import settings
from src.adapters.outbound.embeddings.embedding_adapters import ResilientEmbeddingAdapter
from src.adapters.outbound.vector_store.chroma_vector_store import ChromaVectorStoreAdapter
from src.adapters.outbound.memory.chroma_episodic_memory import ChromaEpisodicMemoryAdapter
from src.adapters.outbound.llm.llm_adapters import LLMFactory
from src.domain.ports.inbound import MakeDecisionCommand
from src.application.use_cases.make_decision_use_case import MakeDecisionUseCase


def register_decision_tools(mcp: MCPServer):
    @mcp.tool()
    def make_decision(
        query: str,
        project_source: Optional[str] = None,
        target_hardware: Optional[str] = None,
        target_commit: Optional[str] = None,
        policy_version: str = "1.0.0",
        max_tokens: int = 2500,
        provider: Optional[str] = None
    ) -> str:
        """
        Orquestra uma decisão de engenharia bilateral confrontando teoria canônica dos livros
        e evidências empíricas (benchmarks) de projetos externos sob política determinística.
        O veredicto técnico é determinístico (FAVORABLE, CONTROVERSIAL, INSUFFICIENT, REFUTED).
        """
        try:
            embedding_port = ResilientEmbeddingAdapter()
            vector_store = ChromaVectorStoreAdapter()
            memory_port = ChromaEpisodicMemoryAdapter()
            selected_provider = provider or settings.LLM_PROVIDER
            llm_port = LLMFactory.create(selected_provider)

            use_case = MakeDecisionUseCase(
                embedding_port=embedding_port,
                vector_store=vector_store,
                memory_port=memory_port,
                llm_port=llm_port
            )
            cmd = MakeDecisionCommand(
                query=query,
                project_source=project_source,
                target_hardware=target_hardware,
                target_commit=target_commit,
                policy_version=policy_version,
                max_tokens=max_tokens
            )
            report = use_case.execute(cmd)

            emp_summary = []
            for ev in report.empirical_evidence:
                st = "Obsoleto" if ev.get("is_stale") else "Válido"
                emp_summary.append(
                    f"  - Exp: {ev.get('experiment_id') or ev.get('episode_id', '')[:8]} "
                    f"| Semântica: {ev.get('semantic_score', 0.0):.2f} "
                    f"| Completude: {ev.get('completeness_score', 0.0):.2f} | Status: {st}"
                )
            emp_block = "\n".join(emp_summary) if emp_summary else "  (Nenhuma evidência empírica recuperada)"

            books_block = ", ".join(report.used_source_books) if report.used_source_books else "Nenhum livro citado"

            return (
                f"=== RELATÓRIO DE DECISÃO TÉCNICA ===\n"
                f"🎯 Veredicto: {report.verdict.value}\n"
                f"📌 Consulta: {report.query}\n"
                f"🏷️ Política: v{report.policy_version} | ID: {report.decision_id}\n\n"
                f"💡 Recomendação:\n{report.recommendation}\n\n"
                f"⚖️ Justificativa:\n{report.justification}\n\n"
                f"📊 Evidências Empíricas:\n{emp_block}\n\n"
                f"📚 Literatura Citada: {books_block}\n"
                f"⏱️ Decisão Registrada em: {report.created_at}"
            )
        except Exception as e:
            return f"⚠️ Erro ao orquestrar decisão: {str(e)}"
