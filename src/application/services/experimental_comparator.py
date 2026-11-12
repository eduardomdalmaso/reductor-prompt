import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from src.domain.entities.memory import MemoryEpisode


class MetricValue(BaseModel):
    name: str
    raw_value: float
    normalized_value: float  # Base: ms para latência, fps para throughput
    unit: str
    lower_is_better: bool = True


class ComparisonResult(BaseModel):
    winner_episode_id: Optional[str] = None
    metric_compared: str
    ranking: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str


class ExperimentalComparator:
    """Normaliza e compara métricas experimentais entre múltiplos episódios."""

    @staticmethod
    def extract_metric(episode: MemoryEpisode) -> Optional[MetricValue]:
        """Extrai métrica priorizando campos estruturados com fallback textual."""
        env = episode.environment_context or {}

        # 1. Campos estruturados prioritários
        if "metrics" in env and isinstance(env["metrics"], dict):
            for k, v in env["metrics"].items():
                if isinstance(v, (int, float)):
                    k_lower = k.lower()
                    if "latency" in k_lower or "ms" in k_lower or "duration" in k_lower:
                        return MetricValue(name="latency", raw_value=float(v), normalized_value=float(v), unit="ms", lower_is_better=True)
                    elif "fps" in k_lower or "throughput" in k_lower:
                        return MetricValue(name="throughput", raw_value=float(v), normalized_value=float(v), unit="fps", lower_is_better=False)

        for key in ["latency_ms", "p99_ms", "duration_ms"]:
            if key in env and isinstance(env[key], (int, float)):
                return MetricValue(name="latency", raw_value=float(env[key]), normalized_value=float(env[key]), unit="ms", lower_is_better=True)

        for key in ["throughput_fps", "fps", "tokens_per_sec"]:
            if key in env and isinstance(env[key], (int, float)):
                return MetricValue(name="throughput", raw_value=float(env[key]), normalized_value=float(env[key]), unit="fps", lower_is_better=False)

        # 2. Fallback textual controlado com normalização de unidades
        resp = episode.response
        # Busca latência (ms ou µs ou s)
        lat_match = re.search(r'(\d+(\.\d+)?)\s*(ms|µs|us|s)\b', resp, re.IGNORECASE)
        if lat_match:
            val = float(lat_match.group(1))
            unit = lat_match.group(3).lower()
            norm = val if unit == "ms" else (val / 1000.0 if unit in ["µs", "us"] else val * 1000.0)
            return MetricValue(name="latency", raw_value=val, normalized_value=norm, unit="ms", lower_is_better=True)

        # Busca throughput (fps ou req/s)
        tput_match = re.search(r'(\d+(\.\d+)?)\s*(fps|req/s|tokens/s)\b', resp, re.IGNORECASE)
        if tput_match:
            val = float(tput_match.group(1))
            unit = tput_match.group(3).lower()
            return MetricValue(name="throughput", raw_value=val, normalized_value=val, unit=unit, lower_is_better=False)

        return None

    def compare(self, episodes: List[MemoryEpisode]) -> Optional[ComparisonResult]:
        """Compara uma lista de evidências pelo seu indicador de performance comum."""
        if len(episodes) < 2:
            return None

        candidates = []
        for ep in episodes:
            metric = self.extract_metric(ep)
            if metric:
                candidates.append((ep, metric))

        if len(candidates) < 2:
            return None

        # Garante que estamos comparando a mesma grandeza
        metric_name = candidates[0][1].name
        compatible = [c for c in candidates if c[1].name == metric_name]
        if len(compatible) < 2:
            return None

        lower_better = compatible[0][1].lower_is_better
        sorted_candidates = sorted(compatible, key=lambda x: x[1].normalized_value, reverse=not lower_better)

        ranking = []
        for rank, (ep, m) in enumerate(sorted_candidates, 1):
            hw = (ep.environment_context or {}).get("hardware") or "N/A"
            ranking.append({
                "rank": rank,
                "episode_id": ep.id,
                "experiment_id": ep.experiment_id,
                "commit_hash": ep.commit_hash,
                "hardware": hw,
                "metric_value": m.normalized_value,
                "unit": m.unit
            })

        best_ep, best_m = sorted_candidates[0]
        worst_ep, worst_m = sorted_candidates[-1]
        delta_pct = abs(worst_m.normalized_value - best_m.normalized_value) / max(0.001, worst_m.normalized_value) * 100

        summary = (
            f"Comparação de {metric_name.upper()}: Experimento '{best_ep.experiment_id}' apresentou o melhor resultado "
            f"({best_m.normalized_value:.2f} {best_m.unit}), superando '{worst_ep.experiment_id}' em {delta_pct:.1f}%."
        )

        return ComparisonResult(
            winner_episode_id=best_ep.id,
            metric_compared=metric_name,
            ranking=ranking,
            summary=summary
        )
