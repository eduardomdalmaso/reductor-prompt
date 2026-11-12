import hashlib
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from src.domain.entities.decision import DecisionReport, DecisionVerdict
from src.domain.entities.memory import MemoryEpisode, ProvenanceType, EvidenceStatus
from src.domain.ports.inbound import IMakeDecisionUseCase, MakeDecisionCommand
from src.domain.ports.outbound import IEmbeddingPort, IVectorStorePort, ILLMPort, IEpisodicMemoryPort
from src.application.services.prompt_compressor_service import PromptCompressorService
from src.application.services.evidence_quality_evaluator import EvidenceQualityEvaluator
from src.application.services.staleness_detector import StalenessDetector
from src.application.services.experimental_comparator import ExperimentalComparator
from src.application.services.decision_policy_service import DecisionPolicyService
from src.config.settings import settings

logger = logging.getLogger(__name__)


class MakeDecisionUseCase(IMakeDecisionUseCase):
    """
    Caso de uso de Decisão de Engenharia Autônoma.
    Orquestra fundamentação teórica, evidências empíricas, avaliação de completude,
    detecção de obsolescência e política determinística de veredictos.
    """

    def __init__(
        self,
        embedding_port: IEmbeddingPort,
        vector_store: IVectorStorePort,
        memory_port: IEpisodicMemoryPort,
        llm_port: Optional[ILLMPort] = None,
        compressor: Optional[PromptCompressorService] = None,
        staleness_detector: Optional[StalenessDetector] = None,
        comparator: Optional[ExperimentalComparator] = None
    ):
        self.embedding_port = embedding_port
        self.vector_store = vector_store
        self.memory_port = memory_port
        self.llm_port = llm_port
        self.compressor = compressor or PromptCompressorService()
        self.staleness_detector = staleness_detector or StalenessDetector(default_ttl_days=90)
        self.comparator = comparator or ExperimentalComparator()

    def execute(self, command: MakeDecisionCommand) -> DecisionReport:
        decision_id = hashlib.sha256(f"{command.query.strip().lower()}:{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:16]
        q_vec = self.embedding_port.embed_text(command.query)

        # 1. Recuperação Teórica (Livros)
        scored = self.vector_store.search(query_embedding=q_vec, top_k=settings.DEFAULT_TOP_K * 2, book_title_filter=command.book_filter)
        compressed_ctx = self.compressor.compress_and_format(query=command.query, scored_chunks=scored, max_tokens=command.max_tokens)
        theoretical_basis = compressed_ctx.sources
        used_books = list(set(s.get("book_title") for s in theoretical_basis if s.get("book_title")))

        # 2. Recuperação Empírica (HydraStream)
        empirical_episodes = self.memory_port.search_episodes(
            query_embedding=q_vec,
            min_similarity=0.68,
            top_k=4,
            provenance=ProvenanceType.EMPIRICAL,
            status=None  # Recupera tudo para que o detector avalie obsolescência conscientemente
        )

        used_ep_ids = [ep.id for ep in empirical_episodes]
        used_commits = [ep.commit_hash for ep in empirical_episodes if ep.commit_hash]

        # 3. Avaliação de Qualidade e Obsolescência
        completeness_scores = [EvidenceQualityEvaluator.evaluate(ep)[0] for ep in empirical_episodes]
        staleness_analyses = [
            self.staleness_detector.analyze(ep, command.target_hardware, command.target_commit)
            for ep in empirical_episodes
        ]

        # 4. Comparador Experimental
        comparison = self.comparator.compare(empirical_episodes) if len(empirical_episodes) >= 2 else None

        # 5. Aplicação da Política Determinística de Veredictos (A LLM NÃO escolhe o veredicto!)
        policy_result = DecisionPolicyService.evaluate(
            has_theoretical_basis=bool(theoretical_basis),
            empirical_episodes=empirical_episodes,
            completeness_scores=completeness_scores,
            staleness_analyses=staleness_analyses,
            comparison=comparison
        )

        # 6. Síntese Explicativa de Recomendação
        recommendation = policy_result.reason
        if command.llm_synthesis and self.llm_port:
            try:
                emp_text = self.compressor.format_empirical_evidence(empirical_episodes)
                sys_inst = (
                    "Você é um Arquiteto de Software Sênior. Redija uma recomendação técnica formal de 2 a 4 parágrafos. "
                    f"O veredicto determinístico mandatário do sistema é '{policy_result.verdict.value}'. "
                    "Explique a razão desse veredicto com base nas fontes teóricas e empíricas fornecidas, sem alterar o veredicto."
                )
                user_msg = (
                    f"CENÁRIO: {command.query}\n"
                    f"VEREDICTO DETERMINÍSTICO: {policy_result.verdict.value}\n"
                    f"RAZÃO DA POLÍTICA: {policy_result.reason}\n\n"
                    f"TEORIA DOS LIVROS:\n{compressed_ctx.raw_context_text}\n\n"
                    f"EVIDÊNCIAS EMPÍRICAS:\n{emp_text}\n"
                )
                llm_rec = self.llm_port.generate_response(system_instruction=sys_inst, prompt=user_msg)
                if llm_rec and len(llm_rec.strip()) > 20:
                    recommendation = llm_rec.strip()
            except Exception as e:
                logger.warning(f"Síntese LLM falhou ({e}), utilizando recomendação da política determinística.")

        avg_completeness = round(sum(completeness_scores) / max(1, len(completeness_scores)), 2) if completeness_scores else 0.0
        avg_relevance = round(sum(ep.confidence_score for ep in empirical_episodes) / max(1, len(empirical_episodes)), 2) if empirical_episodes else 0.0

        st_dict = {
            "has_stale_evidence": any(st.is_stale for st in staleness_analyses),
            "stale_count": sum(1 for st in staleness_analyses if st.is_stale),
            "details": [st.model_dump() for st in staleness_analyses]
        }

        return DecisionReport(
            decision_id=decision_id,
            query=command.query,
            recommendation=recommendation,
            verdict=policy_result.verdict,
            policy_version=DecisionPolicyService.POLICY_VERSION,
            created_at=datetime.now(timezone.utc).isoformat(),
            theoretical_basis=theoretical_basis,
            empirical_evidence=[ep.to_dict() for ep in empirical_episodes],
            used_episode_ids=used_ep_ids,
            used_commit_hashes=list(set(used_commits)),
            used_source_books=used_books,
            completeness_score=avg_completeness,
            relevance_score=avg_relevance,
            staleness_analysis=st_dict,
            comparative_summary=comparison.summary if comparison else None,
            limitations=policy_result.limitations,
            next_validation_steps=policy_result.next_validation_steps
        )
