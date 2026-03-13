"""RelationalAI-enhanced risk reasoner with graph-based fraud detection.

NOTE: This implementation supports a hybrid mode. It uses the RelationalAI SDK
to project data into a relational knowledge graph (currently backed by a local
DuckDB instance for development/demo purposes).
However, the specific graph algorithms (PageRank, Cycle Detection, etc.) are
currently executed using NetworkX in memory to allow for fully offline
operation without requiring a cloud RelationalAI account.

In a production deployment, these algorithms would be translated into Relational
Knowledge Graph (Rel) relations for server-side execution.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from importlib import import_module

import networkx as nx
from pydantic import BaseModel

from relational_fraud_intelligence.application.dto.investigation import (
    ReasonAboutRiskCommand,
    ReasonAboutRiskResult,
)
from relational_fraud_intelligence.application.ports.reasoner import RiskReasoner
from relational_fraud_intelligence.domain.models import RiskLevel
from relational_fraud_intelligence.settings import AppSettings

# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


class RelationalAIProjection(BaseModel):
    projected_row_count: int
    projected_table_names: list[str]


@dataclass(slots=True)
class GraphInsight:
    """A single finding from the graph analysis layer."""

    category: str  # e.g. "circular-flow", "hub-centrality", "community", "mule-path"
    description: str
    risk_bonus: int = 0  # additional points to add to the base risk score


# ---------------------------------------------------------------------------
# Core reasoner
# ---------------------------------------------------------------------------


class RelationalAIRiskReasoner:
    """Hybrid reasoner: local rules + RelationalAI graph semantics."""

    # Cap the total extra risk that graph analysis can add (prevents runaway scores)
    _MAX_GRAPH_BONUS = 25

    def __init__(self, settings: AppSettings, local_reasoner: RiskReasoner) -> None:
        self._settings = settings
        self._local_reasoner = local_reasoner

    # -- public API ----------------------------------------------------------

    def reason(self, command: ReasonAboutRiskCommand) -> ReasonAboutRiskResult:
        projection = self._project_scenario(command)
        base_result = self._local_reasoner.reason(command)

        # Run the full graph analysis suite
        insights = self._run_graph_analysis(command)

        # Build provider notes from projection + insights
        notes: list[str] = [
            (
                "Projected scenario data through RelationalAI semantics "
                f"({projection.projected_row_count} rows across "
                f"{', '.join(projection.projected_table_names)})."
            ),
        ]

        graph_bonus = 0
        for insight in insights:
            notes.append(f"[{insight.category}] {insight.description}")
            graph_bonus += insight.risk_bonus

        # Cap bonus and compute amplified score
        graph_bonus = min(graph_bonus, self._MAX_GRAPH_BONUS)
        amplified_score = min(100, base_result.total_risk_score + graph_bonus)
        amplified_level = _score_to_level(amplified_score)

        if graph_bonus > 0:
            notes.append(
                f"Graph analysis amplified the risk score by +{graph_bonus} "
                f"({base_result.total_risk_score} → {amplified_score})."
            )

        # Update summary if risk level changed
        summary = base_result.summary
        if amplified_level != base_result.risk_level:
            summary = (
                f"{summary} Graph analysis elevated the risk level from "
                f"{base_result.risk_level.value} to {amplified_level.value}."
            )

        return base_result.model_copy(
            update={
                "requested_provider": "relationalai",
                "active_provider": "hybrid-relationalai",
                "total_risk_score": amplified_score,
                "risk_level": amplified_level,
                "summary": summary,
                "provider_notes": [
                    *notes,
                    *base_result.provider_notes,
                ],
            },
        )

    # -- graph analysis orchestrator -----------------------------------------

    def _run_graph_analysis(self, command: ReasonAboutRiskCommand) -> list[GraphInsight]:
        """Run all graph-based fraud detection queries and collect insights."""
        if not command.scenario.transactions:
            return []

        money_flow = self._build_money_flow_graph(command)
        entity_graph = self._build_entity_graph(command)
        insights: list[GraphInsight] = []

        insights.extend(self._detect_circular_flows(money_flow))
        insights.extend(self._detect_hub_entities(entity_graph))
        insights.extend(self._detect_suspicious_communities(entity_graph, command))
        insights.extend(self._detect_money_mule_paths(money_flow, command))

        return insights

    # -- graph builders ------------------------------------------------------

    @staticmethod
    def _build_money_flow_graph(command: ReasonAboutRiskCommand) -> nx.DiGraph:
        """Directed graph: account → merchant, weighted by total amount."""
        G = nx.DiGraph()
        edge_amounts: dict[tuple[str, str], float] = defaultdict(float)

        for txn in command.scenario.transactions:
            src = f"acct:{txn.account_id}"
            dst = f"merch:{txn.merchant_id}"
            edge_amounts[(src, dst)] += txn.amount

        for (src, dst), total in edge_amounts.items():
            G.add_edge(src, dst, weight=total, txn_count=1)

        return G

    @staticmethod
    def _build_entity_graph(command: ReasonAboutRiskCommand) -> nx.Graph:
        """Undirected graph linking customers, accounts, devices, merchants."""
        G = nx.Graph()

        for customer in command.scenario.customers:
            cnode = f"cust:{customer.customer_id}"
            G.add_node(cnode, kind="customer", label=customer.full_name)
            for aid in customer.linked_account_ids:
                G.add_edge(cnode, f"acct:{aid}", relation="owns")
            for did in customer.linked_device_ids:
                G.add_edge(cnode, f"dev:{did}", relation="uses")

        for device in command.scenario.devices:
            dnode = f"dev:{device.device_id}"
            G.add_node(dnode, kind="device", trust=device.trust_score)
            for cid in device.linked_customer_ids:
                G.add_edge(dnode, f"cust:{cid}", relation="authenticated-from")

        for txn in command.scenario.transactions:
            G.add_edge(
                f"cust:{txn.customer_id}",
                f"merch:{txn.merchant_id}",
                relation="transacts-with",
                weight=txn.amount,
            )

        return G

    # -- analysis queries ----------------------------------------------------

    @staticmethod
    def _detect_circular_flows(money_flow: nx.DiGraph) -> list[GraphInsight]:
        """Detect cycles in the directed money-flow graph.

        Circular flows (A → B → C → A) are a strong indicator of layering
        in money laundering or coordinated bust-out fraud.
        """
        insights: list[GraphInsight] = []

        try:
            cycles = list(nx.simple_cycles(money_flow))
        except Exception:
            return insights

        # Filter to meaningful cycles (length >= 2 nodes)
        meaningful_cycles = [c for c in cycles if len(c) >= 2]

        if not meaningful_cycles:
            return insights

        # Score by cycle length and total money flowing through
        for cycle in meaningful_cycles[:3]:  # report top 3 cycles
            cycle_edges = list(zip(cycle, cycle[1:], strict=False)) + [(cycle[-1], cycle[0])]
            total_flow = sum(
                money_flow.edges[e].get("weight", 0.0)
                for e in cycle_edges
                if money_flow.has_edge(*e)
            )
            node_labels = " → ".join(cycle) + f" → {cycle[0]}"
            bonus = min(12, 4 + len(cycle) * 2)  # longer cycles = more suspicious

            insights.append(
                GraphInsight(
                    category="circular-flow",
                    description=(
                        f"Circular money flow detected: {node_labels}. "
                        f"Total volume in cycle: ${total_flow:,.2f}. "
                        f"This pattern is consistent with layering or round-trip laundering."
                    ),
                    risk_bonus=bonus,
                )
            )

        return insights

    @staticmethod
    def _detect_hub_entities(entity_graph: nx.Graph) -> list[GraphInsight]:
        """Use PageRank to find entities with disproportionate centrality.

        A single entity that dominates the graph is often a facilitator
        (money mule coordinator, shared-device operator, or compromised merchant).
        """
        insights: list[GraphInsight] = []

        if entity_graph.number_of_nodes() < 3:
            return insights

        try:
            pagerank = nx.pagerank(entity_graph, weight="weight")
        except Exception:
            return insights

        sorted_nodes = sorted(pagerank.items(), key=lambda kv: kv[1], reverse=True)
        mean_rank = sum(v for _, v in sorted_nodes) / len(sorted_nodes) if sorted_nodes else 0

        # Also compute mean degree to catch structural hubs
        degrees = {n: entity_graph.degree(n) for n in entity_graph.nodes()}
        mean_degree = sum(degrees.values()) / len(degrees) if degrees else 0

        for node, score in sorted_nodes[:3]:
            degree = degrees.get(node, 0)
            # Flag if PageRank OR degree is disproportionately high
            is_pagerank_hub = score > mean_rank * 1.5
            is_degree_hub = degree > mean_degree * 1.5 and degree >= 3
            if not (is_pagerank_hub or is_degree_hub):
                continue
            kind, entity_id = node.split(":", 1)
            insights.append(
                GraphInsight(
                    category="hub-centrality",
                    description=(
                        f"High-centrality {kind} '{entity_id}' "
                        f"(PageRank={score:.3f}, degree={degree}). "
                        f"This entity connects a disproportionate number of "
                        f"other entities and may be a facilitator or control point."
                    ),
                    risk_bonus=5 if kind in ("dev", "merch") else 3,
                )
            )

        return insights

    @staticmethod
    def _detect_suspicious_communities(
        entity_graph: nx.Graph,
        command: ReasonAboutRiskCommand,
    ) -> list[GraphInsight]:
        """Detect tightly-connected communities that share low-trust devices.

        A community where multiple customers share a device with trust < 0.5
        is a strong indicator of an identity ring.
        """
        insights: list[GraphInsight] = []

        if entity_graph.number_of_nodes() < 4:
            return insights

        try:
            communities = list(nx.community.greedy_modularity_communities(entity_graph))
        except Exception:
            return insights

        if len(communities) <= 1:
            return insights

        # Build a lookup for device trust scores
        device_trust: dict[str, float] = {
            device.device_id: device.trust_score for device in command.scenario.devices
        }

        for i, community in enumerate(communities):
            customers_in_community = [n for n in community if n.startswith("cust:")]
            devices_in_community = [n for n in community if n.startswith("dev:")]

            if len(customers_in_community) < 2 or not devices_in_community:
                continue

            # Check if the shared devices have low trust
            low_trust_devices = [
                d for d in devices_in_community
                if device_trust.get(d.split(":", 1)[1], 1.0) < 0.5
            ]

            if low_trust_devices:
                insights.append(
                    GraphInsight(
                        category="community-ring",
                        description=(
                            f"Community #{i + 1}: {len(customers_in_community)} customers "
                            f"share {len(low_trust_devices)} low-trust device(s). "
                            f"This cluster may represent a synthetic identity ring or "
                            f"coordinated account takeover."
                        ),
                        risk_bonus=8,
                    )
                )

        return insights

    @staticmethod
    def _detect_money_mule_paths(
        money_flow: nx.DiGraph,
        command: ReasonAboutRiskCommand,
    ) -> list[GraphInsight]:
        """Find shortest paths between accounts that suggest mule chains.

        If money flows from account A through intermediaries to account B,
        and the accounts belong to customers in different countries, that is
        a strong cross-border mule indicator.
        """
        insights: list[GraphInsight] = []

        if money_flow.number_of_nodes() < 3:
            return insights

        # Build customer country lookup
        customer_country: dict[str, str] = {
            c.customer_id: c.country_code for c in command.scenario.customers
        }
        # Build account → customer lookup
        account_customer: dict[str, str] = {
            a.account_id: a.customer_id for a in command.scenario.accounts
        }

        account_nodes = [n for n in money_flow.nodes() if n.startswith("acct:")]

        # Check pairs of accounts for indirect paths through merchants
        checked: set[tuple[str, str]] = set()
        for src in account_nodes:
            for dst in account_nodes:
                if src == dst or (src, dst) in checked:
                    continue
                checked.add((src, dst))
                checked.add((dst, src))

                # We need the undirected view to find paths through merchants
                try:
                    path = nx.shortest_path(money_flow.to_undirected(), src, dst)
                except nx.NetworkXNoPath:
                    continue

                if len(path) < 3:
                    continue  # direct edge, not a mule chain

                src_acct_id = src.split(":", 1)[1]
                dst_acct_id = dst.split(":", 1)[1]
                src_cust = account_customer.get(src_acct_id)
                dst_cust = account_customer.get(dst_acct_id)

                if not src_cust or not dst_cust:
                    continue

                src_country = customer_country.get(src_cust, "")
                dst_country = customer_country.get(dst_cust, "")
                is_cross_border = src_country != dst_country and src_country and dst_country

                path_label = " → ".join(path)
                bonus = 6 if is_cross_border else 3

                desc = (
                    f"Indirect money path ({len(path) - 1} hops): {path_label}."
                )
                if is_cross_border:
                    desc += (
                        f" Cross-border flow ({src_country} → {dst_country}) "
                        f"increases money-mule risk."
                    )

                insights.append(
                    GraphInsight(
                        category="mule-path",
                        description=desc,
                        risk_bonus=bonus,
                    )
                )

                if len(insights) >= 3:
                    return insights  # cap to avoid noise

        return insights

    # -- RelationalAI SDK projection (unchanged) -----------------------------

    def _project_scenario(self, command: ReasonAboutRiskCommand) -> RelationalAIProjection:
        config_module = import_module("relationalai.config")
        semantics_module = import_module("relationalai.semantics")
        Config = config_module.Config
        create_config = config_module.create_config
        Model = semantics_module.Model

        if self._settings.relationalai_use_external_config:
            config = create_config()
        else:
            config = Config(
                connections={
                    "local": {"type": "duckdb", "path": self._settings.relationalai_duckdb_path}
                },
                default_connection="local",
                install_mode=True,
            )

        model = Model(name="fraud-projection", config=config)
        transaction_rows = model.data(
            [
                {
                    "transaction_id": transaction.transaction_id,
                    "account_id": transaction.account_id,
                    "device_id": transaction.device_id,
                    "merchant_id": transaction.merchant_id,
                    "amount": transaction.amount,
                }
                for transaction in command.scenario.transactions
            ]
        )
        device_rows = model.data(
            [
                {
                    "device_id": device.device_id,
                    "linked_customer_count": len(device.linked_customer_ids),
                    "trust_score": device.trust_score,
                }
                for device in command.scenario.devices
            ]
        )

        transaction_frame = model.select(
            transaction_rows.transaction_id,
            transaction_rows.account_id,
            transaction_rows.amount,
        ).to_df()
        device_frame = model.select(
            device_rows.device_id,
            device_rows.linked_customer_count,
            device_rows.trust_score,
        ).to_df()

        return RelationalAIProjection(
            projected_row_count=len(transaction_frame) + len(device_frame),
            projected_table_names=["transactions", "devices"],
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _score_to_level(total_risk_score: int) -> RiskLevel:
    if total_risk_score >= 80:
        return RiskLevel.CRITICAL
    if total_risk_score >= 60:
        return RiskLevel.HIGH
    if total_risk_score >= 35:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW
