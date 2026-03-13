"""Behavioral inference over uploaded transaction datasets.

This module moves the dataset workflow beyond generic anomaly counters by
deriving entity-relationship findings directly from uploaded transaction
behavior: shared devices, merchant concentration, geographic drift, peer-group
outliers, and a lightweight relationship graph.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from statistics import median

import networkx as nx

from relational_fraud_intelligence.domain.models import (
    AnomalyFlag,
    AnomalyType,
    BehavioralInsight,
    EntityReference,
    EntityType,
    GraphAnalysisResult,
    RiskLevel,
    UploadedTransaction,
)


@dataclass(slots=True)
class BehavioralAnalysis:
    anomalies: list[AnomalyFlag]
    insights: list[BehavioralInsight]
    graph_analysis: GraphAnalysisResult | None


def analyze_behavioral_patterns(
    transactions: list[UploadedTransaction],
) -> BehavioralAnalysis:
    anomalies: list[AnomalyFlag] = []
    insights: list[BehavioralInsight] = []

    insights.extend(_detect_shared_identifiers(transactions, anomalies))
    insights.extend(_detect_merchant_concentration(transactions, anomalies))
    insights.extend(_detect_geographic_drift(transactions, anomalies))
    insights.extend(_detect_peer_group_outliers(transactions, anomalies))

    graph_analysis = _build_relationship_graph(transactions, insights)

    insights.sort(
        key=lambda item: (
            _severity_rank(item.severity),
            _to_float(item.evidence.get("supporting_amount", 0.0)),
        ),
        reverse=True,
    )
    anomalies.sort(
        key=lambda item: (_severity_rank(item.severity), item.score),
        reverse=True,
    )

    return BehavioralAnalysis(
        anomalies=anomalies[:8],
        insights=insights[:5],
        graph_analysis=graph_analysis,
    )


def _detect_shared_identifiers(
    transactions: list[UploadedTransaction],
    anomalies: list[AnomalyFlag],
) -> list[BehavioralInsight]:
    device_groups: dict[str, list[UploadedTransaction]] = defaultdict(list)
    for transaction in transactions:
        fingerprint = transaction.device_fingerprint.strip()
        if fingerprint:
            device_groups[fingerprint].append(transaction)

    insights: list[BehavioralInsight] = []
    for fingerprint, group in sorted(
        device_groups.items(),
        key=lambda item: (len({txn.account_id for txn in item[1]}), len(item[1])),
        reverse=True,
    ):
        accounts = sorted({txn.account_id for txn in group})
        if len(accounts) < 2:
            continue

        merchants = sorted({txn.merchant for txn in group if txn.merchant})[:3]
        total_amount = round(sum(txn.amount for txn in group), 2)
        severity = (
            RiskLevel.HIGH
            if len(accounts) >= 3 or len(group) >= 6 or total_amount >= 5000
            else RiskLevel.MEDIUM
        )
        score = min(
            1.0,
            0.25 * len(accounts) + 0.04 * len(group) + min(total_amount / 15000, 0.35),
        )

        title = "Shared device links multiple accounts"
        narrative = (
            f"Device {fingerprint} touched {len(accounts)} accounts across {len(group)} "
            f"transactions totaling ${total_amount:,.2f}."
        )
        if merchants:
            narrative += f" The activity clusters around {', '.join(merchants)}."

        entities = [
            EntityReference(
                entity_type=EntityType.DEVICE,
                entity_id=fingerprint,
                display_name=fingerprint,
            ),
            *[
                EntityReference(
                    entity_type=EntityType.ACCOUNT,
                    entity_id=account_id,
                    display_name=account_id,
                )
                for account_id in accounts[:3]
            ],
        ]
        evidence = {
            "account_count": len(accounts),
            "transaction_count": len(group),
            "supporting_amount": total_amount,
            "merchant_count": len({txn.merchant for txn in group if txn.merchant}),
        }
        insights.append(
            BehavioralInsight(
                insight_id=f"shared-device::{fingerprint}",
                title=title,
                severity=severity,
                narrative=narrative,
                entities=entities,
                evidence=evidence,
            )
        )
        anomalies.append(
            AnomalyFlag(
                anomaly_id=f"shared-device::{fingerprint}",
                anomaly_type=AnomalyType.SHARED_IDENTIFIER,
                severity=severity,
                title=title,
                description=narrative,
                affected_entity_id=fingerprint,
                affected_entity_type="device",
                score=round(score, 3),
                evidence=evidence,
            )
        )

    return insights


def _detect_merchant_concentration(
    transactions: list[UploadedTransaction],
    anomalies: list[AnomalyFlag],
) -> list[BehavioralInsight]:
    account_groups: dict[str, list[UploadedTransaction]] = defaultdict(list)
    for transaction in transactions:
        account_groups[transaction.account_id].append(transaction)

    account_totals = {
        account_id: sum(txn.amount for txn in group) for account_id, group in account_groups.items()
    }
    median_total = median(account_totals.values()) if account_totals else 0.0

    candidates: list[tuple[float, BehavioralInsight, AnomalyFlag]] = []
    for account_id, group in account_groups.items():
        if len(group) < 4:
            continue

        total_amount = account_totals[account_id]
        if total_amount < max(1000.0, median_total * 1.35):
            continue

        merchant_totals: dict[str, float] = defaultdict(float)
        for txn in group:
            merchant_name = txn.merchant or "unknown-merchant"
            merchant_totals[merchant_name] += txn.amount

        dominant_merchant, dominant_amount = max(
            merchant_totals.items(),
            key=lambda item: item[1],
        )
        share = dominant_amount / total_amount if total_amount else 0.0
        if share < 0.72:
            continue

        severity = (
            RiskLevel.HIGH
            if share >= 0.85 and total_amount >= max(2500.0, median_total * 1.8)
            else RiskLevel.MEDIUM
        )
        narrative = (
            f"Account {account_id} concentrated {share:.0%} of its ${total_amount:,.2f} "
            f"volume into {dominant_merchant}."
        )
        score = min(1.0, share * 0.75 + min(total_amount / 12000, 0.25))
        evidence = {
            "account_id": account_id,
            "dominant_merchant": dominant_merchant,
            "merchant_share": round(share, 3),
            "supporting_amount": round(dominant_amount, 2),
            "account_total_amount": round(total_amount, 2),
        }
        insight = BehavioralInsight(
            insight_id=f"merchant-concentration::{account_id}",
            title="Counterparty concentration emerged in one account",
            severity=severity,
            narrative=narrative,
            entities=[
                EntityReference(
                    entity_type=EntityType.ACCOUNT,
                    entity_id=account_id,
                    display_name=account_id,
                ),
                EntityReference(
                    entity_type=EntityType.MERCHANT,
                    entity_id=dominant_merchant,
                    display_name=dominant_merchant,
                ),
            ],
            evidence=evidence,
        )
        anomaly = AnomalyFlag(
            anomaly_id=f"merchant-concentration::{account_id}",
            anomaly_type=AnomalyType.MERCHANT_CONCENTRATION,
            severity=severity,
            title=insight.title,
            description=narrative,
            affected_entity_id=account_id,
            affected_entity_type="account",
            score=round(score, 3),
            evidence=evidence,
        )
        candidates.append((share * total_amount, insight, anomaly))

    insights: list[BehavioralInsight] = []
    for _, insight, anomaly in sorted(candidates, key=lambda item: item[0], reverse=True)[:3]:
        insights.append(insight)
        anomalies.append(anomaly)
    return insights


def _detect_geographic_drift(
    transactions: list[UploadedTransaction],
    anomalies: list[AnomalyFlag],
) -> list[BehavioralInsight]:
    account_groups: dict[str, list[UploadedTransaction]] = defaultdict(list)
    for transaction in transactions:
        if transaction.ip_country:
            account_groups[transaction.account_id].append(transaction)

    insights: list[BehavioralInsight] = []
    for account_id, group in account_groups.items():
        if len(group) < 4:
            continue

        country_counts = Counter(txn.ip_country for txn in group if txn.ip_country)
        if len(country_counts) < 2:
            continue

        baseline_country, _ = country_counts.most_common(1)[0]
        drift_transactions = [
            txn for txn in group if txn.ip_country and txn.ip_country != baseline_country
        ]
        drift_amount = sum(txn.amount for txn in drift_transactions)
        total_amount = sum(txn.amount for txn in group)
        drift_share = drift_amount / total_amount if total_amount else 0.0
        if drift_share < 0.35 or max(txn.amount for txn in drift_transactions) < 700:
            continue

        drift_countries = sorted({txn.ip_country for txn in drift_transactions if txn.ip_country})
        severity = (
            RiskLevel.HIGH if drift_share >= 0.6 or len(drift_countries) >= 2 else RiskLevel.MEDIUM
        )
        score = min(1.0, drift_share * 0.9 + min(len(drift_countries) * 0.08, 0.16))
        title = "Account behavior drifted away from its baseline geography"
        narrative = (
            f"Account {account_id} usually appears in {baseline_country}, but "
            f"{len(drift_transactions)} transactions totaling ${drift_amount:,.2f} "
            f"came from {', '.join(drift_countries)}."
        )
        evidence = {
            "baseline_country": baseline_country,
            "drift_countries": drift_countries,
            "drift_share": round(drift_share, 3),
            "supporting_amount": round(drift_amount, 2),
        }
        insights.append(
            BehavioralInsight(
                insight_id=f"geo-drift::{account_id}",
                title=title,
                severity=severity,
                narrative=narrative,
                entities=[
                    EntityReference(
                        entity_type=EntityType.ACCOUNT,
                        entity_id=account_id,
                        display_name=account_id,
                    )
                ],
                evidence=evidence,
            )
        )
        anomalies.append(
            AnomalyFlag(
                anomaly_id=f"geo-drift::{account_id}",
                anomaly_type=AnomalyType.GEOGRAPHIC_DRIFT,
                severity=severity,
                title=title,
                description=narrative,
                affected_entity_id=account_id,
                affected_entity_type="account",
                score=round(score, 3),
                evidence=evidence,
            )
        )

    return insights[:3]


def _detect_peer_group_outliers(
    transactions: list[UploadedTransaction],
    anomalies: list[AnomalyFlag],
) -> list[BehavioralInsight]:
    account_groups: dict[str, list[UploadedTransaction]] = defaultdict(list)
    for transaction in transactions:
        account_groups[transaction.account_id].append(transaction)

    account_volumes = {
        account_id: sum(txn.amount for txn in group) for account_id, group in account_groups.items()
    }
    account_counts = {account_id: len(group) for account_id, group in account_groups.items()}
    volume_values = list(account_volumes.values())
    count_values = [float(value) for value in account_counts.values()]

    candidates: list[tuple[float, BehavioralInsight, AnomalyFlag]] = []
    for account_id in account_groups:
        volume_z = _robust_z_score(account_volumes[account_id], volume_values)
        count_z = _robust_z_score(float(account_counts[account_id]), count_values)
        if volume_z < 3.0 and count_z < 3.0:
            continue

        severity = (
            RiskLevel.HIGH
            if volume_z >= 4.5 or (volume_z >= 3.0 and count_z >= 3.0)
            else RiskLevel.MEDIUM
        )
        title = "Account stands out from the dataset peer group"
        narrative = (
            f"Account {account_id} is an outlier against its peers with volume z={volume_z:.1f} "
            f"and count z={count_z:.1f}."
        )
        score = min(1.0, max(volume_z, count_z) / 6.0)
        evidence = {
            "account_total_amount": round(account_volumes[account_id], 2),
            "account_transaction_count": account_counts[account_id],
            "volume_z_score": round(volume_z, 2),
            "count_z_score": round(count_z, 2),
            "supporting_amount": round(account_volumes[account_id], 2),
        }
        insight = BehavioralInsight(
            insight_id=f"peer-outlier::{account_id}",
            title=title,
            severity=severity,
            narrative=narrative,
            entities=[
                EntityReference(
                    entity_type=EntityType.ACCOUNT,
                    entity_id=account_id,
                    display_name=account_id,
                )
            ],
            evidence=evidence,
        )
        anomaly = AnomalyFlag(
            anomaly_id=f"peer-outlier::{account_id}",
            anomaly_type=AnomalyType.PEER_GROUP_OUTLIER,
            severity=severity,
            title=title,
            description=narrative,
            affected_entity_id=account_id,
            affected_entity_type="account",
            score=round(score, 3),
            evidence=evidence,
        )
        candidates.append((max(volume_z, count_z), insight, anomaly))

    insights: list[BehavioralInsight] = []
    for _, insight, anomaly in sorted(candidates, key=lambda item: item[0], reverse=True)[:3]:
        insights.append(insight)
        anomalies.append(anomaly)
    return insights


def _build_relationship_graph(
    transactions: list[UploadedTransaction],
    insights: list[BehavioralInsight],
) -> GraphAnalysisResult | None:
    if not transactions:
        return None

    graph = nx.Graph()
    for transaction in transactions:
        account_node = _add_node(
            graph,
            prefix="account",
            entity_id=transaction.account_id,
            label=transaction.account_id,
        )
        merchant_name = transaction.merchant.strip() or "unknown-merchant"
        merchant_node = _add_node(
            graph,
            prefix="merchant",
            entity_id=merchant_name,
            label=merchant_name,
        )
        _upsert_edge(graph, account_node, merchant_node, transaction.amount)

        fingerprint = transaction.device_fingerprint.strip()
        if fingerprint:
            device_node = _add_node(
                graph,
                prefix="device",
                entity_id=fingerprint,
                label=fingerprint,
            )
            _upsert_edge(graph, account_node, device_node, 1.0)

    if graph.number_of_nodes() == 0:
        return None

    connected_components = nx.number_connected_components(graph)
    density = nx.density(graph)
    degrees = dict(graph.degree())
    highest_degree_node = max(degrees, key=lambda node: degrees[node])
    highest_degree_entity = _to_entity_reference(graph, highest_degree_node)
    highest_degree_score = degrees[highest_degree_node]

    hub_threshold = max(3, round(sum(degrees.values()) / max(len(degrees), 1) * 1.5))
    hub_entities = [
        _to_entity_reference(graph, node)
        for node, degree in sorted(degrees.items(), key=lambda item: item[1], reverse=True)
        if degree >= hub_threshold
    ][:5]

    if graph.number_of_edges() >= 2 and graph.number_of_nodes() >= 4:
        try:
            community_count = len(list(nx.community.greedy_modularity_communities(graph)))
        except Exception:
            community_count = connected_components
    else:
        community_count = connected_components

    shortest_path_length = _graph_shortest_path_length(graph)
    shared_device_hubs = sum(
        1
        for node, degree in degrees.items()
        if graph.nodes[node]["kind"] == "device" and degree >= 2
    )
    merchant_hubs = sum(
        1
        for node, degree in degrees.items()
        if graph.nodes[node]["kind"] == "merchant" and degree >= 3
    )
    risk_amplification_factor = round(
        1.0
        + min(
            0.9,
            0.14 * shared_device_hubs
            + 0.08 * merchant_hubs
            + 0.05 * max(0, community_count - 1)
            + 0.03 * len(insights),
        ),
        2,
    )

    return GraphAnalysisResult(
        connected_components=connected_components,
        density=round(density, 3),
        highest_degree_entity=highest_degree_entity,
        highest_degree_score=highest_degree_score,
        community_count=community_count,
        shortest_path_length=shortest_path_length,
        hub_entities=hub_entities,
        risk_amplification_factor=risk_amplification_factor,
    )


def _add_node(graph: nx.Graph, *, prefix: str, entity_id: str, label: str) -> str:
    node_id = f"{prefix}::{entity_id}"
    graph.add_node(node_id, kind=prefix, label=label)
    return node_id


def _upsert_edge(graph: nx.Graph, left: str, right: str, weight: float) -> None:
    if graph.has_edge(left, right):
        graph[left][right]["weight"] += weight
        graph[left][right]["count"] += 1
        return
    graph.add_edge(left, right, weight=weight, count=1)


def _to_entity_reference(graph: nx.Graph, node_id: str) -> EntityReference:
    data = graph.nodes[node_id]
    kind = str(data["kind"])
    label = str(data["label"])
    if kind == "account":
        entity_type = EntityType.ACCOUNT
    elif kind == "merchant":
        entity_type = EntityType.MERCHANT
    else:
        entity_type = EntityType.DEVICE
    return EntityReference(
        entity_type=entity_type,
        entity_id=label,
        display_name=label,
    )


def _graph_shortest_path_length(graph: nx.Graph) -> int | None:
    account_nodes = [node for node, data in graph.nodes(data=True) if data["kind"] == "account"]
    if len(account_nodes) < 2:
        return None

    for left_index, left_node in enumerate(account_nodes[:-1]):
        for right_node in account_nodes[left_index + 1 :]:
            if nx.has_path(graph, left_node, right_node):
                return int(nx.shortest_path_length(graph, left_node, right_node))
    return None


def _robust_z_score(value: float, values: list[float]) -> float:
    if len(values) < 3:
        return 0.0

    center = median(values)
    deviations = [abs(item - center) for item in values]
    median_absolute_deviation = median(deviations)
    if median_absolute_deviation == 0:
        max_value = max(values)
        return 0.0 if max_value == center else (value - center) / max(max_value - center, 1.0)
    return abs((value - center) / (1.4826 * median_absolute_deviation))


def _severity_rank(level: RiskLevel) -> int:
    if level == RiskLevel.CRITICAL:
        return 4
    if level == RiskLevel.HIGH:
        return 3
    if level == RiskLevel.MEDIUM:
        return 2
    return 1


def _to_float(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0
