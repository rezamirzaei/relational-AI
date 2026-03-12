from dataclasses import dataclass

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from relational_fraud_intelligence.application.ports.reasoner import RiskReasoner
from relational_fraud_intelligence.application.ports.text_signals import TextSignalService
from relational_fraud_intelligence.application.services.case_assembler import (
    InvestigationCaseAssembler,
)
from relational_fraud_intelligence.application.services.investigation_service import (
    InvestigationService,
)
from relational_fraud_intelligence.application.services.scenario_catalog_service import (
    ScenarioCatalogService,
)
from relational_fraud_intelligence.infrastructure.persistence.repository import (
    SqlAlchemyScenarioRepository,
)
from relational_fraud_intelligence.infrastructure.persistence.seed import (
    DatabaseInitializer,
    SeedResult,
)
from relational_fraud_intelligence.infrastructure.persistence.session import (
    build_engine,
    build_session_factory,
    ping_database,
)
from relational_fraud_intelligence.infrastructure.reasoners.fallback_reasoner import (
    FallbackRiskReasoner,
)
from relational_fraud_intelligence.infrastructure.reasoners.local_risk_reasoner import (
    LocalRiskReasoner,
)
from relational_fraud_intelligence.infrastructure.reasoners.relationalai_reasoner import (
    RelationalAIRiskReasoner,
)
from relational_fraud_intelligence.infrastructure.seed.scenarios import build_seed_scenarios
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
    engine: Engine
    session_factory: sessionmaker[Session]
    seed_result: SeedResult
    scenario_catalog_service: ScenarioCatalogService
    investigation_service: InvestigationService

    def is_database_ready(self) -> bool:
        return ping_database(self.session_factory)

    def shutdown(self) -> None:
        self.engine.dispose()


def build_container(settings: AppSettings | None = None) -> ApplicationContainer:
    app_settings = settings or AppSettings()

    engine = build_engine(app_settings.database_url, echo=app_settings.database_echo)
    session_factory = build_session_factory(engine)
    initializer = DatabaseInitializer(
        engine=engine,
        session_factory=session_factory,
        scenarios=build_seed_scenarios(),
    )
    seed_result = initializer.initialize(
        create_schema=app_settings.database_auto_create_schema,
        seed_if_empty=app_settings.seed_scenarios_on_startup,
    )

    scenario_repository = SqlAlchemyScenarioRepository(session_factory)
    scenario_catalog_service = ScenarioCatalogService(scenario_repository)

    keyword_service = KeywordTextSignalService()
    text_signal_service: TextSignalService
    if app_settings.text_signal_provider == "huggingface":
        text_signal_service = FallbackTextSignalService(
            primary=HuggingFaceTextSignalService(app_settings),
            fallback=keyword_service,
            requested_provider="huggingface",
        )
    else:
        text_signal_service = keyword_service

    local_reasoner = LocalRiskReasoner()
    risk_reasoner: RiskReasoner
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
        engine=engine,
        session_factory=session_factory,
        seed_result=seed_result,
        scenario_catalog_service=scenario_catalog_service,
        investigation_service=investigation_service,
    )
