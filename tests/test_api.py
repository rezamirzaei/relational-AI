from fastapi.testclient import TestClient

from relational_fraud_intelligence.app import create_app


def test_list_scenarios_returns_seed_data() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/scenarios")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["scenarios"]) >= 2


def test_investigate_scenario_returns_case_payload() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/investigations",
        json={"scenario_id": "travel-ato-escalation"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["investigation"]["scenario"]["scenario_id"] == "travel-ato-escalation"
    assert payload["investigation"]["provider_summary"]["active_text_provider"] == "keyword"
