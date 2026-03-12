"""Round-amount detection on uploaded transaction data.

Identifies suspicious patterns where a high proportion of transactions
use exact round amounts — a common structuring indicator.
"""
from __future__ import annotations

from relational_fraud_intelligence.domain.models import (
    AnomalyFlag,
    AnomalyType,
    RiskLevel,
    UploadedTransaction,
)


def detect_round_amounts(
    transactions: list[UploadedTransaction],
    *,
    round_threshold: float = 100.0,
    min_amount: float = 200.0,
    suspicious_ratio: float = 0.35,
) -> list[AnomalyFlag]:
    """Flag accounts with suspicious concentration of round-amount transactions."""
    if len(transactions) < 5:
        return []

    by_account: dict[str, list[UploadedTransaction]] = {}
    for txn in transactions:
        by_account.setdefault(txn.account_id, []).append(txn)

    anomalies: list[AnomalyFlag] = []

    for account_id, account_txns in by_account.items():
        qualifying = [t for t in account_txns if t.amount >= min_amount]
        if len(qualifying) < 3:
            continue

        round_txns = [t for t in qualifying if t.amount % round_threshold == 0]
        ratio = len(round_txns) / len(qualifying)

        if ratio >= suspicious_ratio:
            total_round = sum(t.amount for t in round_txns)
            severity = RiskLevel.HIGH if ratio >= 0.6 else RiskLevel.MEDIUM

            anomalies.append(
                AnomalyFlag(
                    anomaly_id=f"round::{account_id}",
                    anomaly_type=AnomalyType.ROUND_AMOUNT,
                    severity=severity,
                    title=f"Round-amount structuring: {ratio:.0%} of transactions",
                    description=(
                        f"Account {account_id} has {len(round_txns)} of "
                        f"{len(qualifying)} qualifying transactions ({ratio:.0%}) "
                        f"with exact round amounts totaling ${total_round:,.2f}. "
                        f"This pattern is consistent with structured deposits or cash-out activity."
                    ),
                    affected_entity_id=account_id,
                    affected_entity_type="account",
                    score=round(min(1.0, ratio * 1.3), 3),
                    evidence={
                        "round_count": len(round_txns),
                        "total_count": len(qualifying),
                        "ratio": round(ratio, 3),
                        "total_round_amount": round(total_round, 2),
                    },
                )
            )

    return anomalies

