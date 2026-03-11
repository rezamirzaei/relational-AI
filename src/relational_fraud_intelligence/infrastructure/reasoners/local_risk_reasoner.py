from __future__ import annotations

from collections import defaultdict
from itertools import combinations

from relational_fraud_intelligence.application.dto.investigation import (
    ReasonAboutRiskCommand,
    ReasonAboutRiskResult,
)
from relational_fraud_intelligence.domain.models import (
    EntityReference,
    EntityType,
    GraphLink,
    InvestigationMetrics,
    RiskLevel,
    RuleHit,
    ScenarioTag,
    TransactionRecord,
)


class LocalRiskReasoner:
    _high_risk_categories = {"digital_goods", "money_transfer", "crypto", "gift_cards"}

    def reason(self, command: ReasonAboutRiskCommand) -> ReasonAboutRiskResult:
        customers = {customer.customer_id: customer for customer in command.scenario.customers}
        accounts = {account.account_id: account for account in command.scenario.accounts}
        merchants = {merchant.merchant_id: merchant for merchant in command.scenario.merchants}
        devices = {device.device_id: device for device in command.scenario.devices}

        suspicious_transactions: dict[str, TransactionRecord] = {}
        graph_links: list[GraphLink] = []
        rule_hits: list[RuleHit] = []

        shared_devices = [device for device in devices.values() if len(device.linked_customer_ids) > 1]
        if shared_devices:
            evidence = []
            for device in shared_devices:
                for customer_id in device.linked_customer_ids:
                    customer = customers[customer_id]
                    evidence.append(
                        EntityReference(
                            entity_type=EntityType.CUSTOMER,
                            entity_id=customer.customer_id,
                            display_name=customer.full_name,
                        )
                    )
                for left_customer_id, right_customer_id in combinations(device.linked_customer_ids, 2):
                    left_customer = customers[left_customer_id]
                    right_customer = customers[right_customer_id]
                    graph_links.append(
                        GraphLink(
                            relation="shares-device",
                            source=EntityReference(
                                entity_type=EntityType.CUSTOMER,
                                entity_id=left_customer.customer_id,
                                display_name=left_customer.full_name,
                            ),
                            target=EntityReference(
                                entity_type=EntityType.CUSTOMER,
                                entity_id=right_customer.customer_id,
                                display_name=right_customer.full_name,
                            ),
                            explanation=f"Both customers authenticated from device {device.device_id}.",
                        )
                    )
            rule_hits.append(
                RuleHit(
                    rule_code="shared-device-cluster",
                    title="Shared device cluster",
                    weight=28,
                    narrative="Multiple customers are linked to the same low-trust device, suggesting an identity ring or coordinated takeover.",
                    evidence=evidence,
                )
            )

        rapid_sequences = self._find_rapid_sequences(command.scenario.transactions)
        if rapid_sequences:
            for transaction in rapid_sequences:
                suspicious_transactions[transaction.transaction_id] = transaction
            rule_hits.append(
                RuleHit(
                    rule_code="rapid-spend-burst",
                    title="Rapid spend burst",
                    weight=18,
                    narrative="High-value transactions arrived within a short window, which is consistent with cash-out behavior.",
                    evidence=[
                        EntityReference(
                            entity_type=EntityType.ACCOUNT,
                            entity_id=transaction.account_id,
                            display_name=transaction.account_id,
                        )
                        for transaction in rapid_sequences[:2]
                    ],
                )
            )

        high_risk_transactions = [
            transaction
            for transaction in command.scenario.transactions
            if merchants[transaction.merchant_id].category in self._high_risk_categories
        ]
        if high_risk_transactions:
            for transaction in high_risk_transactions:
                suspicious_transactions[transaction.transaction_id] = transaction
                graph_links.append(
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
                            display_name=merchants[transaction.merchant_id].display_name,
                        ),
                        explanation="The account concentrated spend in a high-risk merchant category.",
                    )
                )
            rule_hits.append(
                RuleHit(
                    rule_code="high-risk-merchant-concentration",
                    title="High-risk merchant concentration",
                    weight=16,
                    narrative="A large share of the volume flows through merchants associated with resale, transfer, or rapid liquidation.",
                    evidence=[
                        EntityReference(
                            entity_type=EntityType.MERCHANT,
                            entity_id=transaction.merchant_id,
                            display_name=merchants[transaction.merchant_id].display_name,
                        )
                        for transaction in high_risk_transactions[:2]
                    ],
                )
            )

        cross_border_transactions = [
            transaction
            for transaction in command.scenario.transactions
            if merchants[transaction.merchant_id].country_code != customers[transaction.customer_id].country_code
        ]
        if cross_border_transactions:
            for transaction in cross_border_transactions:
                suspicious_transactions[transaction.transaction_id] = transaction
            rule_hits.append(
                RuleHit(
                    rule_code="cross-border-mismatch",
                    title="Cross-border mismatch",
                    weight=12,
                    narrative="Merchant geography differs from the customer baseline, increasing the likelihood of takeover or coordinated fraud.",
                    evidence=[
                        EntityReference(
                            entity_type=EntityType.TRANSACTION,
                            entity_id=transaction.transaction_id,
                            display_name=transaction.transaction_id,
                        )
                        for transaction in cross_border_transactions[:3]
                    ],
                )
            )

        review_accounts = [
            account
            for account in accounts.values()
            if account.chargeback_count > 0 or account.manual_review_count > 0
        ]
        if review_accounts:
            rule_hits.append(
                RuleHit(
                    rule_code="historical-risk-pressure",
                    title="Historical risk pressure",
                    weight=8,
                    narrative="Accounts already show chargeback or manual-review pressure, which raises prior risk.",
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

        text_signal_weight = min(18, round(sum(signal.confidence for signal in command.text_signals) * 4))
        if text_signal_weight:
            rule_hits.append(
                RuleHit(
                    rule_code="textual-fraud-context",
                    title="Textual fraud context",
                    weight=text_signal_weight,
                    narrative="Investigator notes and merchant descriptions reinforce the fraud hypothesis.",
                    evidence=[],
                )
            )

        if ScenarioTag.ACCOUNT_TAKEOVER in command.scenario.tags and command.text_signals:
            graph_links.append(
                GraphLink(
                    relation="investigator-context",
                    source=EntityReference(
                        entity_type=EntityType.NOTE,
                        entity_id=command.scenario.investigator_notes[0].note_id,
                        display_name="Investigator note",
                    ),
                    target=EntityReference(
                        entity_type=EntityType.CUSTOMER,
                        entity_id=command.scenario.customers[0].customer_id,
                        display_name=command.scenario.customers[0].full_name,
                    ),
                    explanation="The note indicates possible credential compromise and SIM swap activity.",
                )
            )

        total_risk_score = min(100, sum(rule.weight for rule in rule_hits))
        risk_level = self._score_to_level(total_risk_score)
        suspicious_volume = round(sum(transaction.amount for transaction in suspicious_transactions.values()), 2)
        total_volume = round(sum(transaction.amount for transaction in command.scenario.transactions), 2)

        top_titles = ", ".join(rule.title.lower() for rule in rule_hits[:2]) or "limited rule coverage"
        summary = (
            f"{command.scenario.title} is scored {risk_level.value} at {total_risk_score}/100 because of "
            f"{top_titles}."
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
                shared_device_count=len(shared_devices),
                linked_customer_count=len(command.scenario.customers),
            ),
            top_rule_hits=sorted(rule_hits, key=lambda item: item.weight, reverse=True),
            graph_links=graph_links[:8],
            suspicious_transactions=sorted(
                suspicious_transactions.values(),
                key=lambda transaction: transaction.occurred_at,
            ),
            recommended_actions=self._build_recommendations(risk_level, command.text_signals),
        )

    def _find_rapid_sequences(self, transactions: list[TransactionRecord]) -> list[TransactionRecord]:
        grouped_transactions: dict[str, list[TransactionRecord]] = defaultdict(list)
        for transaction in transactions:
            grouped_transactions[transaction.account_id].append(transaction)

        suspicious: list[TransactionRecord] = []
        for account_transactions in grouped_transactions.values():
            ordered = sorted(account_transactions, key=lambda item: item.occurred_at)
            for current_transaction, next_transaction in zip(ordered, ordered[1:]):
                minutes_between = (next_transaction.occurred_at - current_transaction.occurred_at).total_seconds() / 60
                if minutes_between <= 10 and current_transaction.amount >= 900 and next_transaction.amount >= 900:
                    suspicious.extend([current_transaction, next_transaction])
        unique_transactions = {transaction.transaction_id: transaction for transaction in suspicious}
        return list(unique_transactions.values())

    @staticmethod
    def _score_to_level(total_risk_score: int) -> RiskLevel:
        if total_risk_score >= 80:
            return RiskLevel.CRITICAL
        if total_risk_score >= 60:
            return RiskLevel.HIGH
        if total_risk_score >= 35:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    @staticmethod
    def _build_recommendations(risk_level: RiskLevel, text_signals: list) -> list[str]:
        recommendations = [
            "Freeze outbound spend on linked accounts until enhanced verification succeeds.",
            "Route the device cluster and associated entities into analyst review.",
        ]
        if any(signal.label in {"credential compromise", "sim swap", "account takeover"} for signal in text_signals):
            recommendations.append("Force credential reset and reset MFA enrollment for the impacted customer.")
        if risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
            recommendations.append("Create a case in the fraud queue with merchant and device evidence attached.")
        return recommendations
