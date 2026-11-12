import re
from typing import Dict, Any, Tuple
from src.domain.entities.memory import MemoryEpisode


class EvidenceQualityEvaluator:
    """
    Avalia a completude e o rigor experimental de uma evidência empírica.
    Importante: mede a riqueza dos metadados fornecidos, e não a veracidade criptográfica do Git.
    """

    @staticmethod
    def evaluate(episode: MemoryEpisode) -> Tuple[float, Dict[str, bool]]:
        """
        Calcula o score de completude (0.0 a 1.0) e detalha os critérios atendidos.
        Retorna (score, criteria_breakdown).
        """
        breakdown = {
            "has_commit_hash": False,
            "has_environment_context": False,
            "has_timestamp": False,
            "has_identifiable_metrics": False
        }

        # 1. Commit hash
        if episode.commit_hash and len(episode.commit_hash.strip()) >= 4:
            breakdown["has_commit_hash"] = True

        # 2. Contexto de execução e hardware
        env = episode.environment_context or {}
        if env and any(k in env for k in ["hardware", "gpu", "os", "concurrency", "runtime", "cpu"]):
            breakdown["has_environment_context"] = True

        # 3. Timestamp da medição
        if episode.measured_at or episode.created_at:
            breakdown["has_timestamp"] = True

        # 4. Métricas estruturadas ou identificáveis
        has_metrics = False
        if "metrics" in env and isinstance(env["metrics"], dict) and env["metrics"]:
            has_metrics = True
        elif any(k in env for k in ["latency_ms", "throughput_fps", "p99_ms", "duration_ms", "fps"]):
            has_metrics = True
        else:
            # Fallback textual: procura padrões numéricos com unidades técnicas (ms, fps, req/s, MB/s)
            resp = episode.response.lower()
            if re.search(r'\b\d+(\.\d+)?\s*(ms|µs|us|s|fps|req/s|mb/s|gb/s|tokens/s)\b', resp):
                has_metrics = True
        breakdown["has_identifiable_metrics"] = has_metrics

        # Ponderação
        score = 0.0
        if breakdown["has_commit_hash"]:
            score += 0.25
        if breakdown["has_environment_context"]:
            score += 0.25
        if breakdown["has_timestamp"]:
            score += 0.20
        if breakdown["has_identifiable_metrics"]:
            score += 0.30

        return round(min(1.0, score), 2), breakdown
