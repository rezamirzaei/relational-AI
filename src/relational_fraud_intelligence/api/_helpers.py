"""Shared type aliases and helper functions for API route modules."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, File, HTTPException, Query, UploadFile

from relational_fraud_intelligence.api.dependencies import get_container, require_roles
from relational_fraud_intelligence.application.dto.alerts import UpdateAlertStatusCommand
from relational_fraud_intelligence.application.dto.cases import (
    CaseDatasetDetail,
    CreateCaseCommand,
    GetCaseResult,
)
from relational_fraud_intelligence.application.dto.investigation import (
    GetScenarioQuery,
    InvestigateScenarioCommand,
)
from relational_fraud_intelligence.bootstrap import ApplicationContainer
from relational_fraud_intelligence.domain.models import (
    AlertStatus,
    AnalysisResult,
    CaseComment,
    CaseEvidenceSnapshot,
    CasePriority,
    CaseStatus,
    Dataset,
    FraudAlert,
    FraudCase,
    InvestigationCase,
    InvestigatorNote,
    OperatorPrincipal,
    OperatorRole,
    RiskLevel,
    TransactionRecord,
    UploadedTransaction,
    WorkflowSourceType,
)

# ---------------------------------------------------------------------------
# Shared dependency type aliases
# ---------------------------------------------------------------------------

ContainerDep = Annotated[ApplicationContainer, Depends(get_container)]
AnalystDep = Annotated[
    OperatorPrincipal,
    Depends(require_roles(OperatorRole.ANALYST, OperatorRole.ADMIN)),
]
AdminDep = Annotated[OperatorPrincipal, Depends(require_roles(OperatorRole.ADMIN))]
CaseStatusFilter = Annotated[CaseStatus | None, Query()]
CasePriorityFilter = Annotated[CasePriority | None, Query()]
AlertStatusFilter = Annotated[AlertStatus | None, Query()]
RiskLevelFilter = Annotated[RiskLevel | None, Query()]
PageParam = Annotated[int, Query(ge=1)]
PageSizeParam = Annotated[int, Query(ge=1, le=100)]
UploadFileParam = Annotated[UploadFile, File(...)]


# ---------------------------------------------------------------------------
# Shared helper functions
# ---------------------------------------------------------------------------


async def validate_case_source(
    command: CreateCaseCommand,
    container: ApplicationContainer,
) -> None:
    if command.source_type == WorkflowSourceType.DATASET:
        await container.dataset_service.get_dataset(command.source_id or "")
        return
    await container.scenario_catalog_service.get_scenario(
        GetScenarioQuery(scenario_id=command.source_id or "")
    )


async def build_case_command_from_alert(
    alert: FraudAlert,
    container: ApplicationContainer,
) -> CreateCaseCommand:
    risk_level = alert.severity
    risk_score = risk_score_from_severity(risk_level)
    summary = alert.narrative

    if alert.source_type == WorkflowSourceType.DATASET:
        try:
            analysis = await container.dataset_service.get_result(alert.source_id)
            risk_score = analysis.risk_score
            summary = analysis.summary
        except LookupError:
            pass

    return CreateCaseCommand(
        source_type=alert.source_type,
        source_id=alert.source_id,
        scenario_id=alert.scenario_id,
        title=f"Alert review: {alert.title}",
        summary=summary,
        priority=priority_from_risk_level(risk_level),
        risk_score=risk_score,
        risk_level=risk_level,
    )


def findings_from_investigation(investigation: InvestigationCase) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = [
        {
            "rule_code": lead.lead_type,
            "title": lead.title,
            "narrative": f"{lead.hypothesis} {lead.narrative}".strip(),
        }
        for lead in investigation.investigation_leads
    ]
    if findings:
        return findings
    fallback_findings: list[dict[str, object]] = [
        {
            "rule_code": hit.rule_code,
            "title": hit.title,
            "narrative": hit.narrative,
        }
        for hit in investigation.top_rule_hits
    ]
    return fallback_findings


def build_case_command_from_investigation(
    investigation: InvestigationCase,
) -> CreateCaseCommand:
    top_lead = investigation.investigation_leads[0] if investigation.investigation_leads else None
    summary_parts = [investigation.summary]
    if top_lead is not None:
        summary_parts.append(f"Primary lead: {top_lead.title}.")
        summary_parts.append(top_lead.hypothesis)
        summary_parts.append(top_lead.narrative)
        if top_lead.recommended_actions:
            summary_parts.append("Next steps: " + " ".join(top_lead.recommended_actions[:2]))

    title = (
        f"{investigation.scenario.title}: {top_lead.title}"
        if top_lead is not None
        else investigation.scenario.title
    )

    return CreateCaseCommand(
        source_type=WorkflowSourceType.SCENARIO,
        source_id=investigation.scenario.scenario_id,
        scenario_id=investigation.scenario.scenario_id,
        title=title,
        summary=" ".join(summary_parts),
        priority=priority_from_risk_level(investigation.risk_level),
        risk_score=investigation.total_risk_score,
        risk_level=investigation.risk_level,
    )


async def build_case_command_from_analysis(
    dataset_id: str,
    container: ApplicationContainer,
) -> CreateCaseCommand:
    dataset = await container.dataset_service.get_dataset(dataset_id)
    analysis = await container.dataset_service.get_result(dataset_id)
    top_lead = analysis.investigation_leads[0] if analysis.investigation_leads else None
    additional_leads = max(0, len(analysis.investigation_leads) - 1)

    summary_parts = [analysis.summary]
    if top_lead is not None:
        summary_parts.append(f"Primary lead: {top_lead.title}.")
        summary_parts.append(top_lead.hypothesis)
        summary_parts.append(top_lead.narrative)
        if top_lead.recommended_actions:
            summary_parts.append("Next steps: " + " ".join(top_lead.recommended_actions[:2]))
    if additional_leads:
        summary_parts.append(
            f"{additional_leads} additional investigation lead(s) remain attached to the analysis."
        )

    title = (
        f"{dataset.name}: {top_lead.title}"
        if top_lead is not None
        else f"Dataset review: {dataset.name}"
    )

    return CreateCaseCommand(
        source_type=WorkflowSourceType.DATASET,
        source_id=dataset_id,
        title=title,
        summary=" ".join(summary_parts),
        priority=priority_from_risk_level(analysis.risk_level),
        risk_score=analysis.risk_score,
        risk_level=analysis.risk_level,
    )


def to_case_dataset_detail(dataset: Dataset) -> CaseDatasetDetail:
    return CaseDatasetDetail(
        dataset_id=dataset.dataset_id,
        name=dataset.name,
        uploaded_at=dataset.uploaded_at.isoformat(),
        row_count=dataset.row_count,
        status=dataset.status,
        error_message=dataset.error_message,
    )


def priority_from_risk_level(risk_level: RiskLevel) -> CasePriority:
    return {
        RiskLevel.LOW: CasePriority.LOW,
        RiskLevel.MEDIUM: CasePriority.MEDIUM,
        RiskLevel.HIGH: CasePriority.HIGH,
        RiskLevel.CRITICAL: CasePriority.CRITICAL,
    }[risk_level]


def risk_score_from_severity(risk_level: RiskLevel) -> int:
    return {
        RiskLevel.LOW: 20,
        RiskLevel.MEDIUM: 45,
        RiskLevel.HIGH: 70,
        RiskLevel.CRITICAL: 90,
    }[risk_level]


def case_detail_from_snapshot(
    *,
    case: FraudCase,
    comments: list[CaseComment],
    related_alerts: list[FraudAlert],
) -> GetCaseResult | None:
    snapshot = case.evidence_snapshot
    if snapshot is None:
        return None

    if case.source_type == WorkflowSourceType.DATASET:
        if snapshot.dataset is None:
            return None
        return GetCaseResult(
            case=case,
            comments=comments,
            related_alerts=related_alerts,
            analysis=snapshot.analysis,
            dataset=to_case_dataset_detail(snapshot.dataset),
            dataset_transactions=snapshot.dataset_transactions,
        )

    if (
        snapshot.investigation is None
        and not snapshot.scenario_transactions
        and not snapshot.investigator_notes
    ):
        return None

    return GetCaseResult(
        case=case,
        comments=comments,
        related_alerts=related_alerts,
        investigation=snapshot.investigation,
        scenario_transactions=snapshot.scenario_transactions,
        investigator_notes=snapshot.investigator_notes,
    )


async def build_case_evidence_snapshot(
    command: CreateCaseCommand,
    container: ApplicationContainer,
) -> CaseEvidenceSnapshot:
    if command.source_type == WorkflowSourceType.DATASET:
        dataset = await container.dataset_service.get_dataset(command.source_id or "")
        try:
            analysis = await container.dataset_service.get_result(dataset.dataset_id)
        except LookupError:
            analysis = None
        return build_dataset_case_snapshot(
            dataset=dataset,
            analysis=analysis,
            dataset_transactions=await container.dataset_service.get_transactions(
                dataset.dataset_id
            ),
        )

    scenario_id = command.scenario_id or command.source_id or ""
    scenario = (
        await container.scenario_catalog_service.get_scenario(
            GetScenarioQuery(scenario_id=scenario_id)
        )
    ).scenario
    investigation = (
        await container.investigation_service.execute(
            InvestigateScenarioCommand(scenario_id=scenario_id)
        )
    ).investigation
    return build_scenario_case_snapshot(
        investigation=investigation,
        scenario_transactions=scenario.transactions,
        investigator_notes=scenario.investigator_notes,
    )


def build_dataset_case_snapshot(
    *,
    dataset: Dataset,
    analysis: AnalysisResult | None,
    dataset_transactions: list[UploadedTransaction],
) -> CaseEvidenceSnapshot:
    return CaseEvidenceSnapshot(
        analysis=analysis,
        dataset=dataset,
        dataset_transactions=dataset_transactions,
    )


def build_scenario_case_snapshot(
    *,
    investigation: InvestigationCase | None,
    scenario_transactions: list[TransactionRecord],
    investigator_notes: list[InvestigatorNote],
) -> CaseEvidenceSnapshot:
    return CaseEvidenceSnapshot(
        investigation=investigation,
        scenario_transactions=scenario_transactions,
        investigator_notes=investigator_notes,
    )


async def create_case_with_source_links(
    *,
    command: CreateCaseCommand,
    container: ApplicationContainer,
    evidence_snapshot: CaseEvidenceSnapshot,
    related_alerts: list[FraudAlert] | None = None,
) -> tuple[FraudCase, list[FraudAlert]]:
    source_alerts = related_alerts or await container.alert_service.list_alerts_for_source(
        source_type=command.source_type,
        source_id=command.source_id or "",
    )
    existing_case_id = _existing_linked_case_id(source_alerts)
    if existing_case_id is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"{_source_label(command.source_type)} '{command.source_id}' already has alerts "
                f"linked to case '{existing_case_id}'."
            ),
        )

    created_case = (
        await container.case_service.create_case(
            command,
            evidence_snapshot=evidence_snapshot,
        )
    ).case
    linked_alerts = await _link_source_alerts(container, source_alerts, created_case.case_id)
    synced_case = await container.case_service.sync_alert_count(
        created_case.case_id,
        await container.alert_service.count_linked_to_case(created_case.case_id),
    )
    return synced_case, linked_alerts


async def sync_case_alert_counts(
    container: ApplicationContainer,
    *case_ids: str | None,
) -> None:
    seen_case_ids: set[str] = set()
    for case_id in case_ids:
        if case_id is None or case_id in seen_case_ids:
            continue
        seen_case_ids.add(case_id)
        try:
            await container.case_service.sync_alert_count(
                case_id,
                await container.alert_service.count_linked_to_case(case_id),
            )
        except LookupError:
            continue


async def _link_source_alerts(
    container: ApplicationContainer,
    alerts: list[FraudAlert],
    case_id: str,
) -> list[FraudAlert]:
    linked_alerts: list[FraudAlert] = []
    for alert in alerts:
        if alert.status in {AlertStatus.RESOLVED, AlertStatus.FALSE_POSITIVE}:
            continue
        linked_alerts.append(
            (
                await container.alert_service.update_status(
                    UpdateAlertStatusCommand(
                        alert_id=alert.alert_id,
                        status=AlertStatus.INVESTIGATING,
                        linked_case_id=case_id,
                    )
                )
            ).alert
        )
    return linked_alerts


def _existing_linked_case_id(alerts: list[FraudAlert]) -> str | None:
    return next((alert.linked_case_id for alert in alerts if alert.linked_case_id), None)


def _source_label(source_type: WorkflowSourceType) -> str:
    return "Dataset" if source_type == WorkflowSourceType.DATASET else "Scenario"
