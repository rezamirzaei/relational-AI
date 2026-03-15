from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from relational_fraud_intelligence.application.ports.explanations import (
    AnalysisExplanationService,
)
from relational_fraud_intelligence.application.ports.reasoner import RiskReasoner
from relational_fraud_intelligence.application.ports.security import RateLimiter
from relational_fraud_intelligence.application.ports.text_signals import TextSignalService
from relational_fraud_intelligence.application.services.alert_service import AlertService
from relational_fraud_intelligence.application.services.audit_service import AuditService
from relational_fraud_intelligence.application.services.auth_service import AuthService
from relational_fraud_intelligence.application.services.case_assembler import (
    InvestigationCaseAssembler,
)
from relational_fraud_intelligence.application.services.case_service import CaseService
from relational_fraud_intelligence.application.services.dashboard_service import DashboardService
from relational_fraud_intelligence.application.services.dataset_service import DatasetService
from relational_fraud_intelligence.application.services.investigation_service import (
    InvestigationService,
)
from relational_fraud_intelligence.application.services.scenario_catalog_service import (
    ScenarioCatalogService,
)
from relational_fraud_intelligence.application.services.workspace_guide_service import (
    WorkspaceGuideService,
)
from relational_fraud_intelligence.infrastructure.explanations import (
    DeterministicAnalysisExplanationService,
    FallbackAnalysisExplanationService,
    HuggingFaceAnalysisExplanationService,
)
from relational_fraud_intelligence.infrastructure.persistence.repository import (
    SqlAlchemyScenarioRepository,
)
from relational_fraud_intelligence.infrastructure.persistence.security_repository import (
    SqlAlchemyAuditLogRepository,
    SqlAlchemyOperatorRepository,
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
from relational_fraud_intelligence.infrastructure.persistence.workflow_repository import (
    SqlAlchemyAlertRepository,
    SqlAlchemyCaseRepository,
    SqlAlchemyDatasetStore,
)
from relational_fraud_intelligence.infrastructure.rate_limit.memory import (
    MemoryRateLimiter,
)
from relational_fraud_intelligence.infrastructure.rate_limit.redis_backend import (
    RedisRateLimiter,
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
from relational_fraud_intelligence.infrastructure.security.bootstrap import (
    OperatorBootstrapper,
    OperatorBootstrapResult,
)
from relational_fraud_intelligence.infrastructure.security.passwords import (
    PasswordHasher,
)
from relational_fraud_intelligence.infrastructure.security.tokens import TokenService
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
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    seed_result: SeedResult
    operator_bootstrap_result: OperatorBootstrapResult
    auth_service: AuthService
    audit_service: AuditService
    pruned_audit_events: int
    rate_limiter: RateLimiter
    active_rate_limit_backend: str
    requested_text_signal_provider: str
    active_text_signal_provider: str
    requested_reasoning_provider: str
    active_reasoning_provider: str
    requested_explanation_provider: str
    active_explanation_provider: str
    provider_startup_notes: list[str]
    scenario_catalog_service: ScenarioCatalogService
    investigation_service: InvestigationService
    case_service: CaseService
    alert_service: AlertService
    dashboard_service: DashboardService
    dataset_service: DatasetService
    analysis_explanation_service: AnalysisExplanationService
    workspace_guide_service: WorkspaceGuideService

    async def is_database_ready(self) -> bool:
        return await ping_database(self.session_factory)

    def is_rate_limiter_ready(self) -> bool:
        return self.rate_limiter.is_healthy()

    async def shutdown(self) -> None:
        close = getattr(self.rate_limiter, "close", None)
        if callable(close):
            close()
        await self.engine.dispose()


async def build_container(settings: AppSettings | None = None) -> ApplicationContainer:
    app_settings = settings or AppSettings()

    engine = build_engine(app_settings.database_url, echo=app_settings.database_echo)
    session_factory = build_session_factory(engine)
    initializer = DatabaseInitializer(
        engine=engine,
        session_factory=session_factory,
        scenarios=build_seed_scenarios(),
    )
    seed_result = await initializer.initialize(
        create_schema=app_settings.database_auto_create_schema,
        seed_if_empty=app_settings.seed_scenarios_on_startup,
    )

    operator_repository = SqlAlchemyOperatorRepository(session_factory)
    audit_log_repository = SqlAlchemyAuditLogRepository(session_factory)
    password_hasher = PasswordHasher()
    token_service = TokenService(app_settings)
    operator_bootstrap_result = await OperatorBootstrapper(
        repository=operator_repository,
        password_hasher=password_hasher,
        settings=app_settings,
    ).bootstrap()
    auth_service = AuthService(
        operator_repository=operator_repository,
        audit_log_repository=audit_log_repository,
        password_hasher=password_hasher,
        token_service=token_service,
        settings=app_settings,
    )
    audit_service = AuditService(audit_log_repository)
    pruned_audit_events = await audit_service.prune_expired_events(
        app_settings.audit_log_retention_days
    )

    scenario_repository = SqlAlchemyScenarioRepository(session_factory)
    scenario_catalog_service = ScenarioCatalogService(scenario_repository)

    rate_limiter: RateLimiter
    active_rate_limit_backend = app_settings.rate_limit_backend
    if app_settings.rate_limit_backend == "redis":
        redis_rate_limiter = RedisRateLimiter(app_settings.rate_limit_redis_url)
        if redis_rate_limiter.is_healthy():
            rate_limiter = redis_rate_limiter
        else:
            rate_limiter = MemoryRateLimiter()
            active_rate_limit_backend = "memory"
    else:
        rate_limiter = MemoryRateLimiter()

    keyword_service = KeywordTextSignalService()
    text_signal_service: TextSignalService
    provider_startup_notes: list[str] = []
    requested_text_signal_provider = app_settings.text_signal_provider
    active_text_signal_provider = requested_text_signal_provider
    if requested_text_signal_provider == "huggingface":
        try:
            text_signal_service = FallbackTextSignalService(
                primary=HuggingFaceTextSignalService(app_settings),
                fallback=keyword_service,
                requested_provider="huggingface",
            )
        except ValueError as exc:
            text_signal_service = keyword_service
            active_text_signal_provider = "keyword"
            provider_startup_notes.append(
                f"Text signal provider requested Hugging Face but started in keyword mode: {exc}"
            )
    else:
        text_signal_service = keyword_service

    local_reasoner = LocalRiskReasoner()
    risk_reasoner: RiskReasoner
    requested_reasoning_provider = app_settings.reasoning_provider
    active_reasoning_provider = requested_reasoning_provider
    if requested_reasoning_provider == "relationalai":
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

    case_repository = SqlAlchemyCaseRepository(session_factory)
    alert_repository = SqlAlchemyAlertRepository(session_factory)
    case_service = CaseService(case_repository)
    alert_service = AlertService(alert_repository)
    dataset_store = SqlAlchemyDatasetStore(session_factory)
    dataset_service = DatasetService(dataset_store)
    dashboard_service = DashboardService(
        scenario_repository=scenario_repository,
        case_repository=case_repository,
        alert_repository=alert_repository,
        dataset_store=dataset_store,
    )
    workspace_guide_service = WorkspaceGuideService()

    deterministic_explanation_service = DeterministicAnalysisExplanationService()
    analysis_explanation_service: AnalysisExplanationService
    requested_explanation_provider = app_settings.explanation_provider
    active_explanation_provider = requested_explanation_provider
    if requested_explanation_provider == "huggingface":
        try:
            analysis_explanation_service = FallbackAnalysisExplanationService(
                primary=HuggingFaceAnalysisExplanationService(app_settings),
                fallback=deterministic_explanation_service,
                requested_provider="huggingface",
            )
        except ValueError as exc:
            analysis_explanation_service = deterministic_explanation_service
            active_explanation_provider = "deterministic"
            provider_startup_notes.append(
                "Explanation provider requested Hugging Face but started in "
                f"deterministic mode: {exc}"
            )
    else:
        analysis_explanation_service = deterministic_explanation_service

    return ApplicationContainer(
        settings=app_settings,
        engine=engine,
        session_factory=session_factory,
        seed_result=seed_result,
        operator_bootstrap_result=operator_bootstrap_result,
        auth_service=auth_service,
        audit_service=audit_service,
        pruned_audit_events=pruned_audit_events,
        rate_limiter=rate_limiter,
        active_rate_limit_backend=active_rate_limit_backend,
        requested_text_signal_provider=requested_text_signal_provider,
        active_text_signal_provider=active_text_signal_provider,
        requested_reasoning_provider=requested_reasoning_provider,
        active_reasoning_provider=active_reasoning_provider,
        requested_explanation_provider=requested_explanation_provider,
        active_explanation_provider=active_explanation_provider,
        provider_startup_notes=provider_startup_notes,
        scenario_catalog_service=scenario_catalog_service,
        investigation_service=investigation_service,
        case_service=case_service,
        alert_service=alert_service,
        dashboard_service=dashboard_service,
        dataset_service=dataset_service,
        analysis_explanation_service=analysis_explanation_service,
        workspace_guide_service=workspace_guide_service,
    )
