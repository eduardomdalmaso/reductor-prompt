from typing import List, Dict, Any, Tuple, Optional
from pydantic import BaseModel, Field
from src.domain.entities.decision import DecisionVerdict
from src.domain.entities.memory import MemoryEpisode
from src.application.services.staleness_detector import StalenessAnalysis
from src.application.services.experimental_comparator import ComparisonResult


class PolicyEvaluationResult(BaseModel):
    verdict: DecisionVerdict
    reason: str
    limitations: List[str] = Field(default_factory=list)
    next_validation_steps: List[str] = Field(default_factory=list)


class DecisionPolicyService:
    """
    Política determinística de avaliação e emissão de veredictos técnicos.
    Garante que a LLM não alucine ou invente veredictos sem respaldo em evidências comprovadas.
    Regra áurea: ausência de evidência nunca é tratada como refutação.
    """

    POLICY_VERSION = "1.0"

    @classmethod
    def evaluate(
        cls,
        has_theoretical_basis: bool,
        empirical_episodes: List[MemoryEpisode],
        completeness_scores: List[float],
        staleness_analyses: List[StalenessAnalysis],
        comparison: Optional[ComparisonResult] = None
    ) -> PolicyEvaluationResult:
        limitations: List[str] = []
        next_steps: List[str] = []

        # 1. Regra de Insuficiência: Ausência de evidências empíricas
        if not empirical_episodes:
            return PolicyEvaluationResult(
                verdict=DecisionVerdict.INSUFFICIENT,
                reason="Ausência de evidências empíricas no acervo. Há apenas fundamentação teórica, que deve ser validada experimentalmente.",
                limitations=["Nenhum benchmark operacional foi registrado para este cenário específico."],
                next_validation_steps=["Executar benchmark controlado no HydraStream e enviar os resultados para ingestão."]
            )

        # 2. Regra de Insuficiência: Todas as evidências estão obsoletas (STALE)
        valid_episodes = [
            (ep, cs, st) for ep, cs, st in zip(empirical_episodes, completeness_scores, staleness_analyses)
            if not st.is_stale
        ]

        if not valid_episodes:
            all_reasons = set()
            for st in staleness_analyses:
                all_reasons.update(st.reasons)
            return PolicyEvaluationResult(
                verdict=DecisionVerdict.INSUFFICIENT,
                reason=f"Evidências empíricas existentes estão desatualizadas: {'; '.join(all_reasons)}.",
                limitations=["Medições históricas não refletem o ambiente ou versão atual de execução."],
                next_validation_steps=["Reexecutar os experimentos no hardware e versão vigentes."]
            )

        # 3. Regra de Insuficiência: Completude média muito baixa (< 0.45)
        avg_completeness = sum(cs for _, cs, _ in valid_episodes) / len(valid_episodes)
        if avg_completeness < 0.45:
            return PolicyEvaluationResult(
                verdict=DecisionVerdict.INSUFFICIENT,
                reason=f"Completude experimental insuficiente ({avg_completeness:.2f} < 0.45). Metadados essenciais ausentes.",
                limitations=["Faltam identificadores de hardware, commit ou métricas quantitativas formais."],
                next_validation_steps=["Registrar benchmarks completos incluindo parâmetros de hardware e métricas no payload."]
            )

        # Coleta limitações observadas nas evidências válidas
        for ep, _, _ in valid_episodes:
            env = ep.environment_context or {}
            hw = env.get("hardware") or env.get("gpu")
            if hw:
                limitations.append(f"Resultados obtidos especificamente no hardware '{hw}'.")
            if ep.commit_hash:
                limitations.append(f"Comportamento aferido na versão de código #{ep.commit_hash[:7]}.")

        # 4. Regra de Refutação: Evidência robusta (completeness >= 0.7) contradiz a premissa teórica
        for ep, cs, _ in valid_episodes:
            if cs >= 0.70:
                resp_lower = ep.response.lower()
                refutation_markers = [
                    "refuta", "inviável", "degradação severa", "gargalo inaceitável",
                    "contraindicado", "falha sob carga", "perda de pacotes crítica"
                ]
                matched_marker = next((m for m in refutation_markers if m in resp_lower), None)
                if matched_marker:
                    return PolicyEvaluationResult(
                        verdict=DecisionVerdict.REFUTED,
                        reason=f"Evidência empírica robusta ({ep.experiment_id or ep.id}, completude {cs:.2f}) demonstrou refutação ou contraindicação na prática ('{matched_marker}').",
                        limitations=list(set(limitations)),
                        next_validation_steps=["Avaliar arquitetura alternativa que contorne o gargalo identificado."]
                    )

        # 5. Regra de Controvérsia: Comparador detecta divergências ou trade-offs severos
        if comparison and len(comparison.ranking) >= 2:
            best_val = comparison.ranking[0]["metric_value"]
            worst_val = comparison.ranking[-1]["metric_value"]
            delta_ratio = abs(worst_val - best_val) / max(0.001, min(worst_val, best_val))
            
            # Se a variação for maior que 50% entre experimentos sob o mesmo escopo
            if delta_ratio > 0.50:
                next_steps.append("Isolar as variáveis de ambiente que causaram dispersão superior a 50% entre as execuções.")
                return PolicyEvaluationResult(
                    verdict=DecisionVerdict.CONTROVERSIAL,
                    reason=f"Evidências empíricas apresentam alta dispersão de desempenho ({delta_ratio:.0%} de variação entre configurações). Decisão exige cautela com trade-offs.",
                    limitations=list(set(limitations)),
                    next_validation_steps=next_steps or ["Realizar testes de estresse adicionais com carga constante."]
                )

        # 6. Regra Favorável: Evidência válida confirma a viabilidade
        next_steps.append("Monitorar a estabilidade sob carga em produção e manter os benchmarks de regressão ativos.")
        return PolicyEvaluationResult(
            verdict=DecisionVerdict.FAVORABLE,
            reason="Evidências empíricas válidas confirmam a viabilidade prática e convergem com a fundamentação técnica.",
            limitations=list(set(limitations)),
            next_validation_steps=next_steps
        )
