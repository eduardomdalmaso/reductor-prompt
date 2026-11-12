from typing import List, Dict, Any, Optional, Set
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
    Garante que a LLM não invente ou altere veredictos sem respaldo em evidências comprovadas.
    Regra áurea: ausência de evidência nunca é tratada como refutação.
    """

    POLICY_VERSION = "1.1"

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

        # 0. Deduplicação Consciente (ADV-10): Evidências duplicadas não somam confirmações
        seen_keys: Set[tuple] = set()
        dedup_episodes: List[MemoryEpisode] = []
        dedup_completeness: List[float] = []
        dedup_staleness: List[StalenessAnalysis] = []

        for ep, cs, st in zip(empirical_episodes, completeness_scores, staleness_analyses):
            key = (ep.id, ep.experiment_id, ep.content_hash)
            if key not in seen_keys:
                seen_keys.add(key)
                dedup_episodes.append(ep)
                dedup_completeness.append(cs)
                dedup_staleness.append(st)

        # 1. Regra de Insuficiência: Ausência de evidências empíricas (ADV-01, ADV-03)
        if not dedup_episodes:
            return PolicyEvaluationResult(
                verdict=DecisionVerdict.INSUFFICIENT,
                reason="Ausência de evidências empíricas no acervo. Há apenas fundamentação teórica, que deve ser validada experimentalmente.",
                limitations=["Nenhum benchmark operacional foi registrado para este cenário específico."],
                next_validation_steps=["Executar benchmark controlado no HydraStream e enviar os resultados para ingestão."]
            )

        # 2. Regra de Insuficiência: Todas as evidências estão obsoletas (ADV-04)
        valid_episodes = [
            (ep, cs, st) for ep, cs, st in zip(dedup_episodes, dedup_completeness, dedup_staleness)
            if not st.is_stale
        ]

        if not valid_episodes:
            temporal_reasons = set()
            hardware_reasons = set()
            for st in dedup_staleness:
                for r in st.reasons:
                    if "Temporal" in r:
                        temporal_reasons.add(r)
                    else:
                        hardware_reasons.add(r)
            if temporal_reasons:
                limitations.append(f"Obsolescência Temporal: {'; '.join(temporal_reasons)}.")
            if hardware_reasons:
                limitations.append(f"Incompatibilidade de Hardware: {'; '.join(hardware_reasons)}.")

            return PolicyEvaluationResult(
                verdict=DecisionVerdict.INSUFFICIENT,
                reason="Todas as evidências empíricas existentes estão desatualizadas ou incompatíveis com o ambiente alvo.",
                limitations=limitations,
                next_validation_steps=["Reexecutar os experimentos no hardware e versão vigentes."]
            )

        # 3. Regra de Insuficiência: Completude média muito baixa (< 0.45) (ADV-02)
        avg_completeness = sum(cs for _, cs, _ in valid_episodes) / len(valid_episodes)
        if avg_completeness < 0.45:
            missing_fields = set()
            for ep, _, _ in valid_episodes:
                if not ep.commit_hash: missing_fields.add("commit_hash")
                if not (ep.environment_context or {}).get("hardware"): missing_fields.add("hardware")
                if not ep.measured_at: missing_fields.add("measured_at")
            missing_str = ", ".join(sorted(missing_fields)) or "metadados de execução"
            return PolicyEvaluationResult(
                verdict=DecisionVerdict.INSUFFICIENT,
                reason=f"Completude experimental insuficiente ({avg_completeness:.2f} < 0.45). Metadados essenciais ausentes.",
                limitations=[f"Faltam identificadores obrigatórios nos experimentos: {missing_str}."],
                next_validation_steps=["Registrar benchmarks completos incluindo parâmetros de hardware, commit e métricas no payload."]
            )

        # Coleta limitações observadas nas evidências válidas
        for ep, _, _ in valid_episodes:
            env = ep.environment_context or {}
            hw = env.get("hardware") or env.get("gpu")
            if hw:
                limitations.append(f"Resultados obtidos especificamente no hardware '{hw}'.")
            if ep.commit_hash:
                limitations.append(f"Comportamento aferido na versão de código #{ep.commit_hash[:7]}.")

        # 4. Regra de Refutação: Exige rigor metrológico formal (ADV-06, Endurecimento A)
        if has_theoretical_basis:
            for ep, cs, _ in valid_episodes:
                env = ep.environment_context or {}
                metrics = env.get("metrics")
                has_quantitative_metrics = bool(metrics and isinstance(metrics, dict) and len(metrics) > 0)

                # Refutação exige completude >= 0.70 E métricas quantitativas identificadas
                if cs >= 0.70 and has_quantitative_metrics:
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

        # 5. Regra de Controvérsia: Comparabilidade Experimental (ADV-07, Endurecimento B)
        if comparison and len(comparison.ranking) >= 2:
            hws = set()
            for item in comparison.ranking:
                ep_match = next((e for e in dedup_episodes if (e.experiment_id or e.id) == item["experiment_id"]), None)
                if ep_match:
                    hws.add((ep_match.environment_context or {}).get("hardware") or "desconhecido")

            best_val = comparison.ranking[0]["metric_value"]
            worst_val = comparison.ranking[-1]["metric_value"]
            delta_ratio = abs(worst_val - best_val) / max(0.001, min(worst_val, best_val))

            if delta_ratio > 0.50:
                # Controvérsia legítima: sob condições e hardwares equivalentes
                if len(hws) <= 1:
                    hw_name = next(iter(hws)) if hws else "equivalente"
                    return PolicyEvaluationResult(
                        verdict=DecisionVerdict.CONTROVERSIAL,
                        reason=f"Evidências empíricas sob ambiente equivalente ('{hw_name}') apresentam alta dispersão de desempenho ({delta_ratio:.0%}). Decisão exige cautela com trade-offs.",
                        limitations=list(set(limitations)),
                        next_validation_steps=["Isolar variáveis de processo que causaram dispersão superior a 50% sob mesmo hardware."]
                    )
                else:
                    # Divergência esperada decorrente de hardwares distintos
                    limitations.append(
                        f"Comparabilidade restrita: variação de {delta_ratio:.0%} observada entre hardwares distintos ({', '.join(hws)})."
                    )

        # 6. Regra Favorável: Evidência válida confirma a viabilidade prática (ADV-09)
        next_steps.append("Monitorar a estabilidade sob carga em produção e manter os benchmarks de regressão ativos.")
        return PolicyEvaluationResult(
            verdict=DecisionVerdict.FAVORABLE,
            reason="Evidências empíricas válidas confirmam a viabilidade prática e convergem com a fundamentação técnica.",
            limitations=list(set(limitations)),
            next_validation_steps=next_steps
        )
