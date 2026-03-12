"""Statistical outlier detection using Z-score and IQR methods.

Identifies transactions with amounts significantly deviating from the norm
for their account or merchant — a common fraud indicator.
"""
from __future__ import annotations

import math

from relational_fraud_intelligence.domain.models import (
    AnomalyFlag,
    AnomalyType,
    RiskLevel,
    UploadedTransaction,
)


def detect_outliers(
    transactions: list[UploadedTransaction],
    *,
    z_threshold: float = 3.0,
    iqr_multiplier: float = 1.5,
) -> list[AnomalyFlag]:
    """Detect statistical outliers by account using both Z-score and IQR."""
    if len(transactions) < 5:
        return []

    # Group by account
    by_account: dict[str, list[UploadedTransaction]] = {}
    for txn in transactions:
        by_account.setdefault(txn.account_id, []).append(txn)

    anomalies: list[AnomalyFlag] = []
    seen_txns: set[str] = set()

    # Global statistics for fallback
    all_amounts = [t.amount for t in transactions]
    global_mean, global_std = _mean_std(all_amounts)
    global_q1, global_q3 = _quartiles(all_amounts)
    global_iqr = global_q3 - global_q1

    for account_id, account_txns in by_account.items():
        amounts = [t.amount for t in account_txns]

        if len(amounts) >= 5:
            mean, std = _mean_std(amounts)
            q1, q3 = _quartiles(amounts)
            iqr = q3 - q1
        else:
            # Use global stats for accounts with few transactions
            mean, std = global_mean, global_std
            q1, q3, iqr = global_q1, global_q3, global_iqr

        for txn in account_txns:
            if txn.transaction_id in seen_txns:
                continue

            z_score = abs(txn.amount - mean) / std if std > 0 else 0.0
            is_z_outlier = z_score > z_threshold

            lower_fence = q1 - iqr_multiplier * iqr
            upper_fence = q3 + iqr_multiplier * iqr
            is_iqr_outlier = txn.amount < lower_fence or txn.amount > upper_fence

            if is_z_outlier or is_iqr_outlier:
                seen_txns.add(txn.transaction_id)
                severity = _severity_from_z(z_score)
                confidence = min(1.0, z_score / 6.0) if z_score > 0 else 0.5

                anomalies.append(
                    AnomalyFlag(
                        anomaly_id=f"outlier::{txn.transaction_id}",
                        anomaly_type=AnomalyType.STATISTICAL_OUTLIER,
                        severity=severity,
                        title=f"Statistical outlier: ${txn.amount:,.2f}",
                        description=(
                            f"Transaction {txn.transaction_id} for account {account_id} "
                            f"has amount ${txn.amount:,.2f} which is {z_score:.1f}σ from "
                            f"the mean (${mean:,.2f}). "
                            f"{'Z-score and IQR both flag this.' if is_z_outlier and is_iqr_outlier else 'Flagged by ' + ('Z-score' if is_z_outlier else 'IQR') + ' method.'}"
                        ),
                        affected_entity_id=txn.transaction_id,
                        affected_entity_type="transaction",
                        score=round(confidence, 3),
                        evidence={
                            "amount": txn.amount,
                            "account_id": account_id,
                            "z_score": round(z_score, 2),
                            "account_mean": round(mean, 2),
                            "account_std": round(std, 2),
                            "method": "z-score+iqr" if is_z_outlier and is_iqr_outlier else "z-score" if is_z_outlier else "iqr",
                        },
                    )
                )

    return anomalies


def _mean_std(values: list[float]) -> tuple[float, float]:
    n = len(values)
    if n == 0:
        return 0.0, 0.0
    mean = sum(values) / n
    if n < 2:
        return mean, 0.0
    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    return mean, math.sqrt(variance)


def _quartiles(values: list[float]) -> tuple[float, float]:
    s = sorted(values)
    n = len(s)
    if n == 0:
        return 0.0, 0.0
    q1_idx = n // 4
    q3_idx = (3 * n) // 4
    return s[q1_idx], s[min(q3_idx, n - 1)]


def _severity_from_z(z: float) -> RiskLevel:
    if z >= 5.0:
        return RiskLevel.CRITICAL
    if z >= 4.0:
        return RiskLevel.HIGH
    if z >= 3.0:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW

