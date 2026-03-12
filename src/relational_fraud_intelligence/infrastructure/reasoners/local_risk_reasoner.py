from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from itertools import combinations
from typing import Protocol

from relational_fraud_intelligence.application.dto.investigation import (
    ReasonAboutRiskCommand,
    ReasonAboutRiskResult,
)
from relational_fraud_intelligence.domain.models import (
    AccountProfile,
    CustomerProfile,
    DeviceProfile,
    EntityReference,
    EntityType,
    GraphLink,
    InvestigationMetrics,
    InvestigatorNote,
    MerchantProfile,
    RiskLevel,
    RuleHit,
    ScenarioTag,
    TextSignal,
    TransactionRecord,
)


@dataclass(slots=True)
class ScenarioIndex:
    scenario_id: str
    scenario_title: str
    scenario_tags: list[ScenarioTag]
    customers: dict[str, CustomerProfile]
    accounts: dict[str, AccountProfile]
    devices: dict[str, DeviceProfile]
    merchants: dict[str, MerchantProfile]
    transactions: list[TransactionRecord]
    investigator_notes: list[InvestigatorNote]

    @classmethod
    def from_command(cls, command: ReasonAboutRiskCommand) -> ScenarioIndex:
        return cls(
            scenario_id=command.scenario.scenario_id,
            scenario_title=command.scenario.title,
            scenario_tags=list(command.scenario.tags),
            customers={customer.customer_id: customer for customer in command.scenario.customers},
            accounts={account.account_id: account for account in command.scenario.accounts},
            devices={device.device_id: device for device in command.scenario.devices},
            merchants={merchant.merchant_id: merchant for merchant in command.scenario.merchants},
            transactions=list(command.scenario.transactions),
            investigator_notes=list(command.scenario.investigator_notes),
        )


@dataclass(slots=True)
class RuleEvaluation:
    rule_hit: RuleHit | None = None
    graph_links: list[GraphLink] = field(default_factory=list)
    suspicious_transactions: list[TransactionRecord] = field(default_factory=list)


class RiskRule(Protocol):
    def evaluate(
        self,
        index: ScenarioIndex,
        text_signals: list[TextSignal],
    ) -> RuleEvaluation | None: ...


class SharedDeviceClusterRule:
    def evaluate(
        self,
        index: ScenarioIndex,
        text_signals: list[TextSignal],
    ) -> RuleEvaluation | None:
        _ = text_signals
        shared_devices = [
            device for device in index.devices.values() if len(device.linked_customer_ids) > 1
        ]
        if not shared_devices:
            return None

        evidence: list[EntityReference] = []
        graph_links: list[GraphLink] = []
        for device in shared_devices:
            for customer_id in sorted(device.linked_customer_ids):
                customer = index.customers[customer_id]
                evidence.append(
                    EntityReference(
                        entity_type=EntityType.CUSTOMER,
                        entity_id=customer.customer_id,
                        display_name=customer.full_name,
                    )
                )
            for left_customer_id, right_customer_id in combinations(
                sorted(device.linked_customer_ids),
                2,
            ):
                left_customer = index.customers[left_customer_id]
                right_customer = index.customers[right_customer_id]
                graph_links.append(
                    GraphLink(
                        relation="shares-device",
                        source=_customer_ref(left_customer),
                        target=_customer_ref(right_customer),
                        explanation=(
                            f"Both customers authenticated from device {device.device_id}."
                        ),
                    )
                )

        return RuleEvaluation(
            rule_hit=RuleHit(
                rule_code="shared-device-cluster",
                title="Shared device cluster",
                weight=28,
                narrative=(
                    "Multiple customers are linked to the same low-trust device, "
                    "suggesting an identity ring or coordinated takeover."
                ),
                evidence=evidence,
            ),
            graph_links=graph_links,
        )


class RapidSpendBurstRule:
    def evaluate(
        self,
        index: ScenarioIndex,
        text_signals: list[TextSignal],
    ) -> RuleEvaluation | None:
        _ = text_signals
        rapid_sequences = _find_rapid_sequences(index.transactions)
        if not rapid_sequences:
            return None

        return RuleEvaluation(
            rule_hit=RuleHit(
                rule_code="rapid-spend-burst",
                title="Rapid spend burst",
                weight=18,
                narrative=(
                    "High-value transactions arrived within a short window, "
                    "which is consistent with cash-out behavior."
                ),
                evidence=[
                    EntityReference(
                        entity_type=EntityType.ACCOUNT,
                        entity_id=transaction.account_id,
                        display_name=transaction.account_id,
                    )
                    for transaction in rapid_sequences[:2]
                ],
            ),
            suspicious_transactions=rapid_sequences,
        )


class HighRiskMerchantConcentrationRule:
    _high_risk_categories = {"digital_goods", "money_transfer", "crypto", "gift_cards"}

    def evaluate(
        self,
        index: ScenarioIndex,
        text_signals: list[TextSignal],
    ) -> RuleEvaluation | None:
        _ = text_signals
        high_risk_transactions = [
            transaction
            for transaction in index.transactions
            if index.merchants[transaction.merchant_id].category in self._high_risk_categories
        ]
        if not high_risk_transactions:
            return None

        return RuleEvaluation(
            rule_hit=RuleHit(
                rule_code="high-risk-merchant-concentration",
                title="High-risk merchant concentration",
                weight=16,
                narrative=(
                    "A large share of the volume flows through merchants associated "
                    "with resale, transfer, or rapid liquidation."
                ),
                evidence=[
                    EntityReference(
                        entity_type=EntityType.MERCHANT,
                        entity_id=transaction.merchant_id,
                        display_name=index.merchants[transaction.merchant_id].display_name,
                    )
                    for transaction in high_risk_transactions[:2]
                ],
            ),
            graph_links=[
                GraphLink(
                    relation="transacts-with",
                    source=EntityReference(
                        entity_type=EntityType.ACCOUNT,
                        entity_id=transaction.account_id,
                        display_name=transaction.account_id,
                    ),
                    target=EntityReference(
                        entity_type=EntityType.MERCHANT,
                        entity_id=transaction.merchant_id,
                        display_name=index.merchants[transaction.merchant_id].display_name,
                    ),
                    explanation=(
                        "The account concentrated spend in a high-risk merchant category."
                    ),
                )
                for transaction in high_risk_transactions
            ],
            suspicious_transactions=high_risk_transactions,
        )


class CrossBorderMismatchRule:
    def evaluate(
        self,
        index: ScenarioIndex,
        text_signals: list[TextSignal],
    ) -> RuleEvaluation | None:
        _ = text_signals
        cross_border_transactions = [
            transaction
            for transaction in index.transactions
            if index.merchants[transaction.merchant_id].country_code
            != index.customers[transaction.customer_id].country_code
        ]
        if not cross_border_transactions:
            return None

        return RuleEvaluation(
            rule_hit=RuleHit(
                rule_code="cross-border-mismatch",
                title="Cross-border mismatch",
                weight=12,
                narrative=(
                    "Merchant geography differs from the customer baseline, "
                    "increasing the likelihood of takeover or coordinated fraud."
                ),
                evidence=[
                    EntityReference(
                        entity_type=EntityType.TRANSACTION,
                        entity_id=transaction.transaction_id,
                        display_name=transaction.transaction_id,
                    )
                    for transaction in cross_border_transactions[:3]
                ],
            ),
            suspicious_transactions=cross_border_transactions,
        )


class HistoricalRiskPressureRule:
    def evaluate(
        self,
        index: ScenarioIndex,
        text_signals: list[TextSignal],
    ) -> RuleEvaluation | None:
        _ = text_signals
        review_accounts = [
            account
            for account in index.accounts.values()
            if account.chargeback_count > 0 or account.manual_review_count > 0
        ]
        if not review_accounts:
            return None

        return RuleEvaluation(
            rule_hit=RuleHit(
                rule_code="historical-risk-pressure",
                title="Historical risk pressure",
                weight=8,
                narrative=(
                    "Accounts already show chargeback or manual-review pressure, "
                    "which raises prior risk."
                ),
                evidence=[
                    EntityReference(
                        entity_type=EntityType.ACCOUNT,
                        entity_id=account.account_id,
                        display_name=account.account_id,
                    )
                    for account in review_accounts
                ],
            )
        )


class TextualFraudContextRule:
    def evaluate(
        self,
        index: ScenarioIndex,
        text_signals: list[TextSignal],
    ) -> RuleEvaluation | None:
        _ = index
        text_signal_weight = min(
            18,
            round(sum(signal.confidence for signal in text_signals) * 4),
        )
        if text_signal_weight <= 0:
            return None

        return RuleEvaluation(
            rule_hit=RuleHit(
                rule_code="textual-fraud-context",
                title="Textual fraud context",
                weight=text_signal_weight,
                narrative=(
                    "Investigator notes and merchant descriptions reinforce the fraud hypothesis."
                ),
                evidence=[],
            )
        )


class VelocityAnomalyRule:
    """Detects abnormal transaction velocity — too many transactions in a short window."""

    def evaluate(
        self,
        index: ScenarioIndex,
        text_signals: list[TextSignal],
    ) -> RuleEvaluation | None:
        _ = text_signals
        grouped: dict[str, list[TransactionRecord]] = defaultdict(list)
        for txn in index.transactions:
            grouped[txn.customer_id].append(txn)

        anomalous_customers: list[str] = []
        for customer_id, txns in grouped.items():
            if len(txns) < 3:
                continue
            ordered = sorted(txns, key=lambda t: t.occurred_at)
            # Sliding window: check if 3+ transactions within 30 minutes
            for i in range(len(ordered) - 2):
                span_minutes = (
                    ordered[i + 2].occurred_at - ordered[i].occurred_at
                ).total_seconds() / 60
                if span_minutes <= 30:
                    anomalous_customers.append(customer_id)
                    break

        if not anomalous_customers:
            return None

        return RuleEvaluation(
            rule_hit=RuleHit(
                rule_code="velocity-anomaly",
                title="Transaction velocity anomaly",
                weight=14,
                narrative=(
                    "Multiple transactions were concentrated in a tight time window, "
                    "which is consistent with automated or scripted cash-out behavior."
                ),
                evidence=[
                    EntityReference(
                        entity_type=EntityType.CUSTOMER,
                        entity_id=cid,
                        display_name=index.customers[cid].full_name,
                    )
                    for cid in anomalous_customers[:3]
                ],
            ),
        )


class RoundAmountDetectionRule:
    """Detects suspicious round-amount transactions — a sign of structuring."""

    def evaluate(
        self,
        index: ScenarioIndex,
        text_signals: list[TextSignal],
    ) -> RuleEvaluation | None:
        _ = text_signals
        round_txns = [
            txn
            for txn in index.transactions
            if txn.amount >= 500 and txn.amount % 100 == 0
        ]
        if len(round_txns) < 2:
            return None

        total_round = sum(t.amount for t in round_txns)
        total_all = sum(t.amount for t in index.transactions)
        ratio = total_round / total_all if total_all > 0 else 0

        if ratio < 0.4:
            return None

        return RuleEvaluation(
            rule_hit=RuleHit(
                rule_code="round-amount-structuring",
                title="Round-amount structuring",
                weight=10,
                narrative=(
                    f"{len(round_txns)} transactions with exact round amounts "
                    f"represent {ratio:.0%} of total volume, suggesting structuring to avoid thresholds."
                ),
                evidence=[
                    EntityReference(
                        entity_type=EntityType.TRANSACTION,
                        entity_id=txn.transaction_id,
                        display_name=f"${txn.amount:,.0f}",
                    )
                    for txn in round_txns[:3]
                ],
            ),
            suspicious_transactions=round_txns,
        )


class DormantAccountActivationRule:
    """Detects accounts that were dormant (low balance) then suddenly activated with high-value transactions."""

    def evaluate(
        self,
        index: ScenarioIndex,
        text_signals: list[TextSignal],
    ) -> RuleEvaluation | None:
        _ = text_signals
        flagged_accounts: list[AccountProfile] = []

        for account in index.accounts.values():
            if account.current_balance < 500 and account.average_monthly_inflow < 1000:
                # Check if this account has high-value transactions
                account_txns = [
                    t for t in index.transactions if t.account_id == account.account_id
                ]
                high_value = [t for t in account_txns if t.amount >= 800]
                if len(high_value) >= 2:
                    flagged_accounts.append(account)

        if not flagged_accounts:
            return None

        return RuleEvaluation(
            rule_hit=RuleHit(
                rule_code="dormant-account-activation",
                title="Dormant account activation",
                weight=12,
                narrative=(
                    "Previously low-activity accounts are now processing high-value "
                    "transactions, a pattern common in account takeover and money mule schemes."
                ),
                evidence=[
                    EntityReference(
                        entity_type=EntityType.ACCOUNT,
                        entity_id=account.account_id,
                        display_name=account.account_id,
                    )
                    for account in flagged_accounts
                ],
            ),
        )


class AccountTakeoverInvestigatorContextRule:
    def evaluate(
        self,
        index: ScenarioIndex,
        text_signals: list[TextSignal],
    ) -> RuleEvaluation | None:
        if ScenarioTag.ACCOUNT_TAKEOVER not in index.scenario_tags:
            return None
        if not text_signals or not index.investigator_notes:
            return None

        note = index.investigator_notes[0]
        customer = next(iter(index.customers.values()))
        return RuleEvaluation(
            graph_links=[
                GraphLink(
                    relation="investigator-context",
                    source=EntityReference(
                        entity_type=EntityType.NOTE,
                        entity_id=note.note_id,
                        display_name="Investigator note",
                    ),
                    target=_customer_ref(customer),
                    explanation=(
                        "The note indicates possible credential compromise and SIM swap activity."
                    ),
                )
            ]
        )


class LocalRiskReasoner:
    def __init__(self, rules: list[RiskRule] | None = None) -> None:
        self._rules = rules or [
            SharedDeviceClusterRule(),
            RapidSpendBurstRule(),
            HighRiskMerchantConcentrationRule(),
            CrossBorderMismatchRule(),
            HistoricalRiskPressureRule(),
            TextualFraudContextRule(),
            VelocityAnomalyRule(),
            RoundAmountDetectionRule(),
            DormantAccountActivationRule(),
            AccountTakeoverInvestigatorContextRule(),
        ]

    def reason(self, command: ReasonAboutRiskCommand) -> ReasonAboutRiskResult:
        index = ScenarioIndex.from_command(command)
        evaluations = [
            evaluation
            for rule in self._rules
            if (evaluation := rule.evaluate(index, command.text_signals)) is not None
        ]

        suspicious_transactions: dict[str, TransactionRecord] = {}
        graph_links: list[GraphLink] = []
        rule_hits: list[RuleHit] = []
        for evaluation in evaluations:
            if evaluation.rule_hit is not None:
                rule_hits.append(evaluation.rule_hit)
            for graph_link in evaluation.graph_links:
                graph_links.append(graph_link)
            for transaction in evaluation.suspicious_transactions:
                suspicious_transactions[transaction.transaction_id] = transaction

        total_risk_score = min(100, sum(rule.weight for rule in rule_hits))
        risk_level = _score_to_level(total_risk_score)
        suspicious_volume = round(
            sum(transaction.amount for transaction in suspicious_transactions.values()),
            2,
        )
        total_volume = round(sum(transaction.amount for transaction in index.transactions), 2)
        top_titles = (
            ", ".join(rule.title.lower() for rule in rule_hits[:2]) or "limited rule coverage"
        )
        summary = (
            f"{index.scenario_title} is scored {risk_level.value} at {total_risk_score}/100 "
            f"because of {top_titles}."
        )

        shared_device_count = sum(
            1 for device in index.devices.values() if len(device.linked_customer_ids) > 1
        )
        return ReasonAboutRiskResult(
            requested_provider="local-rule-engine",
            active_provider="local-rule-engine",
            provider_notes=["Local graph rule engine executed deterministic fraud heuristics."],
            risk_level=risk_level,
            total_risk_score=total_risk_score,
            summary=summary,
            metrics=InvestigationMetrics(
                total_transaction_volume=total_volume,
                suspicious_transaction_volume=suspicious_volume,
                suspicious_transaction_count=len(suspicious_transactions),
                shared_device_count=shared_device_count,
                linked_customer_count=len(index.customers),
            ),
            top_rule_hits=sorted(rule_hits, key=lambda item: item.weight, reverse=True),
            graph_links=graph_links[:8],
            suspicious_transactions=sorted(
                suspicious_transactions.values(),
                key=lambda transaction: transaction.occurred_at,
            ),
            recommended_actions=_build_recommendations(risk_level, command.text_signals),
        )


def _customer_ref(customer: CustomerProfile) -> EntityReference:
    return EntityReference(
        entity_type=EntityType.CUSTOMER,
        entity_id=customer.customer_id,
        display_name=customer.full_name,
    )


def _find_rapid_sequences(transactions: list[TransactionRecord]) -> list[TransactionRecord]:
    grouped_transactions: dict[str, list[TransactionRecord]] = defaultdict(list)
    for transaction in transactions:
        grouped_transactions[transaction.account_id].append(transaction)

    suspicious: list[TransactionRecord] = []
    for account_transactions in grouped_transactions.values():
        ordered = sorted(account_transactions, key=lambda item: item.occurred_at)
        for current_transaction, next_transaction in zip(
            ordered,
            ordered[1:],
            strict=False,
        ):
            minutes_between = (
                next_transaction.occurred_at - current_transaction.occurred_at
            ).total_seconds() / 60
            if (
                minutes_between <= 10
                and current_transaction.amount >= 900
                and next_transaction.amount >= 900
            ):
                suspicious.extend([current_transaction, next_transaction])

    unique_transactions = {transaction.transaction_id: transaction for transaction in suspicious}
    return list(unique_transactions.values())


def _score_to_level(total_risk_score: int) -> RiskLevel:
    if total_risk_score >= 80:
        return RiskLevel.CRITICAL
    if total_risk_score >= 60:
        return RiskLevel.HIGH
    if total_risk_score >= 35:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _build_recommendations(
    risk_level: RiskLevel,
    text_signals: list[TextSignal],
) -> list[str]:
    recommendations = [
        "Freeze outbound spend on linked accounts until enhanced verification succeeds.",
        "Route the device cluster and associated entities into analyst review.",
    ]
    if any(
        signal.label in {"credential compromise", "sim swap", "account takeover"}
        for signal in text_signals
    ):
        recommendations.append(
            "Force credential reset and reset MFA enrollment for the impacted customer."
        )
    if risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
        recommendations.append(
            "Create a case in the fraud queue with merchant and device evidence attached."
        )
    return recommendations
