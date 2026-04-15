from relational_fraud_intelligence.application.dto.investigation import (
    AssembleInvestigationCommand,
    GetScenarioQuery,
    InvestigateScenarioCommand,
    InvestigateScenarioDraftCommand,
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
from relational_fraud_intelligence.domain.models import FraudScenario
from relational_fraud_intelligence.infrastructure.graph.analyzer import analyze_scenario_graph


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

    async def execute(self, command: InvestigateScenarioCommand) -> InvestigateScenarioResult:
        scenario_result = await self._scenario_repository.get_scenario(
            GetScenarioQuery(scenario_id=command.scenario_id)
        )
        return self._investigate_scenario(scenario_result.scenario)

    async def execute_draft(
        self,
        command: InvestigateScenarioDraftCommand,
    ) -> InvestigateScenarioResult:
        return self._investigate_scenario(command.scenario)

    def _investigate_scenario(
        self,
        scenario: FraudScenario,
    ) -> InvestigateScenarioResult:
        text_result = self._text_signal_service.score(
            ScoreTextSignalsCommand(scenario=scenario)
        )
        reasoning_result = self._risk_reasoner.reason(
            ReasonAboutRiskCommand(
                scenario=scenario,
                text_signals=text_result.signals,
            )
        )

        # Run graph analysis on the scenario relationship network
        graph_analysis = analyze_scenario_graph(scenario)

        return self._case_assembler.assemble(
            AssembleInvestigationCommand(
                scenario_overview=build_scenario_overview(scenario),
                text_result=text_result,
                reasoning_result=reasoning_result,
            ),
            graph_analysis=graph_analysis,
        )
