"""Transaction velocity analysis — detect sudden spikes in activity.

Monitors transaction frequency and volume per entity across time windows,
flags accounts or merchants whose activity suddenly exceeds baseline norms.
"""

from __future__ import annotations

import math
from datetime import timedelta

from relational_fraud_intelligence.domain.models import (
    AnomalyFlag,
    AnomalyType,
    RiskLevel,
    UploadedTransaction,
    VelocitySpike,
)


def detect_velocity_spikes(
    transactions: list[UploadedTransaction],
    *,
    window_hours: int = 24,
    z_threshold: float = 2.5,
) -> tuple[list[VelocitySpike], list[AnomalyFlag]]:
    """Detect velocity spikes for accounts using sliding windows.

    Returns:
        (velocity_spikes, anomaly_flags)
    """
    if len(transactions) < 10:
        return [], []

    window = timedelta(hours=window_hours)
    sorted_txns = sorted(transactions, key=lambda t: t.timestamp)

    # Group by account
    by_account: dict[str, list[UploadedTransaction]] = {}
    for txn in sorted_txns:
        by_account.setdefault(txn.account_id, []).append(txn)

    spikes: list[VelocitySpike] = []
    anomalies: list[AnomalyFlag] = []

    for account_id, account_txns in by_account.items():
        if len(account_txns) < 3:
            continue

        # Build daily windows
        windows: list[tuple[int, float]] = []  # (count, total_amount) per window
        start = account_txns[0].timestamp
        end = account_txns[-1].timestamp
        current = start

        while current <= end:
            window_end = current + window
            window_txns = [t for t in account_txns if current <= t.timestamp < window_end]
            if window_txns:
                windows.append((len(window_txns), sum(t.amount for t in window_txns)))
            else:
                windows.append((0, 0.0))
            current = window_end

        if len(windows) < 2:
            continue

        # Compute baseline statistics
        counts = [w[0] for w in windows]
        mean_count = sum(counts) / len(counts)
        if len(counts) > 1:
            var = sum((c - mean_count) ** 2 for c in counts) / (len(counts) - 1)
            std_count = math.sqrt(var)
        else:
            std_count = 0.0

        # Detect spikes
        current = start
        for i, (count, total) in enumerate(windows):
            if std_count > 0:
                z = (count - mean_count) / std_count
            else:
                z = 0.0 if count <= mean_count else 3.0

            if z >= z_threshold and count >= 3:
                spike = VelocitySpike(
                    entity_id=account_id,
                    entity_type="account",
                    window_start=current,
                    window_end=current + window,
                    transaction_count=count,
                    total_amount=round(total, 2),
                    baseline_avg_count=round(mean_count, 2),
                    z_score=round(z, 2),
                )
                spikes.append(spike)

                severity = (
                    RiskLevel.CRITICAL if z >= 4 else RiskLevel.HIGH if z >= 3 else RiskLevel.MEDIUM
                )
                anomalies.append(
                    AnomalyFlag(
                        anomaly_id=f"velocity::{account_id}::{i}",
                        anomaly_type=AnomalyType.VELOCITY_SPIKE,
                        severity=severity,
                        title=f"Velocity spike: {count} txns in {window_hours}h",
                        description=(
                            f"Account {account_id} had {count} transactions "
                            f"totaling ${total:,.2f} in a {window_hours}-hour window, "
                            f"which is {z:.1f}σ above the baseline average of "
                            f"{mean_count:.1f} transactions per window."
                        ),
                        affected_entity_id=account_id,
                        affected_entity_type="account",
                        score=round(min(1.0, z / 5.0), 3),
                        evidence={
                            "window_start": current.isoformat(),
                            "transaction_count": count,
                            "total_amount": round(total, 2),
                            "baseline_avg": round(mean_count, 2),
                            "z_score": round(z, 2),
                        },
                    )
                )

            current = current + window

    return spikes, anomalies
