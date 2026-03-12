from relational_fraud_intelligence.application.dto.investigation import (
    AssembleInvestigationCommand,
    InvestigateScenarioResult,
)
from relational_fraud_intelligence.domain.models import (
    GraphAnalysisResult,
    InvestigationCase,
    ProviderSummary,
)


class InvestigationCaseAssembler:
    def assemble(
        self,
        command: AssembleInvestigationCommand,
        graph_analysis: GraphAnalysisResult | None = None,
    ) -> InvestigateScenarioResult:
        provider_summary = ProviderSummary(
            requested_reasoning_provider=command.reasoning_result.requested_provider,
            active_reasoning_provider=command.reasoning_result.active_provider,
            requested_text_provider=command.text_result.requested_provider,
            active_text_provider=command.text_result.active_provider,
            notes=command.text_result.notes + command.reasoning_result.provider_notes,
        )

        return InvestigateScenarioResult(
            investigation=InvestigationCase(
                scenario=command.scenario_overview,
                risk_level=command.reasoning_result.risk_level,
                total_risk_score=command.reasoning_result.total_risk_score,
                summary=command.reasoning_result.summary,
                metrics=command.reasoning_result.metrics,
                provider_summary=provider_summary,
                top_rule_hits=command.reasoning_result.top_rule_hits,
                graph_links=command.reasoning_result.graph_links,
                text_signals=command.text_result.signals,
                suspicious_transactions=command.reasoning_result.suspicious_transactions,
                recommended_actions=command.reasoning_result.recommended_actions,
                graph_analysis=graph_analysis,
            )
        )
