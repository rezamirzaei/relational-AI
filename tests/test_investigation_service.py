from relational_fraud_intelligence.application.dto.investigation import InvestigateScenarioCommand
from relational_fraud_intelligence.application.services.case_assembler import InvestigationCaseAssembler
from relational_fraud_intelligence.application.services.investigation_service import InvestigationService
from relational_fraud_intelligence.infrastructure.reasoners.local_risk_reasoner import LocalRiskReasoner
from relational_fraud_intelligence.infrastructure.repositories.demo_repository import DemoScenarioRepository
from relational_fraud_intelligence.infrastructure.text.keyword_text_signal_service import (
    KeywordTextSignalService,
)


def test_investigation_service_scores_synthetic_identity_ring_as_critical() -> None:
    service = InvestigationService(
        scenario_repository=DemoScenarioRepository(),
        text_signal_service=KeywordTextSignalService(),
        risk_reasoner=LocalRiskReasoner(),
        case_assembler=InvestigationCaseAssembler(),
    )

    result = service.execute(InvestigateScenarioCommand(scenario_id="synthetic-identity-ring"))

    assert result.investigation.total_risk_score >= 80
    assert result.investigation.risk_level == "critical"
    assert result.investigation.metrics.shared_device_count == 1
