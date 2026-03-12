"""Tests for individual fraud detection rules."""
from __future__ import annotations

from datetime import datetime

from relational_fraud_intelligence.domain.models import (
    AccountProfile,
    CustomerProfile,
    DeviceProfile,
    MerchantProfile,
    ScenarioTag,
    TransactionChannel,
    TransactionRecord,
    TransactionStatus,
)
from relational_fraud_intelligence.infrastructure.reasoners.local_risk_reasoner import (
    DormantAccountActivationRule,
    RoundAmountDetectionRule,
    ScenarioIndex,
    VelocityAnomalyRule,
)


def _build_index(
    transactions: list[TransactionRecord] | None = None,
    accounts: dict[str, AccountProfile] | None = None,
    customers: dict[str, CustomerProfile] | None = None,
) -> ScenarioIndex:
    default_customer = CustomerProfile(
        customer_id="cust_1", full_name="Alice", country_code="US",
        segment="consumer", declared_income_band="$50k-$70k",
        linked_account_ids=["acct_1"], linked_device_ids=["dev_1"],
    )
    default_account = AccountProfile(
        account_id="acct_1", customer_id="cust_1",
        opened_at=datetime(2026, 1, 1), current_balance=1000.0,
        average_monthly_inflow=2000.0, chargeback_count=0, manual_review_count=0,
    )

    return ScenarioIndex(
        scenario_id="test",
        scenario_title="Test",
        scenario_tags=[ScenarioTag.FRAUD],
        customers=customers or {"cust_1": default_customer},
        accounts=accounts or {"acct_1": default_account},
        devices={"dev_1": DeviceProfile(
            device_id="dev_1", fingerprint="fp-1", ip_country_code="US",
            linked_customer_ids=["cust_1"], trust_score=0.5,
        )},
        merchants={"merch_1": MerchantProfile(
            merchant_id="merch_1", display_name="Merchant", country_code="US",
            category="retail", description="Test",
        )},
        transactions=transactions or [],
        investigator_notes=[],
    )


def _txn(txn_id: str, amount: float, minutes_offset: int = 0) -> TransactionRecord:
    return TransactionRecord(
        transaction_id=txn_id, customer_id="cust_1", account_id="acct_1",
        device_id="dev_1", merchant_id="merch_1",
        occurred_at=datetime(2026, 3, 1, 10, minutes_offset),
        amount=amount, currency="USD",
        channel=TransactionChannel.CARD_NOT_PRESENT,
        status=TransactionStatus.APPROVED,
    )


class TestVelocityAnomalyRule:
    def test_fires_when_three_transactions_within_30_minutes(self) -> None:
        txns = [_txn("t1", 500, 0), _txn("t2", 600, 10), _txn("t3", 700, 20)]
        index = _build_index(transactions=txns)

        result = VelocityAnomalyRule().evaluate(index, [])

        assert result is not None
        assert result.rule_hit is not None
        assert result.rule_hit.rule_code == "velocity-anomaly"

    def test_does_not_fire_when_transactions_are_spread_out(self) -> None:
        txns = [_txn("t1", 500, 0)]
        index = _build_index(transactions=txns)

        result = VelocityAnomalyRule().evaluate(index, [])

        assert result is None


class TestRoundAmountDetectionRule:
    def test_fires_when_high_ratio_of_round_amounts(self) -> None:
        txns = [
            _txn("t1", 1000, 0),
            _txn("t2", 500, 5),
            _txn("t3", 1000, 10),
        ]
        index = _build_index(transactions=txns)

        result = RoundAmountDetectionRule().evaluate(index, [])

        assert result is not None
        assert result.rule_hit is not None
        assert result.rule_hit.rule_code == "round-amount-structuring"

    def test_does_not_fire_with_non_round_amounts(self) -> None:
        txns = [_txn("t1", 123.45, 0), _txn("t2", 678.90, 5)]
        index = _build_index(transactions=txns)

        result = RoundAmountDetectionRule().evaluate(index, [])

        assert result is None


class TestDormantAccountActivationRule:
    def test_fires_for_low_balance_account_with_high_value_transactions(self) -> None:
        account = AccountProfile(
            account_id="acct_1", customer_id="cust_1",
            opened_at=datetime(2026, 1, 1), current_balance=200.0,
            average_monthly_inflow=500.0, chargeback_count=0, manual_review_count=0,
        )
        txns = [_txn("t1", 900, 0), _txn("t2", 850, 10)]
        index = _build_index(transactions=txns, accounts={"acct_1": account})

        result = DormantAccountActivationRule().evaluate(index, [])

        assert result is not None
        assert result.rule_hit is not None
        assert result.rule_hit.rule_code == "dormant-account-activation"

    def test_does_not_fire_for_active_account(self) -> None:
        account = AccountProfile(
            account_id="acct_1", customer_id="cust_1",
            opened_at=datetime(2026, 1, 1), current_balance=5000.0,
            average_monthly_inflow=3000.0, chargeback_count=0, manual_review_count=0,
        )
        txns = [_txn("t1", 900, 0), _txn("t2", 850, 10)]
        index = _build_index(transactions=txns, accounts={"acct_1": account})

        result = DormantAccountActivationRule().evaluate(index, [])

        assert result is None


