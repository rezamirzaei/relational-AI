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
    BehavioralInsight,
    Dataset,
    DatasetStatus,
    EntityReference,
    EntityType,
    GraphAnalysisResult,
    InvestigationLead,
    RiskLevel,
    UploadedTransaction,
    VelocitySpike,
)
from relational_fraud_intelligence.infrastructure.analysis.behavioral import (
    analyze_behavioral_patterns,
)
from relational_fraud_intelligence.infrastructure.analysis.benford import analyze_benford
from relational_fraud_intelligence.infrastructure.analysis.outliers import detect_outliers
from relational_fraud_intelligence.infrastructure.analysis.round_amounts import detect_round_amounts
from relational_fraud_intelligence.infrastructure.analysis.velocity import detect_velocity_spikes

if TYPE_CHECKING:
    from relational_fraud_intelligence.application.ports.repositories import (
        DatasetStore as DatasetStorePort,
    )


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
    def __init__(self, store: DatasetStorePort) -> None:
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

            # 5. Behavioral inference over accounts, merchants, devices, and geographies
            behavioral_analysis = analyze_behavioral_patterns(transactions)
            all_anomalies.extend(behavioral_analysis.anomalies)
            investigation_leads = _build_investigation_leads(
                anomalies=all_anomalies,
                behavioral_insights=behavioral_analysis.insights,
                graph_analysis=behavioral_analysis.graph_analysis,
                velocity_spikes=velocity_spikes,
                benford_suspicious=benford_suspicious,
            )

            # Compute overall risk score
            risk_score = _compute_risk_score(
                all_anomalies,
                len(transactions),
                benford_suspicious,
                behavioral_analysis.graph_analysis,
            )
            risk_level = _risk_level_from_score(risk_score)

            # Build summary
            summary_parts = _build_summary_parts(
                total_transactions=len(transactions),
                benford_suspicious=benford_suspicious,
                p_value=p_value,
                outlier_flags=outlier_flags,
                velocity_spikes=velocity_spikes,
                round_flags=round_flags,
                behavioral_insights=behavioral_analysis.insights,
                investigation_leads=investigation_leads,
                graph_analysis=behavioral_analysis.graph_analysis,
                all_anomalies=all_anomalies,
            )

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
                graph_analysis=behavioral_analysis.graph_analysis,
                behavioral_insights=behavioral_analysis.insights,
                investigation_leads=investigation_leads,
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
    graph_analysis: GraphAnalysisResult | None,
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

    graph_bonus = 0
    if graph_analysis is not None and graph_analysis.risk_amplification_factor > 1.0:
        graph_bonus = int((graph_analysis.risk_amplification_factor - 1.0) * 20)

    return min(100, base + density_bonus + graph_bonus)


def _build_summary_parts(
    *,
    total_transactions: int,
    benford_suspicious: bool,
    p_value: float,
    outlier_flags: list[AnomalyFlag],
    velocity_spikes: list[VelocitySpike],
    round_flags: list[AnomalyFlag],
    behavioral_insights: list[BehavioralInsight],
    investigation_leads: list[InvestigationLead],
    graph_analysis: GraphAnalysisResult | None,
    all_anomalies: list[AnomalyFlag],
) -> list[str]:
    summary_parts: list[str] = [f"Analyzed {total_transactions} transactions."]
    if benford_suspicious:
        summary_parts.append(f"Benford's Law violation detected (p={p_value:.4f}).")
    if outlier_flags:
        summary_parts.append(f"{len(outlier_flags)} statistical outlier(s) found.")
    if velocity_spikes:
        summary_parts.append(f"{len(velocity_spikes)} velocity spike(s) detected.")
    if round_flags:
        summary_parts.append(f"{len(round_flags)} round-amount pattern(s) flagged.")
    if behavioral_insights:
        summary_parts.append(
            f"{len(behavioral_insights)} behavioral inference(s) highlighted "
            "account, device, or merchant structure."
        )
        summary_parts.append(behavioral_insights[0].narrative)
    if investigation_leads:
        summary_parts.append(
            f"Synthesized {len(investigation_leads)} investigation lead(s) from the dataset."
        )
        summary_parts.append(
            f"Top lead: {investigation_leads[0].title}. {investigation_leads[0].hypothesis}"
        )
    if graph_analysis is not None and graph_analysis.highest_degree_entity is not None:
        summary_parts.append(
            "Relationship graph centered on "
            f"{graph_analysis.highest_degree_entity.display_name} with degree "
            f"{graph_analysis.highest_degree_score} and amplification "
            f"{graph_analysis.risk_amplification_factor:.2f}x."
        )
    if not all_anomalies:
        summary_parts.append("No significant anomalies detected.")
    return summary_parts


def _build_investigation_leads(
    *,
    anomalies: list[AnomalyFlag],
    behavioral_insights: list[BehavioralInsight],
    graph_analysis: GraphAnalysisResult | None,
    velocity_spikes: list[VelocitySpike],
    benford_suspicious: bool,
) -> list[InvestigationLead]:
    leads: list[InvestigationLead] = []
    anomaly_ids = {anomaly.anomaly_id for anomaly in anomalies}

    for insight in behavioral_insights:
        related_ids = [
            anomaly.anomaly_id
            for anomaly in anomalies
            if anomaly.anomaly_id == insight.insight_id
            or anomaly.anomaly_id.endswith(f"::{insight.insight_id.split('::', 1)[-1]}")
        ]
        lead = _lead_from_behavioral_insight(
            insight=insight,
            graph_analysis=graph_analysis,
            supporting_anomaly_ids=related_ids,
        )
        if lead is not None:
            leads.append(lead)

    velocity_lead = _lead_from_velocity_spikes(velocity_spikes, anomalies)
    if velocity_lead is not None:
        leads.append(velocity_lead)

    structuring_lead = _lead_from_amount_patterns(anomalies, benford_suspicious)
    if structuring_lead is not None:
        leads.append(structuring_lead)

    graph_lead = _lead_from_graph(graph_analysis, behavioral_insights, anomaly_ids)
    if graph_lead is not None:
        leads.append(graph_lead)

    deduped: list[InvestigationLead] = []
    seen_ids: set[str] = set()
    for lead in sorted(leads, key=_lead_sort_key, reverse=True):
        if lead.lead_id in seen_ids:
            continue
        seen_ids.add(lead.lead_id)
        deduped.append(lead)
    return deduped[:4]


def _severity_rank(level: RiskLevel) -> int:
    return {
        RiskLevel.CRITICAL: 4,
        RiskLevel.HIGH: 3,
        RiskLevel.MEDIUM: 2,
        RiskLevel.LOW: 1,
    }[level]


def _coerce_float(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _lead_from_behavioral_insight(
    *,
    insight: BehavioralInsight,
    graph_analysis: GraphAnalysisResult | None,
    supporting_anomaly_ids: list[str],
) -> InvestigationLead | None:
    prefix = insight.insight_id.split("::", 1)[0]
    if prefix == "shared-device":
        narrative = insight.narrative
        if graph_analysis is not None and graph_analysis.risk_amplification_factor > 1.1:
            narrative += (
                " The relationship graph amplified this cluster to "
                f"{graph_analysis.risk_amplification_factor:.2f}x baseline risk."
            )
        return InvestigationLead(
            lead_id=f"lead::{insight.insight_id}",
            lead_type="shared-device-ring",
            title="Potential shared-device coordination ring",
            severity=insight.severity,
            hypothesis=(
                "Multiple accounts are converging on the same device, which is consistent "
                "with coordinated cash-out, account sharing, or synthetic identity reuse."
            ),
            narrative=narrative,
            entities=insight.entities,
            supporting_anomaly_ids=supporting_anomaly_ids,
            recommended_actions=[
                (
                    "Confirm whether the linked accounts share a legitimate owner or "
                    "onboarding trail."
                ),
                (
                    "Review device binding, login, and credential-reset history for the "
                    "linked accounts."
                ),
                (
                    "Hold downstream payout, gift card, or crypto redemption activity if "
                    "the cluster is unauthorized."
                ),
            ],
            evidence=insight.evidence,
        )
    if prefix == "geo-drift":
        return InvestigationLead(
            lead_id=f"lead::{insight.insight_id}",
            lead_type="account-takeover",
            title="Potential account takeover from geographic drift",
            severity=insight.severity,
            hypothesis=(
                "The account shifted away from its normal geography while meaningful value "
                "continued to move, which is consistent with takeover or mule usage."
            ),
            narrative=insight.narrative,
            entities=insight.entities,
            supporting_anomaly_ids=supporting_anomaly_ids,
            recommended_actions=[
                "Check recent login, MFA, and password-reset events for the affected account.",
                (
                    "Compare the drifted activity against customer travel signals or known "
                    "device history."
                ),
                (
                    "Step up authentication or contact the customer before more value "
                    "leaves the account."
                ),
            ],
            evidence=insight.evidence,
        )
    if prefix == "merchant-concentration":
        return InvestigationLead(
            lead_id=f"lead::{insight.insight_id}",
            lead_type="merchant-funnel",
            title="Potential funnel or bust-out concentration",
            severity=insight.severity,
            hypothesis=(
                "One account concentrated an unusual share of spend into a single merchant, "
                "which can indicate cash-out, bust-out behavior, or laundering through a "
                "known counterparty."
            ),
            narrative=insight.narrative,
            entities=insight.entities,
            supporting_anomaly_ids=supporting_anomaly_ids,
            recommended_actions=[
                (
                    "Review the merchant relationship and any prior fraud history for the "
                    "same counterparty."
                ),
                (
                    "Inspect whether the concentrated spend aligns with the account's "
                    "stated profile or limits."
                ),
                "Check whether related accounts are also routing value into the same merchant.",
            ],
            evidence=insight.evidence,
        )
    if prefix == "peer-outlier":
        return InvestigationLead(
            lead_id=f"lead::{insight.insight_id}",
            lead_type="peer-outlier",
            title="Account behavior diverges sharply from peers",
            severity=insight.severity,
            hypothesis=(
                "This account's volume and frequency sit far outside the dataset peer group, "
                "so it likely deserves case-level review instead of queue-only triage."
            ),
            narrative=insight.narrative,
            entities=insight.entities,
            supporting_anomaly_ids=supporting_anomaly_ids,
            recommended_actions=[
                "Review recent account lifecycle events and compare them to the peer cohort.",
                (
                    "Sample the largest transactions to determine whether the outlier "
                    "behavior is legitimate."
                ),
                (
                    "Escalate if the account's purpose, limits, or ownership do not "
                    "explain the deviation."
                ),
            ],
            evidence=insight.evidence,
        )
    return None


def _lead_from_velocity_spikes(
    velocity_spikes: list[VelocitySpike],
    anomalies: list[AnomalyFlag],
) -> InvestigationLead | None:
    if not velocity_spikes:
        return None

    spike = max(
        velocity_spikes,
        key=lambda item: (item.z_score, item.total_amount, item.transaction_count),
    )
    supporting_anomaly_ids = [
        anomaly.anomaly_id
        for anomaly in anomalies
        if anomaly.anomaly_type == AnomalyType.VELOCITY_SPIKE
        and anomaly.affected_entity_id == spike.entity_id
    ]
    severity = (
        RiskLevel.HIGH if spike.z_score >= 4.5 or spike.transaction_count >= 6 else RiskLevel.MEDIUM
    )
    return InvestigationLead(
        lead_id=f"lead::velocity::{spike.entity_type}::{spike.entity_id}",
        lead_type="velocity-burst",
        title="Rapid transaction burst requires timeline review",
        severity=severity,
        hypothesis=(
            "The entity compressed unusual transaction volume into a short window, which is "
            "consistent with account takeover, automated testing, or fast cash-out behavior."
        ),
        narrative=(
            f"{spike.entity_type.title()} {spike.entity_id} generated {spike.transaction_count} "
            f"transactions totaling ${spike.total_amount:,.2f} with z={spike.z_score:.1f}."
        ),
        entities=[
            EntityReference(
                entity_type=(
                    EntityType.ACCOUNT if spike.entity_type == "account" else EntityType.MERCHANT
                ),
                entity_id=spike.entity_id,
                display_name=spike.entity_id,
            )
        ],
        supporting_anomaly_ids=supporting_anomaly_ids,
        recommended_actions=[
            ("Reconstruct the timeline around the spike window and identify the triggering event."),
            "Review authorizations, declines, and any repeated retries tied to the same entity.",
            "Consider temporary controls if the burst is still in progress.",
        ],
        evidence={
            "entity_id": spike.entity_id,
            "entity_type": spike.entity_type,
            "transaction_count": spike.transaction_count,
            "supporting_amount": round(spike.total_amount, 2),
            "z_score": round(spike.z_score, 2),
        },
    )


def _lead_from_amount_patterns(
    anomalies: list[AnomalyFlag],
    benford_suspicious: bool,
) -> InvestigationLead | None:
    supporting_anomalies = [
        anomaly
        for anomaly in anomalies
        if anomaly.anomaly_type in {AnomalyType.BENFORD_VIOLATION, AnomalyType.ROUND_AMOUNT}
    ]
    if not supporting_anomalies:
        return None

    round_amount_flags = [
        anomaly
        for anomaly in supporting_anomalies
        if anomaly.anomaly_type == AnomalyType.ROUND_AMOUNT
    ]
    fallback_severity = max(
        supporting_anomalies,
        key=lambda anomaly: _severity_rank(anomaly.severity),
    ).severity
    severity = (
        RiskLevel.HIGH if benford_suspicious and len(round_amount_flags) >= 1 else fallback_severity
    )
    narrative_parts: list[str] = []
    if benford_suspicious:
        narrative_parts.append("Leading digits deviated materially from expected frequencies.")
    if round_amount_flags:
        narrative_parts.append(
            f"{len(round_amount_flags)} round-amount pattern(s) suggest structured or "
            "manually chosen values."
        )
    return InvestigationLead(
        lead_id="lead::amount-structuring",
        lead_type="structured-amounts",
        title="Structured or fabricated amount pattern across the dataset",
        severity=severity,
        hypothesis=(
            "The batch contains amount patterns that are more consistent with manual structuring "
            "or fabricated values than organic customer behavior."
        ),
        narrative=" ".join(narrative_parts),
        supporting_anomaly_ids=[anomaly.anomaly_id for anomaly in supporting_anomalies],
        recommended_actions=[
            (
                "Sample the largest structured amounts and compare them to known "
                "merchant or card denomination patterns."
            ),
            "Check whether the suspicious amounts cluster in time, channel, or destination.",
            (
                "Verify whether upstream systems could have generated synthetic or "
                "rounded values in bulk."
            ),
        ],
        evidence={
            "benford_suspicious": benford_suspicious,
            "round_amount_count": len(round_amount_flags),
            "supporting_amount": round(
                sum(
                    _coerce_float(anomaly.evidence.get("total_round_amount", 0.0))
                    for anomaly in round_amount_flags
                ),
                2,
            ),
        },
    )


def _lead_from_graph(
    graph_analysis: GraphAnalysisResult | None,
    behavioral_insights: list[BehavioralInsight],
    anomaly_ids: set[str],
) -> InvestigationLead | None:
    if graph_analysis is None or graph_analysis.risk_amplification_factor <= 1.2:
        return None
    if any(
        anomaly_id.startswith(("shared-device::", "merchant-concentration::"))
        for anomaly_id in anomaly_ids
    ):
        return None
    hub_entity = graph_analysis.highest_degree_entity
    if hub_entity is None:
        return None
    return InvestigationLead(
        lead_id="lead::graph-cluster",
        lead_type="network-cluster",
        title="Related entities should be investigated as one network",
        severity=RiskLevel.MEDIUM,
        hypothesis=(
            "The inferred relationship graph suggests the anomalies are connected and should "
            "be reviewed as one scheme rather than as isolated records."
        ),
        narrative=(
            f"The graph centers on {hub_entity.display_name} with degree "
            f"{graph_analysis.highest_degree_score} and a "
            f"{graph_analysis.risk_amplification_factor:.2f}x amplification factor."
        ),
        entities=[hub_entity, *graph_analysis.hub_entities[:3]],
        supporting_anomaly_ids=[],
        recommended_actions=[
            (
                "Open a single case for the connected entities instead of triaging the "
                "findings separately."
            ),
            "Map ownership, device, and merchant overlap for the hub entity first.",
            "Use the graph hubs to prioritize which entities to review before the long tail.",
        ],
        evidence={
            "connected_components": graph_analysis.connected_components,
            "community_count": graph_analysis.community_count,
            "risk_amplification_factor": graph_analysis.risk_amplification_factor,
            "supporting_amount": float(len(behavioral_insights)),
        },
    )


def _lead_sort_key(lead: InvestigationLead) -> tuple[int, float, int]:
    return (
        _severity_rank(lead.severity),
        _coerce_float(lead.evidence.get("supporting_amount", 0.0)),
        len(lead.supporting_anomaly_ids),
    )


def _risk_level_from_score(score: int) -> RiskLevel:
    if score >= 75:
        return RiskLevel.CRITICAL
    if score >= 50:
        return RiskLevel.HIGH
    if score >= 25:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW
