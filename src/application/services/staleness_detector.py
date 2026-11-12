from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from src.domain.entities.memory import MemoryEpisode, EvidenceStatus


class StalenessAnalysis(BaseModel):
    """Diagnóstico analítico de obsolescência de uma evidência empírica."""
    is_stale: bool = False
    status_recommendation: EvidenceStatus = EvidenceStatus.VALID
    reasons: List[str] = Field(default_factory=list)
    age_days: Optional[float] = None
    hardware_match: bool = True


class StalenessDetector:
    """
    Detecta obsolescência de evidências empíricas frente ao ambiente atual.
    Não altera o banco automaticamente: produz uma análise auditável.
    """

    def __init__(self, default_ttl_days: int = 90):
        self.default_ttl_days = default_ttl_days

    def analyze(
        self,
        episode: MemoryEpisode,
        current_hardware: Optional[str] = None,
        current_commit: Optional[str] = None
    ) -> StalenessAnalysis:
        reasons = []
        is_stale = False
        hw_match = True

        # 1. Verificação de status pré-existente
        if episode.status == EvidenceStatus.STALE:
            reasons.append("Evidência já marcada explicitamente como STALE no banco.")
            is_stale = True
        elif episode.status == EvidenceStatus.INVALID:
            reasons.append("Evidência marcada explicitamente como INVALID no banco.")
            is_stale = True

        # 2. Verificação de Hardware Mismatch
        env = episode.environment_context or {}
        evidence_hw = (env.get("hardware") or env.get("gpu") or "").strip().lower()

        if current_hardware and evidence_hw:
            cur_hw_clean = current_hardware.strip().lower()
            # Se forem gerações ou modelos claramente distintos
            if evidence_hw not in cur_hw_clean and cur_hw_clean not in evidence_hw:
                hw_match = False
                is_stale = True
                reasons.append(
                    f"Divergência de Hardware: evidência aferida em '{evidence_hw}', ambiente atual opera em '{current_hardware}'."
                )

        # 3. Verificação de Commit / Drift de Código
        if current_commit and episode.commit_hash:
            if current_commit.strip().lower() != episode.commit_hash.strip().lower():
                reasons.append(
                    f"Versão de Código: evidência gerada no commit #{episode.commit_hash[:7]}, ambiente atual em #{current_commit[:7]}."
                )

        # 4. Verificação Temporal (TTL)
        ts_str = episode.measured_at or episode.created_at
        age_days = None
        if ts_str:
            try:
                # Normaliza ISO string
                clean_ts = ts_str.replace("Z", "+00:00")
                dt = datetime.fromisoformat(clean_ts)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                age_days = round((now - dt).total_seconds() / 86400.0, 1)

                if age_days > self.default_ttl_days:
                    is_stale = True
                    reasons.append(f"Validade Temporal Excedida: medição tem {age_days} dias (limite: {self.default_ttl_days} dias).")
            except Exception:
                pass

        return StalenessAnalysis(
            is_stale=is_stale,
            status_recommendation=EvidenceStatus.STALE if is_stale else EvidenceStatus.VALID,
            reasons=reasons,
            age_days=age_days,
            hardware_match=hw_match
        )
