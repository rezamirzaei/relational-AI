"""Graph analysis engine for fraud relationship networks.

Builds a NetworkX graph from scenario data and computes structural metrics
that amplify or contextualize rule-based risk scores.
"""

from __future__ import annotations

from relational_fraud_intelligence.domain.models import (
    EntityReference,
    EntityType,
    FraudScenario,
    GraphAnalysisResult,
)


def analyze_scenario_graph(scenario: FraudScenario) -> GraphAnalysisResult:
    """Analyze the entity relationship graph of a fraud scenario.

    Uses adjacency lists to compute graph metrics without requiring
    networkx as a dependency. If networkx is available, it will be used
    for more sophisticated analysis.
    """
    try:
        return _analyze_with_networkx(scenario)
    except ImportError:
        return _analyze_basic(scenario)


def _analyze_basic(scenario: FraudScenario) -> GraphAnalysisResult:
    """Basic graph analysis without networkx."""
    adjacency: dict[str, set[str]] = {}

    def _add_edge(a: str, b: str) -> None:
        adjacency.setdefault(a, set()).add(b)
        adjacency.setdefault(b, set()).add(a)

    # Build entity graph
    for customer in scenario.customers:
        node_id = f"customer:{customer.customer_id}"
        adjacency.setdefault(node_id, set())
        for account_id in customer.linked_account_ids:
            _add_edge(node_id, f"account:{account_id}")
        for device_id in customer.linked_device_ids:
            _add_edge(node_id, f"device:{device_id}")

    for txn in scenario.transactions:
        _add_edge(f"customer:{txn.customer_id}", f"merchant:{txn.merchant_id}")
        _add_edge(f"account:{txn.account_id}", f"merchant:{txn.merchant_id}")

    if not adjacency:
        return GraphAnalysisResult(
            connected_components=0,
            density=0.0,
            risk_amplification_factor=1.0,
        )

    # Compute degree centrality
    node_count = len(adjacency)
    edge_count = sum(len(neighbors) for neighbors in adjacency.values()) // 2
    max_edges = node_count * (node_count - 1) / 2 if node_count > 1 else 1
    density = round(edge_count / max_edges, 4) if max_edges > 0 else 0.0

    # Find highest degree node
    highest_node = max(adjacency, key=lambda n: len(adjacency[n]))
    highest_degree = len(adjacency[highest_node])
    entity_type_str, entity_id = highest_node.split(":", 1)
    entity_type_map = {
        "customer": EntityType.CUSTOMER,
        "account": EntityType.ACCOUNT,
        "device": EntityType.DEVICE,
        "merchant": EntityType.MERCHANT,
    }

    # Connected components via BFS
    visited: set[str] = set()
    components = 0
    for node in adjacency:
        if node not in visited:
            components += 1
            queue = [node]
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                queue.extend(adjacency.get(current, set()) - visited)

    # Hub detection: nodes with degree > average + 1 std dev
    degrees = [len(neighbors) for neighbors in adjacency.values()]
    avg_degree = sum(degrees) / len(degrees) if degrees else 0
    variance = sum((d - avg_degree) ** 2 for d in degrees) / len(degrees) if degrees else 0
    std_dev = variance**0.5
    hub_threshold = avg_degree + std_dev

    hub_entities: list[EntityReference] = []
    for node, neighbors in adjacency.items():
        if len(neighbors) > hub_threshold:
            parts = node.split(":", 1)
            if parts[0] in entity_type_map:
                hub_entities.append(
                    EntityReference(
                        entity_type=entity_type_map[parts[0]],
                        entity_id=parts[1],
                        display_name=parts[1],
                    )
                )

    # Risk amplification based on graph density and hub concentration
    amplification = 1.0 + (density * 0.5) + (len(hub_entities) * 0.1)
    amplification = round(min(amplification, 2.0), 2)

    return GraphAnalysisResult(
        connected_components=components,
        density=density,
        highest_degree_entity=EntityReference(
            entity_type=entity_type_map.get(entity_type_str, EntityType.CUSTOMER),
            entity_id=entity_id,
            display_name=entity_id,
        ),
        highest_degree_score=highest_degree,
        community_count=components,
        hub_entities=hub_entities[:5],
        risk_amplification_factor=amplification,
    )


def _analyze_with_networkx(scenario: FraudScenario) -> GraphAnalysisResult:
    """Enhanced graph analysis using networkx."""
    import networkx as nx  # type: ignore[import-untyped]

    G = nx.Graph()

    entity_type_map = {
        "customer": EntityType.CUSTOMER,
        "account": EntityType.ACCOUNT,
        "device": EntityType.DEVICE,
        "merchant": EntityType.MERCHANT,
    }

    # Add nodes and edges
    for customer in scenario.customers:
        node = f"customer:{customer.customer_id}"
        G.add_node(node, entity_type="customer", label=customer.full_name)
        for account_id in customer.linked_account_ids:
            G.add_edge(node, f"account:{account_id}", relation="owns")
        for device_id in customer.linked_device_ids:
            G.add_edge(node, f"device:{device_id}", relation="uses")

    for txn in scenario.transactions:
        G.add_edge(
            f"customer:{txn.customer_id}",
            f"merchant:{txn.merchant_id}",
            relation="transacts-with",
        )

    if G.number_of_nodes() == 0:
        return GraphAnalysisResult(
            connected_components=0,
            density=0.0,
            risk_amplification_factor=1.0,
        )

    components = nx.number_connected_components(G)
    density = round(nx.density(G), 4)

    # Degree centrality
    degree_centrality = nx.degree_centrality(G)
    highest_node = max(degree_centrality, key=degree_centrality.get)
    highest_degree = G.degree(highest_node)
    parts = highest_node.split(":", 1)

    # Community detection
    try:
        communities = list(nx.community.greedy_modularity_communities(G))
        community_count = len(communities)
    except Exception:
        community_count = components

    # Hub entities (top 5 by degree)
    sorted_nodes = sorted(G.nodes(), key=lambda n: G.degree(n), reverse=True)
    hub_entities: list[EntityReference] = []
    for node in sorted_nodes[:5]:
        node_parts = node.split(":", 1)
        if node_parts[0] in entity_type_map:
            label = G.nodes[node].get("label", node_parts[1])
            hub_entities.append(
                EntityReference(
                    entity_type=entity_type_map[node_parts[0]],
                    entity_id=node_parts[1],
                    display_name=label,
                )
            )

    amplification = 1.0 + (density * 0.5) + (len(hub_entities) * 0.1)
    amplification = round(min(amplification, 2.0), 2)

    return GraphAnalysisResult(
        connected_components=components,
        density=density,
        highest_degree_entity=EntityReference(
            entity_type=entity_type_map.get(parts[0], EntityType.CUSTOMER),
            entity_id=parts[1],
            display_name=G.nodes[highest_node].get("label", parts[1]),
        ),
        highest_degree_score=highest_degree,
        community_count=community_count,
        hub_entities=hub_entities,
        risk_amplification_factor=amplification,
    )
