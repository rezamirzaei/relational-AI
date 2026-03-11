from dataclasses import dataclass

from relational_fraud_intelligence.application.services.case_assembler import InvestigationCaseAssembler
from relational_fraud_intelligence.application.services.investigation_service import InvestigationService
from relational_fraud_intelligence.application.services.scenario_catalog_service import ScenarioCatalogService
from relational_fraud_intelligence.infrastructure.reasoners.fallback_reasoner import FallbackRiskReasoner
from relational_fraud_intelligence.infrastructure.reasoners.local_risk_reasoner import LocalRiskReasoner
from relational_fraud_intelligence.infrastructure.reasoners.relationalai_reasoner import (
    RelationalAIRiskReasoner,
)
from relational_fraud_intelligence.infrastructure.repositories.demo_repository import DemoScenarioRepository
from relational_fraud_intelligence.infrastructure.text.fallback_text_signal_service import (
    FallbackTextSignalService,
)
from relational_fraud_intelligence.infrastructure.text.huggingface_text_signal_service import (
    HuggingFaceTextSignalService,
)
from relational_fraud_intelligence.infrastructure.text.keyword_text_signal_service import (
    KeywordTextSignalService,
)
from relational_fraud_intelligence.settings import AppSettings


@dataclass(slots=True)
class ApplicationContainer:
    settings: AppSettings
    scenario_catalog_service: ScenarioCatalogService
    investigation_service: InvestigationService


def build_container(settings: AppSettings | None = None) -> ApplicationContainer:
    app_settings = settings or AppSettings()

    scenario_repository = DemoScenarioRepository()
    scenario_catalog_service = ScenarioCatalogService(scenario_repository)

    keyword_service = KeywordTextSignalService()
    if app_settings.text_signal_provider == "huggingface":
        text_signal_service = FallbackTextSignalService(
            primary=HuggingFaceTextSignalService(app_settings),
            fallback=keyword_service,
            requested_provider="huggingface",
        )
    else:
        text_signal_service = keyword_service

    local_reasoner = LocalRiskReasoner()
    if app_settings.reasoning_provider == "relationalai":
        risk_reasoner = FallbackRiskReasoner(
            primary=RelationalAIRiskReasoner(app_settings, local_reasoner),
            fallback=local_reasoner,
            requested_provider="relationalai",
        )
    else:
        risk_reasoner = local_reasoner

    investigation_service = InvestigationService(
        scenario_repository=scenario_repository,
        text_signal_service=text_signal_service,
        risk_reasoner=risk_reasoner,
        case_assembler=InvestigationCaseAssembler(),
    )

    return ApplicationContainer(
        settings=app_settings,
        scenario_catalog_service=scenario_catalog_service,
        investigation_service=investigation_service,
    )
