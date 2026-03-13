from collections.abc import Iterable

from relational_fraud_intelligence.application.dto.investigation import (
    AssembleInvestigationCommand,
    InvestigateScenarioResult,
)
from relational_fraud_intelligence.domain.models import (
    EntityReference,
    GraphAnalysisResult,
    InvestigationCase,
    InvestigationLead,
    ProviderSummary,
    RiskLevel,
    RuleHit,
    ScenarioTag,
    TextSignal,
    TransactionRecord,
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
        investigation_leads = _build_investigation_leads(
            rule_hits=command.reasoning_result.top_rule_hits,
            text_signals=command.text_result.signals,
            suspicious_transactions=command.reasoning_result.suspicious_transactions,
            scenario_tags=command.scenario_overview.tags,
            graph_analysis=graph_analysis,
        )
        summary = command.reasoning_result.summary
        if investigation_leads:
            summary = (
                f"{summary} Primary lead: {investigation_leads[0].title}. "
                f"{investigation_leads[0].hypothesis}"
            )

        return InvestigateScenarioResult(
            investigation=InvestigationCase(
                scenario=command.scenario_overview,
                risk_level=command.reasoning_result.risk_level,
                total_risk_score=command.reasoning_result.total_risk_score,
                summary=summary,
                metrics=command.reasoning_result.metrics,
                provider_summary=provider_summary,
                top_rule_hits=command.reasoning_result.top_rule_hits,
                graph_links=command.reasoning_result.graph_links,
                text_signals=command.text_result.signals,
                suspicious_transactions=command.reasoning_result.suspicious_transactions,
                recommended_actions=_merge_recommended_actions(
                    investigation_leads,
                    command.reasoning_result.recommended_actions,
                ),
                investigation_leads=investigation_leads,
                graph_analysis=graph_analysis,
            )
        )


def _build_investigation_leads(
    *,
    rule_hits: list[RuleHit],
    text_signals: list[TextSignal],
    suspicious_transactions: list[TransactionRecord],
    scenario_tags: list[ScenarioTag],
    graph_analysis: GraphAnalysisResult | None,
) -> list[InvestigationLead]:
    by_code = {rule_hit.rule_code: rule_hit for rule_hit in rule_hits}
    text_labels = {signal.label.lower() for signal in text_signals}
    leads: list[InvestigationLead] = []

    shared_device_rule = by_code.get("shared-device-cluster")
    if shared_device_rule is not None:
        narrative = shared_device_rule.narrative
        if graph_analysis is not None and graph_analysis.risk_amplification_factor > 1.2:
            narrative += (
                " The relationship graph amplified the cluster to "
                f"{graph_analysis.risk_amplification_factor:.2f}x baseline risk."
            )
        leads.append(
            InvestigationLead(
                lead_id="scenario-lead::shared-device-ring",
                lead_type="shared-device-ring",
                title="Potential shared-device coordination ring",
                severity=_severity_from_weight(shared_device_rule.weight),
                hypothesis=(
                    "Multiple customers are converging on the same device, which is "
                    "consistent with a coordinated identity ring or linked account takeover."
                ),
                narrative=narrative,
                entities=_unique_entities(shared_device_rule.evidence),
                supporting_anomaly_ids=[shared_device_rule.rule_code],
                recommended_actions=[
                    (
                        "Validate whether the linked customers have a legitimate "
                        "shared owner or household."
                    ),
                    (
                        "Review device binding, credential-reset history, and recent "
                        "login telemetry."
                    ),
                    (
                        "Keep linked accounts in the same investigation so the "
                        "network is reviewed together."
                    ),
                ],
                evidence={"supporting_amount": float(shared_device_rule.weight)},
            )
        )

    takeover_supporting_rules = [
        rule
        for rule in (
            by_code.get("cross-border-mismatch"),
            by_code.get("textual-fraud-context"),
            by_code.get("velocity-anomaly"),
        )
        if rule is not None
    ]
    if (
        ScenarioTag.ACCOUNT_TAKEOVER in scenario_tags
        or {
            "account takeover",
            "credential compromise",
            "sim swap",
        }
        & text_labels
    ):
        supporting_rules = takeover_supporting_rules or rule_hits[:1]
        leads.append(
            InvestigationLead(
                lead_id="scenario-lead::account-takeover",
                lead_type="account-takeover",
                title="Potential account takeover progression",
                severity=_max_rule_severity(supporting_rules, default=RiskLevel.HIGH),
                hypothesis=(
                    "The scenario combines takeover context, geography mismatch, or velocity "
                    "pressure in a way that fits compromised-account monetization."
                ),
                narrative=(
                    "Customer context and transaction behavior indicate the account may "
                    "already be in a live takeover or post-takeover cash-out stage."
                ),
                entities=_unique_entities(
                    entity for rule in supporting_rules for entity in rule.evidence
                ),
                supporting_anomaly_ids=[rule.rule_code for rule in supporting_rules],
                recommended_actions=[
                    (
                        "Confirm recent login, MFA reset, and SIM-swap indicators "
                        "before allowing more spend."
                    ),
                    (
                        "Step up authentication and prepare direct customer outreach "
                        "for the impacted identity."
                    ),
                    (
                        "Review outbound transfers and card-not-present activity as "
                        "a takeover timeline."
                    ),
                ],
                evidence={
                    "supporting_amount": float(sum(rule.weight for rule in supporting_rules))
                },
            )
        )

    merchant_rule = by_code.get("high-risk-merchant-concentration")
    rapid_rule = by_code.get("rapid-spend-burst")
    if merchant_rule is not None or rapid_rule is not None:
        supporting_rules = [rule for rule in (merchant_rule, rapid_rule) if rule is not None]
        cash_out_volume = sum(transaction.amount for transaction in suspicious_transactions)
        leads.append(
            InvestigationLead(
                lead_id="scenario-lead::cash-out",
                lead_type="cash-out-path",
                title="Cash-out path centers on rapid spend and liquidation merchants",
                severity=_max_rule_severity(supporting_rules, default=RiskLevel.MEDIUM),
                hypothesis=(
                    "The scenario's suspicious activity is not random; it is moving toward "
                    "merchant categories that support quick liquidation or transfer."
                ),
                narrative=" ".join(rule.narrative for rule in supporting_rules),
                entities=_unique_entities(
                    entity for rule in supporting_rules for entity in rule.evidence
                ),
                supporting_anomaly_ids=[rule.rule_code for rule in supporting_rules],
                recommended_actions=[
                    (
                        "Map the payout or liquidation path before reviewing the rest "
                        "of the scenario evidence."
                    ),
                    (
                        "Check whether the same merchants or channels appear in "
                        "other linked investigations."
                    ),
                    (
                        "Freeze or monitor the downstream cash-out channel if the "
                        "activity is still live."
                    ),
                ],
                evidence={"supporting_amount": float(cash_out_volume)},
            )
        )

    structuring_rules = [
        rule
        for rule in (
            by_code.get("round-amount-structuring"),
            by_code.get("dormant-account-activation"),
            by_code.get("historical-risk-pressure"),
        )
        if rule is not None
    ]
    if structuring_rules:
        leads.append(
            InvestigationLead(
                lead_id="scenario-lead::account-pressure",
                lead_type="account-pressure",
                title="Account pressure points suggest layered fraud preparation",
                severity=_max_rule_severity(structuring_rules, default=RiskLevel.MEDIUM),
                hypothesis=(
                    "The scenario shows account-level pressure such as structuring, dormant "
                    "reactivation, or prior review signals that often precede bust-out or mule use."
                ),
                narrative=" ".join(rule.narrative for rule in structuring_rules),
                entities=_unique_entities(
                    entity for rule in structuring_rules for entity in rule.evidence
                ),
                supporting_anomaly_ids=[rule.rule_code for rule in structuring_rules],
                recommended_actions=[
                    (
                        "Review account history and prior analyst notes before "
                        "treating the activity as isolated."
                    ),
                    (
                        "Compare current spend to the account's baseline inflow, "
                        "balance, and prior review pattern."
                    ),
                    (
                        "Escalate faster if low-activity accounts suddenly support "
                        "high-value movement."
                    ),
                ],
                evidence={
                    "supporting_amount": float(sum(rule.weight for rule in structuring_rules))
                },
            )
        )

    if graph_analysis is not None and graph_analysis.risk_amplification_factor > 1.25:
        hub_entity = graph_analysis.highest_degree_entity
        if hub_entity is not None:
            leads.append(
                InvestigationLead(
                    lead_id="scenario-lead::network-cluster",
                    lead_type="network-cluster",
                    title="Scenario evidence should be worked as one connected network",
                    severity=RiskLevel.MEDIUM,
                    hypothesis=(
                        "The graph structure shows a connected scheme, so isolated triage "
                        "would miss how the entities reinforce each other."
                    ),
                    narrative=(
                        f"The scenario graph centers on {hub_entity.display_name} with degree "
                        f"{graph_analysis.highest_degree_score} and a "
                        f"{graph_analysis.risk_amplification_factor:.2f}x amplification factor."
                    ),
                    entities=_unique_entities([hub_entity, *graph_analysis.hub_entities[:3]]),
                    supporting_anomaly_ids=[],
                    recommended_actions=[
                        (
                            "Keep the core entities in one case instead of "
                            "splitting the scenario into separate reviews."
                        ),
                        (
                            "Use the hub entity as the first pivot when "
                            "reconstructing ownership and access history."
                        ),
                        (
                            "Prioritize the highest-degree links before the "
                            "low-signal tail of the graph."
                        ),
                    ],
                    evidence={
                        "supporting_amount": graph_analysis.risk_amplification_factor,
                    },
                )
            )

    deduped: list[InvestigationLead] = []
    seen_titles: set[str] = set()
    for lead in sorted(leads, key=_lead_sort_key, reverse=True):
        if lead.title in seen_titles:
            continue
        seen_titles.add(lead.title)
        deduped.append(lead)
    return deduped[:4]


def _merge_recommended_actions(
    investigation_leads: list[InvestigationLead],
    existing_actions: list[str],
) -> list[str]:
    merged: list[str] = []
    for lead in investigation_leads:
        for action in lead.recommended_actions[:2]:
            if action not in merged:
                merged.append(action)
    for action in existing_actions:
        if action not in merged:
            merged.append(action)
    return merged[:5]


def _severity_from_weight(weight: int) -> RiskLevel:
    if weight >= 24:
        return RiskLevel.CRITICAL
    if weight >= 16:
        return RiskLevel.HIGH
    if weight >= 10:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _max_rule_severity(
    rules: list[RuleHit],
    *,
    default: RiskLevel,
) -> RiskLevel:
    if not rules:
        return default
    return max((_severity_from_weight(rule.weight) for rule in rules), key=_severity_rank)


def _lead_sort_key(lead: InvestigationLead) -> tuple[int, float, int]:
    return (
        _severity_rank(lead.severity),
        _coerce_float(lead.evidence.get("supporting_amount", 0.0)),
        len(lead.supporting_anomaly_ids),
    )


def _severity_rank(level: RiskLevel) -> int:
    return {
        RiskLevel.CRITICAL: 4,
        RiskLevel.HIGH: 3,
        RiskLevel.MEDIUM: 2,
        RiskLevel.LOW: 1,
    }[level]


def _unique_entities(entities: Iterable[EntityReference]) -> list[EntityReference]:
    unique: dict[tuple[str, str], EntityReference] = {}
    for entity in entities:
        unique[(str(entity.entity_type), entity.entity_id)] = entity
    return list(unique.values())[:4]


def _coerce_float(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0
