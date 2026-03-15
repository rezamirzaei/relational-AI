"""Dataset upload, ingestion, analysis, explanation, and case creation endpoints."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from relational_fraud_intelligence.api._helpers import (
    AnalystDep,
    ContainerDep,
    UploadFileParam,
    build_case_command_from_analysis,
    build_dataset_case_snapshot,
    create_case_with_source_links,
    validate_case_source,
)
from relational_fraud_intelligence.application.dto.explanations import (
    GetAnalysisExplanationResult,
)
from relational_fraud_intelligence.application.dto.routes import (
    AnalysisResponse,
    CreateCaseFromAnalysisResult,
    DatasetListResponse,
    DatasetResponse,
    TransactionIngestBody,
)
from relational_fraud_intelligence.domain.models import (
    ExplanationAudience,
    WorkflowSourceType,
)

router = APIRouter()


@router.post(
    "/datasets/upload",
    response_model=DatasetResponse,
    tags=["Datasets"],
    summary="Upload a transaction CSV",
    description=(
        "Upload a CSV file with transaction data for fraud analysis. "
        "Required columns: transaction_id, account_id, amount, timestamp. "
        "Optional: merchant, category, device_fingerprint, ip_country, channel, is_fraud."
    ),
)
async def upload_dataset(
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
    file: UploadFileParam,
) -> DatasetResponse:
    request.state.current_principal = principal
    request.state.audit_action = "upload-dataset"
    request.state.audit_resource_type = "dataset"
    try:
        content = await file.read()
        dataset = await container.dataset_service.upload_csv(
            filename=file.filename or "upload.csv",
            content=content,
        )
        request.state.audit_resource_id = dataset.dataset_id
        return DatasetResponse(
            dataset_id=dataset.dataset_id,
            name=dataset.name,
            uploaded_at=dataset.uploaded_at.isoformat(),
            row_count=dataset.row_count,
            status=dataset.status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/datasets/ingest",
    response_model=DatasetResponse,
    tags=["Datasets"],
    summary="Ingest transactions via API",
    description="Accepts a JSON array of transaction records for programmatic ingestion.",
)
async def ingest_transactions(
    body: TransactionIngestBody,
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
) -> DatasetResponse:
    request.state.current_principal = principal
    request.state.audit_action = "ingest-transactions"
    request.state.audit_resource_type = "dataset"
    try:
        dataset = await container.dataset_service.ingest_transactions(
            name=body.name,
            transactions=body.transactions,
        )
        request.state.audit_resource_id = dataset.dataset_id
        return DatasetResponse(
            dataset_id=dataset.dataset_id,
            name=dataset.name,
            uploaded_at=dataset.uploaded_at.isoformat(),
            row_count=dataset.row_count,
            status=dataset.status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/datasets",
    response_model=DatasetListResponse,
    tags=["Datasets"],
    summary="List uploaded datasets",
)
async def list_datasets(
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
) -> DatasetListResponse:
    request.state.current_principal = principal
    request.state.audit_action = "list-datasets"
    request.state.audit_resource_type = "dataset"
    datasets = await container.dataset_service.list_datasets()
    return DatasetListResponse(
        datasets=[
            DatasetResponse(
                dataset_id=d.dataset_id,
                name=d.name,
                uploaded_at=d.uploaded_at.isoformat(),
                row_count=d.row_count,
                status=d.status,
                error_message=d.error_message,
            )
            for d in datasets
        ]
    )


@router.post(
    "/datasets/{dataset_id}/analyze",
    response_model=AnalysisResponse,
    tags=["Datasets"],
    summary="Run fraud analysis on a dataset",
    description=(
        "Executes Benford's Law analysis, statistical outlier detection, "
        "velocity spike detection, round-amount structuring detection, and "
        "behavioral relationship inference over accounts, devices, merchants, "
        "and geographies."
    ),
)
async def analyze_dataset(
    dataset_id: str,
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
) -> AnalysisResponse:
    request.state.current_principal = principal
    request.state.audit_action = "analyze-dataset"
    request.state.audit_resource_type = "dataset"
    request.state.audit_resource_id = dataset_id
    try:
        result = await container.dataset_service.analyze(dataset_id)
        findings: list[dict[str, object]] = [
            {
                "rule_code": lead.lead_type,
                "title": lead.title,
                "narrative": f"{lead.hypothesis} {lead.narrative}".strip(),
            }
            for lead in result.investigation_leads
        ]
        if not findings:
            findings = [
                {
                    "rule_code": anomaly.anomaly_type,
                    "title": anomaly.title,
                    "narrative": anomaly.description,
                }
                for anomaly in result.anomalies
            ]
        await container.alert_service.generate_alerts_from_analysis(
            dataset_id=dataset_id,
            risk_score=result.risk_score,
            findings=findings,
        )
        return AnalysisResponse(analysis=result)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/datasets/{dataset_id}/analysis",
    response_model=AnalysisResponse,
    tags=["Datasets"],
    summary="Get analysis results for a dataset",
)
async def get_analysis_results(
    dataset_id: str,
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
) -> AnalysisResponse:
    request.state.current_principal = principal
    request.state.audit_action = "get-analysis-results"
    request.state.audit_resource_type = "dataset"
    request.state.audit_resource_id = dataset_id
    try:
        result = await container.dataset_service.get_result(dataset_id)
        return AnalysisResponse(analysis=result)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/datasets/{dataset_id}/case",
    response_model=CreateCaseFromAnalysisResult,
    tags=["Datasets"],
    summary="Create a case from a dataset analysis",
    description=(
        "Creates a persistent fraud case from a completed dataset analysis using the "
        "analysis-generated investigation leads, and links any open dataset alerts to that case."
    ),
)
async def create_case_from_analysis(
    dataset_id: str,
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
) -> CreateCaseFromAnalysisResult:
    request.state.current_principal = principal
    request.state.audit_action = "create-case-from-analysis"
    request.state.audit_resource_type = "dataset"
    request.state.audit_resource_id = dataset_id
    try:
        analysis = await container.dataset_service.get_result(dataset_id)
        case_command = await build_case_command_from_analysis(dataset_id, container)
        await validate_case_source(case_command, container)
        related_alerts = await container.alert_service.list_alerts_for_source(
            source_type=WorkflowSourceType.DATASET,
            source_id=dataset_id,
        )
        created_case, linked_alerts = await create_case_with_source_links(
            command=case_command,
            container=container,
            evidence_snapshot=build_dataset_case_snapshot(
                dataset=await container.dataset_service.get_dataset(dataset_id),
                analysis=analysis,
                dataset_transactions=await container.dataset_service.get_transactions(dataset_id),
            ),
            related_alerts=related_alerts,
        )

        return CreateCaseFromAnalysisResult(
            analysis=analysis,
            case=created_case,
            linked_alerts=linked_alerts,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/datasets/{dataset_id}/explanation",
    response_model=GetAnalysisExplanationResult,
    tags=["Datasets"],
    summary="Explain a dataset analysis",
    description=(
        "Returns an operator-facing explanation of a completed dataset analysis. "
        "Statistical and behavioral scoring remain the source of truth even when the optional "
        "Hugging Face explanation provider is active."
    ),
)
async def get_analysis_explanation(
    dataset_id: str,
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
    audience: Annotated[ExplanationAudience, Query()] = ExplanationAudience.ANALYST,
) -> GetAnalysisExplanationResult:
    request.state.current_principal = principal
    request.state.audit_action = "get-analysis-explanation"
    request.state.audit_resource_type = "dataset"
    request.state.audit_resource_id = dataset_id
    try:
        dataset = await container.dataset_service.get_dataset(dataset_id)
        analysis = await container.dataset_service.get_result(dataset_id)
        explanation = container.analysis_explanation_service.explain(
            dataset=dataset,
            analysis=analysis,
            audience=audience,
        )
        return GetAnalysisExplanationResult(explanation=explanation)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc














