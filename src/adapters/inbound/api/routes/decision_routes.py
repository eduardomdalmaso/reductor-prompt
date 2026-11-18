import asyncio
from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.adapters.inbound.api.dependencies import (
    get_decision_use_case,
    get_evidence_use_case,
    verify_auth,
)
from src.application.dtos.decision_dtos import (
    DecisionResponseDTO,
    MakeDecisionRequestDTO,
)
from src.application.dtos.evidence_dtos import (
    IngestEvidenceRequestDTO,
    IngestEvidenceResponseDTO,
)
from src.application.services.system_telemetry_service import telemetry_service
from src.application.use_cases.ingest_evidence_use_case import IngestEvidenceUseCase
from src.application.use_cases.make_decision_use_case import MakeDecisionUseCase
from src.domain.entities.memory import EvidenceStatus, ProvenanceType
from src.domain.exceptions.exceptions import EvidenceConflictException
from src.domain.ports.inbound import IngestEvidenceCommand, MakeDecisionCommand

router = APIRouter()


@router.post("/api/v1/evidence", response_model=IngestEvidenceResponseDTO, dependencies=[Depends(verify_auth)])
async def ingest_evidence_endpoint(
    req: IngestEvidenceRequestDTO,
    response: Response,
    use_case: IngestEvidenceUseCase = Depends(get_evidence_use_case),
):
    """Recebe medições, benchmarks e evidências empíricas de projetos externos."""
    try:
        prov = ProvenanceType(req.provenance) if req.provenance in ProvenanceType._value2member_map_ else ProvenanceType.EMPIRICAL
        stat = EvidenceStatus(req.status) if req.status in EvidenceStatus._value2member_map_ else EvidenceStatus.VALID
        cmd = IngestEvidenceCommand(
            query=req.query,
            response=req.response,
            project_source=req.project_source,
            experiment_id=req.experiment_id,
            commit_hash=req.commit_hash,
            provenance=prov,
            status=stat,
            measured_at=req.measured_at,
            environment_context=req.environment_context,
            confidence_score=req.confidence_score,
            topic=req.topic,
            source_hashes=req.source_hashes,
        )
        episode, is_created = await asyncio.to_thread(use_case.execute, cmd)
        response.status_code = status.HTTP_201_CREATED if is_created else status.HTTP_200_OK
        msg = "Evidência empírica criada com sucesso." if is_created else "Evidência empírica existente retornada (idempotência)."
        return IngestEvidenceResponseDTO(
            id=episode.id,
            experiment_id=episode.experiment_id or req.experiment_id,
            project_source=episode.project_source or req.project_source,
            content_hash=episode.content_hash or "",
            status=episode.status.value if hasattr(episode.status, "value") else str(episode.status),
            is_created=is_created,
            message=msg,
        )
    except EvidenceConflictException as e:
        telemetry_service.log("WARNING", "EvidenceAPI", f"Conflito de evidência: {str(e)}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        telemetry_service.log("ERROR", "EvidenceAPI", f"Erro ao processar evidência: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/decisions", response_model=DecisionResponseDTO, dependencies=[Depends(verify_auth)])
async def make_decision_endpoint(
    req: MakeDecisionRequestDTO,
    use_case: MakeDecisionUseCase = Depends(get_decision_use_case),
):
    """Orquestra uma decisão de engenharia formal e rastreável."""
    try:
        cmd = MakeDecisionCommand(
            query=req.query,
            target_hardware=req.target_hardware,
            target_commit=req.target_commit,
            book_filter=req.book_filter,
            max_tokens=req.max_tokens,
            llm_synthesis=req.llm_synthesis,
        )
        report = await asyncio.to_thread(use_case.execute, cmd)
        return DecisionResponseDTO(
            decision_id=report.decision_id,
            query=report.query,
            verdict=report.verdict.value if hasattr(report.verdict, "value") else str(report.verdict),
            recommendation=report.recommendation,
            policy_version=report.policy_version,
            completeness_score=report.completeness_score,
            relevance_score=report.relevance_score,
            evidence_count=len(report.empirical_evidence),
            used_commit_hashes=report.used_commit_hashes,
            used_source_books=report.used_source_books,
            limitations=report.limitations,
            next_validation_steps=report.next_validation_steps,
            comparative_summary=report.comparative_summary,
            created_at=report.created_at.isoformat() if hasattr(report.created_at, "isoformat") else str(report.created_at),
        )
    except Exception as e:
        telemetry_service.log("ERROR", "DecisionAPI", f"Erro ao orquestrar decisão: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
