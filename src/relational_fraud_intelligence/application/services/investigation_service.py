from relational_fraud_intelligence.application.dto.investigation import (
    AssembleInvestigationCommand,
    GetScenarioQuery,
    InvestigateScenarioCommand,
    InvestigateScenarioResult,
    ReasonAboutRiskCommand,
    ScoreTextSignalsCommand,
)
from relational_fraud_intelligence.application.ports.reasoner import RiskReasoner
from relational_fraud_intelligence.application.ports.repositories import ScenarioRepository
from relational_fraud_intelligence.application.ports.text_signals import TextSignalService
from relational_fraud_intelligence.application.services.case_assembler import (
    InvestigationCaseAssembler,
)
from relational_fraud_intelligence.application.services.scenario_overview_factory import (
    build_scenario_overview,
)


class InvestigationService:
    def __init__(
        self,
        scenario_repository: ScenarioRepository,
        text_signal_service: TextSignalService,
        risk_reasoner: RiskReasoner,
        case_assembler: InvestigationCaseAssembler,
    ) -> None:
        self._scenario_repository = scenario_repository
        self._text_signal_service = text_signal_service
        self._risk_reasoner = risk_reasoner
        self._case_assembler = case_assembler

    def execute(self, command: InvestigateScenarioCommand) -> InvestigateScenarioResult:
        scenario_result = self._scenario_repository.get_scenario(
            GetScenarioQuery(scenario_id=command.scenario_id)
        )
        text_result = self._text_signal_service.score(
            ScoreTextSignalsCommand(scenario=scenario_result.scenario)
        )
        reasoning_result = self._risk_reasoner.reason(
            ReasonAboutRiskCommand(
                scenario=scenario_result.scenario,
                text_signals=text_result.signals,
            )
        )
        return self._case_assembler.assemble(
            AssembleInvestigationCommand(
                scenario_overview=build_scenario_overview(scenario_result.scenario),
                text_result=text_result,
                reasoning_result=reasoning_result,
            )
        )
