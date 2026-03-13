"""Dataset and analysis orchestration service.

Handles CSV upload, transaction parsing, and coordinates all analysis
engines (Benford, outliers, velocity, round-amounts) to produce a
unified AnalysisResult with actionable anomaly flags.
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from relational_fraud_intelligence.domain.models import (
    AnalysisResult,
    AnomalyFlag,
    AnomalyType,
    Dataset,
    DatasetStatus,
    RiskLevel,
    UploadedTransaction,
)
from relational_fraud_intelligence.infrastructure.analysis.benford import analyze_benford
from relational_fraud_intelligence.infrastructure.analysis.outliers import detect_outliers
from relational_fraud_intelligence.infrastructure.analysis.round_amounts import detect_round_amounts
from relational_fraud_intelligence.infrastructure.analysis.velocity import detect_velocity_spikes

if TYPE_CHECKING:
    from relational_fraud_intelligence.application.ports.repositories import DatasetStore


class InMemoryDatasetStore:
    """In-memory implementation of DatasetStore for testing and local use."""

    def __init__(self) -> None:
        self._datasets: dict[str, Dataset] = {}
        self._transactions: dict[str, list[UploadedTransaction]] = {}
        self._results: dict[str, AnalysisResult] = {}

    def save_dataset(self, dataset: Dataset) -> None:
        self._datasets[dataset.dataset_id] = dataset

    def get_dataset(self, dataset_id: str) -> Dataset | None:
        return self._datasets.get(dataset_id)

    def list_datasets(self) -> list[Dataset]:
        return sorted(self._datasets.values(), key=lambda d: d.uploaded_at, reverse=True)

    def save_transactions(self, dataset_id: str, txns: list[UploadedTransaction]) -> None:
        self._transactions[dataset_id] = txns

    def get_transactions(self, dataset_id: str) -> list[UploadedTransaction]:
        return self._transactions.get(dataset_id, [])

    def save_result(self, result: AnalysisResult) -> None:
        self._results[result.dataset_id] = result

    def get_result(self, dataset_id: str) -> AnalysisResult | None:
        return self._results.get(dataset_id)

    def list_results(self) -> list[AnalysisResult]:
        return sorted(self._results.values(), key=lambda result: result.completed_at, reverse=True)

    def total_transactions(self) -> int:
        return sum(len(txns) for txns in self._transactions.values())

    def total_anomalies(self) -> int:
        return sum(r.total_anomalies for r in self._results.values())


# Backwards compatibility alias
DatasetStore = InMemoryDatasetStore


# Required and optional CSV column names
REQUIRED_COLUMNS = {"transaction_id", "account_id", "amount", "timestamp"}
OPTIONAL_COLUMNS = {
    "merchant",
    "category",
    "device_fingerprint",
    "ip_country",
    "channel",
    "is_fraud",
}


def _parse_timestamp(value: str) -> datetime:
    """Try common timestamp formats."""
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y",
    ):
        try:
            return datetime.strptime(value.strip(), fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse timestamp: '{value}'")


class DatasetService:
    def __init__(self, store: DatasetStore) -> None:
        self._store = store

    def upload_csv(self, filename: str, content: str | bytes) -> Dataset:
        """Parse a CSV file and store as a new dataset."""
        if isinstance(content, bytes):
            content = content.decode("utf-8-sig")

        reader = csv.DictReader(io.StringIO(content))
        if reader.fieldnames is None:
            raise ValueError("CSV file has no headers.")

        headers = {h.strip().lower().replace(" ", "_") for h in reader.fieldnames}
        missing = REQUIRED_COLUMNS - headers
        if missing:
            raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")

        # Normalize header mapping
        header_map: dict[str, str] = {}
        for h in reader.fieldnames:
            header_map[h] = h.strip().lower().replace(" ", "_")

        transactions: list[UploadedTransaction] = []
        errors: list[str] = []

        for i, row in enumerate(reader):
            normalized = {header_map[k]: v.strip() for k, v in row.items() if k in header_map}
            try:
                amount = float(normalized["amount"])
                if amount <= 0:
                    errors.append(f"Row {i + 2}: amount must be positive, got {amount}")
                    continue

                is_fraud: bool | None = None
                if "is_fraud" in normalized and normalized["is_fraud"]:
                    is_fraud = normalized["is_fraud"].lower() in ("1", "true", "yes")

                txn = UploadedTransaction(
                    row_index=i,
                    transaction_id=normalized.get("transaction_id", f"txn-{i}"),
                    account_id=normalized["account_id"],
                    amount=amount,
                    timestamp=_parse_timestamp(normalized["timestamp"]),
                    merchant=normalized.get("merchant", ""),
                    category=normalized.get("category", ""),
                    device_fingerprint=normalized.get("device_fingerprint", ""),
                    ip_country=normalized.get("ip_country", ""),
                    channel=normalized.get("channel", ""),
                    is_fraud_label=is_fraud,
                )
                transactions.append(txn)
            except (ValueError, KeyError) as exc:
                errors.append(f"Row {i + 2}: {exc}")
                if len(errors) > 50:
                    break

        if not transactions:
            raise ValueError(f"No valid transactions found. Errors: {'; '.join(errors[:5])}")

        dataset = Dataset(
            dataset_id=str(uuid4()),
            name=filename,
            uploaded_at=datetime.now(UTC),
            row_count=len(transactions),
            status=DatasetStatus.UPLOADED,
        )
        self._store.save_dataset(dataset)
        self._store.save_transactions(dataset.dataset_id, transactions)
        return dataset

    def ingest_transactions(self, name: str, transactions: list[dict[str, object]]) -> Dataset:
        """Ingest transactions via API (JSON array)."""
        parsed: list[UploadedTransaction] = []
        for i, raw in enumerate(transactions):
            amount = float(str(raw.get("amount", 0)))
            if amount <= 0:
                continue
            ts_raw = str(raw.get("timestamp", ""))
            try:
                ts = _parse_timestamp(ts_raw)
            except ValueError:
                ts = datetime.now(UTC)

            is_fraud: bool | None = None
            if "is_fraud" in raw:
                is_fraud = str(raw["is_fraud"]).lower() in ("1", "true", "yes")

            parsed.append(
                UploadedTransaction(
                    row_index=i,
                    transaction_id=str(raw.get("transaction_id", f"txn-{i}")),
                    account_id=str(raw.get("account_id", "unknown")),
                    amount=amount,
                    timestamp=ts,
                    merchant=str(raw.get("merchant", "")),
                    category=str(raw.get("category", "")),
                    device_fingerprint=str(raw.get("device_fingerprint", "")),
                    ip_country=str(raw.get("ip_country", "")),
                    channel=str(raw.get("channel", "")),
                    is_fraud_label=is_fraud,
                )
            )

        if not parsed:
            raise ValueError("No valid transactions in payload.")

        dataset = Dataset(
            dataset_id=str(uuid4()),
            name=name,
            uploaded_at=datetime.now(UTC),
            row_count=len(parsed),
            status=DatasetStatus.UPLOADED,
        )
        self._store.save_dataset(dataset)
        self._store.save_transactions(dataset.dataset_id, parsed)
        return dataset

    def analyze(self, dataset_id: str) -> AnalysisResult:
        """Run all analysis engines on a dataset."""
        dataset = self._store.get_dataset(dataset_id)
        if dataset is None:
            raise LookupError(f"Dataset '{dataset_id}' not found.")

        transactions = self._store.get_transactions(dataset_id)
        if not transactions:
            raise ValueError(f"Dataset '{dataset_id}' has no transactions.")

        # Update status
        dataset.status = DatasetStatus.ANALYZING
        self._store.save_dataset(dataset)

        all_anomalies: list[AnomalyFlag] = []

        try:
            # 1. Benford's Law
            benford_digits, chi_sq, p_value = analyze_benford(transactions)
            benford_suspicious = p_value < 0.05 and len(transactions) >= 50
            if benford_suspicious:
                all_anomalies.append(
                    AnomalyFlag(
                        anomaly_id=f"benford::{dataset_id}",
                        anomaly_type=AnomalyType.BENFORD_VIOLATION,
                        severity=RiskLevel.HIGH if p_value < 0.01 else RiskLevel.MEDIUM,
                        title="Benford's Law violation detected",
                        description=(
                            f"The leading-digit distribution of {len(transactions)} transactions "
                            f"significantly deviates from Benford's Law (χ²={chi_sq:.2f}, "
                            f"p={p_value:.4f}). This suggests the data may contain "
                            f"fabricated or structured amounts."
                        ),
                        affected_entity_id=dataset_id,
                        affected_entity_type="dataset",
                        score=round(min(1.0, chi_sq / 30.0), 3),
                        evidence={"chi_squared": chi_sq, "p_value": p_value},
                    )
                )

            # 2. Statistical outliers
            outlier_flags = detect_outliers(transactions)
            all_anomalies.extend(outlier_flags)

            # 3. Velocity spikes
            velocity_spikes, velocity_flags = detect_velocity_spikes(transactions)
            all_anomalies.extend(velocity_flags)

            # 4. Round-amount structuring
            round_flags = detect_round_amounts(transactions)
            all_anomalies.extend(round_flags)

            # Compute overall risk score
            risk_score = _compute_risk_score(all_anomalies, len(transactions), benford_suspicious)
            risk_level = _risk_level_from_score(risk_score)

            # Build summary
            summary_parts: list[str] = []
            summary_parts.append(f"Analyzed {len(transactions)} transactions.")
            if benford_suspicious:
                summary_parts.append(f"Benford's Law violation detected (p={p_value:.4f}).")
            if outlier_flags:
                summary_parts.append(f"{len(outlier_flags)} statistical outlier(s) found.")
            if velocity_spikes:
                summary_parts.append(f"{len(velocity_spikes)} velocity spike(s) detected.")
            if round_flags:
                summary_parts.append(f"{len(round_flags)} round-amount pattern(s) flagged.")
            if not all_anomalies:
                summary_parts.append("No significant anomalies detected.")

            result = AnalysisResult(
                analysis_id=str(uuid4()),
                dataset_id=dataset_id,
                completed_at=datetime.now(UTC),
                total_transactions=len(transactions),
                total_anomalies=len(all_anomalies),
                risk_score=risk_score,
                risk_level=risk_level,
                benford_chi_squared=chi_sq,
                benford_p_value=p_value,
                benford_is_suspicious=benford_suspicious,
                benford_digits=benford_digits,
                outlier_count=len(outlier_flags),
                outlier_pct=(
                    round(len(outlier_flags) / len(transactions) * 100, 2) if transactions else 0
                ),
                velocity_spikes=velocity_spikes,
                anomalies=all_anomalies,
                summary=" ".join(summary_parts),
            )

            dataset.status = DatasetStatus.COMPLETED
            self._store.save_dataset(dataset)
            self._store.save_result(result)
            return result

        except Exception as exc:
            dataset.status = DatasetStatus.FAILED
            dataset.error_message = str(exc)
            self._store.save_dataset(dataset)
            raise

    def get_dataset(self, dataset_id: str) -> Dataset:
        dataset = self._store.get_dataset(dataset_id)
        if dataset is None:
            raise LookupError(f"Dataset '{dataset_id}' not found.")
        return dataset

    def list_datasets(self) -> list[Dataset]:
        return self._store.list_datasets()

    def get_result(self, dataset_id: str) -> AnalysisResult:
        result = self._store.get_result(dataset_id)
        if result is None:
            raise LookupError(f"No analysis results for dataset '{dataset_id}'.")
        return result

    def get_transactions(self, dataset_id: str) -> list[UploadedTransaction]:
        return self._store.get_transactions(dataset_id)


def _compute_risk_score(
    anomalies: list[AnomalyFlag],
    total_txns: int,
    benford_suspicious: bool,
) -> int:
    if not anomalies:
        return 5

    base = 0
    if benford_suspicious:
        base += 25

    severity_weights = {
        RiskLevel.CRITICAL: 15,
        RiskLevel.HIGH: 10,
        RiskLevel.MEDIUM: 5,
        RiskLevel.LOW: 2,
    }

    for anomaly in anomalies[:20]:  # Cap contribution
        base += severity_weights.get(anomaly.severity, 2)

    # Scale by anomaly density
    density = len(anomalies) / max(total_txns, 1)
    density_bonus = int(density * 100)

    return min(100, base + density_bonus)


def _risk_level_from_score(score: int) -> RiskLevel:
    if score >= 75:
        return RiskLevel.CRITICAL
    if score >= 50:
        return RiskLevel.HIGH
    if score >= 25:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW
